#!/usr/bin/env python3
"""Typed stdio MCP adapter for CUEstrap workbook operations."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from bootstrap_client import BootstrapCodeModeClient, MCPAdapter, QuarantinedObservation
from bootstrap_client.generated.models import (
    ApplyCellTransaction,
    BootstrapRunBinding,
    CaptureState,
    ResolveSession,
    RunFocusedProbe,
    SessionBinding,
)
from s04_package import ExecuteRealizationInput, execute_s04_package
from supervisory_hooks.controller import ControllerRequest
from workbook_adapter import (
    DEFAULT_CODE_MODE_ENDPOINT,
    ControllerCodeModeBinding,
    WorkbookAdapterService,
)

MCP_SERVER_VERSION = "0.3.0"


class _ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class BootstrapToolInput(_ToolInput):
    run: BootstrapRunBinding
    operation: dict[str, object]
    session_binding: SessionBinding | None = Field(default=None, alias="sessionBinding")


class BindOperationInput(_ToolInput):
    request: ControllerRequest


class BoundOperationInput(BindOperationInput):
    binding: ControllerCodeModeBinding


class WorkbookMcpServer:
    """MCP transport over the same typed services used by local frontends."""

    def __init__(
        self,
        repository_root: Path,
        endpoint: str = DEFAULT_CODE_MODE_ENDPOINT,
        *,
        operation_service: WorkbookAdapterService | None = None,
    ) -> None:
        self.repository_root = repository_root.resolve(strict=True)
        self.endpoint = endpoint
        self.operation_service = operation_service or WorkbookAdapterService(
            self.repository_root,
            endpoint,
        )

    def tools(self) -> list[dict[str, object]]:
        bootstrap = BootstrapToolInput.model_json_schema(by_alias=True)
        controller = BoundOperationInput.model_json_schema(by_alias=True)
        bind_controller = BindOperationInput.model_json_schema(by_alias=True)
        realization = ExecuteRealizationInput.model_json_schema(by_alias=True)
        return [
            {
                "name": "resolve_session",
                "description": "Resolve exactly one target workbook session by exact path.",
                "inputSchema": bootstrap,
            },
            {
                "name": "capture_state",
                "description": "Capture bounded raw state from an exact workbook session.",
                "inputSchema": bootstrap,
            },
            {
                "name": "run_probe",
                "description": "Run one approved focused probe in an exact workbook session.",
                "inputSchema": bootstrap,
            },
            {
                "name": "apply_transaction",
                "description": "Apply one preimage-bound live-cell transaction.",
                "inputSchema": bootstrap,
            },
            {
                "name": "execute_realization",
                "description": "Execute one S04 problem package and return its CUE-derived independent judgement.",
                "inputSchema": realization,
            },
            {
                "name": "bind_operation",
                "description": "Bind a controller request to one exact operation workbook session.",
                "inputSchema": bind_controller,
            },
            {
                "name": "inspect_operation",
                "description": "Inspect a bound operation workbook without performing its effect.",
                "inputSchema": controller,
            },
            {
                "name": "execute_operation",
                "description": "Claim and execute one bound operation through its workbook session.",
                "inputSchema": controller,
            },
            {
                "name": "collect_diagnosis",
                "description": "Collect bound workbook state, outputs, errors, and receipt.",
                "inputSchema": controller,
            },
            {
                "name": "release_binding",
                "description": "Release an operation binding without terminating the shared server.",
                "inputSchema": controller,
            },
        ]

    async def _bootstrap_call(
        self,
        name: str,
        arguments: Mapping[str, Any],
    ) -> dict[str, object]:
        parsed = BootstrapToolInput.model_validate(arguments)
        run = parsed.run
        session = parsed.session_binding
        models = {
            "resolve_session": ResolveSession,
            "capture_state": CaptureState,
            "run_probe": RunFocusedProbe,
            "apply_transaction": ApplyCellTransaction,
        }
        operation = models[name].model_validate(parsed.operation)
        client = BootstrapCodeModeClient(
            run,
            self.repository_root,
            MCPAdapter(self.endpoint),
            session_binding=session,
        )
        try:
            if name == "resolve_session":
                result = await client.resolve_session(operation)
            elif name == "capture_state":
                result = await client.capture_state(operation)
            elif name == "run_probe":
                result = await client.run_focused_probe(operation)
            else:
                result = await client.apply_cell_transaction(operation)
        except QuarantinedObservation as error:
            return {
                "schema": "cuestrap.workbook-adapter-quarantine/v1",
                "disposition": error.disposition.model_dump(by_alias=True, mode="json"),
                "observation": error.observation.model_dump(by_alias=True, mode="json"),
            }
        return result.model_dump(by_alias=True, mode="json")

    async def call(self, name: str, arguments: Mapping[str, Any]) -> dict[str, object]:
        if name in {"resolve_session", "capture_state", "run_probe", "apply_transaction"}:
            return await self._bootstrap_call(name, arguments)
        if name == "execute_realization":
            parsed_realization = ExecuteRealizationInput.model_validate(arguments)
            return execute_s04_package(self.repository_root, parsed_realization.package_path)

        if name == "bind_operation":
            parsed_bind = BindOperationInput.model_validate(arguments)
            request = parsed_bind.request
            result: object = await self.operation_service.bind_operation(request)
        else:
            parsed_bound = BoundOperationInput.model_validate(arguments)
            request = parsed_bound.request
            binding = parsed_bound.binding
            if name == "inspect_operation":
                result = await self.operation_service.inspect_operation(request, binding)
            elif name == "execute_operation":
                result = await self.operation_service.execute_operation(request, binding)
            elif name == "collect_diagnosis":
                result = await self.operation_service.collect_diagnosis(request, binding)
            elif name == "release_binding":
                result = await self.operation_service.release_binding(request, binding)
            else:
                raise ValueError(f"unknown workbook MCP tool: {name}")
        if hasattr(result, "model_dump"):
            return result.model_dump(by_alias=True, mode="json")
        if not isinstance(result, dict):
            raise TypeError("workbook adapter returned a non-object result")
        return result

    async def handle(self, message: Mapping[str, Any]) -> dict[str, Any] | None:
        method = message.get("method")
        request_id = message.get("id")
        if method == "initialize":
            params = message.get("params") or {}
            requested = (
                params.get("protocolVersion", "2025-06-18")
                if isinstance(params, dict)
                else "2025-06-18"
            )
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": requested,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {
                        "name": "cuestrap-workbook",
                        "version": MCP_SERVER_VERSION,
                    },
                    "instructions": (
                        "Typed CUEstrap workbook operations over exact Marimo code-mode "
                        "session bindings. Transport tools return raw observations; "
                        "execute_realization returns only the independent CUE judge output."
                    ),
                },
            }
        if method in {"notifications/initialized", "notifications/cancelled"}:
            return None
        if method == "ping":
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": self.tools()}}
        if method == "tools/call":
            params = message.get("params") or {}
            name = params.get("name")
            arguments = params.get("arguments") or {}
            if not isinstance(name, str) or not isinstance(arguments, dict):
                raise ValueError("invalid tools/call")
            value = await self.call(name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(value, sort_keys=True, indent=2),
                        }
                    ],
                    "structuredContent": value,
                },
            }
        if method == "resources/list":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"resources": []}}
        if request_id is None:
            return None
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"method not found: {method}"},
        }

    def serve(self) -> int:
        for line in sys.stdin:
            if not line.strip():
                continue
            message: object = None
            try:
                message = json.loads(line)
                if not isinstance(message, dict):
                    raise ValueError("MCP message must be an object")
                response = asyncio.run(self.handle(message))
            except Exception as error:
                request_id = message.get("id") if isinstance(message, dict) else None
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": f"{type(error).__name__}: {error}"[:1000],
                    },
                }
            if response is not None:
                sys.stdout.write(json.dumps(response, sort_keys=True, separators=(",", ":")) + "\n")
                sys.stdout.flush()
        return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--endpoint", default=DEFAULT_CODE_MODE_ENDPOINT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return WorkbookMcpServer(args.repository_root, args.endpoint).serve()


if __name__ == "__main__":
    raise SystemExit(main())
