"""Command adapter for Codex hooks and explicit operator scope transitions."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import get_args

from pydantic import ValidationError

from .ledger import DurableLedger
from .models import (
    DEFAULT_TARGETS_BY_ACTIVITY,
    Activity,
    PostToolUseInput,
    PreToolUseInput,
    Scope,
    Surface,
    TargetID,
)
from .supervisor import Supervisor


def _git_private_directory(repository_root: Path) -> Path:
    configured = os.environ.get("CUESTRAP_HOOK_DATA_DIR")
    if configured:
        return Path(configured).resolve()
    result = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=repository_root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    directory = Path(result.stdout.strip())
    if not directory.is_absolute():
        directory = repository_root / directory
    return directory.resolve() / "cuestrap-tool-supervisor"


def _supervisor(repository_root: Path) -> Supervisor:
    initial_activity = os.environ.get("CUESTRAP_BOOTSTRAP_PHASE", "inspect")
    if initial_activity not in get_args(Activity):
        raise ValueError(f"invalid initial activity: {initial_activity!r}")
    ledger = DurableLedger(_git_private_directory(repository_root), initial_activity=initial_activity)
    return Supervisor(repository_root, ledger)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("hook")

    scope = subparsers.add_parser("set-scope")
    scope.add_argument("activity", choices=get_args(Activity))
    scope.add_argument("--surface", choices=get_args(Surface), required=True)
    scope.add_argument("--owned-path", action="append", default=[])
    scope.add_argument("--allowed-target", choices=get_args(TargetID), action="append")
    scope.add_argument("--reason", required=True)

    phase = subparsers.add_parser("set-phase")
    phase.add_argument("phase", choices=get_args(Activity))
    phase.add_argument("--reason", required=True)
    subparsers.add_parser("status")
    return parser


def _protocol_failure(event_name: object, reason: str) -> dict[str, object]:
    if event_name == "PreToolUse":
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "approve",
                "additionalContext": reason,
            }
        }
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": reason,
        }
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repository_root = args.repository_root.resolve(strict=True)
    supervisor = _supervisor(repository_root)
    if args.command == "status":
        print(json.dumps(supervisor.status(), sort_keys=True, indent=2))
        return 0
    if args.command == "set-scope":
        targets = tuple(args.allowed_target or DEFAULT_TARGETS_BY_ACTIVITY[args.activity])
        state = supervisor.set_scope(
            Scope(
                activity=args.activity,
                surface=args.surface,
                owned_paths=tuple(args.owned_path),
                allowed_targets=targets,
            ),
            reason=args.reason,
        )
        print(state.model_dump_json(by_alias=True, indent=2))
        return 0
    if args.command == "set-phase":
        state = supervisor.set_phase(args.phase, reason=args.reason)
        print(state.model_dump_json(by_alias=True, indent=2))
        return 0

    raw: object = None
    try:
        raw = json.load(sys.stdin)
        if not isinstance(raw, dict):
            raise ValueError("hook input must be a JSON object")
        event_name = raw.get("hook_event_name")
        if event_name == "PreToolUse":
            response = supervisor.handle_pre(PreToolUseInput.model_validate(raw))
        elif event_name == "PostToolUse":
            response = supervisor.handle_post(PostToolUseInput.model_validate(raw))
        else:
            raise ValueError(f"unsupported hook event: {event_name!r}")
    except (OSError, ValueError, ValidationError) as error:
        event_name = raw.get("hook_event_name") if isinstance(raw, dict) else None
        response = _protocol_failure(
            event_name,
            f"CUEstrap supervisory hook recorded a local adapter failure: {error}",
        )
    print(json.dumps(response, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
