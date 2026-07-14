from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_ROOT = ROOT / "src/cue-workbook"
WORKBOOK = WORKBOOK_ROOT / "cue-workbook.py"
sys.path.insert(0, str(WORKBOOK_ROOT))

from code_mode_client import (  # noqa: E402
    CODE_MODE_OBSERVATION,
    TRANSACTION_PROTOCOL,
    CellTransaction,
    CodeModeClient,
    _RESULT_MARKER,
    _transaction_code,
    select_session,
)


def _inspection() -> dict[str, object]:
    return {
        "engine": {"marimoVersion": "test", "codeModeModule": "marimo._code_mode"},
        "cells": [],
        "graph": {"parents": {}, "children": {}, "definitions": {}},
        "variables": {},
    }


class CodeModeClientTests(unittest.IsolatedAsyncioTestCase):
    def test_select_session_requires_one_exact_resolved_path(self) -> None:
        session = select_session(
            [{"name": WORKBOOK.name, "path": str(WORKBOOK), "session_id": "bound"}],
            WORKBOOK,
        )
        self.assertEqual(session.session_id, "bound")
        with self.assertRaises(RuntimeError):
            select_session([], WORKBOOK)
        with self.assertRaises(RuntimeError):
            select_session(
                [
                    {"name": WORKBOOK.name, "path": str(WORKBOOK), "session_id": "one"},
                    {"name": WORKBOOK.name, "path": str(WORKBOOK), "session_id": "two"},
                ],
                WORKBOOK,
            )

    def test_transaction_is_closed_and_edits_require_source_identity(self) -> None:
        base = {
            "schema": TRANSACTION_PROTOCOL,
            "workbook": str(WORKBOOK),
            "operations": [{"kind": "edit", "target": "cell", "code": "x = 2"}],
        }
        with self.assertRaises(ValidationError):
            CellTransaction.model_validate(base)
        with self.assertRaises(ValidationError):
            CellTransaction.model_validate(
                {
                    "schema": TRANSACTION_PROTOCOL,
                    "workbook": str(WORKBOOK),
                    "operations": [{"kind": "run", "target": "cell", "verdict": True}],
                }
            )

    def test_transaction_code_verifies_before_edit_and_quotes_source(self) -> None:
        digest = "sha256:" + "0" * 64
        request = CellTransaction.model_validate(
            {
                "schema": TRANSACTION_PROTOCOL,
                "workbook": str(WORKBOOK),
                "operations": [
                    {
                        "kind": "edit",
                        "target": "cell-id",
                        "expectedCodeDigest": digest,
                        "code": "value = '''quoted'''\n",
                        "run": True,
                    }
                ],
            }
        )
        code = _transaction_code(request)
        self.assertLess(code.index("_verify(_ctx"), code.index("_ctx.edit_cell"))
        compile(code, "<transaction>", "exec", flags=0x2000)

    async def test_inspection_returns_identity_bound_raw_envelope(self) -> None:
        calls: list[tuple[str, dict[str, object] | None]] = []

        async def call_tool(name: str, arguments: dict[str, object] | None) -> dict[str, object]:
            calls.append((name, arguments))
            if name == "list_sessions":
                return {
                    "sessions": [
                        {"name": WORKBOOK.name, "path": str(WORKBOOK), "session_id": "session-1"}
                    ]
                }
            payload = _inspection()
            return {
                "success": True,
                "stdout": [_RESULT_MARKER + json.dumps(payload)],
                "stderr": [],
                "errors": [],
            }

        result = await CodeModeClient("http://example.test/mcp", WORKBOOK, call_tool=call_tool).inspect()
        self.assertEqual(result["schema"], CODE_MODE_OBSERVATION)
        self.assertEqual(result["session"]["session_id"], "session-1")
        self.assertEqual(result["transport"]["state"], "returned")
        self.assertNotIn("success", json.dumps(result))
        self.assertEqual([name for name, _ in calls], ["list_sessions", "execute_code"])

    async def test_transaction_recaptures_state_after_one_batch(self) -> None:
        execution_count = 0

        async def call_tool(name: str, arguments: dict[str, object] | None) -> dict[str, object]:
            nonlocal execution_count
            if name == "list_sessions":
                return {
                    "sessions": [
                        {"name": WORKBOOK.name, "path": str(WORKBOOK), "session_id": "session-1"}
                    ]
                }
            execution_count += 1
            code = str(arguments["code"] if arguments else "")
            payload = _inspection() if "_ctx.graph" in code else {
                "state": "applied",
                "createdCellIDs": [],
                "operationCount": 1,
            }
            return {
                "success": True,
                "stdout": [_RESULT_MARKER + json.dumps(payload)],
                "stderr": [],
                "errors": [],
            }

        request = CellTransaction.model_validate(
            {
                "schema": TRANSACTION_PROTOCOL,
                "workbook": str(WORKBOOK),
                "operations": [{"kind": "run", "target": "cell-id"}],
            }
        )
        result = await CodeModeClient("http://example.test/mcp", WORKBOOK, call_tool=call_tool).transact(
            request
        )
        self.assertEqual(execution_count, 2)
        self.assertEqual(result["observation"]["transaction"]["operationCount"], 1)
        self.assertIn("capture", result["observation"])
        self.assertEqual(result["observation"]["durability"]["state"], "unchanged")


if __name__ == "__main__":
    unittest.main()
