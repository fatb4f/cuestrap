"""CLI for the typed, constrained Marimo code-mode bootstrap client."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from bootstrap_client import BootstrapCodeModeClient, MCPAdapter, QuarantinedObservation
from bootstrap_client.admission import CANONICAL_ENDPOINT, CodeModeAdmissionContract
from bootstrap_client.generated.models import (
    ApplyCellTransaction,
    BootstrapRunBinding,
    CaptureState,
    ResolveSession,
    RunFocusedProbe,
    SessionBinding,
)

DEFAULT_ENDPOINT = CANONICAL_ENDPOINT
CANONICAL_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_OPERATIONS = {
    "resolve-session": ResolveSession,
    "capture-state": CaptureState,
    "run-focused-probe": RunFocusedProbe,
    "apply-cell-transaction": ApplyCellTransaction,
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--run-binding", type=Path, required=True)
    parser.add_argument("--session-binding", type=Path)
    parser.add_argument("operation", choices=sorted(_OPERATIONS))
    parser.add_argument("request", type=Path)
    return parser


async def _main_async(args: argparse.Namespace) -> tuple[int, object]:
    CodeModeAdmissionContract.for_repository(CANONICAL_REPOSITORY_ROOT).require_invocation(
        endpoint=args.endpoint,
        repository_root=args.repository_root,
        run_binding=args.run_binding,
        session_binding=args.session_binding,
        request=args.request,
        operation=args.operation,
    )
    run = BootstrapRunBinding.model_validate(_load(args.run_binding))
    session = (
        SessionBinding.model_validate(_load(args.session_binding))
        if args.session_binding is not None
        else None
    )
    model = _OPERATIONS[args.operation]
    operation = model.model_validate(_load(args.request))
    client = BootstrapCodeModeClient(
        run,
        args.repository_root,
        MCPAdapter(args.endpoint),
        session_binding=session,
    )
    try:
        if isinstance(operation, ResolveSession):
            result = await client.resolve_session(operation)
        elif isinstance(operation, CaptureState):
            result = await client.capture_state(operation)
        elif isinstance(operation, RunFocusedProbe):
            result = await client.run_focused_probe(operation)
        else:
            result = await client.apply_cell_transaction(operation)
    except QuarantinedObservation as error:
        return 2, {
            "disposition": error.disposition.model_dump(by_alias=True, mode="json"),
            "observation": error.observation.model_dump(by_alias=True, mode="json"),
        }
    return 0, result.model_dump(by_alias=True, mode="json")


def main() -> int:
    code, value = asyncio.run(_main_async(_parser().parse_args()))
    print(json.dumps(value, sort_keys=True, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
