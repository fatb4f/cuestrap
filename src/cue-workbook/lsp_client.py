"""Persistent language-server process and bounded document operations."""
from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping

from models import HarnessError, HarnessFailure, _json_bytes


@dataclass
class _LspPending:
    response: queue.Queue[dict[str, Any]]


class LspSession:
    """Small persistent LSP client owned by one MCP server process."""

    def __init__(self, server: Literal["cue-lsp", "gopls"], root: Path) -> None:
        self.server = server
        self.root = root.resolve(strict=True)
        self.argv = ("cue", "lsp") if server == "cue-lsp" else ("gopls", "serve")
        executable = shutil.which(self.argv[0])
        if executable is None:
            raise HarnessError(HarnessFailure.TOOL_UNAVAILABLE, f"{self.argv[0]} unavailable")
        self.process = subprocess.Popen(
            [executable, *self.argv[1:]],
            cwd=self.root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._write_lock = threading.Lock()
        self._pending: dict[int, _LspPending] = {}
        self._pending_lock = threading.Lock()
        self._notifications: list[dict[str, Any]] = []
        self._diagnostics: dict[str, list[dict[str, Any]]] = {}
        self._diagnostic_generations: dict[str, int] = {}
        self._diagnostic_versions: dict[str, int] = {}
        self._next_id = 1
        self._versions: dict[str, int] = {}
        self._stderr = bytearray()
        threading.Thread(target=self._read_loop, daemon=True).start()
        threading.Thread(target=self._stderr_loop, daemon=True).start()
        initialize = self.request(
            "initialize",
            {
                "processId": os.getpid(),
                "rootUri": self.root.as_uri(),
                "workspaceFolders": [{"uri": self.root.as_uri(), "name": self.root.name}],
                "capabilities": {
                    "workspace": {"configuration": True, "workspaceFolders": True},
                    "textDocument": {
                        "publishDiagnostics": {"relatedInformation": True},
                        "documentSymbol": {},
                        "definition": {},
                        "references": {},
                        "hover": {},
                    },
                },
            },
            timeout=20,
        )
        if "error" in initialize:
            raise HarnessError(HarnessFailure.LSP_FAILURE, f"LSP initialize failed: {initialize['error']}")
        self.capabilities = initialize.get("result", {}).get("capabilities", {})
        self.notify("initialized", {})

    def _stderr_loop(self) -> None:
        assert self.process.stderr is not None
        while True:
            chunk = self.process.stderr.read(4096)
            if not chunk:
                return
            self._stderr.extend(chunk)
            if len(self._stderr) > 20000:
                del self._stderr[:-20000]

    def _read_loop(self) -> None:
        assert self.process.stdout is not None
        stream = self.process.stdout
        while True:
            headers: dict[str, str] = {}
            while True:
                line = stream.readline()
                if not line:
                    return
                if line in {b"\r\n", b"\n"}:
                    break
                name, _, value = line.decode("ascii", "replace").partition(":")
                headers[name.lower().strip()] = value.strip()
            try:
                length = int(headers.get("content-length", "0"))
            except ValueError:
                continue
            if length <= 0:
                continue
            body = stream.read(length)
            if len(body) != length:
                return
            try:
                message = json.loads(body)
            except json.JSONDecodeError:
                continue
            if not isinstance(message, dict):
                continue
            if "id" in message and "method" in message:
                self._respond_to_server_request(message)
            elif "id" in message and ("result" in message or "error" in message):
                with self._pending_lock:
                    pending = self._pending.get(int(message["id"]))
                if pending is not None:
                    pending.response.put(message)
            else:
                self._notifications.append(message)
                if message.get("method") == "textDocument/publishDiagnostics":
                    params = message.get("params", {})
                    uri = params.get("uri")
                    diagnostics = params.get("diagnostics")
                    if isinstance(uri, str) and isinstance(diagnostics, list):
                        self._diagnostics[uri] = diagnostics
                        self._diagnostic_generations[uri] = self._diagnostic_generations.get(uri, 0) + 1
                        version = params.get("version")
                        if isinstance(version, int):
                            self._diagnostic_versions[uri] = version
                        else:
                            self._diagnostic_versions.pop(uri, None)

    def _respond_to_server_request(self, message: Mapping[str, Any]) -> None:
        request_id = message["id"]
        method = message.get("method")
        params = message.get("params")
        if method == "workspace/configuration":
            items = params.get("items", []) if isinstance(params, dict) else []
            result: object = [None for _ in items]
        elif method == "workspace/workspaceFolders":
            result = [{"uri": self.root.as_uri(), "name": self.root.name}]
        elif method in {
            "client/registerCapability",
            "client/unregisterCapability",
            "window/workDoneProgress/create",
        }:
            result = None
        else:
            self._send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"unsupported client method: {method}"},
                }
            )
            return
        self._send({"jsonrpc": "2.0", "id": request_id, "result": result})

    def _send(self, message: Mapping[str, Any]) -> None:
        if self.process.poll() is not None:
            raise HarnessError(HarnessFailure.LSP_FAILURE, f"LSP exited: {self.stderr}")
        body = _json_bytes(message)
        frame = f"Content-Length: {len(body)}\r\n\r\n".encode() + body
        assert self.process.stdin is not None
        with self._write_lock:
            self.process.stdin.write(frame)
            self.process.stdin.flush()

    def request(self, method: str, params: object, *, timeout: float = 10) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        pending = _LspPending(queue.Queue(maxsize=1))
        with self._pending_lock:
            self._pending[request_id] = pending
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        try:
            return pending.response.get(timeout=timeout)
        except queue.Empty as error:
            raise HarnessError(HarnessFailure.LSP_FAILURE, f"LSP request timed out: {method}") from error
        finally:
            with self._pending_lock:
                self._pending.pop(request_id, None)

    def notify(self, method: str, params: object) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    @property
    def stderr(self) -> str:
        return bytes(self._stderr).decode("utf-8", "replace")

    def open_document(self, path: Path) -> str:
        path = path.resolve(strict=True)
        try:
            path.relative_to(self.root)
        except ValueError as error:
            raise HarnessError(HarnessFailure.PATH_ESCAPE, f"document escapes workspace: {path}") from error
        uri = path.as_uri()
        version = self._versions.get(uri, 0) + 1
        self._versions[uri] = version
        language = "cue" if path.suffix == ".cue" else "go"
        method = "textDocument/didOpen" if version == 1 else "textDocument/didChange"
        if method.endswith("didOpen"):
            params = {
                "textDocument": {
                    "uri": uri,
                    "languageId": language,
                    "version": version,
                    "text": path.read_text(encoding="utf-8"),
                }
            }
        else:
            params = {
                "textDocument": {"uri": uri, "version": version},
                "contentChanges": [{"text": path.read_text(encoding="utf-8")}],
            }
        self.notify(method, params)
        return uri

    def diagnostics(self, path: Path) -> dict[str, Any]:
        uri = path.resolve(strict=True).as_uri()
        generation = self._diagnostic_generations.get(uri, 0)
        uri = self.open_document(path)
        document_version = self._versions[uri]
        deadline = time.monotonic() + 3
        fresh = False
        while time.monotonic() < deadline:
            diagnostic_version = self._diagnostic_versions.get(uri)
            fresh = self._diagnostic_generations.get(uri, 0) > generation and (
                diagnostic_version is None or diagnostic_version >= document_version
            )
            if fresh:
                break
            time.sleep(0.05)
        return {
            "server": self.server,
            "path": str(path),
            "diagnostics": self._diagnostics.get(uri, []) if fresh else [],
            "stderr": self.stderr,
            "authoritative": False,
        }

    def text_request(self, method: str, path: Path, line: int = 0, character: int = 0) -> dict[str, Any]:
        uri = self.open_document(path)
        response = self.request(
            method,
            {"textDocument": {"uri": uri}, "position": {"line": line, "character": character}},
        )
        return {"server": self.server, "path": str(path), "response": response, "authoritative": False}

    def document_symbols(self, path: Path) -> dict[str, Any]:
        uri = self.open_document(path)
        response = self.request("textDocument/documentSymbol", {"textDocument": {"uri": uri}})
        return {"server": self.server, "path": str(path), "response": response, "authoritative": False}

    def close(self) -> None:
        if self.process.poll() is not None:
            return
        try:
            self.request("shutdown", None, timeout=2)
            self.notify("exit", {})
            self.process.wait(timeout=2)
        except Exception:
            self.process.kill()
            self.process.wait(timeout=2)
