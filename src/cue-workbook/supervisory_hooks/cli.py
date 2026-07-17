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
from .models import Activity, PostToolUseInput, PreToolUseInput, Scope, default_scope
from .routing import plan_pretool_route, render_pretool_response, restore_posttool_event
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
    configured = os.environ.get("CUESTRAP_BOOTSTRAP_SCOPE")
    if configured is None:
        initial_activity = os.environ.get("CUESTRAP_BOOTSTRAP_PHASE", "inspect")
        if initial_activity not in get_args(Activity):
            raise ValueError(f"invalid initial activity: {initial_activity!r}")
        scope = default_scope(initial_activity)
        reason = "host-configured default bootstrap scope"
    else:
        scope = Scope.model_validate_json(configured)
        initial_activity = scope.activity
        reason = "host-configured explicit bootstrap scope"
    ledger = DurableLedger(
        _git_private_directory(repository_root),
        initial_activity=initial_activity,
    )
    supervisor = Supervisor(repository_root, ledger)
    supervisor.ensure_scope(scope, reason=reason)
    return supervisor


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


def main(argv: list[str] | None = None, *, wire_safe: bool = False) -> int:
    args = _parser().parse_args(argv)
    repository_root = args.repository_root.resolve(strict=True)
    if args.command == "status":
        supervisor = _supervisor(repository_root)
        print(json.dumps(supervisor.status(), sort_keys=True, indent=2))
        return 0

    raw: object = None
    try:
        raw = json.load(sys.stdin)
        if not isinstance(raw, dict):
            raise ValueError("hook input must be a JSON object")
        event_name = raw.get("hook_event_name")
        supervisor = _supervisor(repository_root)
        if event_name == "PreToolUse":
            event = PreToolUseInput.model_validate(raw)
            if wire_safe:
                route = plan_pretool_route(event, repository_root)
                if route.behavior == "redirect":
                    response = render_pretool_response(route, {})
                else:
                    semantic_event = route.semantic_event or event
                    response = render_pretool_response(
                        route,
                        supervisor.handle_pre(semantic_event),
                    )
            else:
                response = supervisor.handle_pre(event)
        elif event_name == "PostToolUse":
            event = PostToolUseInput.model_validate(raw)
            if wire_safe:
                event = restore_posttool_event(event, repository_root)
            response = supervisor.handle_post(event)
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
