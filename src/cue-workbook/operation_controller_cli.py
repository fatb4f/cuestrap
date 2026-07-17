#!/usr/bin/env python3
"""Optional operator/test frontend for the typed workbook adapter service."""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import shlex
from pathlib import Path

from supervisory_hooks.controller import ControllerRequest
from workbook_adapter import (
    DEFAULT_CODE_MODE_ENDPOINT,
    ControllerCodeModeBinding,
    WorkbookAdapterService,
    binding_path,
    load_binding,
)

CONTROLLER_OPERATIONS = ("serve", "inspect", "execute", "diagnose", "close")


def decode_controller_request(payload: str) -> ControllerRequest:
    padding = "=" * (-len(payload) % 4)
    raw = base64.urlsafe_b64decode((payload + padding).encode())
    return ControllerRequest.model_validate(json.loads(raw))


def _controller_tokens(
    repository_root: Path,
    endpoint: str,
    payload: str,
    operation: str,
) -> tuple[str, ...]:
    return (
        str(repository_root / ".venv/bin/python"),
        str(Path(__file__).resolve()),
        "--repository-root",
        str(repository_root),
        "--endpoint",
        endpoint,
        "--payload",
        payload,
        operation,
    )


def _interaction_document(
    binding: ControllerCodeModeBinding,
    path: Path,
    repository_root: Path,
    endpoint: str,
    payload: str,
) -> dict[str, object]:
    return {
        "schema": "cuestrap.operation-controller-cli-session/v1",
        "state": "ready",
        "requestIdentity": binding.request_identity,
        "binding": binding.model_dump(by_alias=True, mode="json"),
        "bindingPath": str(path),
        "commands": {
            operation: shlex.join(
                _controller_tokens(repository_root, endpoint, payload, operation)
            )
            for operation in ("inspect", "execute", "diagnose", "close")
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--endpoint", default=DEFAULT_CODE_MODE_ENDPOINT)
    parser.add_argument("--payload", required=True)
    parser.add_argument("operation", choices=CONTROLLER_OPERATIONS)
    return parser


async def _run(args: argparse.Namespace) -> tuple[int, object]:
    root = args.repository_root.resolve(strict=True)
    request = decode_controller_request(args.payload)
    service = WorkbookAdapterService(root, args.endpoint)
    path = binding_path(request, service.state_root)
    if args.operation == "serve":
        binding = await service.bind_operation(request)
        return 0, _interaction_document(binding, path, root, args.endpoint, args.payload)

    binding = load_binding(path)
    if args.operation == "inspect":
        value = await service.inspect_operation(request, binding)
    elif args.operation == "execute":
        value = await service.execute_operation(request, binding)
    elif args.operation == "diagnose":
        value = await service.collect_diagnosis(request, binding)
    else:
        value = await service.release_binding(request, binding)
    code = value.get("returnCode", 0) if args.operation == "execute" else 0
    return int(code) if isinstance(code, int) else 70, value


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        code, value = asyncio.run(_run(args))
    except (OSError, RuntimeError, ValueError) as error:
        code = 70
        value = {
            "schema": "cuestrap.operation-controller-cli-fault/v1",
            "operation": args.operation,
            "exceptionType": type(error).__name__,
            "exceptionText": str(error),
        }
    print(json.dumps(value, sort_keys=True, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
