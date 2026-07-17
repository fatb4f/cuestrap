"""Closed execution transport shared by Bash, tool_exec, and controller routing."""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

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
_SHELL_PUNCTUATION = frozenset(";&|<>")
_WORKBOOK_CODE_MODE_ACTIONS = frozenset(
    {
        "resolve-session",
        "capture-state",
        "run-focused-probe",
        "apply-cell-transaction",
    }
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
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>")
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


def _python_script_index(argv: tuple[str, ...]) -> int | None:
    if len(argv) >= 2 and Path(argv[0]).name in {"python", "python3"}:
        return 1
    if argv and Path(argv[0]).name == "uv" and "--" in argv:
        index = len(argv) - 1 - tuple(reversed(argv)).index("--")
        if len(argv) > index + 2 and Path(argv[index + 1]).name in {"python", "python3"}:
            return index + 2
    return None


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
    if Path(argv[0]).name == "just":
        if argv == ("just", "marimo-listener"):
            return cwd == root
        if argv == ("just", "--justfile", "justfile", "marimo-listener"):
            return (cwd / "justfile").resolve(strict=False) == root / "justfile"
        return False
    script_index = _python_script_index(argv)
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
            and bool(tail)
            and tail[0] in _WORKBOOK_CODE_MODE_ACTIONS
        )
    if script == "workbook_cli.py":
        return script_path == expected_root / script and any(
            flag in tail for flag in ("--validate", "--probe-request")
        )
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
        script_index = _python_script_index(argv)
        if script_index is None:
            return Classification(recognized=False)
        script = Path(argv[script_index]).name
        tail = argv[script_index + 1 :]
        if script == "code_mode_client.py":
            mapping: dict[str, tuple[TargetID, str]] = {
                "resolve-session": ("code-mode.resolve-session", "read"),
                "capture-state": ("code-mode.capture-state", "read"),
                "run-focused-probe": ("code-mode.run-focused-probe", "probe"),
                "apply-cell-transaction": ("code-mode.apply-cell-transaction", "mutation"),
            }
            target, operation_class = mapping[tail[0]]
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
