"""Closed execution transport shared by Bash, tool_exec, and controller routing."""
from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from bootstrap_client.admission import CodeModeAdmissionContract

from .models import Classification, TargetID
from .policy import (
    _GIT_MUTATION_SUBCOMMANDS,
    _GIT_READ_SUBCOMMANDS,
    _READ_COMMANDS,
    _WORKSPACE_MUTATIONS,
    _canonical_operation,
    _contains_sequence,
    _normalize_paths,
    _shell_target_paths,
)

ExecutionTool = Literal["bash", "tool_exec"]
_COMMAND_FIELDS = ("argv", "command", "cmd")
_SHELL_PUNCTUATION = frozenset("();&|<>")
_WORKBOOK_CODE_MODE_ACTIONS = frozenset(
    {
        "resolve-session",
        "capture-state",
        "run-focused-probe",
        "apply-cell-transaction",
    }
)
_CODE_MODE_OPTIONS = frozenset(
    {"--endpoint", "--repository-root", "--run-binding", "--session-binding"}
)


@dataclass(frozen=True)
class ExecutionInvocation:
    """One shell-free argv invocation plus the input shape used by the tool."""

    tool: ExecutionTool
    argv: tuple[str, ...]
    command_field: str
    command_is_string: bool
    original_input: dict[str, object]


def _has_unquoted_shell_semantics(command: str) -> bool:
    quote: str | None = None
    escaped = False
    at_word_start = True
    for character in command:
        if escaped:
            escaped = False
            at_word_start = False
            continue
        if quote == "'":
            if character == "'":
                quote = None
            continue
        if quote == '"':
            if character == '"':
                quote = None
            elif character == "\\":
                escaped = True
            elif character in {"$", "`"}:
                return True
            continue
        if character in {"'", '"'}:
            quote = character
            at_word_start = False
            continue
        if character == "\\":
            escaped = True
            continue
        if character.isspace():
            at_word_start = True
            continue
        if character in _SHELL_PUNCTUATION:
            return True
        if character in {"*", "?", "[", "{", "}", "`", "$"}:
            return True
        if character == "#" and at_word_start:
            return True
        if character == "~":
            return True
        at_word_start = False
    return escaped or quote is not None


def strict_shell_tokens(command: str) -> tuple[str, ...] | None:
    """Return argv only when shell parsing and direct exec have identical meaning."""
    if not command.strip() or "\n" in command or _has_unquoted_shell_semantics(command):
        return None
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars="();&|<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = tuple(lexer)
    except ValueError:
        return None
    if not tokens or any(token and set(token) <= _SHELL_PUNCTUATION for token in tokens):
        return None
    if any("$" in token or token.startswith("~") for token in tokens):
        return None
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]):
        return None
    return tokens


def parse_execution_input(tool_name: str, tool_input: object) -> ExecutionInvocation | None:
    lowered = tool_name.casefold()
    if lowered not in {"bash", "tool_exec"} or not isinstance(tool_input, dict):
        return None
    present = [field for field in _COMMAND_FIELDS if field in tool_input]
    if lowered == "bash":
        present = [field for field in ("command", "cmd") if field in tool_input]
    if len(present) != 1:
        return None
    field = present[0]
    value = tool_input[field]
    if isinstance(value, str):
        argv = strict_shell_tokens(value)
        if argv is None:
            return None
        is_string = True
    elif isinstance(value, (list, tuple)):
        if not value or any(not isinstance(item, str) or not item for item in value):
            return None
        argv = tuple(value)
        is_string = False
    else:
        return None
    return ExecutionInvocation(
        tool="bash" if lowered == "bash" else "tool_exec",
        argv=argv,
        command_field=field,
        command_is_string=is_string,
        original_input=dict(tool_input),
    )


def render_execution_input(
    invocation: ExecutionInvocation,
    argv: tuple[str, ...],
) -> dict[str, object]:
    updated = dict(invocation.original_input)
    updated[invocation.command_field] = shlex.join(argv) if invocation.command_is_string else list(argv)
    for field in _COMMAND_FIELDS:
        if field != invocation.command_field:
            updated.pop(field, None)
    return updated


def _lexical_executable_path(executable: str, cwd: Path) -> Path | None:
    candidate = Path(executable)
    if candidate.is_absolute() or len(candidate.parts) > 1:
        return Path(os.path.abspath(cwd / candidate))
    return None


def _python_script_index(
    argv: tuple[str, ...],
    *,
    repository_root: Path,
    working_directory: Path,
) -> int | None:
    expected_python = Path(os.path.abspath(repository_root / ".venv/bin/python"))
    executable = _lexical_executable_path(argv[0], working_directory) if argv else None
    if len(argv) >= 2 and executable == expected_python:
        return 1
    return None


