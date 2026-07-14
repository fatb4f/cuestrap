"""Closed classification and phase policy for Codex-supported tool hooks."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from .models import Classification, SupervisorState, digest_json

_GIT_READ_TOOLS = {
    "git_diff",
    "git_diff_staged",
    "git_diff_unstaged",
    "git_list_repositories",
    "git_log",
    "git_show",
    "git_status",
}
_CODE_MODE_OPERATIONS = {
    "resolve-session": "code-mode-read",
    "capture-state": "code-mode-read",
    "run-focused-probe": "code-mode-probe",
    "apply-cell-transaction": "code-mode-mutation",
}
_GIT_MUTATION = re.compile(
    r"(?:^|[;&|]\s*)git\s+(?:add|am|apply|branch\s+-[dD]|checkout|cherry-pick|clean|commit|"
    r"merge|mv|pull|push|rebase|reset|restore|revert|rm|stash|switch|tag)(?:\s|$)"
)
_WORKSPACE_MUTATION = re.compile(
    r"(?:^|[;&|]\s*)(?:rm|mv|cp|mkdir|touch|truncate|install)\s|"
    r"\bsed\s+-i(?:\s|$)|\bperl\s+-pi(?:\s|$)|\btee(?:\s|$)|"
    r"(?:^|[^<])>>?\s*(?!/dev/null\b|/tmp/)"
)
_EVALUATION = re.compile(
    r"\b(?:cue\s+(?:vet|eval|export)|go\s+test|python(?:3)?\s+-m\s+(?:unittest|pytest)|"
    r"workbook_cli\.py\s+--validate|workbook_cli\.py\s+--probe-request)\b"
)
_READ_ONLY = re.compile(
    r"^(?:\s*(?:rg|ls|stat|ss|head|tail|wc|jq|command\s+-v|sed\s+-n|git\s+"
    r"(?:status|diff|show|log|rev-parse|ls-files)|cue\s+fmt\s+--check)\b)"
)
_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(?:sk|rk|pk)-[A-Za-z0-9_-]{20,}\b"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]\s*['\"]?[^\s'\"]+"
    ),
)


def contains_credential_material(value: object) -> bool:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, default=repr)
    return any(pattern.search(encoded) is not None for pattern in _SECRET_PATTERNS)


def _command(tool_input: object) -> str:
    if not isinstance(tool_input, dict):
        return ""
    value = tool_input.get("command", tool_input.get("cmd", ""))
    return value if isinstance(value, str) else ""


def classify_tool(tool_name: str, tool_input: object) -> Classification:
    lowered = tool_name.lower()
    if lowered == "apply_patch":
        return Classification(tool_class="workspace-mutation", mutating=True)
    if lowered.startswith("mcp__marimo_code_mode__"):
        return Classification(tool_class="direct-code-mode")
    if lowered.startswith("mcp__git_mcp_server__"):
        operation = lowered.rsplit("__", 1)[-1]
        if operation in _GIT_READ_TOOLS:
            return Classification(tool_class="read-only", operation=operation)
        return Classification(tool_class="git-mutation", operation=operation, mutating=True)
    if lowered.startswith(("mcp__cue_lsp__", "mcp__gopls__")):
        return Classification(tool_class="read-only")
    if lowered.startswith("mcp__"):
        return Classification(tool_class="external-mcp")

    command = _command(tool_input)
    if not command:
        return Classification(tool_class="unknown")
    if "cuestrap_tool_supervisor.py" in command and re.search(
        r"\b(?:set-phase|reset-state|clear-quarantine)\b", command
    ):
        return Classification(tool_class="supervisor-control")
    if "127.0.0.1:2718/mcp/server" in command or "mcp__marimo_code_mode__" in command:
        return Classification(tool_class="direct-code-mode")
    if "code_mode_client.py" in command:
        for operation, tool_class in _CODE_MODE_OPERATIONS.items():
            if re.search(rf"(?:^|\s){re.escape(operation)}(?:\s|$)", command):
                return Classification(
                    tool_class=tool_class,
                    operation=operation,
                    mutating=tool_class == "code-mode-mutation",
                    evaluation=tool_class == "code-mode-probe",
                )
        return Classification(tool_class="unknown")
    if _GIT_MUTATION.search(command):
        return Classification(tool_class="git-mutation", mutating=True)
    if _WORKSPACE_MUTATION.search(command):
        return Classification(tool_class="workspace-mutation", mutating=True)
    if _EVALUATION.search(command):
        return Classification(tool_class="evaluation", evaluation=True)
    if _READ_ONLY.search(command):
        return Classification(tool_class="read-only")
    return Classification(tool_class="unknown")


def fingerprint(
    phase: str,
    request_digest: str,
    repository_state_digest: str,
) -> str:
    return digest_json(
        {
            "phase": phase,
            "requestDigest": request_digest,
            "repositoryStateDigest": repository_state_digest,
        }
    )


def decide(
    state: SupervisorState,
    classification: Classification,
    *,
    request_digest: str,
    repository_state_digest: str,
) -> tuple[bool, str]:
    tool_class = classification.tool_class
    if tool_class == "supervisor-control":
        return False, "supervisor control transitions require an operator terminal"
    if tool_class == "direct-code-mode":
        return False, "direct Marimo MCP access bypasses the constrained client"
    if tool_class == "git-mutation":
        return False, "Git mutation is outside the bootstrap supervisory phase model"
    if tool_class == "external-mcp":
        return False, "external MCP tool is not in the closed bootstrap tool set"
    if tool_class == "unknown":
        return False, "tool call could not be classified under the closed bootstrap policy"

    failed = fingerprint(state.phase, request_digest, repository_state_digest)
    if failed in state.failed_fingerprints:
        return False, "equivalent tool call already reported an error against this repository state"

    if state.quarantined:
        if tool_class == "read-only":
            return True, "read-only diagnosis is permitted while quarantined"
        if tool_class == "code-mode-read" and classification.operation == "capture-state":
            return True, "fresh constrained state capture is permitted while quarantined"
        return False, "supervisory state is quarantined; capture fresh state before effects"

    allowed = {
        "inspect": {"read-only", "code-mode-read"},
        "probe": {"read-only", "code-mode-read", "code-mode-probe"},
        "implement": {"read-only", "code-mode-read", "workspace-mutation", "code-mode-mutation"},
        "evaluate": {"read-only", "code-mode-read", "code-mode-probe", "evaluation"},
        "collect-evidence": {"read-only", "code-mode-read"},
    }[state.phase]
    if tool_class not in allowed:
        return False, f"tool class {tool_class} is not permitted in phase {state.phase}"
    if classification.mutating and state.mutation_requires_evaluation:
        return False, "another mutation requires a recorded evaluation observation"
    return True, f"tool class {tool_class} is permitted in phase {state.phase}"


def response_reported_error(value: object) -> bool:
    if isinstance(value, dict):
        for key in ("isError", "is_error"):
            if value.get(key) is True:
                return True
        for key in ("exit_code", "exitCode", "status_code", "statusCode"):
            code = value.get(key)
            if isinstance(code, int) and code != 0:
                return True
        if value.get("success") is False:
            return True
        return any(response_reported_error(item) for item in value.values())
    if isinstance(value, list):
        return any(response_reported_error(item) for item in value)
    return False


def repository_state_digest(repository_root: Path) -> str:
    def git(*arguments: str) -> bytes:
        result = subprocess.run(
            ["git", *arguments],
            cwd=repository_root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        return result.stdout

    head = git("rev-parse", "HEAD").strip() or b"unborn"
    raw = git("diff", "--raw", "HEAD", "--")
    names = set(
        filter(
            None,
            git("diff", "--name-only", "-z", "HEAD", "--").decode(errors="surrogateescape").split("\0"),
        )
    )
    names.update(
        filter(
            None,
            git("ls-files", "--others", "--exclude-standard", "-z")
            .decode(errors="surrogateescape")
            .split("\0"),
        )
    )
    files: dict[str, str] = {}
    for name in sorted(names):
        path = repository_root / name
        if path.is_file():
            files[name] = f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"
        else:
            files[name] = "absent"
    return digest_json(
        {
            "head": head.decode(errors="replace"),
            "rawDiffDigest": f"sha256:{hashlib.sha256(raw).hexdigest()}",
            "changedFiles": files,
        }
    )
