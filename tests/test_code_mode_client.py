from __future__ import annotations

import json
import ast
import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_ROOT = ROOT / "src/cue-workbook"
WORKBOOK = WORKBOOK_ROOT / "cue-workbook.py"
sys.path.insert(0, str(WORKBOOK_ROOT))

from bootstrap_client import (  # noqa: E402
    ApplyCellTransaction,
    BootstrapCodeModeClient,
    BootstrapRunBinding,
    CaptureState,
    MCPAdapter,
    QuarantinedObservation,
    ResolveSession,
    RunFocusedProbe,
    SessionBinding,
)
from bootstrap_client.client import PreHookDenied  # noqa: E402
from bootstrap_client.binding import (  # noqa: E402
    digest_file,
    local_client_identity,
    local_skill_identity,
)
from bootstrap_client.codegen.common import RESULT_MARKER  # noqa: E402
from bootstrap_client.codegen import (  # noqa: E402
    capture_state_code,
    cell_transaction_code,
    focused_probe_code,
)
from bootstrap_client.generated.models import digest_json, digest_text  # noqa: E402


def _run(phase: str = "inspect") -> BootstrapRunBinding:
    digest = digest_text("fixture")
    client = local_client_identity(ROOT).model_dump(by_alias=True, mode="json")
    skill = local_skill_identity(ROOT).model_dump(by_alias=True, mode="json")
    cue_source = digest_file(WORKBOOK_ROOT / "bootstrap_client/contracts.cue")
    return BootstrapRunBinding.model_validate(
        {
            "runID": "run-1",
            "attemptID": "attempt-1",
            "phase": phase,
            "controller": {"sourcePath": str(WORKBOOK), "sourceDigest": digest_file(WORKBOOK)},
            "target": {"repositoryDigest": digest, "workbookPath": str(WORKBOOK)},
            "client": client,
            "skill": skill,
            "marimo": {
                "engineIdentity": digest_text("marimo"),
                "engineRevision": digest_text("test"),
            },
            "authority": {"cueSourceDigest": cue_source, "cueEvaluatorDigest": digest},
        }
    )


def _session() -> SessionBinding:
    metadata = _session_metadata()
    return SessionBinding(
        session_id="session-1",
        workbook_path=str(WORKBOOK),
        session_metadata_digest=digest_json(metadata),
        resolved_at_sequence=0,
    )


def _session_metadata() -> dict[str, str]:
    return {"name": WORKBOOK.name, "path": str(WORKBOOK), "session_id": "session-1"}


def _session_list() -> dict[str, object]:
    return {"sessions": [_session_metadata()]}


def _identity(cell_digests: dict[str, str]) -> dict[str, object]:
    graph_digest = digest_json({})
    return {
        "revision": digest_json({"cellDigests": cell_digests, "graphDigest": graph_digest}),
        "cellDigests": cell_digests,
        "graphDigest": graph_digest,
    }


def _capture_payload(cell_digests: dict[str, str], *, after=None) -> dict[str, object]:
    before = _identity(cell_digests)
    return {
        "engine": {
            "engineIdentity": digest_text("marimo"),
            "engineRevision": digest_text("test"),
            "mode": "code-mode",
        },
        "before": before,
        "after": after or before,
        "state": {"cells": [], "missingCellIDs": []},
    }


def _returned(payload: dict[str, object]) -> dict[str, object]:
    return {
        "success": True,
        "stdout": [RESULT_MARKER + json.dumps(payload)],
        "stderr": [],
        "errors": [],
    }


