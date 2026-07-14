"""The only bootstrap-client module that knows MCP primitive names."""
from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CallTool = Callable[[str, dict[str, Any] | None], Awaitable[dict[str, Any]]]


class AdapterResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    transport_state: Literal["returned", "transport-error", "timed-out"]
    execution_state: Literal["exited", "raised", "not-executed"]
    output: Any = None
    stdout: list[str] = Field(default_factory=list)
    stderr: list[str] = Field(default_factory=list)
    errors: list[Any] = Field(default_factory=list)
    exception_type: str | None = None
    exception_text: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


async def _mcp_call(endpoint: str, name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    async with streamable_http_client(endpoint) as (read, write, _session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
    if isinstance(result.structuredContent, dict):
        payload = dict(result.structuredContent)
    else:
        payload: dict[str, Any] = {}
        for content in result.content:
            text = getattr(content, "text", None)
            if not isinstance(text, str):
                continue
            try:
                decoded = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(decoded, dict):
                payload = decoded
                break
    payload["_mcpIsError"] = bool(result.isError)
    return payload


class MCPAdapter:
    def __init__(self, endpoint: str, *, call_tool: CallTool | None = None) -> None:
        self.endpoint = endpoint
        self._call_tool = call_tool or (lambda name, arguments: _mcp_call(endpoint, name, arguments))

    async def list_sessions(self, *, timeout_milliseconds: int) -> AdapterResult:
        return await self._call("list_sessions", None, timeout_milliseconds)

    async def execute_code(
        self,
        session_id: str,
        code: str,
        *,
        timeout_milliseconds: int,
    ) -> AdapterResult:
        return await self._call(
            "execute_code",
            {"session_id": session_id, "code": code},
            timeout_milliseconds,
        )

    async def _call(
        self,
        name: Literal["list_sessions", "execute_code"],
        arguments: dict[str, Any] | None,
        timeout_milliseconds: int,
    ) -> AdapterResult:
        try:
            payload = await asyncio.wait_for(
                self._call_tool(name, arguments),
                timeout=timeout_milliseconds / 1000,
            )
        except TimeoutError:
            return AdapterResult(transport_state="timed-out", execution_state="not-executed")
        except Exception as error:  # transport boundary: preserve type and text as raw facts
            return AdapterResult(
                transport_state="transport-error",
                execution_state="not-executed",
                exception_type=type(error).__name__,
                exception_text=str(error),
            )
        is_error = bool(payload.pop("_mcpIsError", False))
        upstream_exited = payload.pop("success", None)
        errors = payload.get("errors") or []
        exception_text = payload.get("error")
        raised = is_error or upstream_exited is False or bool(errors) or exception_text is not None
        return AdapterResult(
            transport_state="returned",
            execution_state="raised" if raised else "exited",
            output=payload.get("output"),
            stdout=[str(item) for item in payload.get("stdout") or []],
            stderr=[str(item) for item in payload.get("stderr") or []],
            errors=list(errors),
            exception_type="CodeModeExecutionError" if raised else None,
            exception_text=str(exception_text or errors) if raised else None,
            payload=payload,
        )
