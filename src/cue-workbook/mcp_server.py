"""Minimal MCP stdio facade for CUE LSP and gopls."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Literal, Mapping

from lsp_client import LspSession
from models import HarnessError, HarnessFailure, SourceRef

MCP_SERVER_VERSION = "0.1.0"


class McpServer:
    def __init__(self, server: Literal["cue-lsp", "gopls"], root: Path) -> None:
        self.server = server
        self.root = root.resolve(strict=True)
        self.session: LspSession | None = None

    def _session(self) -> LspSession:
        if self.session is None or self.session.process.poll() is not None:
            self.session = LspSession(self.server, self.root)
        return self.session

    def _path(self, value: object) -> Path:
        if not isinstance(value, str) or not value:
            raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "path is required")
        path = SourceRef(path=value).resolve_under(self.root)
        expected = ".cue" if self.server == "cue-lsp" else ".go"
        if path.suffix != expected:
            raise HarnessError(
                HarnessFailure.INVALID_PROTOCOL,
                f"{self.server} only accepts {expected} documents: {value}",
            )
        return path

    def tools(self) -> list[dict[str, Any]]:
        position_schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "path": {"type": "string"},
                "line": {"type": "integer", "minimum": 0, "default": 0},
                "character": {"type": "integer", "minimum": 0, "default": 0},
            },
            "required": ["path"],
        }
        path_schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        }
        return [
            {"name": "diagnostics", "description": f"Return advisory diagnostics from {self.server}.", "inputSchema": path_schema},
            {"name": "hover", "description": f"Request hover information from {self.server}.", "inputSchema": position_schema},
            {"name": "definition", "description": f"Request definitions from {self.server}.", "inputSchema": position_schema},
            {"name": "references", "description": f"Request references from {self.server}.", "inputSchema": position_schema},
            {"name": "document_symbols", "description": f"Request document symbols from {self.server}.", "inputSchema": path_schema},
        ]

    def call(self, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        session = self._session()
        path = self._path(arguments.get("path"))
        line = int(arguments.get("line", 0))
        character = int(arguments.get("character", 0))
        if name == "diagnostics":
            result = session.diagnostics(path)
        elif name == "hover":
            result = session.text_request("textDocument/hover", path, line, character)
        elif name == "definition":
            result = session.text_request("textDocument/definition", path, line, character)
        elif name == "references":
            uri = session.open_document(path)
            response = session.request(
                "textDocument/references",
                {
                    "textDocument": {"uri": uri},
                    "position": {"line": line, "character": character},
                    "context": {"includeDeclaration": True},
                },
            )
            result = {"server": self.server, "path": str(path), "response": response, "authoritative": False}
        elif name == "document_symbols":
            result = session.document_symbols(path)
        else:
            raise HarnessError(HarnessFailure.INVALID_PROTOCOL, f"unknown MCP tool: {name}")
        return {
            "content": [{"type": "text", "text": json.dumps(result, sort_keys=True, indent=2)}],
            "structuredContent": result,
        }

    def serve(self) -> int:
        try:
            for line in sys.stdin:
                if not line.strip():
                    continue
                message: object = None
                try:
                    message = json.loads(line)
                    if not isinstance(message, dict):
                        raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "MCP message must be an object")
                    response = self.handle(message)
                except Exception as error:
                    request_id = message.get("id") if isinstance(message, dict) else None
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32603, "message": f"{type(error).__name__}: {error}"[:1000]},
                    }
                if response is not None:
                    sys.stdout.write(json.dumps(response, sort_keys=True, separators=(",", ":")) + "\n")
                    sys.stdout.flush()
            return 0
        finally:
            if self.session is not None:
                self.session.close()

    def handle(self, message: Mapping[str, Any]) -> dict[str, Any] | None:
        method = message.get("method")
        request_id = message.get("id")
        if method == "initialize":
            # Establish the underlying persistent LSP session during MCP startup,
            # rather than deferring tool availability failures to the first call.
            self._session()
            params = message.get("params") or {}
            requested = params.get("protocolVersion", "2025-06-18") if isinstance(params, dict) else "2025-06-18"
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": requested,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": f"cuestrap-{self.server}", "version": MCP_SERVER_VERSION},
                    "instructions": f"Advisory {self.server} language intelligence for repository-bounded source files.",
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
                raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "invalid tools/call")
            return {"jsonrpc": "2.0", "id": request_id, "result": self.call(name, arguments)}
        if method == "resources/list":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"resources": []}}
        if request_id is None:
            return None
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"method not found: {method}"},
        }