def _resolved_argument_path(value: str, working_directory: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = working_directory / path
    return path.resolve(strict=False)


def _is_path_within(value: str, root: Path, working_directory: Path) -> bool:
    try:
        _resolved_argument_path(value, working_directory).relative_to(root)
    except ValueError:
        return False
    return True


def _parse_closed_options(
    tail: tuple[str, ...],
    admitted_options: frozenset[str],
) -> tuple[dict[str, str], tuple[str, ...]] | None:
    options: dict[str, str] = {}
    positional: list[str] = []
    index = 0
    while index < len(tail):
        token = tail[index]
        if token in admitted_options:
            if token in options or index + 1 >= len(tail):
                return None
            value = tail[index + 1]
            if value.startswith("--"):
                return None
            options[token] = value
            index += 2
            continue
        if token.startswith("-"):
            return None
        positional.append(token)
        index += 1
    return options, tuple(positional)


def _canonical_repository_root(
    options: dict[str, str],
    *,
    repository_root: Path,
    working_directory: Path,
    option: str,
) -> bool:
    value = options.get(option)
    effective = (
        working_directory
        if value is None
        else _resolved_argument_path(value, working_directory)
    )
    return effective == repository_root


def _closed_code_mode_action(
    tail: tuple[str, ...],
    *,
    repository_root: Path,
    working_directory: Path,
) -> str | None:
    parsed = _parse_closed_options(tail, _CODE_MODE_OPTIONS)
    if parsed is None:
        return None
    options, positional = parsed
    if len(positional) != 2:
        return None
    operation, request = positional
    if operation not in _WORKBOOK_CODE_MODE_ACTIONS:
        return None
    contract = CodeModeAdmissionContract.for_repository(repository_root)
    endpoint = options.get("--endpoint", contract.canonical_endpoint)
    proposed_root = options.get("--repository-root")
    effective_root = (
        working_directory
        if proposed_root is None
        else _resolved_argument_path(proposed_root, working_directory)
    )
    run_binding = options.get("--run-binding")
    session_binding = options.get("--session-binding")
    if run_binding is None:
        return None
    if not contract.admits_invocation(
        endpoint=endpoint,
        repository_root=effective_root,
        run_binding=_resolved_argument_path(run_binding, working_directory),
        session_binding=(
            None
            if session_binding is None
            else _resolved_argument_path(session_binding, working_directory)
        ),
        request=_resolved_argument_path(request, working_directory),
        operation=operation,
    ):
        return None
    return operation


def _closed_workbook_cli_action(
    tail: tuple[str, ...],
    *,
    repository_root: Path,
    working_directory: Path,
) -> Literal["validate", "probe"] | None:
    repo_root: str | None = None
    probe_request: str | None = None
    validate = False
    index = 0
    while index < len(tail):
        token = tail[index]
        if token == "--validate":
            if validate:
                return None
            validate = True
            index += 1
            continue
        if token in {"--repo-root", "--probe-request"}:
            if index + 1 >= len(tail) or tail[index + 1].startswith("--"):
                return None
            value = tail[index + 1]
            if token == "--repo-root":
                if repo_root is not None:
                    return None
                repo_root = value
            else:
                if probe_request is not None:
                    return None
                probe_request = value
            index += 2
            continue
        return None
    options = {"--repo-root": repo_root} if repo_root is not None else {}
    if not _canonical_repository_root(
        options,
        repository_root=repository_root,
        working_directory=working_directory,
        option="--repo-root",
    ):
        return None
    if validate == (probe_request is not None):
        return None
    if validate:
        return "validate"
    assert probe_request is not None
    if not _is_path_within(probe_request, repository_root, working_directory):
        return None
    return "probe"


def is_exact_workbook_argv(
    argv: tuple[str, ...],
    *,
    repository_root: Path,
    working_directory: Path | None = None,
) -> bool:
    """Recognize an invocation of a workbook adapter, never a path mention."""
    if not argv:
        return False
    root = repository_root.resolve(strict=True)
    cwd = (working_directory or root).resolve(strict=False)
    script_index = _python_script_index(
        argv,
        repository_root=root,
        working_directory=cwd,
    )
    if script_index is None or script_index >= len(argv):
        return False
    script_path = Path(argv[script_index])
    if not script_path.is_absolute():
        script_path = cwd / script_path
    script_path = script_path.resolve(strict=False)
    expected_root = root / "src/cue-workbook"
    script = script_path.name
    tail = argv[script_index + 1 :]
    if script == "code_mode_client.py":
        return (
            script_path == expected_root / script
            and _closed_code_mode_action(
                tail,
                repository_root=root,
                working_directory=cwd,
            )
            is not None
        )
    if script == "workbook_cli.py":
        return script_path == expected_root / script and _closed_workbook_cli_action(
            tail,
            repository_root=root,
            working_directory=cwd,
        ) is not None
    return False


def classify_execution_argv(
    argv: tuple[str, ...],
    *,
    repository_root: Path | None = None,
    working_directory: Path | None = None,
) -> Classification:
    """Classify exact argv without interpreting arbitrary shell source."""
    if not argv:
        return Classification(recognized=False)

    if repository_root is not None and is_exact_workbook_argv(
        argv,
        repository_root=repository_root,
        working_directory=working_directory,
    ):
        root = repository_root.resolve(strict=True)
        cwd = (working_directory or root).resolve(strict=False)
        script_index = _python_script_index(
            argv,
            repository_root=root,
            working_directory=cwd,
        )
        if script_index is None:
            return Classification(recognized=False)
        script = Path(argv[script_index]).name
        tail = argv[script_index + 1 :]
        if script == "code_mode_client.py":
            action = _closed_code_mode_action(
                tail,
                repository_root=root,
                working_directory=cwd,
            )
            assert action is not None
            mapping: dict[str, tuple[TargetID, str]] = {
                "resolve-session": ("code-mode.resolve-session", "read"),
                "capture-state": ("code-mode.capture-state", "read"),
                "run-focused-probe": ("code-mode.run-focused-probe", "probe"),
                "apply-cell-transaction": ("code-mode.apply-cell-transaction", "mutation"),
            }
            target, operation_class = mapping[action]
            return _canonical_operation(
                target,
                operation_class,
                {"target": target, "tokens": argv},
                mutating=operation_class == "mutation",
                observation_channel="code-mode",
            )
        return _canonical_operation(
            "evaluation.workbook",
            "evaluation",
            {"target": "evaluation.workbook", "tokens": argv},
            observation_channel="runtime",
        )

    executable = Path(argv[0]).name
    if executable == "just":
        if argv == ("just", "--fmt", "--check"):
            return _canonical_operation(
                "just.check",
                "evaluation",
                {"target": "just.check", "justfile": "justfile"},
                observation_channel="static-source",
            )
        action_flags = [flag for flag in ("--list", "--summary", "--dump") if flag in argv]
        if len(action_flags) != 1:
            return Classification(recognized=False)
        action = action_flags[0][2:]
        target = f"just.{action}"
        paths: tuple[str, ...] = ()
        if "--justfile" in argv:
            index = argv.index("--justfile")
            if index + 1 >= len(argv):
                return Classification(recognized=False)
            paths = _normalize_paths((argv[index + 1],), repository_root)
        allowed = {"just", action_flags[0], "--justfile", *paths}
        if any(token not in allowed for token in argv):
            return Classification(recognized=False)
        return _canonical_operation(
            target,
            "evaluation",
            {"target": target, "justfile": paths[0] if paths else "justfile"},
            target_paths=paths,
            observation_channel="static-source",
        )

    if executable == "git" and len(argv) > 1:
        subcommand = argv[1]
        if subcommand in _GIT_READ_SUBCOMMANDS:
            return _canonical_operation(
                "git.read",
                "read",
                {"target": "git.read", "tokens": argv},
                observation_channel="static-source",
                fanout=32 if subcommand == "diff" else 1,
            )
        if subcommand in _GIT_MUTATION_SUBCOMMANDS:
            return _canonical_operation(
                "git.mutation",
                "mutation",
                {"target": "git.mutation", "tokens": argv},
                mutating=True,
                target_paths=_normalize_paths(_shell_target_paths(argv[1:]), repository_root),
                observation_channel="static-source",
            )

    if (
        (executable in _READ_COMMANDS and not (executable == "sed" and "-i" in argv))
        or argv[:2] == ("command", "-v")
    ):
        fanout = 128 if executable == "rg" and "--files" in argv else 1
        return _canonical_operation(
            "shell.read",
            "read",
            {"target": "shell.read", "tokens": argv},
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
        if _contains_sequence(argv, sequence):
            evaluation = (target, sequence)
            break
    if evaluation is not None:
        target, _ = evaluation
        return _canonical_operation(
            target,
            "evaluation",
            {"target": target, "tokens": argv},
            observation_channel="native-evaluation",
        )

    if executable in _WORKSPACE_MUTATIONS or (executable == "sed" and "-i" in argv):
        paths = _normalize_paths(_shell_target_paths(argv), repository_root)
        return _canonical_operation(
            "workspace.mutation",
            "mutation",
            {"target": "workspace.mutation", "tokens": argv},
            mutating=True,
            target_paths=paths,
            observation_channel="static-source",
        )
    return Classification(recognized=False)
