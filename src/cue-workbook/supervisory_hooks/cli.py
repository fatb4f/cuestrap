"""Command adapter for Codex lifecycle hooks and operator phase control."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from pydantic import ValidationError

from .ledger import DurableLedger
from .models import Phase, PostToolUseInput, PreToolUseInput
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
    phase = os.environ.get("CUESTRAP_BOOTSTRAP_PHASE", "inspect")
    ledger = DurableLedger(_git_private_directory(repository_root), initial_phase=phase)
    return Supervisor(repository_root, ledger)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("hook")
    phase = subparsers.add_parser("set-phase")
    phase.add_argument("phase", choices=["inspect", "probe", "implement", "evaluate", "collect-evidence"])
    phase.add_argument("--reason", required=True)
    subparsers.add_parser("status")
    return parser


def _protocol_failure(event_name: object, reason: str) -> dict[str, object]:
    if event_name == "PreToolUse":
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    return {
        "decision": "block",
        "reason": reason,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": reason,
        },
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repository_root = args.repository_root.resolve(strict=True)
    supervisor = _supervisor(repository_root)
    if args.command == "status":
        print(json.dumps(supervisor.status(), sort_keys=True, indent=2))
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
        response = _protocol_failure(event_name, f"CUEstrap supervisory hook failed closed: {error}")
    print(json.dumps(response, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
