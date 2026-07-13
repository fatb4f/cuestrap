from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_ROOT = ROOT / "src/cue-workbook"
sys.path.insert(0, str(WORKBOOK_ROOT))

from mcp_server import McpServer  # noqa: E402
from backends import observe_cue_py  # noqa: E402
from lsp_client import LspSession  # noqa: E402
from models import (  # noqa: E402
    DEFAULT_WORKBOOK_REQUEST,
    OBSERVATION_PROTOCOL,
    HarnessError,
    HarnessFailure,
    ProbeObservation,
    SemanticSubject,
    SourceRef,
    materialize_subject,
    parse_probe_request,
)
from validation import execute_probe, run_properties  # noqa: E402
from runtime import observe_environment  # noqa: E402


class HarnessTests(unittest.TestCase):
    def test_default_request_materializes_stable_subject(self) -> None:
        request = parse_probe_request(DEFAULT_WORKBOOK_REQUEST)
        subject, module, files = materialize_subject(ROOT, request)
        self.assertEqual(module, ROOT)
        self.assertEqual([path.relative_to(ROOT).as_posix() for path in files], ["pattern/pilot.cue"])
        reparsed = SemanticSubject.model_validate(subject.model_dump(by_alias=True))
        self.assertEqual(reparsed.digest, subject.digest)

    def test_tampered_subject_digest_is_rejected(self) -> None:
        request = parse_probe_request(DEFAULT_WORKBOOK_REQUEST)
        subject, _, _ = materialize_subject(ROOT, request)
        value = subject.model_dump(by_alias=True)
        value["digest"] = "sha256:" + "0" * 64
        with self.assertRaises(ValidationError):
            SemanticSubject.model_validate(value)

    def test_claimant_request_field_is_rejected(self) -> None:
        value = dict(DEFAULT_WORKBOOK_REQUEST)
        value["passed"] = True
        with self.assertRaises(HarnessError) as caught:
            parse_probe_request(value)
        self.assertEqual(caught.exception.code, HarnessFailure.CLAIMANT_FIELD_PRESENT)

    def test_claimant_observation_field_is_rejected(self) -> None:
        request = parse_probe_request(DEFAULT_WORKBOOK_REQUEST)
        subject, _, _ = materialize_subject(ROOT, request)
        with self.assertRaises(HarnessError) as caught:
            ProbeObservation.model_validate(
                {
                    "schema": OBSERVATION_PROTOCOL,
                    "probeID": request.probe_id,
                    "evaluator": "test",
                    "stage": "evaluate",
                    "subject": subject.model_dump(by_alias=True),
                    "facts": {"admitted": True},
                    "diagnostics": [],
                    "commands": [],
                }
            )
        self.assertEqual(caught.exception.code, HarnessFailure.CLAIMANT_FIELD_PRESENT)

    def test_paths_are_repository_bounded(self) -> None:
        with self.assertRaises(HarnessError) as caught:
            SourceRef(path="../outside").resolve_under(ROOT, must_exist=False)
        self.assertEqual(caught.exception.code, HarnessFailure.PATH_ESCAPE)

    def test_deterministic_properties_pass(self) -> None:
        result = run_properties(ROOT)
        self.assertEqual(result["status"], "pass")
        self.assertGreater(result["examples"], 0)

    def test_probe_transport_degrades_to_raw_unavailable_observations(self) -> None:
        with patch("backends.shutil.which", return_value=None), patch.dict(
            os.environ,
            {"CUESTRAP_CUE_PY_ROOT": "", "CUESTRAP_LIBCUE_LIBRARY": ""},
            clear=False,
        ):
            result = execute_probe(ROOT, DEFAULT_WORKBOOK_REQUEST)
        self.assertEqual(result["schema"], "cuestrap.workbook-result.v0")
        self.assertFalse(result["cli"]["facts"]["available"])
        self.assertFalse(result["cuePy"]["facts"]["available"])
        self.assertTrue(result["comparison"]["equivalentSubjects"])

    def test_unavailable_cue_py_does_not_preprocess_sources(self) -> None:
        request = parse_probe_request(DEFAULT_WORKBOOK_REQUEST)
        with patch("backends._cue_py_environment", return_value=None), patch(
            "backends._cue_py_payload", side_effect=AssertionError("payload must not be built")
        ):
            result = observe_cue_py(ROOT, request)
        self.assertFalse(result.facts["available"])

    def test_canonical_interpreter_uses_virtualenv_prefix(self) -> None:
        with patch("runtime.shutil.which", return_value=None), patch(
            "runtime.sys.executable", "/usr/bin/python3.14"
        ), patch("runtime.sys.prefix", str(ROOT / ".venv")):
            result = observe_environment(ROOT)
        canonical = next(check for check in result.checks if check["id"] == "canonical-interpreter")
        self.assertEqual(canonical["status"], "pass")
        self.assertEqual(canonical["observed"], str((ROOT / ".venv").resolve()))

    def test_diagnostics_wait_for_a_new_publication(self) -> None:
        session = object.__new__(LspSession)
        path = ROOT / "pattern/pilot.cue"
        uri = path.resolve().as_uri()
        session.server = "cue-lsp"
        session._stderr = bytearray()
        session._diagnostics = {uri: [{"message": "old"}]}
        session._diagnostic_generations = {uri: 1}
        session._diagnostic_versions = {uri: 1}
        session._versions = {uri: 1}

        def open_document(_path: Path) -> str:
            session._versions[uri] = 2
            return uri

        def publish_diagnostics(_delay: float) -> None:
            session._diagnostics[uri] = [{"message": "new"}]
            session._diagnostic_generations[uri] = 2
            session._diagnostic_versions[uri] = 2

        session.open_document = Mock(side_effect=open_document)
        with patch("lsp_client.time.sleep", side_effect=publish_diagnostics):
            result = session.diagnostics(path)
        self.assertEqual(result["diagnostics"], [{"message": "new"}])

    def test_mcp_tool_surface_is_narrow(self) -> None:
        tools = McpServer("cue-lsp", ROOT).tools()
        self.assertEqual(
            [item["name"] for item in tools],
            ["diagnostics", "hover", "definition", "references", "document_symbols"],
        )


if __name__ == "__main__":
    unittest.main()
