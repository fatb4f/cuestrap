"""Whitelist recognition, pure anti-churn decisions, and evidence reduction."""
from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import shlex
import subprocess
from pathlib import Path

from .models import (
    ArtifactRole,
    Budgets,
    CanonicalOperation,
    Classification,
    CompletedOperation,
    Decision,
    DenialReason,
    Guidance,
    LedgerProjection,
    ObservationChannel,
    ObservationSummary,
    ObservedResult,
    PostObservationRecord,
    ProgressEvidence,
    ReducerResult,
    Scope,
    TargetID,
    digest_json,
)

DENIAL_PRECEDENCE: tuple[DenialReason, ...] = (
    "protected-artifact-mutation",
    "mixed-candidate-state",
    "wrong-observation-channel",
    "identical-retry",
    "failure-cluster-exhausted",
    "fanout-budget-exceeded",
    "phase-invalid-churn",
)

_GIT_READ_TOOLS = {
    "git_diff",
    "git_diff_staged",
    "git_diff_unstaged",
    "git_list_repositories",
    "git_log",
    "git_show",
    "git_status",
}
_GIT_READ_SUBCOMMANDS = {"diff", "log", "show", "status", "rev-parse", "ls-files"}
_GIT_MUTATION_SUBCOMMANDS = {
    "add",
    "am",
    "apply",
    "branch",
    "checkout",
    "cherry-pick",
    "clean",
    "commit",
    "merge",
    "mv",
    "pull",
    "push",
    "rebase",
    "reset",
    "restore",
    "revert",
    "rm",
    "stash",
    "switch",
    "tag",
}
_READ_COMMANDS = {"rg", "ls", "stat", "ss", "head", "tail", "wc", "jq", "sed"}
_WORKSPACE_MUTATIONS = {"rm", "mv", "cp", "mkdir", "touch", "truncate", "install", "tee"}
_PATCH_PATH = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", re.MULTILINE)


def _command(tool_input: object) -> str:
    if not isinstance(tool_input, dict):
        return ""
    value = tool_input.get("command", tool_input.get("cmd", ""))
    return value if isinstance(value, str) else ""


