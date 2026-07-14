"""Constrained client for a live Marimo code-mode MCP controller workbook."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

CODE_MODE_OBSERVATION = "cuestrap.marimo-code-mode-observation.v0"
TRANSACTION_PROTOCOL = "cuestrap.marimo-cell-transaction.v0"
DEFAULT_ENDPOINT = "http://127.0.0.1:2718/mcp/server"
_RESULT_MARKER = "CUESTRAP_CODE_MODE_JSON:"


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _digest_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _digest_file(path: Path) -> str:
    return _digest_bytes(path.read_bytes())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class SessionInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    path: str
    session_id: str = Field(alias="session_id")


class CreateCell(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["create"]
    code: str
    before: str | None = None
    after: str | None = None
    run: bool = False

    @model_validator(mode="after")
    def one_anchor(self) -> "CreateCell":
        if self.before is not None and self.after is not None:
            raise ValueError("create accepts at most one of before and after")
        return self


class EditCell(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["edit"]
    target: str = Field(min_length=1)
    expected_code_digest: str = Field(alias="expectedCodeDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    code: str
    run: bool = False


class DeleteCell(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["delete"]
    target: str = Field(min_length=1)
    expected_code_digest: str = Field(alias="expectedCodeDigest", pattern=r"^sha256:[0-9a-f]{64}$")


class MoveCell(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["move"]
    target: str = Field(min_length=1)
    before: str | None = None
    after: str | None = None

    @model_validator(mode="after")
    def exactly_one_anchor(self) -> "MoveCell":
        if (self.before is None) == (self.after is None):
            raise ValueError("move requires exactly one of before and after")
        return self


class RunCell(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["run"]
    target: str = Field(min_length=1)


CellOperation = Annotated[CreateCell | EditCell | DeleteCell | MoveCell | RunCell, Field(discriminator="kind")]


class CellTransaction(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal[TRANSACTION_PROTOCOL] = Field(alias="schema")
    workbook: str = Field(min_length=1)
    operations: list[CellOperation] = Field(min_length=1, max_length=16)


CallTool = Callable[[str, dict[str, Any] | None], Awaitable[dict[str, Any]]]


async def _mcp_call(endpoint: str, name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    async with streamable_http_client(endpoint) as (read, write, _session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
    payload: dict[str, Any]
    if isinstance(result.structuredContent, dict):
        payload = dict(result.structuredContent)
    else:
        payload = {}
        for content in result.content:
            text = getattr(content, "text", None)
            if not isinstance(text, str):
                continue
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                payload = parsed
                break
    payload["_mcpIsError"] = bool(result.isError)
    return payload


def select_session(sessions: object, workbook: Path) -> SessionInfo:
    expected = workbook.resolve(strict=True)
    parsed = TypeAdapter(list[SessionInfo]).validate_python(sessions)
    matches: list[SessionInfo] = []
    for session in parsed:
        try:
            observed = Path(session.path).resolve(strict=True)
        except OSError:
            continue
        if observed == expected:
            matches.append(session)
    if len(matches) != 1:
        identities = [f"{session.session_id}:{session.path}" for session in parsed]
        raise RuntimeError(
            f"expected exactly one session for {expected}, found {len(matches)}; "
            f"active sessions: {identities}"
        )
    return matches[0]


def _inspection_code() -> str:
    return f'''import hashlib as _hashlib
import json as _json
import marimo as _marimo
import marimo._code_mode as _cm

_ctx = _cm.get_context()

def _digest(_value):
    return "sha256:" + _hashlib.sha256(_value.encode("utf-8", "replace")).hexdigest()

def _render(_value):
    _text = repr(_value)
    return {{"type": type(_value).__name__, "repr": _text[:20000], "digest": _digest(_text)}}

def _output(_value):
    if _value is None:
        return None
    return {{
        "channel": str(_value.channel),
        "mimetype": str(_value.mimetype),
        "data": _render(_value.data),
    }}

_cells = []
for _cell in _ctx.cells:
    _code = _cell.code
    _cells.append({{
        "id": str(_cell.id),
        "name": _cell.name,
        "code": _code,
        "codeDigest": _digest(_code),
        "status": str(_cell.status) if _cell.status is not None else None,
        "config": {{
            "disabled": _cell.config.disabled,
            "hideCode": _cell.config.hide_code,
            "column": _cell.config.column,
        }},
        "errors": [{{"kind": _error.kind, "message": _error.msg}} for _error in _cell.errors],
        "output": _output(_cell.output),
        "consoleOutputs": [_output(_item) for _item in _cell.console_outputs],
    }})

_graph = _ctx.graph
_payload = {{
    "engine": {{"marimoVersion": _marimo.__version__, "codeModeModule": _cm.__name__}},
    "cells": _cells,
    "graph": {{
        "parents": {{str(_key): sorted(str(_item) for _item in _value) for _key, _value in _graph.parents.items()}},
        "children": {{str(_key): sorted(str(_item) for _item in _value) for _key, _value in _graph.children.items()}},
        "definitions": {{str(_key): sorted(str(_item) for _item in _value) for _key, _value in _graph.definitions.items()}},
    }},
    "variables": {{str(_key): _render(_value) for _key, _value in sorted(_ctx.globals.items()) if not str(_key).startswith("_")}},
}}
print({_RESULT_MARKER!r} + _json.dumps(_payload, sort_keys=True, separators=(",", ":")))'''


def _transaction_code(request: CellTransaction) -> str:
    lines = [
        "import hashlib as _hashlib",
        "import json as _json",
        "import marimo._code_mode as _cm",
        "_created = []",
        "def _verify(_ctx, _target, _expected):",
        "    _actual = 'sha256:' + _hashlib.sha256(_ctx.cells[_target].code.encode()).hexdigest()",
        "    if _actual != _expected:",
        "        raise RuntimeError(f'cell {_target!r} changed: expected {_expected}, observed {_actual}')",
        "async with _cm.get_context() as _ctx:",
    ]
    for operation in request.operations:
        if isinstance(operation, CreateCell):
            args = [repr(operation.code)]
            if operation.before is not None:
                args.append(f"before={operation.before!r}")
            if operation.after is not None:
                args.append(f"after={operation.after!r}")
            lines.append(f"    _cell_id = _ctx.create_cell({', '.join(args)})")
            lines.append("    _created.append(str(_cell_id))")
            if operation.run:
                lines.append("    _ctx.run_cell(_cell_id)")
        elif isinstance(operation, EditCell):
            lines.append(
                f"    _verify(_ctx, {operation.target!r}, {operation.expected_code_digest!r})"
            )
            lines.append(f"    _ctx.edit_cell({operation.target!r}, code={operation.code!r})")
            if operation.run:
                lines.append(f"    _ctx.run_cell({operation.target!r})")
        elif isinstance(operation, DeleteCell):
            lines.append(
                f"    _verify(_ctx, {operation.target!r}, {operation.expected_code_digest!r})"
            )
            lines.append(f"    _ctx.delete_cell({operation.target!r})")
        elif isinstance(operation, MoveCell):
            anchor = (
                f"before={operation.before!r}"
                if operation.before is not None
                else f"after={operation.after!r}"
            )
            lines.append(f"    _ctx.move_cell({operation.target!r}, {anchor})")
        else:
            lines.append(f"    _ctx.run_cell({operation.target!r})")
    lines.extend(
        [
            f"_transaction = {{'state': 'applied', 'createdCellIDs': _created, 'operationCount': {len(request.operations)}}}",
            f"print({_RESULT_MARKER!r} + _json.dumps(_transaction, sort_keys=True, separators=(',', ':')))",
        ]
    )
    return "\n".join(lines)


def _normalize_execution(payload: dict[str, Any]) -> dict[str, Any]:
    upstream_state = payload.get("success")
    return {
        "state": "returned" if upstream_state is True and not payload.get("_mcpIsError") else "rejected",
        "output": payload.get("output"),
        "stdout": payload.get("stdout", []),
        "stderr": payload.get("stderr", []),
        "errors": payload.get("errors", []),
        "error": payload.get("error"),
    }


def _marked_json(execution: dict[str, Any]) -> dict[str, Any]:
    candidates = list(execution.get("stdout") or [])
    output = execution.get("output")
    if isinstance(output, str):
        candidates.append(output)
    for candidate in reversed(candidates):
        position = candidate.rfind(_RESULT_MARKER)
        if position < 0:
            continue
        encoded = candidate[position + len(_RESULT_MARKER) :].strip()
        parsed = json.loads(encoded)
        if isinstance(parsed, dict):
            return parsed
    raise RuntimeError(f"code-mode response did not contain {_RESULT_MARKER}")


class CodeModeClient:
    def __init__(
        self,
        endpoint: str,
        workbook: Path,
        *,
        call_tool: CallTool | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.workbook = workbook.resolve(strict=True)
        self._caller = call_tool or (lambda name, arguments: _mcp_call(endpoint, name, arguments))

    async def _bound_session(self) -> SessionInfo:
        payload = await self._caller("list_sessions", None)
        sessions = payload.get("sessions")
        if not isinstance(sessions, list):
            raise RuntimeError("list_sessions returned no sessions list")
        return select_session(sessions, self.workbook)

    async def _execute(self, session: SessionInfo, code: str) -> dict[str, Any]:
        payload = await self._caller("execute_code", {"session_id": session.session_id, "code": code})
        return _normalize_execution(payload)

    def _envelope(
        self,
        operation: str,
        session: SessionInfo,
        request: object,
        transport: dict[str, Any],
        observation: dict[str, Any],
    ) -> dict[str, Any]:
        request_identity = _digest_bytes(_json_bytes(request))
        output_identity = _digest_bytes(_json_bytes({"transport": transport, "observation": observation}))
        return {
            "schema": CODE_MODE_OBSERVATION,
            "operation": operation,
            "observedAt": _now(),
            "endpoint": self.endpoint,
            "session": session.model_dump(by_alias=True),
            "workbook": {"path": str(self.workbook), "digest": _digest_file(self.workbook)},
            "engine": observation.get("engine"),
            "requestIdentity": request_identity,
            "outputIdentity": output_identity,
            "transport": transport,
            "observation": observation,
        }

    async def inspect(self) -> dict[str, Any]:
        session = await self._bound_session()
        transport = await self._execute(session, _inspection_code())
        observation = _marked_json(transport)
        return self._envelope("inspect", session, {"operation": "inspect"}, transport, observation)

    async def transact(self, request: CellTransaction) -> dict[str, Any]:
        requested_workbook = Path(request.workbook)
        if not requested_workbook.is_absolute():
            requested_workbook = (Path.cwd() / requested_workbook).resolve(strict=True)
        else:
            requested_workbook = requested_workbook.resolve(strict=True)
        if requested_workbook != self.workbook:
            raise RuntimeError(
                f"transaction workbook {requested_workbook} does not match bound workbook {self.workbook}"
            )
        before_digest = _digest_file(self.workbook)
        session = await self._bound_session()
        transaction_transport = await self._execute(session, _transaction_code(request))
        transaction_observation = _marked_json(transaction_transport)
        capture_transport = await self._execute(session, _inspection_code())
        capture = _marked_json(capture_transport)
        source_mutation = any(operation.kind != "run" for operation in request.operations)
        after_digest = _digest_file(self.workbook)
        if source_mutation:
            for _ in range(50):
                if after_digest != before_digest:
                    break
                await asyncio.sleep(0.1)
                after_digest = _digest_file(self.workbook)
        durability = {
            "state": "observed" if after_digest != before_digest else "unchanged",
            "beforeDigest": before_digest,
            "afterDigest": after_digest,
        }
        transport = {"transaction": transaction_transport, "capture": capture_transport}
        observation = {
            "transaction": transaction_observation,
            "capture": capture,
            "durability": durability,
        }
        request_value = request.model_dump(by_alias=True)
        return self._envelope("transaction", session, request_value, transport, observation)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--workbook", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("inspect")
    run_cell = commands.add_parser("run-cell")
    run_cell.add_argument("target")
    transact = commands.add_parser("transact")
    transact.add_argument("request", type=Path)
    return parser


async def _main_async(args: argparse.Namespace) -> dict[str, Any]:
    client = CodeModeClient(args.endpoint, args.workbook)
    if args.command == "inspect":
        return await client.inspect()
    if args.command == "run-cell":
        request = CellTransaction.model_validate(
            {
                "schema": TRANSACTION_PROTOCOL,
                "workbook": str(args.workbook),
                "operations": [{"kind": "run", "target": args.target}],
            }
        )
        return await client.transact(request)
    value = json.loads(args.request.read_text(encoding="utf-8"))
    return await client.transact(CellTransaction.model_validate(value))


def main() -> int:
    result = asyncio.run(_main_async(_parser().parse_args()))
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
