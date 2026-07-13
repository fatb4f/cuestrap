from __future__ import annotations

import json
import os
import selectors
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, BinaryIO

from ..process import run_process
from ..protocol import bounded_files


def _write_lsp(stream: BinaryIO, message: dict[str, Any]) -> None:
    body = json.dumps(message, separators=(",", ":")).encode()
    stream.write(f"Content-Length: {len(body)}\r\n\r\n".encode() + body)
    stream.flush()


def _read_lsp(buffer: bytearray) -> tuple[list[dict[str, Any]], bytearray]:
    messages: list[dict[str, Any]] = []
    while b"\r\n\r\n" in buffer:
        header, rest = buffer.split(b"\r\n\r\n", 1)
        length = None
        for line in header.split(b"\r\n"):
            if line.lower().startswith(b"content-length:"):
                length = int(line.split(b":", 1)[1].strip())
                break
        if length is None or len(rest) < length:
            break
        body, buffer = rest[:length], bytearray(rest[length:])
        try:
            value = json.loads(body)
        except json.JSONDecodeError:
            value = {"invalidMessage": body.decode("utf-8", "replace")[:2000]}
        if isinstance(value, dict):
            messages.append(value)
    return messages, buffer


def observe_diagnostics(
    server: str,
    repo_root: Path,
    files: list[str],
    timeout: float = 3.0,
) -> dict[str, Any]:
    repo_root = repo_root.resolve(strict=True)
    paths = bounded_files(repo_root, files)
    if server == "cue-lsp":
        argv, language_id = ["cue", "lsp"], "cue"
    elif server == "gopls":
        argv, language_id = ["gopls", "serve"], "go"
    else:
        raise ValueError(f"unsupported server: {server}")
    if shutil.which(argv[0]) is None:
        return {
            "availability": "unavailable",
            "server": server,
            "diagnostics": [],
            "reason": f"{argv[0]} not found",
        }

    process = subprocess.Popen(
        argv,
        cwd=repo_root,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None and process.stdout is not None
    started = time.monotonic()
    messages: list[dict[str, Any]] = []
    buffer = bytearray()
    try:
        _write_lsp(
            process.stdin,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "processId": os.getpid(),
                    "rootUri": repo_root.as_uri(),
                    "capabilities": {},
                },
            },
        )
        _write_lsp(
            process.stdin,
            {"jsonrpc": "2.0", "method": "initialized", "params": {}},
        )
        for path in paths:
            _write_lsp(
                process.stdin,
                {
                    "jsonrpc": "2.0",
                    "method": "textDocument/didOpen",
                    "params": {
                        "textDocument": {
                            "uri": path.as_uri(),
                            "languageId": language_id,
                            "version": 1,
                            "text": path.read_text(encoding="utf-8"),
                        }
                    },
                },
            )
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        idle_deadline = time.monotonic() + timeout
        while time.monotonic() < idle_deadline and len(messages) < 256:
            ready = selector.select(timeout=0.1)
            if not ready:
                continue
            chunk = os.read(process.stdout.fileno(), 65536)
            if not chunk:
                break
            buffer.extend(chunk)
            parsed, buffer = _read_lsp(buffer)
            messages.extend(parsed)
            idle_deadline = min(started + timeout, time.monotonic() + 0.4)
        _write_lsp(
            process.stdin,
            {"jsonrpc": "2.0", "id": 2, "method": "shutdown", "params": None},
        )
        _write_lsp(
            process.stdin,
            {"jsonrpc": "2.0", "method": "exit", "params": {}},
        )
        try:
            _, stderr = process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            process.terminate()
            _, stderr = process.communicate(timeout=2)
        diagnostics = [
            item
            for item in messages
            if item.get("method") == "textDocument/publishDiagnostics"
        ]
        return {
            "availability": "available",
            "server": server,
            "argv": argv,
            "diagnostics": diagnostics,
            "messages": messages,
            "stderr": stderr.decode("utf-8", "replace")[:4000],
            "authoritative": False,
        }
    except Exception as error:
        if process.poll() is None:
            process.kill()
            process.wait()
        return {
            "availability": "unavailable",
            "server": server,
            "diagnostics": [],
            "reason": f"{type(error).__name__}: {error}",
        }


def _mcp_result(value: Any) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(value, sort_keys=True)}],
        "structuredContent": value,
    }


def _tool_list(server: str) -> list[dict[str, Any]]:
    return [
        {
            "name": "diagnostics",
            "description": (
                f"Open repository files in {server} and return advisory LSP diagnostics."
            ),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["files"],
                "properties": {
                    "files": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string"},
                    },
                    "timeout": {
                        "type": "number",
                        "minimum": 0.5,
                        "maximum": 10,
                        "default": 3,
                    },
                },
            },
        },
        {
            "name": "version",
            "description": f"Return the configured {server} executable version.",
            "inputSchema": {"type": "object", "additionalProperties": False},
        },
    ]


def serve_mcp(server: str, repo_root: Path) -> int:
    repo_root = repo_root.resolve(strict=True)
    for line in sys.stdin:
        request: dict[str, Any] | None = None
        try:
            decoded = json.loads(line)
            if not isinstance(decoded, dict):
                continue
            request = decoded
            method = request.get("method")
            request_id = request.get("id")
            if method == "initialize":
                result = {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": f"cuestrap-{server}",
                        "version": "0.1.0",
                    },
                }
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": _tool_list(server)}
            elif method == "tools/call":
                params = request.get("params") or {}
                name = params.get("name")
                arguments = params.get("arguments") or {}
                if name == "diagnostics":
                    result = _mcp_result(
                        observe_diagnostics(
                            server,
                            repo_root,
                            list(arguments.get("files") or []),
                            float(arguments.get("timeout", 3)),
                        )
                    )
                elif name == "version":
                    argv = (
                        ["cue", "version"]
                        if server == "cue-lsp"
                        else ["gopls", "version"]
                    )
                    result = _mcp_result(
                        run_process(argv, cwd=repo_root, timeout=10).model_dump(
                            by_alias=True
                        )
                    )
                else:
                    raise ValueError(f"unknown tool: {name}")
            elif method and str(method).startswith("notifications/"):
                continue
            else:
                raise ValueError(f"unsupported method: {method}")
            if request_id is not None:
                print(
                    json.dumps(
                        {"jsonrpc": "2.0", "id": request_id, "result": result},
                        separators=(",", ":"),
                    ),
                    flush=True,
                )
        except Exception as error:
            request_id = request.get("id") if request else None
            if request_id is not None:
                print(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32000,
                                "message": f"{type(error).__name__}: {error}",
                            },
                        },
                        separators=(",", ":"),
                    ),
                    flush=True,
                )
    return 0