def _patch_text(tool_input: object) -> str:
    if isinstance(tool_input, str):
        return tool_input
    if not isinstance(tool_input, dict):
        return ""
    for key in ("patch", "input", "command"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
    return ""


def _artifact_role(path: str) -> ArtifactRole:
    normalized = path.replace("\\", "/").strip()
    parts = tuple(part for part in normalized.split("/") if part not in ("", "."))
    if Path(normalized).is_absolute() or ".." in parts:
        return "protected"
    if any(part in {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache"} for part in parts):
        return "runtime-state"
    if "generated" in parts or any(part.endswith((".generated", ".min.js", ".map")) for part in parts):
        return "generated"
    if any(part in {"secrets", "credentials"} for part in parts) or any(
        part.endswith((".pem", ".key")) for part in parts
    ):
        return "protected"
    return "owned" if normalized else "unclassified"


def _normalize_paths(
    paths: tuple[str, ...], repository_root: Path | None
) -> tuple[str, ...]:
    if repository_root is None:
        return paths
    root = repository_root.resolve()
    normalized: list[str] = []
    for value in paths:
        candidate = Path(value)
        if candidate.is_absolute():
            try:
                value = candidate.resolve(strict=False).relative_to(root).as_posix()
            except ValueError:
                pass
        normalized.append(value)
    return tuple(normalized)


def _canonical_operation(
    target_id: TargetID,
    operation_class: str,
    canonical_request: object,
    *,
    mutating: bool = False,
    target_paths: tuple[str, ...] = (),
    observation_channel: ObservationChannel,
    fanout: int = 1,
) -> Classification:
    return Classification(
        recognized=True,
        operation=CanonicalOperation(
            target_id=target_id,
            operation_class=operation_class,
            request_digest=digest_json(canonical_request),
            mutating=mutating,
            target_paths=target_paths,
            artifact_roles=tuple(_artifact_role(path) for path in target_paths),
            observation_channel=observation_channel,
            fanout=fanout,
        ),
    )


def _unknown() -> Classification:
    return Classification(recognized=False)


def _tokens(command: str) -> tuple[str, ...] | None:
    if not command.strip() or re.search(r"(?:&&|\|\||[;\n])", command):
        return None
    try:
        return tuple(shlex.split(command))
    except ValueError:
        return None


def _contains_sequence(tokens: tuple[str, ...], sequence: tuple[str, ...]) -> bool:
    width = len(sequence)
    return any(tokens[index : index + width] == sequence for index in range(len(tokens) - width + 1))


def _shell_target_paths(tokens: tuple[str, ...]) -> tuple[str, ...]:
    candidates = [token for token in tokens[1:] if token and not token.startswith("-")]
    return tuple(candidates)


def classify_tool(
    tool_name: str,
    tool_input: object,
    *,
    repository_root: Path | None = None,
) -> Classification:
    """Return one canonical whitelist operation or an unrecognized classification."""
    lowered = tool_name.lower()
    if lowered == "apply_patch":
        patch = _patch_text(tool_input)
        paths = _normalize_paths(tuple(_PATCH_PATH.findall(patch)), repository_root)
        normalized = tuple(line.rstrip() for line in patch.splitlines())
        return _canonical_operation(
            "workspace.apply-patch",
            "mutation",
            {"target": "workspace.apply-patch", "patch": normalized},
            mutating=True,
            target_paths=paths,
            observation_channel="static-source",
        )
    if lowered.startswith("mcp__git_mcp_server__"):
        name = lowered.rsplit("__", 1)[-1]
        target: TargetID = "git.read" if name in _GIT_READ_TOOLS else "git.mutation"
        return _canonical_operation(
            target,
            "read" if target == "git.read" else "mutation",
            {"target": target, "operation": name, "input": tool_input},
            mutating=target == "git.mutation",
            observation_channel="static-source",
            fanout=32 if name.startswith("git_diff") else 1,
        )
    if lowered.startswith("mcp__cue_lsp__"):
        return _canonical_operation(
            "cue.lsp",
            "read",
            {"target": "cue.lsp", "tool": lowered, "input": tool_input},
            observation_channel="lsp",
        )
    if lowered.startswith("mcp__gopls__"):
        return _canonical_operation(
            "gopls.read",
            "read",
            {"target": "gopls.read", "tool": lowered, "input": tool_input},
            observation_channel="lsp",
        )
    if lowered.startswith("mcp__"):
        return _unknown()

    command = _command(tool_input)
    tokens = _tokens(command)
    if not tokens:
        return _unknown()

    if "cuestrap_tool_supervisor.py" in command and any(
        token in {"set-phase", "set-scope"} for token in tokens
    ):
        return _canonical_operation(
            "supervisor.transition",
            "transition",
            {"target": "supervisor.transition", "tokens": tokens},
            observation_channel="control",
        )

    if "code_mode_client.py" in command:
        code_mode = {
            "resolve-session": ("code-mode.resolve-session", "read"),
            "capture-state": ("code-mode.capture-state", "read"),
            "run-focused-probe": ("code-mode.run-focused-probe", "probe"),
            "apply-cell-transaction": ("code-mode.apply-cell-transaction", "mutation"),
        }
        for name, (target, operation_class) in code_mode.items():
            if name in tokens:
                return _canonical_operation(
                    target,
                    operation_class,
                    {"target": target, "tokens": tokens},
                    mutating=operation_class == "mutation",
                    observation_channel="code-mode",
                )
        return _unknown()

    executable = Path(tokens[0]).name
    if executable == "just":
        if tokens == ("just", "--fmt", "--check"):
            return _canonical_operation(
                "just.check",
                "evaluation",
                {"target": "just.check", "justfile": "justfile"},
                observation_channel="static-source",
            )
        action_flags = [flag for flag in ("--list", "--summary", "--dump") if flag in tokens]
        if len(action_flags) != 1:
            return _unknown()
        action = action_flags[0][2:]
        target = f"just.{action}"
        paths: tuple[str, ...] = ()
        if "--justfile" in tokens:
            index = tokens.index("--justfile")
            if index + 1 >= len(tokens):
                return _unknown()
            paths = _normalize_paths((tokens[index + 1],), repository_root)
        allowed = {"just", action_flags[0], "--justfile", *paths}
        if any(token not in allowed for token in tokens):
            return _unknown()
        return _canonical_operation(
            target,
            "evaluation",
            {"target": target, "justfile": paths[0] if paths else "justfile"},
            target_paths=paths,
            observation_channel="static-source",
        )

    if executable == "git" and len(tokens) > 1:
        subcommand = tokens[1]
        if subcommand in _GIT_READ_SUBCOMMANDS:
            return _canonical_operation(
                "git.read",
                "read",
                {"target": "git.read", "tokens": tokens},
                observation_channel="static-source",
                fanout=32 if subcommand == "diff" else 1,
            )
        if subcommand in _GIT_MUTATION_SUBCOMMANDS:
            return _canonical_operation(
                "git.mutation",
                "mutation",
                {"target": "git.mutation", "tokens": tokens},
                mutating=True,
                target_paths=_normalize_paths(
                    _shell_target_paths(tokens[1:]), repository_root
                ),
                observation_channel="static-source",
            )

    if (
        (executable in _READ_COMMANDS and not (executable == "sed" and "-i" in tokens))
        or tokens[:2] == ("command", "-v")
    ):
        fanout = 128 if executable == "rg" and "--files" in tokens else 1
        return _canonical_operation(
            "shell.read",
            "read",
            {"target": "shell.read", "tokens": tokens},
            observation_channel="static-source",
            fanout=fanout,
        )

    evaluation: tuple[TargetID, tuple[str, ...]] | None = None
    for target, sequence in (
        ("evaluation.cue", ("cue", "vet")),
        ("evaluation.cue", ("cue", "eval")),
        ("evaluation.cue", ("cue", "export")),
        ("evaluation.python", ("python", "-m", "unittest")),
        ("evaluation.python", ("python", "-m", "pytest")),
        ("evaluation.python", ("python3", "-m", "unittest")),
        ("evaluation.go", ("go", "test")),
    ):
        if _contains_sequence(tokens, sequence):
            evaluation = (target, sequence)
            break
    if evaluation is not None:
        target, _ = evaluation
        return _canonical_operation(
            target,
            "evaluation",
            {"target": target, "tokens": tokens},
            observation_channel="native-evaluation",
        )
    if "workbook_cli.py" in command and any(
        flag in tokens for flag in ("--validate", "--probe-request")
    ):
        return _canonical_operation(
            "evaluation.workbook",
            "evaluation",
            {"target": "evaluation.workbook", "tokens": tokens},
            observation_channel="runtime",
        )

    if executable in _WORKSPACE_MUTATIONS or (executable == "sed" and "-i" in tokens):
        paths = _normalize_paths(_shell_target_paths(tokens), repository_root)
        return _canonical_operation(
            "workspace.mutation",
            "mutation",
            {"target": "workspace.mutation", "tokens": tokens},
            mutating=True,
            target_paths=paths,
            observation_channel="static-source",
        )
    return _unknown()


def _path_owned(path: str, owned_paths: tuple[str, ...]) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    if not normalized or Path(path).is_absolute() or ".." in normalized.split("/"):
        return False
    for pattern in owned_paths:
        normalized_pattern = pattern.replace("\\", "/").lstrip("./")
        if normalized == normalized_pattern or fnmatch.fnmatchcase(normalized, normalized_pattern):
            return True
        if normalized_pattern.endswith("/**") and normalized.startswith(normalized_pattern[:-3] + "/"):
            return True
    return False


def _matched_denials(
    scope: Scope,
    operation: CanonicalOperation,
    ledger: LedgerProjection,
    budgets: Budgets,
) -> tuple[DenialReason, ...]:
    matches: set[DenialReason] = set()
    if operation.mutating and any(
        role in {"protected", "generated", "runtime-state"} for role in operation.artifact_roles
    ):
        matches.add("protected-artifact-mutation")
    if (
        scope.activity in {"evaluate", "collect-evidence"}
        and ledger.active_candidate_digest is not None
        and operation.candidate_digest is not None
        and ledger.active_candidate_digest != operation.candidate_digest
    ):
        matches.add("mixed-candidate-state")
    if (
        ledger.required_observation_channel is not None
        and ledger.required_observation_channel != operation.observation_channel
    ):
        matches.add("wrong-observation-channel")
    if any(
        observation.target_id == operation.target_id
        and observation.request_digest == operation.request_digest
        and observation.relevant_state_digest == operation.candidate_digest
        for observation in ledger.observations
    ):
        matches.add("identical-retry")
    if ledger.active_failure_signature is not None:
        corrections = {
            (item.request_digest, item.relevant_state_digest, item.candidate_digest)
            for item in ledger.observations
            if item.target_id == operation.target_id
            and item.failure_signature == ledger.active_failure_signature
        }
        current = (operation.request_digest, operation.candidate_digest, operation.candidate_digest)
        if (
            len(corrections) >= budgets.maximum_failure_cluster_corrections
            and current not in corrections
        ):
            matches.add("failure-cluster-exhausted")
    if operation.fanout > budgets.maximum_observation_fanout:
        matches.add("fanout-budget-exceeded")
    if operation.target_id not in scope.allowed_targets:
        matches.add("phase-invalid-churn")
    if operation.mutating and (
        not operation.target_paths
        or not scope.owned_paths
        or any(not _path_owned(path, scope.owned_paths) for path in operation.target_paths)
    ):
        matches.add("phase-invalid-churn")
    if operation.target_paths and any(
        Path(path).is_absolute() or ".." in path.replace("\\", "/").split("/")
        for path in operation.target_paths
    ):
        matches.add("phase-invalid-churn")
    return tuple(reason for reason in DENIAL_PRECEDENCE if reason in matches)


def decide(
    scope: Scope,
    operation: CanonicalOperation,
    ledger: LedgerProjection,
    budgets: Budgets,
) -> Decision:
    """Pure, replayable decision function with deterministic denial precedence."""
    if operation.target_id == "supervisor.transition":
        return Decision(action="approve", reason="phase-relevant")
    matched = _matched_denials(scope, operation, ledger, budgets)
    if matched:
        primary = matched[0]
        guidance = Guidance(
            retry_requires_any=(
                "request-change",
                "relevant-state-change",
                "candidate-change",
                "phase-transition",
            ),
            recommended_targets=scope.allowed_targets,
        )
        return Decision(action="deny", reason=primary, matched_predicates=matched, guidance=guidance)

    prior = [item for item in ledger.observations if item.target_id == operation.target_id]
    if prior:
        latest = prior[-1]
        changed = (
            latest.request_digest != operation.request_digest
            or latest.relevant_state_digest != operation.candidate_digest
            or latest.candidate_digest != operation.candidate_digest
        )
        reason = "bounded-correction" if changed and latest.failure_signature else "new-observation"
    else:
        reason = "phase-relevant"
    return Decision(action="approve", reason=reason)


def unknown_decision() -> Decision:
    return Decision(action="approve", reason="unknown-operation")


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


def normalize_result(value: object) -> ObservedResult:
    reported_error = response_reported_error(value)
    result_class = "reported-error" if reported_error else "returned"
    if isinstance(value, dict):
        for key in ("exit_code", "exitCode", "status_code", "statusCode"):
            code = value.get(key)
            if isinstance(code, int):
                result_class = f"exit-code:{code}"
                break
    return ObservedResult(
        outcome="reported-error" if reported_error else "returned",
        result_class=result_class,
        result_digest=digest_json(
            {
                "outcome": "reported-error" if reported_error else "returned",
                "resultClass": result_class,
            }
        ),
        required_observation_channel=_extract_observation_channel(value),
        resolved_question_ids=_extract_question_ids(value, "resolvedQuestionIDs"),
        introduced_question_ids=_extract_question_ids(value, "introducedQuestionIDs"),
    )


def _extract_observation_channel(value: object) -> ObservationChannel | None:
    allowed = {
        "static-source",
        "runtime",
        "lsp",
        "native-evaluation",
        "code-mode",
        "control",
    }
    if isinstance(value, dict):
        candidate = value.get("requiredObservationChannel")
        if isinstance(candidate, str) and candidate in allowed:
            return candidate
        for item in value.values():
            found = _extract_observation_channel(item)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _extract_observation_channel(item)
            if found is not None:
                return found
    return None


def _extract_question_ids(value: object, key: str) -> tuple[str, ...]:
    if isinstance(value, dict):
        candidate = value.get(key)
        if isinstance(candidate, list) and all(
            isinstance(item, str) and item for item in candidate
        ):
            return tuple(dict.fromkeys(candidate))
        for item in value.values():
            found = _extract_question_ids(item, key)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _extract_question_ids(item, key)
            if found:
                return found
    return ()


def _failure_signature(completed: CompletedOperation, observed: ObservedResult) -> str | None:
    if observed.outcome != "reported-error":
        return None
    return digest_json(
        {
            "operationClass": completed.operation.operation_class,
            "activity": completed.scope.activity,
            "surface": completed.scope.surface,
            "target": completed.operation.target_id,
            "errorClass": observed.result_class,
            "sourceDigest": completed.relevant_state_digest,
        }
    )


def reduce_observation(
    ledger: LedgerProjection,
    completed: CompletedOperation,
    observed: ObservedResult,
) -> ReducerResult:
    """Pure post-hook reducer; no clock, filesystem, environment, or ledger access."""
    previous = [
        item for item in ledger.observations if item.target_id == completed.operation.target_id
    ]
    latest = previous[-1] if previous else None
    failure_signature = _failure_signature(completed, observed)
    resolved_from_operation = (
        tuple(
            question
            for question in completed.operation.question_ids
            if question in ledger.unresolved_question_ids
        )
        if observed.outcome == "returned"
        else ()
    )
    resolved = tuple(
        dict.fromkeys((*resolved_from_operation, *observed.resolved_question_ids))
    )
    progress = ProgressEvidence(
        request_changed=latest is None or latest.request_digest != completed.operation.request_digest,
        result_changed=latest is None or latest.result_digest != observed.result_digest,
        relevant_state_changed=(
            latest is None or latest.relevant_state_digest != completed.relevant_state_digest
        ),
        candidate_changed=(
            latest is None or latest.candidate_digest != completed.operation.candidate_digest
        ),
        resolved_question_ids=resolved,
        introduced_question_ids=observed.introduced_question_ids,
    )
    guidance = None
    evidence_status = "observation-recorded"
    if observed.outcome == "reported-error":
        evidence_status = "failure-observed"
        guidance = Guidance(
            retry_requires_any=(
                "request-change",
                "relevant-state-change",
                "candidate-change",
                "phase-transition",
            ),
            recommended_targets=completed.scope.allowed_targets,
        )
    observation = ObservationSummary(
        target_id=completed.operation.target_id,
        activity=completed.scope.activity,
        request_digest=completed.operation.request_digest,
        relevant_state_digest=completed.relevant_state_digest,
        result_digest=observed.result_digest,
        candidate_digest=completed.operation.candidate_digest,
        failure_signature=failure_signature,
        required_observation_channel=observed.required_observation_channel,
        outcome=observed.outcome,
    )
    return ReducerResult(
        observation=observation,
        progress=progress,
        evidence_status=evidence_status,
        guidance=guidance,
    )


def project_evidence(records: list[dict[str, object]]) -> LedgerProjection:
    """Project only v2 completed observations; v1 evidence remains preserved but inert."""
    observations: list[ObservationSummary] = []
    unresolved_questions: list[str] = []
    required_channel: ObservationChannel | None = None
    for raw in records:
        if raw.get("schemaVersion") != "supervisory-evidence/v2":
            continue
        if raw.get("kind") != "post-observation":
            continue
        record = PostObservationRecord.model_validate(raw)
        observations.append(
            ObservationSummary(
                target_id=record.target_id,
                activity=record.scope.activity,
                request_digest=record.request_digest,
                relevant_state_digest=record.relevant_state_digest,
                result_digest=record.result_digest,
                candidate_digest=record.candidate_digest,
                failure_signature=record.failure_signature,
                required_observation_channel=record.required_observation_channel,
                outcome=record.outcome,
            )
        )
        resolved = set(record.progress.resolved_question_ids)
        unresolved_questions = [item for item in unresolved_questions if item not in resolved]
        for question in record.progress.introduced_question_ids:
            if question not in unresolved_questions:
                unresolved_questions.append(question)
        if record.required_observation_channel is not None:
            required_channel = record.required_observation_channel
        elif not unresolved_questions:
            required_channel = None
    latest = observations[-1] if observations else None
    latest_failure = latest.failure_signature if latest is not None else None
    return LedgerProjection(
        observations=tuple(observations),
        active_candidate_digest=latest.candidate_digest if latest else None,
        active_failure_signature=latest_failure,
        required_observation_channel=required_channel,
        unresolved_question_ids=tuple(unresolved_questions),
    )


def repository_state_digest(
    repository_root: Path,
    relevant_paths: tuple[str, ...] = (),
) -> str:
    """Compute the relevant candidate digest outside the pure decision boundary."""
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
            git("diff", "--name-only", "-z", "HEAD", "--")
            .decode(errors="surrogateescape")
            .split("\0"),
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
    if relevant_paths:
        candidates = set(
            filter(
                None,
                git("ls-files", "-z").decode(errors="surrogateescape").split("\0"),
            )
        ) | names
        selected = {
            name
            for name in candidates
            if any(_path_owned(name, (pattern,)) for pattern in relevant_paths)
        }
        selected.update(
            path
            for path in relevant_paths
            if not any(character in path for character in "*?[")
            and not Path(path).is_absolute()
        )
        names = selected

    files: dict[str, str] = {}
    for name in sorted(names):
        path = repository_root / name
        files[name] = (
            f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"
            if path.is_file()
            else "absent"
        )
    return digest_json(
        {
            "head": head.decode(errors="replace") if not relevant_paths else None,
            "rawDiffDigest": (
                f"sha256:{hashlib.sha256(raw).hexdigest()}" if not relevant_paths else None
            ),
            "relevantPaths": relevant_paths,
            "changedFiles": files,
        }
    )
