from __future__ import annotations

import hashlib
import json
import subprocess
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
from native import (  # noqa: E402
    CUE_MODULE_VERSION,
    CUE_REVISION,
    NativeBindingUnavailable,
    binding_identity,
    import_bindings,
    verify_cue_cli,
    verify_cueprobe_artifact,
    verify_extension_artifact,
)
import native_backend  # noqa: E402
from native_backend import compare_native_backends, observe_cueprobe, observe_gopy_worker  # noqa: E402
from native_validation import execute_native_probe  # noqa: E402


class NativeHarnessTests(unittest.TestCase):
    def test_cue_cli_identity_requires_the_pinned_v018_revision(self) -> None:
        pinned = subprocess.CompletedProcess(
            [str(sys.executable), "version"],
            0,
            stdout=(
                "cue version v0.18.0-0.dev.0.20260713230317-806821e40fae\n\n"
                "CUE language version v0.18.0\n"
            ),
            stderr="",
        )
        stale = subprocess.CompletedProcess(
            [str(sys.executable), "version"],
            0,
            stdout="cue version v0.18.0\n\nCUE language version v0.18.0\n",
            stderr="",
        )
        with patch("native.subprocess.run", return_value=pinned):
            identity = verify_cue_cli(str(sys.executable))
        self.assertEqual(identity["cueRevision"], CUE_REVISION)
        self.assertEqual(identity["languageVersion"], CUE_MODULE_VERSION)
        with patch("native.subprocess.run", return_value=stale):
            with self.assertRaisesRegex(NativeBindingUnavailable, "identity mismatch"):
                verify_cue_cli(str(sys.executable))

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

    def test_large_integer_projection_matches_live_native_backends(self) -> None:
        configured = native_backend.os.environ.get("CUESTRAP_GOPY_MODULE_DIR")
        extension = (
            Path(configured).resolve()
            if configured
            else ROOT / "src" / "cue-workbook" / "cue_native"
        )
        cueprobe_binary = native_backend._cueprobe_path(
            ROOT,
            native_backend.os.environ.get("CUESTRAP_CUEPROBE"),
            native_backend.os.name,
        )
        native_files = [
            path
            for path in extension.glob("*")
            if path.suffix in {".so", ".dylib", ".dll", ".pyd"}
        ]
        if not native_files or not cueprobe_binary.is_file():
            self.skipTest("native artifacts have not been bootstrapped")

        number = 9_007_199_254_740_993
        request_data = {**DEFAULT_WORKBOOK_REQUEST, "concreteInput": number}
        request = parse_probe_request(request_data)
        gopy = observe_gopy_worker(ROOT, request)
        cueprobe = observe_cueprobe(ROOT, request)

        expected_digest = "sha256:" + hashlib.sha256(str(number).encode()).hexdigest()
        self.assertEqual(gopy.state, "project", gopy.diagnostics)
        self.assertEqual(cueprobe.state, "project", cueprobe.diagnostics)
        self.assertEqual(gopy.facts["concreteValueDigest"], expected_digest)
        self.assertEqual(cueprobe.facts["concreteValueDigest"], expected_digest)
        self.assertEqual(compare_native_backends(gopy, cueprobe)["state"], "shared-facts-equal")

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
                        "observedCUEModuleVersion": CUE_MODULE_VERSION,
                        "buildManifestDigest": "sha256:" + "1" * 64,
                        "artifactDigest": "sha256:" + "2" * 64,
                        "artifactManifestVerified": True,
                    },
                }
            )

        result = compare_native_backends(
            observation("gopy-worker", CUE_REVISION),
            observation("cueprobe", "0" * 40),
        )
        self.assertEqual(result["state"], "engine-identity-mismatch")
        self.assertFalse(result["equivalentEngines"])

    def test_native_comparison_rejects_absent_observed_identity(self) -> None:
        request = parse_probe_request(DEFAULT_WORKBOOK_REQUEST)
        subject, _, _ = materialize_subject(ROOT, request)
        extensions = {
            "cueRevision": CUE_REVISION,
            "cueModuleVersion": CUE_MODULE_VERSION,
            "buildManifestDigest": "sha256:" + "1" * 64,
            "artifactDigest": "sha256:" + "2" * 64,
            "artifactManifestVerified": True,
        }
        observations = [
            ProbeObservation.model_validate(
                {
                    "schema": OBSERVATION_PROTOCOL,
                    "probeID": request.probe_id,
                    "backend": backend,
                    "subjectDigest": subject.digest,
                    "subjectIdentity": subject.model_dump(by_alias=True),
                    "state": "project",
                    "facts": {"available": True, "semanticBottom": False},
                    "extensions": extensions,
                }
            )
            for backend in ("gopy-worker", "cueprobe")
        ]

        result = compare_native_backends(*observations)

        self.assertEqual(result["state"], "engine-identity-mismatch")
        self.assertFalse(result["equivalentEngines"])

    def test_native_comparison_requires_one_verified_build_manifest(self) -> None:
        request = parse_probe_request(DEFAULT_WORKBOOK_REQUEST)
        subject, _, _ = materialize_subject(ROOT, request)

        def observation(backend: str, manifest: str, verified: bool = True) -> ProbeObservation:
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
                        "cueRevision": CUE_REVISION,
                        "cueModuleVersion": CUE_MODULE_VERSION,
                        "observedCUEModuleVersion": CUE_MODULE_VERSION,
                        "buildManifestDigest": manifest,
                        "artifactDigest": "sha256:" + "2" * 64,
                        "artifactManifestVerified": verified,
                    },
                }
            )

        mismatched = compare_native_backends(
            observation("gopy-worker", "sha256:" + "1" * 64),
            observation("cueprobe", "sha256:" + "3" * 64),
        )
        unverified = compare_native_backends(
            observation("gopy-worker", "sha256:" + "1" * 64),
            observation("cueprobe", "sha256:" + "1" * 64, verified=False),
        )

        for result in (mismatched, unverified):
            self.assertEqual(result["state"], "engine-identity-mismatch")
            self.assertFalse(result["equivalentEngines"])

    def test_binding_identity_rejects_observed_module_mismatch(self) -> None:
        bindings = SimpleNamespace(
            IdentityJSON=lambda: json.dumps(
                {
                    "cue_revision": CUE_REVISION,
                    "cue_module_version": CUE_MODULE_VERSION,
                    "observed_cue_module_version": "v0.17.0",
                }
            )
        )

        with self.assertRaisesRegex(NativeBindingUnavailable, "compiled CUE module"):
            binding_identity(bindings)

    def test_artifacts_must_match_the_build_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            extension = root / "extension"
            artifact = extension / "binding.so"
            binary = root / "cueprobe"
            manifest_path = root / ".deps" / "manifest.json"
            extension.mkdir()
            manifest_path.parent.mkdir()
            artifact.write_bytes(b"extension")
            binary.write_bytes(b"cueprobe")
            extension_digest = "sha256:" + hashlib.sha256(artifact.read_bytes()).hexdigest()
            binary_digest = "sha256:" + hashlib.sha256(binary.read_bytes()).hexdigest()
            manifest_path.write_text(
                json.dumps(
                    {
                        "cue": {
                            "revision": CUE_REVISION,
                            "moduleVersion": CUE_MODULE_VERSION,
                        },
                        "extension": {
                            "files": [
                                {
                                    "relativePath": artifact.name,
                                    "digest": extension_digest,
                                }
                            ]
                        },
                        "cueprobe": {"digest": binary_digest},
                    }
                ),
                encoding="utf-8",
            )

            self.assertTrue(verify_extension_artifact(root, extension)["artifactManifestVerified"])
            self.assertTrue(verify_cueprobe_artifact(root, binary)["artifactManifestVerified"])
            artifact.write_bytes(b"stale")
            with self.assertRaisesRegex(NativeBindingUnavailable, "does not match"):
                verify_extension_artifact(root, extension)
            binary.write_bytes(b"stale")
            with self.assertRaisesRegex(NativeBindingUnavailable, "does not match"):
                verify_cueprobe_artifact(root, binary)

    def test_direct_import_fails_closed_when_extension_is_absent(self) -> None:
        with patch("native.importlib.import_module", side_effect=ImportError("missing")):
            with self.assertRaises(NativeBindingUnavailable):
                import_bindings()

    def test_package_selector_matches_live_native_backends(self) -> None:
        configured = native_backend.os.environ.get("CUESTRAP_GOPY_MODULE_DIR")
        extension = (
            Path(configured).resolve()
            if configured
            else ROOT / "src" / "cue-workbook" / "cue_native"
        )
        cueprobe_binary = native_backend._cueprobe_path(
            ROOT,
            native_backend.os.environ.get("CUESTRAP_CUEPROBE"),
            native_backend.os.name,
        )
        native_files = [
            path
            for path in extension.glob("*")
            if path.suffix in {".so", ".dylib", ".dll", ".pyd"}
        ]
        if not native_files or not cueprobe_binary.is_file():
            self.skipTest("native artifacts have not been bootstrapped")

        request_data = json.loads(
            (ROOT / "tests/fixtures/native-alternate-packages-request.json").read_text(
                encoding="utf-8"
            )
        )
        request = parse_probe_request(request_data)
        gopy = observe_gopy_worker(ROOT, request)
        cueprobe = observe_cueprobe(ROOT, request)

        self.assertEqual(gopy.state, "load-error", gopy.diagnostics)
        self.assertEqual(cueprobe.state, "load-error", cueprobe.diagnostics)
        self.assertTrue(gopy.diagnostics)
        self.assertTrue(cueprobe.diagnostics)
        self.assertTrue(compare_native_backends(gopy, cueprobe)["equivalentEngines"])

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
