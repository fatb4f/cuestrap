#!/usr/bin/env python3
"""Operate one disposable controller workbook through constrained Marimo code-mode."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shlex
import signal
import socket
import subprocess
import sys
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

WORKBOOK_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(WORKBOOK_ROOT))

from bootstrap_client.binding import digest_file, resolve_exact_session  # noqa: E402
from bootstrap_client.codegen.common import (  # noqa: E402
    RESULT_MARKER,
    decode_marked_json,
    support_code,
)
from bootstrap_client.generated.models import SessionBinding  # noqa: E402
from bootstrap_client.mcp_adapter import MCPAdapter  # noqa: E402
from supervisory_hooks.controller import (  # noqa: E402
    ControllerRequest,
    _atomic_json,
    controller_operation_directory,
    validate_controller_request,
)
from supervisory_hooks.routing import decode_controller_request  # noqa: E402

CONTROLLER_HOST = "127.0.0.1"
CONTROLLER_PORT = 2719
CONTROLLER_ENDPOINT = f"http://{CONTROLLER_HOST}:{CONTROLLER_PORT}/mcp/server"
CONTROLLER_WEBSOCKET_ENDPOINT = f"ws://{CONTROLLER_HOST}:{CONTROLLER_PORT}/ws"
CONTROLLER_INSTANTIATE_ENDPOINT = (
    f"http://{CONTROLLER_HOST}:{CONTROLLER_PORT}/api/kernel/instantiate"
)
CONTROLLER_OPERATIONS = ("serve", "inspect", "execute", "diagnose", "close")
_LOCAL_PROCESSES: dict[int, subprocess.Popen[bytes]] = {}


class ControllerCodeModeBinding(BaseModel):
    """Closed binding to one disposable workbook process and exact Marimo session."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    schema_version: Literal["cuestrap.operation-controller-code-mode-binding/v0"] = Field(
        default="cuestrap.operation-controller-code-mode-binding/v0",
        alias="schema",
    )
    request_identity: str = Field(
        alias="requestIdentity",
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    endpoint: Literal[CONTROLLER_ENDPOINT] = CONTROLLER_ENDPOINT
    workbook_path: str = Field(alias="workbookPath")
    workbook_digest: str = Field(alias="workbookDigest")
    server_pid: int = Field(alias="serverPID", gt=0)
    session: SessionBinding


def _git_private_directory(repository_root: Path) -> Path:
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


def _binding_path(request: ControllerRequest, state_root: Path) -> Path:
    return controller_operation_directory(request, state_root) / "code-mode-binding.json"


def _load_binding(path: Path) -> ControllerCodeModeBinding:
    return ControllerCodeModeBinding.model_validate_json(path.read_text(encoding="utf-8"))


def _controller_tokens(
    repository_root: Path,
    payload: str,
    operation: str,
) -> tuple[str, ...]:
    return (
        str(repository_root / ".venv/bin/python"),
        str(WORKBOOK_ROOT / "operation_controller_cli.py"),
        "--repository-root",
        str(repository_root),
        "--payload",
        payload,
        operation,
    )


def _interaction_document(
    binding: ControllerCodeModeBinding,
    binding_path: Path,
    repository_root: Path,
    payload: str,
) -> dict[str, object]:
    return {
        "schema": "cuestrap.operation-controller-code-mode-session/v0",
        "state": "ready",
        "requestIdentity": binding.request_identity,
        "endpoint": binding.endpoint,
        "bindingPath": str(binding_path),
        "session": binding.session.model_dump(by_alias=True, mode="json"),
        "commands": {
            operation: shlex.join(_controller_tokens(repository_root, payload, operation))
            for operation in ("inspect", "execute", "diagnose", "close")
        },
    }


def _process_matches(pid: int, workbook: Path) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    command_line = Path(f"/proc/{pid}/cmdline")
    if command_line.exists():
        try:
            tokens = command_line.read_bytes().split(b"\0")
        except OSError:
            return False
        return str(workbook).encode() in tokens and b"marimo" in b" ".join(tokens)
    observed = subprocess.run(
        ["ps", "-p", str(pid), "-o", "command="],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return (
        observed.returncode == 0
        and str(workbook) in observed.stdout
        and "marimo" in observed.stdout
    )


def _signal_process_group(
    pid: int,
    workbook: Path,
    process_signal: signal.Signals,
) -> int | None:
    if not _process_matches(pid, workbook):
        return None
    process_group = os.getpgid(pid)
    if process_group != pid:
        raise RuntimeError("operation-controller process group identity mismatch")
    os.killpg(process_group, process_signal)
    return process_group


def _controller_stopped(pid: int, workbook: Path) -> bool:
    local_process = _LOCAL_PROCESSES.get(pid)
    if local_process is not None:
        local_process.poll()
    stopped = not _process_matches(pid, workbook) and _port_available()
    if stopped:
        _LOCAL_PROCESSES.pop(pid, None)
    return stopped


def _port_available() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
        candidate.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            candidate.bind((CONTROLLER_HOST, CONTROLLER_PORT))
        except OSError:
            return False
    return True


async def _resolve_live_session(
    workbook: Path,
    repository_root: Path,
    *,
    sequence: int,
) -> SessionBinding:
    result = await MCPAdapter(CONTROLLER_ENDPOINT).list_sessions(timeout_milliseconds=1000)
    sessions = result.payload.get("sessions")
    if result.transport_state != "returned" or not isinstance(sessions, list):
        raise RuntimeError("operation-controller code-mode server did not return sessions")
    return resolve_exact_session(
        sessions,
        workbook,
        repository_root,
        sequence=sequence,
    )


def _instantiate_session(session_id: str) -> None:
    request = Request(
        CONTROLLER_INSTANTIATE_ENDPOINT,
        data=json.dumps(
            {
                "objectIds": [],
                "values": [],
                "autoRun": True,
            }
        ).encode(),
        headers={
            "Content-Type": "application/json",
            "Marimo-Session-Id": session_id,
        },
        method="POST",
    )
    with urlopen(request, timeout=2) as response:
        result = json.load(response)
    if result != {"success": True}:
        raise RuntimeError(
            f"operation-controller session instantiation failed: {result!r}"
        )


async def _wait_for_session(workbook: Path, repository_root: Path) -> SessionBinding:
    query = urlencode({"session_id": f"cuestrap-controller-{uuid4()}"})
    websocket_endpoint = f"{CONTROLLER_WEBSOCKET_ENDPOINT}?{query}"
    last_error: Exception | None = None
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 10
    while loop.time() < deadline:
        try:
            async with connect(
                websocket_endpoint,
                open_timeout=1,
                close_timeout=1,
            ):
                while loop.time() < deadline:
                    try:
                        opened = await _resolve_live_session(
                            workbook,
                            repository_root,
                            sequence=0,
                        )
                        await asyncio.to_thread(
                            _instantiate_session,
                            opened.session_id,
                        )
                        break
                    except (RuntimeError, ValueError, OSError) as error:
                        last_error = error
                        await asyncio.sleep(0.1)
                else:
                    raise RuntimeError(
                        "operation-controller websocket did not create a session"
                    )
            while loop.time() < deadline:
                try:
                    orphaned = await _resolve_live_session(
                        workbook,
                        repository_root,
                        sequence=0,
                    )
                    if orphaned != opened:
                        raise RuntimeError(
                            "operation-controller session changed after websocket disconnect"
                        )
                    return orphaned
                except (RuntimeError, ValueError, OSError) as error:
                    last_error = error
                    await asyncio.sleep(0.1)
        except (RuntimeError, ValueError, OSError, WebSocketException) as error:
            last_error = error
            await asyncio.sleep(0.1)
    raise RuntimeError(f"operation-controller code-mode session did not start: {last_error}")


def _write_bound_request(request: ControllerRequest, operation_directory: Path) -> None:
    request_path = operation_directory / "request.json"
    document = request.model_dump(by_alias=True, mode="json", exclude_none=True)
    if request_path.exists():
        if json.loads(request_path.read_text(encoding="utf-8")) != document:
            raise ValueError("operation ID is already bound to a different controller request")
        return
    _atomic_json(request_path, document)


async def _serve(
    request: ControllerRequest,
    repository_root: Path,
    state_root: Path,
    payload: str,
) -> dict[str, object]:
    workbook = WORKBOOK_ROOT / "operation-controller.py"
    operation_directory = controller_operation_directory(request, state_root)
    binding_path = _binding_path(request, state_root)
    _write_bound_request(request, operation_directory)

    if binding_path.exists():
        current = _load_binding(binding_path)
        if current.request_identity != request.identity:
            raise ValueError("code-mode binding belongs to a different request")
        if _process_matches(current.server_pid, workbook):
            observed = await _resolve_live_session(workbook, repository_root, sequence=0)
            if observed == current.session:
                return _interaction_document(
                    current,
                    binding_path,
                    repository_root,
                    payload,
                )

    if not _port_available():
        raise RuntimeError(
            f"controller endpoint {CONTROLLER_ENDPOINT} is occupied by another process"
        )

    environment = os.environ.copy()
    environment.update(
        {
            "CUESTRAP_CONTROLLER_REQUEST": request.model_dump_json(
                by_alias=True,
                exclude_none=True,
            ),
            "CUESTRAP_CONTROLLER_REQUEST_IDENTITY": request.identity,
            "CUESTRAP_CONTROLLER_REPOSITORY_ROOT": str(repository_root),
            "CUESTRAP_CONTROLLER_STATE_ROOT": str(state_root),
        }
    )
    command = [
        sys.executable,
        "-m",
        "marimo",
        "edit",
        "--headless",
        "--no-token",
        "--no-skew-protection",
        "--host",
        CONTROLLER_HOST,
        "--port",
        str(CONTROLLER_PORT),
        "--mcp",
        "code-mode",
        str(workbook),
    ]
    operation_directory.mkdir(parents=True, exist_ok=True)
    stdout_log = (operation_directory / "code-mode.stdout.log").open("ab")
    stderr_log = (operation_directory / "code-mode.stderr.log").open("ab")
    try:
        process = subprocess.Popen(
            command,
            cwd=repository_root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=stdout_log,
            stderr=stderr_log,
            start_new_session=True,
        )
        _LOCAL_PROCESSES[process.pid] = process
    finally:
        stdout_log.close()
        stderr_log.close()

    try:
        session = await _wait_for_session(workbook, repository_root)
    except Exception:
        _signal_process_group(process.pid, workbook, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _signal_process_group(process.pid, workbook, signal.SIGKILL)
            process.wait(timeout=5)
        finally:
            _LOCAL_PROCESSES.pop(process.pid, None)
        raise

    binding = ControllerCodeModeBinding(
        requestIdentity=request.identity,
        workbookPath=str(workbook),
        workbookDigest=digest_file(workbook),
        serverPID=process.pid,
        session=session,
    )
    _atomic_json(
        binding_path,
        binding.model_dump(by_alias=True, mode="json"),
    )
    return _interaction_document(binding, binding_path, repository_root, payload)


def _bound_support_code(request: ControllerRequest) -> str:
    return support_code() + f'''
_ctx = _cm.get_context()
_bound_request = _ctx.globals.get("controller_request_model")
if _bound_request is None:
    raise RuntimeError("operation-controller workbook is not configured")
if _bound_request.identity != {request.identity!r}:
    raise RuntimeError("operation-controller request identity mismatch")
'''


def _inspect_code(request: ControllerRequest, *, include_receipt: bool) -> str:
    return _bound_support_code(request) + f'''
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
        _path(_ctx.globals["repository_root"]),
        _path(_ctx.globals["controller_state_root"]),
    )
    if _observed_receipt is not None:
        _receipt = _observed_receipt.model_dump(by_alias=True, mode="json", exclude_none=True)
_payload = {{
    "schema": "cuestrap.operation-controller-code-mode-observation/v0",
    "request": _bound_request.model_dump(by_alias=True, mode="json", exclude_none=True),
    "workbook": {{"identity": _identity(_ctx), "cells": _cells}},
    "receipt": _receipt,
}}
print({RESULT_MARKER!r} + _json.dumps(_payload, sort_keys=True, separators=(",", ":")))
'''


def _execute_code(request: ControllerRequest) -> str:
    return _bound_support_code(request) + f'''
_executor = _ctx.globals["execute_controller_request"]
_path = _ctx.globals["Path"]
_receipt = _executor(
    _bound_request,
    _path(_ctx.globals["repository_root"]),
    _path(_ctx.globals["controller_state_root"]),
)
_payload = _receipt.model_dump(by_alias=True, mode="json", exclude_none=True)
print({RESULT_MARKER!r} + _json.dumps(_payload, sort_keys=True, separators=(",", ":")))
'''


async def _checked_binding(
    request: ControllerRequest,
    repository_root: Path,
    state_root: Path,
) -> ControllerCodeModeBinding:
    binding = _load_binding(_binding_path(request, state_root))
    workbook = WORKBOOK_ROOT / "operation-controller.py"
    if binding.request_identity != request.identity:
        raise ValueError("code-mode binding belongs to a different request")
    if (
        binding.workbook_path != str(workbook)
        or binding.workbook_digest != digest_file(workbook)
    ):
        raise ValueError("code-mode binding workbook identity mismatch")
    if not _process_matches(binding.server_pid, workbook):
        raise RuntimeError("operation-controller code-mode process is not running")
    current = await _resolve_live_session(
        workbook,
        repository_root,
        sequence=binding.session.resolved_at_sequence,
    )
    if current != binding.session:
        raise RuntimeError("operation-controller code-mode session binding changed")
    return binding


async def _interact(
    operation: str,
    request: ControllerRequest,
    repository_root: Path,
    state_root: Path,
) -> tuple[int, object]:
    binding = await _checked_binding(request, repository_root, state_root)
    code = (
        _execute_code(request)
        if operation == "execute"
        else _inspect_code(request, include_receipt=operation == "diagnose")
    )
    result = await MCPAdapter(binding.endpoint).execute_code(
        binding.session.session_id,
        code,
        timeout_milliseconds=request.timeout_seconds * 1000,
    )
    decoded = decode_marked_json(result)
    if decoded is None:
        return 70, {
            "schema": "cuestrap.operation-controller-code-mode-fault/v0",
            "transportState": result.transport_state,
            "executionState": result.execution_state,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "errors": result.errors,
            "exceptionType": result.exception_type,
            "exceptionText": result.exception_text,
        }
    if operation == "execute" and isinstance(decoded.get("returnCode"), int):
        return int(decoded["returnCode"]), decoded
    return 0, decoded


async def _close(
    request: ControllerRequest,
    repository_root: Path,
    state_root: Path,
) -> dict[str, object]:
    del repository_root
    binding = _load_binding(_binding_path(request, state_root))
    workbook = WORKBOOK_ROOT / "operation-controller.py"
    if binding.request_identity != request.identity:
        raise ValueError("code-mode binding belongs to a different request")
    if binding.workbook_path != str(workbook):
        raise ValueError("code-mode binding workbook identity mismatch")
    process_group = _signal_process_group(
        binding.server_pid,
        workbook,
        signal.SIGTERM,
    )
    if process_group is None:
        return {
            "schema": "cuestrap.operation-controller-code-mode-close/v0",
            "state": "closed",
            "requestIdentity": request.identity,
        }
    for _attempt in range(50):
        if _controller_stopped(binding.server_pid, workbook):
            return {
                "schema": "cuestrap.operation-controller-code-mode-close/v0",
                "state": "closed",
                "requestIdentity": request.identity,
            }
        await asyncio.sleep(0.1)
    if (
        _signal_process_group(binding.server_pid, workbook, signal.SIGKILL)
        is None
    ):
        if _controller_stopped(binding.server_pid, workbook):
            return {
                "schema": "cuestrap.operation-controller-code-mode-close/v0",
                "state": "closed",
                "requestIdentity": request.identity,
            }
    for _attempt in range(50):
        if _controller_stopped(binding.server_pid, workbook):
            return {
                "schema": "cuestrap.operation-controller-code-mode-close/v0",
                "state": "closed",
                "requestIdentity": request.identity,
            }
        await asyncio.sleep(0.1)
    return {
        "schema": "cuestrap.operation-controller-code-mode-close/v0",
        "state": "termination-requested",
        "requestIdentity": request.identity,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--payload", required=True)
    parser.add_argument("operation", choices=CONTROLLER_OPERATIONS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        root = args.repository_root.resolve(strict=True)
        request = decode_controller_request(args.payload)
        validate_controller_request(request, root)
        state_root = _git_private_directory(root)
        if args.operation == "serve":
            code, value = 0, asyncio.run(_serve(request, root, state_root, args.payload))
        elif args.operation == "close":
            code, value = 0, asyncio.run(_close(request, root, state_root))
        else:
            code, value = asyncio.run(_interact(args.operation, request, root, state_root))
    except (OSError, RuntimeError, ValueError) as error:
        code = 70
        value = {
            "schema": "cuestrap.operation-controller-code-mode-fault/v0",
            "operation": args.operation,
            "exceptionType": type(error).__name__,
            "exceptionText": str(error),
        }
    print(json.dumps(value, sort_keys=True, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