class BootstrapCodeModeClientTests(unittest.IsolatedAsyncioTestCase):
    def test_operation_models_are_closed_and_replacement_digest_is_checked(self) -> None:
        with self.assertRaises(ValidationError):
            CaptureState.model_validate(
                {"operationID": "capture-1", "unexpected": "ambient request surface"}
            )

    def test_generated_requests_compile_and_transaction_verifies_before_edit(self) -> None:
        old_digest = digest_text("old")
        source = "value = '''quoted'''\n"
        operation = ApplyCellTransaction.model_validate(
            {
                "operationID": "tx-1",
                "transactionID": "transaction-1",
                "targetCells": [
                    {
                        "cellID": "cell-1",
                        "expectedPreimageDigest": old_digest,
                        "replacement": {"source": source, "sourceDigest": digest_text(source)},
                    }
                ],
                "expectedWorkbookRevision": digest_text("revision"),
            }
        )
        transaction_code = cell_transaction_code(operation)
        self.assertLess(transaction_code.index("preimage mismatch"), transaction_code.index("edit_cell"))
        compile(transaction_code, "<transaction>", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        compile(capture_state_code(CaptureState(operation_id="capture-1")), "<capture>", "exec")
        probe = RunFocusedProbe.model_validate(
            {
                "operationID": "probe-1",
                "questionID": "question-1",
                "subject": {
                    "workbookPath": str(WORKBOOK),
                    "cellIDs": ["cell-1"],
                    "variableNames": [],
                },
                "probe": {"templateID": "cell-source", "parameters": {"cellID": "cell-1"}},
                "expectedObservationShape": {"kind": "object", "requiredKeys": []},
            }
        )
        compile(focused_probe_code(probe), "<probe>", "exec")

    async def test_phase_denial_happens_before_any_mcp_dispatch(self) -> None:
        calls: list[str] = []

        async def call_tool(name, arguments):
            calls.append(name)
            return {}

        source = "replacement"
        operation = ApplyCellTransaction.model_validate(
            {
                "operationID": "tx-1",
                "transactionID": "transaction-1",
                "targetCells": [
                    {
                        "cellID": "cell-1",
                        "expectedPreimageDigest": digest_text("old"),
                        "replacement": {"source": source, "sourceDigest": digest_text(source)},
                    }
                ],
                "expectedWorkbookRevision": digest_text("revision"),
            }
        )
        client = BootstrapCodeModeClient(
            _run("inspect"),
            ROOT,
            MCPAdapter("http://example.test", call_tool=call_tool),
            session_binding=_session(),
        )
        with self.assertRaises(PreHookDenied):
            await client.apply_cell_transaction(operation)
        self.assertEqual(calls, [])
        with self.assertRaises(ValidationError):
            ApplyCellTransaction.model_validate(
                {
                    "operationID": "tx-1",
                    "transactionID": "transaction-1",
                    "targetCells": [
                        {
                            "cellID": "cell-1",
                            "expectedPreimageDigest": digest_text("old"),
                            "replacement": {
                                "source": "new",
                                "sourceDigest": digest_text("different"),
                            },
                        }
                    ],
                    "expectedWorkbookRevision": digest_text("workbook"),
                }
            )

    async def test_exact_path_session_resolution_issues_binding_and_records_raw_fact(self) -> None:
        calls: list[str] = []

        async def call_tool(name, arguments):
            calls.append(name)
            return {
                "sessions": [
                    {"name": WORKBOOK.name, "path": str(WORKBOOK), "session_id": "session-1"}
                ]
            }

        client = BootstrapCodeModeClient(
            _run(), ROOT, MCPAdapter("http://example.test", call_tool=call_tool)
        )
        binding = await client.resolve_session(
            ResolveSession(operation_id="resolve-1", workbook_path=str(WORKBOOK))
        )
        self.assertEqual(binding.session_id, "session-1")
        self.assertEqual(calls, ["list_sessions"])
        self.assertEqual(client.recorder.observations[0].transport.state, "returned")

    async def test_zero_or_ambiguous_exact_sessions_are_denied(self) -> None:
        for sessions in (
            [],
            [
                {"path": str(WORKBOOK), "session_id": "one"},
                {"path": str(WORKBOOK), "session_id": "two"},
            ],
        ):
            async def call_tool(name, arguments, sessions=sessions):
                return {"sessions": sessions}

            client = BootstrapCodeModeClient(
                _run(), ROOT, MCPAdapter("http://example.test", call_tool=call_tool)
            )
            with self.assertRaises(RuntimeError):
                await client.resolve_session(
                    ResolveSession(operation_id="resolve-1", workbook_path=str(WORKBOOK))
                )

    async def test_restored_session_binding_is_rechecked_before_execute(self) -> None:
        calls: list[str] = []

        async def call_tool(name, arguments):
            calls.append(name)
            return _session_list()

        stale = _session().model_copy(
            update={"session_metadata_digest": digest_text("stale-metadata")}
        )
        client = BootstrapCodeModeClient(
            _run(),
            ROOT,
            MCPAdapter("http://example.test", call_tool=call_tool),
            session_binding=stale,
        )
        with self.assertRaises(PreHookDenied):
            await client.capture_state(CaptureState(operation_id="capture-1"))
        self.assertEqual(calls, ["list_sessions"])

    async def test_read_only_capture_releases_only_raw_structural_observation(self) -> None:
        state = {"cell-1": digest_text("source")}

        async def call_tool(name, arguments):
            if name == "list_sessions":
                return _session_list()
            return _returned(_capture_payload(state))

        client = BootstrapCodeModeClient(
            _run(),
            ROOT,
            MCPAdapter("http://example.test", call_tool=call_tool),
            session_binding=_session(),
        )
        observation = await client.capture_state(CaptureState(operation_id="capture-1"))
        encoded = observation.model_dump_json(by_alias=True)
        self.assertEqual(observation.effects.changed_cell_ids, [])
        self.assertNotIn('"success"', encoded)
        self.assertNotIn('"valid"', encoded)
        self.assertNotIn('"admitted"', encoded)

    async def test_read_only_capture_that_changes_a_cell_is_quarantined(self) -> None:
        before = {"cell-1": digest_text("before")}
        after = _identity({"cell-1": digest_text("after")})

        async def call_tool(name, arguments):
            if name == "list_sessions":
                return _session_list()
            return _returned(_capture_payload(before, after=after))

        client = BootstrapCodeModeClient(
            _run(),
            ROOT,
            MCPAdapter("http://example.test", call_tool=call_tool),
            session_binding=_session(),
        )
        with self.assertRaises(QuarantinedObservation) as caught:
            await client.capture_state(CaptureState(operation_id="capture-1"))
        self.assertEqual(caught.exception.observation.effects.observed, "live-cells")

    async def test_probe_shape_mismatch_is_recorded_without_semantic_verdict(self) -> None:
        state = {"cell-1": digest_text("source")}
        payload = _capture_payload(state)
        payload["observation"] = "not-an-object"

        async def call_tool(name, arguments):
            if name == "list_sessions":
                return _session_list()
            return _returned(payload)

        operation = RunFocusedProbe.model_validate(
            {
                "operationID": "probe-1",
                "questionID": "question-1",
                "subject": {
                    "workbookPath": str(WORKBOOK),
                    "cellIDs": ["cell-1"],
                    "variableNames": [],
                },
                "probe": {"templateID": "cell-source", "parameters": {"cellID": "cell-1"}},
                "expectedObservationShape": {"kind": "object", "requiredKeys": ["cellID"]},
            }
        )
        client = BootstrapCodeModeClient(
            _run("probe"),
            ROOT,
            MCPAdapter("http://example.test", call_tool=call_tool),
            session_binding=_session(),
        )
        observation = await client.run_focused_probe(operation)
        self.assertFalse(observation.output.shape_matched)
        self.assertEqual(observation.execution.state, "exited")

    async def test_transaction_checks_preimage_compares_delta_and_closes_mutation_gate(self) -> None:
        old_digest = digest_text("old source")
        new_source = "new source"
        new_digest = digest_text(new_source)
        cells = {"cell-1": old_digest}
        execution_count = 0

        async def call_tool(name, arguments):
            nonlocal execution_count, cells
            if name == "list_sessions":
                return _session_list()
            execution_count += 1
            code = arguments["code"]
            if "_ctx.edit_cell" in code:
                cells = {"cell-1": new_digest}
                return _returned({"transactionID": "transaction-1"})
            return _returned(_capture_payload(cells))

        initial = _identity(cells)
        operation = ApplyCellTransaction.model_validate(
            {
                "operationID": "tx-1",
                "transactionID": "transaction-1",
                "targetCells": [
                    {
                        "cellID": "cell-1",
                        "expectedPreimageDigest": old_digest,
                        "replacement": {"source": new_source, "sourceDigest": new_digest},
                    }
                ],
                "expectedWorkbookRevision": initial["revision"],
            }
        )
        client = BootstrapCodeModeClient(
            _run("implement"),
            ROOT,
            MCPAdapter("http://example.test", call_tool=call_tool),
            session_binding=_session(),
        )
        observation = await client.apply_cell_transaction(operation)
        self.assertEqual(execution_count, 3)
        self.assertEqual(observation.structural_result, "applied-as-declared")
        with self.assertRaises(PreHookDenied):
            await client.apply_cell_transaction(operation)

    async def test_stale_transaction_is_denied_before_mutation_dispatch(self) -> None:
        cells = {"cell-1": digest_text("observed")}
        calls: list[str] = []

        async def call_tool(name, arguments):
            if name == "list_sessions":
                return _session_list()
            calls.append(arguments["code"])
            return _returned(_capture_payload(cells))

        operation = ApplyCellTransaction.model_validate(
            {
                "operationID": "tx-1",
                "transactionID": "transaction-1",
                "targetCells": [
                    {
                        "cellID": "cell-1",
                        "expectedPreimageDigest": digest_text("stale"),
                        "replacement": {
                            "source": "replacement",
                            "sourceDigest": digest_text("replacement"),
                        },
                    }
                ],
                "expectedWorkbookRevision": _identity(cells)["revision"],
            }
        )
        client = BootstrapCodeModeClient(
            _run("implement"),
            ROOT,
            MCPAdapter("http://example.test", call_tool=call_tool),
            session_binding=_session(),
        )
        with self.assertRaises(PreHookDenied):
            await client.apply_cell_transaction(operation)
        self.assertEqual(len(calls), 1)
        self.assertNotIn("_ctx.edit_cell", calls[0])


if __name__ == "__main__":
    unittest.main()
