"""Command adapter for Codex hooks and read-only supervisor inspection."""
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
from .models import Activity, PostToolUseInput, PreToolUseInput
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
    subparsers.add_parser("status")
    return parser


def _protocol_failure(event_name: object, reason: str) -> dict[str, object]:
    if event_name in {"PreToolUse", "PostToolUse"}:
        return {
            "hookSpecificOutput": {
                "hookEventName": event_name,
                "additionalContext": reason,
            }
        }
    return {"systemMessage": reason}


def _wire_safe_response(response: dict[str, object]) -> dict[str, object]:
    """Remove the provisional internal approve marker from Codex wire output."""
    specific = response.get("hookSpecificOutput")
    if not isinstance(specific, dict):
        return response
    if specific.get("hookEventName") != "PreToolUse":
        return response
    if specific.get("permissionDecision") != "approve":
        return response

    sanitized = dict(specific)
    sanitized.pop("permissionDecision", None)
    if set(sanitized) == {"hookEventName"}:
        return {}
    return {**response, "hookSpecificOutput": sanitized}


def main(argv: list[str] | None = None, *, wire_safe: bool = False) -> int:
    args = _parser().parse_args(argv)
    repository_root = args.repository_root.resolve(strict=True)
    supervisor = _supervisor(repository_root)
    if args.command == "status":
        print(json.dumps(supervisor.status(), sort_keys=True, indent=2))
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
    if wire_safe:
        response = _wire_safe_response(response)
    print(json.dumps(response, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
