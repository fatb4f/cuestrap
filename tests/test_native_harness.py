from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_ROOT = ROOT / "src/cue-workbook"
sys.path.insert(0, str(WORKBOOK_ROOT))

from models import DEFAULT_WORKBOOK_REQUEST, OBSERVATION_PROTOCOL, ProbeObservation, materialize_subject, parse_probe_request  # noqa: E402
from native import CUE_MODULE_VERSION, CUE_REVISION, NativeBindingUnavailable, import_bindings  # noqa: E402
import native_backend  # noqa: E402
from native_backend import compare_native_backends, observe_cueprobe, observe_gopy_worker  # noqa: E402
from native_validation import execute_native_probe  # noqa: E402


class NativeHarnessTests(unittest.TestCase):
    def test_gopy_file_lists_use_the_generated_slice_proxy(self) -> None:
        sentinel = object()
        constructor_calls: list[list[str]] = []

        def slice_string(values: list[str]) -> object:
            constructor_calls.append(values)
            return sentinel

        bindings = SimpleNamespace(go=SimpleNamespace(Slice_string=slice_string))
        result = native_backend._gopy_string_slice(bindings, ["one.cue", "two.cue"])
        self.assertIs(result, sentinel)
        self.assertEqual(constructor_calls, [["one.cue", "two.cue"]])

    def test_configured_gopy_package_parent_leads_pythonpath(self) -> None:
        request = parse_probe_request(DEFAULT_WORKBOOK_REQUEST)
        worker = SimpleNamespace(state="exited", exit_code=2, stderr="expected", stdout="")
        with tempfile.TemporaryDirectory() as temporary:
            module_root = Path(temporary) / "generated" / "cue_native"
            module_root.mkdir(parents=True)
            with patch.dict(
                "os.environ", {"CUESTRAP_GOPY_MODULE_DIR": str(module_root)}, clear=False
            ), patch("native_backend.run_process", return_value=worker) as run_worker:
                observe_gopy_worker(ROOT, request)

        environment = run_worker.call_args.kwargs["env"]
        self.assertEqual(
            environment["PYTHONPATH"].split(native_backend.os.pathsep)[0],
            str(module_root.parent),
        )

    def test_default_windows_cueprobe_has_exe_suffix(self) -> None:
        binary = native_backend._cueprobe_path(ROOT, None, "nt")
        self.assertEqual(binary.name, "cueprobe.exe")

    def test_missing_native_artifacts_are_typed_capability_gaps(self) -> None:
        request = parse_probe_request(DEFAULT_WORKBOOK_REQUEST)
        with patch.dict("os.environ", {"CUESTRAP_GOPY_MODULE_DIR": str(ROOT / "missing-native")}, clear=False):
            gopy = observe_gopy_worker(ROOT, request)
        with patch.dict("os.environ", {"CUESTRAP_CUEPROBE": str(ROOT / "missing-cueprobe")}, clear=False):
            cueprobe = observe_cueprobe(ROOT, request)
        self.assertEqual(gopy.state, "unavailable")
        self.assertEqual(cueprobe.state, "unavailable")
        self.assertFalse(gopy.facts["available"])
        self.assertFalse(cueprobe.facts["available"])
        comparison = compare_native_backends(gopy, cueprobe)
        self.assertEqual(comparison["state"], "capability-gap")
        self.assertTrue(comparison["equivalentSubjects"])

    def test_native_comparison_requires_engine_identity(self) -> None:
        request = parse_probe_request(DEFAULT_WORKBOOK_REQUEST)
        subject, _, _ = materialize_subject(ROOT, request)

        def observation(backend: str, revision: str) -> ProbeObservation:
            return ProbeObservation.model_validate(
                {
                    "schema": OBSERVATION_PROTOCOL,
                    "probeID": request.probe_id,
                    "backend": backend,
                    "subjectDigest": subject.digest,
                    "subjectIdentity": subject.model_dump(by_alias=True),
                    "state": "project",
                    "facts": {"available": True, "semanticBottom": False},
                    "extensions": {
                        "cueRevision": revision,
                        "cueModuleVersion": CUE_MODULE_VERSION,
                    },
                }
            )

        result = compare_native_backends(
            observation("gopy-worker", CUE_REVISION),
            observation("cueprobe", "0" * 40),
        )
        self.assertEqual(result["state"], "engine-identity-mismatch")
        self.assertFalse(result["equivalentEngines"])

    def test_direct_import_fails_closed_when_extension_is_absent(self) -> None:
        with patch("native.importlib.import_module", side_effect=ImportError("missing")):
            with self.assertRaises(NativeBindingUnavailable):
                import_bindings()

    def test_admitted_workbook_surface_excludes_cue_py(self) -> None:
        with patch("native_validation.observe_cli") as cli, patch(
            "native_validation.observe_gopy_worker"
        ) as gopy, patch("native_validation.observe_cueprobe") as cueprobe:
            request = parse_probe_request(DEFAULT_WORKBOOK_REQUEST)
            subject, _, _ = materialize_subject(ROOT, request)
            observations = []
            for backend in ("cue-cli", "gopy-worker", "cueprobe"):
                observations.append(
                    ProbeObservation.model_validate(
                        {
                            "schema": OBSERVATION_PROTOCOL,
                            "probeID": request.probe_id,
                            "backend": backend,
                            "subjectDigest": subject.digest,
                            "subjectIdentity": subject.model_dump(by_alias=True),
                            "state": "unavailable",
                            "facts": {"available": False},
                            "extensions": {
                                "cueRevision": CUE_REVISION,
                                "cueModuleVersion": CUE_MODULE_VERSION,
                            },
                        }
                    )
                )
            cli.return_value, gopy.return_value, cueprobe.return_value = observations
            result = execute_native_probe(ROOT, DEFAULT_WORKBOOK_REQUEST)
        self.assertIn("gopyWorker", result)
        self.assertIn("cueprobe", result)
        self.assertNotIn("cuePy", result)
        self.assertEqual(result["nativeComparison"]["state"], "capability-gap")


if __name__ == "__main__":
    unittest.main()
