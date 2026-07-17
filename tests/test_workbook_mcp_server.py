from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_ROOT = ROOT / "src/cue-workbook"
sys.path.insert(0, str(WORKBOOK_ROOT))

from bootstrap_client.binding import digest_file  # noqa: E402
from bootstrap_client.generated.models import digest_text  # noqa: E402
from supervisory_hooks.controller import ControllerRequest  # noqa: E402
from supervisory_hooks.execution_transport import classify_execution_argv  # noqa: E402
from workbook_adapter import ControllerCodeModeBinding  # noqa: E402
from workbook_mcp_server import WorkbookMcpServer  # noqa: E402


def _request() -> ControllerRequest:
    argv = ("rg", "hook", "src")
    operation = classify_execution_argv(
        argv,
        repository_root=ROOT,
        working_directory=ROOT,
    ).operation
    assert operation is not None
    return ControllerRequest.build(
        operationID="operation-1",
        sessionID="agent-session-1",
        turnID="turn-1",
        targetID=operation.target_id,
        requestDigest=operation.request_digest,
        proposedToolName="Bash",
        workingDirectory=".",
        argv=argv,
    )


def _binding(request: ControllerRequest) -> ControllerCodeModeBinding:
    return ControllerCodeModeBinding(
        requestIdentity=request.identity,
        serverEndpoint="http://127.0.0.1:2718/mcp/server",
        workbookPath=str(WORKBOOK_ROOT / "operation-controller.py"),
        workbookDigest=digest_file(WORKBOOK_ROOT / "operation-controller.py"),
        sessionID="controller-session-1",
        sessionDigest=digest_text("controller-session"),
        resolvedAtSequence=0,
    )


class WorkbookMcpServerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = AsyncMock()
        self.server = WorkbookMcpServer(ROOT, operation_service=self.service)

    def test_capability_discovery_exposes_typed_workbook_operations(self) -> None:
        tools = self.server.tools()
        names = {tool["name"] for tool in tools}
        self.assertEqual(
            names,
            {
                "resolve_session",
                "capture_state",
                "run_probe",
                "apply_transaction",
                "execute_realization",
                "bind_operation",
                "inspect_operation",
                "execute_operation",
                "collect_diagnosis",
                "release_binding",
            },
        )
        for tool in tools:
            schema = tool["inputSchema"]
            self.assertFalse(schema["additionalProperties"])
            self.assertNotIn("command", schema["properties"])
            self.assertNotIn("payload", schema["properties"])

    async def test_execute_realization_consumes_only_a_package_coordinate(self) -> None:
        result = {
            "schema": "cuestrap.s04-package-run/v0",
            "packageID": "s04.lt-01",
        }
        with patch("workbook_mcp_server.execute_s04_package", return_value=result) as execute:
            observed = await self.server.call(
                "execute_realization",
                {"packagePath": "tests/fixtures/s04-lt01-package.json"},
            )

        self.assertEqual(observed, result)
        execute.assert_called_once_with(ROOT, "tests/fixtures/s04-lt01-package.json")

    async def test_bind_operation_consumes_structured_request(self) -> None:
        request = _request()
        binding = _binding(request)
        self.service.bind_operation.return_value = binding

        result = await self.server.call(
            "bind_operation",
            {"request": request.model_dump(by_alias=True, mode="json")},
        )

        self.assertEqual(result["sessionID"], binding.session_id)
        self.assertEqual(result["requestIdentity"], request.identity)
        called = self.service.bind_operation.await_args.args[0]
        self.assertIsInstance(called, ControllerRequest)
        self.assertEqual(called, request)

    async def test_execute_operation_passes_typed_binding_to_service(self) -> None:
        request = _request()
        binding = _binding(request)
        receipt = {
            "schema": "cuestrap.operation-controller-receipt/v0",
            "returnCode": 0,
            "outcome": "returned",
        }
        self.service.execute_operation.return_value = receipt

        result = await self.server.call(
            "execute_operation",
            {
                "request": request.model_dump(by_alias=True, mode="json"),
                "binding": binding.model_dump(by_alias=True, mode="json"),
            },
        )

        self.assertEqual(result, receipt)
        called_request, called_binding = self.service.execute_operation.await_args.args
        self.assertEqual(called_request, request)
        self.assertEqual(called_binding, binding)

    async def test_initialize_describes_raw_and_judgement_boundaries(self) -> None:
        response = await self.server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18"},
            }
        )
        assert response is not None
        result = response["result"]
        self.assertEqual(result["serverInfo"]["name"], "cuestrap-workbook")
        self.assertIn("raw observations", result["instructions"])
        self.assertIn("CUE judge output", result["instructions"])


if __name__ == "__main__":
    unittest.main()
