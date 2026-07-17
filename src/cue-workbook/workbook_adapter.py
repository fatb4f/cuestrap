"""Typed workbook operations over a shared Marimo code-mode endpoint."""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from bootstrap_client.binding import digest_file, resolve_exact_session
from bootstrap_client.codegen.common import RESULT_MARKER, decode_marked_json, support_code
from bootstrap_client.generated.models import SessionBinding
from bootstrap_client.mcp_adapter import MCPAdapter
from supervisory_hooks.controller import (
    ControllerRequest,
    _atomic_json,
    controller_operation_directory,
    validate_controller_request,
)
from supervisory_hooks.models import digest_json

DEFAULT_CODE_MODE_ENDPOINT = "http://127.0.0.1:2718/mcp/server"
OPERATION_WORKBOOK = Path(__file__).with_name("operation-controller.py")


class ControllerCodeModeBinding(BaseModel):
    """Closed binding to an exact workbook session on a shared MCP endpoint."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    schema_version: Literal["cuestrap.operation-controller-code-mode-binding/v1"] = Field(
        default="cuestrap.operation-controller-code-mode-binding/v1",
        alias="schema",
    )
    request_identity: str = Field(
        alias="requestIdentity",
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    server_endpoint: str = Field(alias="serverEndpoint", min_length=1)
    workbook_path: str = Field(alias="workbookPath", min_length=1)
    workbook_digest: str = Field(
        alias="workbookDigest",
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    session_id: str = Field(alias="sessionID", min_length=1)
    session_digest: str = Field(
        alias="sessionDigest",
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    resolved_at_sequence: int = Field(alias="resolvedAtSequence", ge=0)

    @classmethod
    def from_session(
        cls,
        *,
        request_identity: str,
        server_endpoint: str,
        workbook_digest: str,
        session: SessionBinding,
    ) -> "ControllerCodeModeBinding":
        return cls(
            requestIdentity=request_identity,
            serverEndpoint=server_endpoint,
            workbookPath=session.workbook_path,
            workbookDigest=workbook_digest,
            sessionID=session.session_id,
            sessionDigest=session.session_metadata_digest,
            resolvedAtSequence=session.resolved_at_sequence,
        )

    def session_binding(self) -> SessionBinding:
        return SessionBinding(
            sessionID=self.session_id,
            workbookPath=self.workbook_path,
            sessionMetadataDigest=self.session_digest,
            resolvedAtSequence=self.resolved_at_sequence,
        )


class ControllerBindingRelease(BaseModel):
    """Durable revocation of one exact operation binding."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    schema_version: Literal["cuestrap.workbook-binding-release/v1"] = Field(
        default="cuestrap.workbook-binding-release/v1",
        alias="schema",
    )
    state: Literal["released"] = "released"
    request_identity: str = Field(
        alias="requestIdentity",
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    binding_digest: str = Field(
        alias="bindingDigest",
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    server_endpoint: str = Field(alias="serverEndpoint", min_length=1)
    session_id: str = Field(alias="sessionID", min_length=1)
    released_at_nanoseconds: int = Field(alias="releasedAtNanoseconds", ge=0)

def controller_state_root(repository_root: Path) -> Path:
    configured = os.environ.get("CUESTRAP_CONTROLLER_DATA_DIR")
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
    return directory.resolve() / "cuestrap-operation-controller"


def binding_path(request: ControllerRequest, state_root: Path) -> Path:
    return controller_operation_directory(request, state_root) / "code-mode-binding.json"


def release_path(request: ControllerRequest, state_root: Path) -> Path:
    return controller_operation_directory(request, state_root) / "release.json"


def load_binding(path: Path) -> ControllerCodeModeBinding:
    return ControllerCodeModeBinding.model_validate_json(path.read_text(encoding="utf-8"))


def load_release(path: Path) -> ControllerBindingRelease:
    return ControllerBindingRelease.model_validate_json(path.read_text(encoding="utf-8"))


def write_bound_request(request: ControllerRequest, state_root: Path) -> None:
    operation_directory = controller_operation_directory(request, state_root)
    request_path = operation_directory / "request.json"
    document = request.model_dump(by_alias=True, mode="json", exclude_none=True)
    if request_path.exists():
        if json.loads(request_path.read_text(encoding="utf-8")) != document:
            raise ValueError("operation ID is already bound to a different controller request")
        return
    _atomic_json(request_path, document)


def _bound_support_code(
    request: ControllerRequest,
    repository_root: Path,
    state_root: Path,
) -> str:
    request_json = request.model_dump_json(by_alias=True, exclude_none=True)
    return support_code() + f'''
_ctx = _cm.get_context()
_request_type = _ctx.globals.get("ControllerRequest")
if _request_type is None:
    raise RuntimeError("operation-controller workbook contract is unavailable")
_bound_request = _request_type.model_validate_json({request_json!r})
if _bound_request.identity != {request.identity!r}:
    raise RuntimeError("operation-controller request identity mismatch")
_repository_root = {str(repository_root)!r}
_controller_state_root = {str(state_root)!r}
'''


def inspection_code(
    request: ControllerRequest,
    repository_root: Path,
    state_root: Path,
    *,
    include_receipt: bool,
) -> str:
    return _bound_support_code(request, repository_root, state_root) + f'''
_cells = []
for _cell in _ctx.cells:
    _item = {{
        "id": str(_cell.id),
        "sourceDigest": _digest_text(_cell.code),
        "errors": [{{"kind": _error.kind, "message": _error.msg}} for _error in _cell.errors],
    }}
    if {include_receipt!r}:
        def _render_output(_value):
            if _value is None:
                return None
            _text = repr(_value.data)
            return {{
                "channel": str(_value.channel),
                "mimetype": str(_value.mimetype),
                "repr": _text[:20000],
                "digest": _digest_text(_text),
            }}
        _item["output"] = _render_output(_cell.output)
        _item["consoleOutputs"] = [_render_output(_value) for _value in _cell.console_outputs]
    _cells.append(_item)
_receipt = None
if {include_receipt!r}:
    _reader = _ctx.globals["read_controller_receipt"]
    _path = _ctx.globals["Path"]
    _observed_receipt = _reader(
        _bound_request,
        _path(_repository_root),
        _path(_controller_state_root),
    )
    if _observed_receipt is not None:
        _receipt = _observed_receipt.model_dump(by_alias=True, mode="json", exclude_none=True)
_payload = {{
    "schema": "cuestrap.operation-controller-code-mode-observation/v1",
    "request": _bound_request.model_dump(by_alias=True, mode="json", exclude_none=True),
    "workbook": {{"identity": _identity(_ctx), "cells": _cells}},
    "receipt": _receipt,
}}
print({RESULT_MARKER!r} + _json.dumps(_payload, sort_keys=True, separators=(",", ":")))
'''


def execution_code(
    request: ControllerRequest,
    repository_root: Path,
    state_root: Path,
) -> str:
    return _bound_support_code(request, repository_root, state_root) + f'''
_executor = _ctx.globals["execute_controller_request"]
_path = _ctx.globals["Path"]
_receipt = _executor(
    _bound_request,
    _path(_repository_root),
    _path(_controller_state_root),
)
_payload = _receipt.model_dump(by_alias=True, mode="json", exclude_none=True)
print({RESULT_MARKER!r} + _json.dumps(_payload, sort_keys=True, separators=(",", ":")))
'''


class WorkbookAdapterService:
    """Shared implementation used by the workbook MCP server and optional CLI."""

    def __init__(
        self,
        repository_root: Path,
        endpoint: str = DEFAULT_CODE_MODE_ENDPOINT,
        *,
        state_root: Path | None = None,
        adapter: MCPAdapter | None = None,
    ) -> None:
        self.repository_root = repository_root.resolve(strict=True)
        self.endpoint = endpoint
        self.state_root = state_root or controller_state_root(self.repository_root)
        self.adapter = adapter or MCPAdapter(endpoint)

    async def _resolve_session(self, *, sequence: int) -> SessionBinding:
        result = await self.adapter.list_sessions(timeout_milliseconds=1000)
        sessions = result.payload.get("sessions")
        if result.transport_state != "returned" or not isinstance(sessions, list):
            raise RuntimeError("shared code-mode endpoint did not return sessions")
        return resolve_exact_session(
            sessions,
            OPERATION_WORKBOOK,
            self.repository_root,
            sequence=sequence,
        )

    async def bind_operation(
        self,
        request: ControllerRequest,
    ) -> ControllerCodeModeBinding:
        validate_controller_request(request, self.repository_root)
        write_bound_request(request, self.state_root)
        session = await self._resolve_session(sequence=0)
        binding = ControllerCodeModeBinding.from_session(
            request_identity=request.identity,
            server_endpoint=self.endpoint,
            workbook_digest=digest_file(OPERATION_WORKBOOK),
            session=session,
        )
        path = binding_path(request, self.state_root)
        if release_path(request, self.state_root).exists():
            raise RuntimeError("binding-released")
        if path.exists() and load_binding(path) != binding:
            raise ValueError("operation already has a different workbook binding")
        _atomic_json(path, binding.model_dump(by_alias=True, mode="json"))
        return binding

    async def _check_binding(
        self,
        request: ControllerRequest,
        binding: ControllerCodeModeBinding,
    ) -> None:
        validate_controller_request(request, self.repository_root)
        if binding.request_identity != request.identity:
            raise ValueError("binding belongs to a different controller request")
        if binding.server_endpoint != self.endpoint:
            raise ValueError("binding endpoint mismatch")
        if (
            binding.workbook_path != str(OPERATION_WORKBOOK)
            or binding.workbook_digest != digest_file(OPERATION_WORKBOOK)
        ):
            raise ValueError("binding workbook identity mismatch")
        stored = load_binding(binding_path(request, self.state_root))
        if stored != binding:
            raise ValueError("binding differs from the durable operation binding")
        if release_path(request, self.state_root).exists():
            raise RuntimeError("binding-released")
        current = await self._resolve_session(sequence=binding.resolved_at_sequence)
        if current != binding.session_binding():
            raise RuntimeError("workbook session binding changed")

    async def _execute_code(
        self,
        request: ControllerRequest,
        binding: ControllerCodeModeBinding,
        code: str,
    ) -> dict[str, object]:
        await self._check_binding(request, binding)
        result = await self.adapter.execute_code(
            binding.session_id,
            code,
            timeout_milliseconds=request.timeout_seconds * 1000,
        )
        decoded = decode_marked_json(result)
        if decoded is None:
            return {
                "schema": "cuestrap.workbook-adapter-fault/v1",
                "transportState": result.transport_state,
                "executionState": result.execution_state,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "errors": result.errors,
                "exceptionType": result.exception_type,
                "exceptionText": result.exception_text,
            }
        return decoded

    async def inspect_operation(
        self,
        request: ControllerRequest,
        binding: ControllerCodeModeBinding,
    ) -> dict[str, object]:
        return await self._execute_code(
            request,
            binding,
            inspection_code(
                request,
                self.repository_root,
                self.state_root,
                include_receipt=False,
            ),
        )

    async def execute_operation(
        self,
        request: ControllerRequest,
        binding: ControllerCodeModeBinding,
    ) -> dict[str, object]:
        return await self._execute_code(
            request,
            binding,
            execution_code(request, self.repository_root, self.state_root),
        )

    async def collect_diagnosis(
        self,
        request: ControllerRequest,
        binding: ControllerCodeModeBinding,
    ) -> dict[str, object]:
        return await self._execute_code(
            request,
            binding,
            inspection_code(
                request,
                self.repository_root,
                self.state_root,
                include_receipt=True,
            ),
        )

    async def release_binding(
        self,
        request: ControllerRequest,
        binding: ControllerCodeModeBinding,
    ) -> dict[str, object]:
        path = release_path(request, self.state_root)
        binding_digest = digest_json(binding.model_dump(by_alias=True, mode="json"))
        if path.exists():
            current = load_release(path)
            if (
                current.request_identity != request.identity
                or current.binding_digest != binding_digest
            ):
                raise ValueError("release record belongs to a different binding")
            return {
                **current.model_dump(by_alias=True, mode="json"),
                "state": "already-released",
                "releasePath": str(path),
            }

        await self._check_binding(request, binding)
        release = ControllerBindingRelease(
            requestIdentity=request.identity,
            bindingDigest=binding_digest,
            serverEndpoint=binding.server_endpoint,
            sessionID=binding.session_id,
            releasedAtNanoseconds=time.time_ns(),
        )
        _atomic_json(path, release.model_dump(by_alias=True, mode="json"))
        return {
            **release.model_dump(by_alias=True, mode="json"),
            "releasePath": str(path),
        }
