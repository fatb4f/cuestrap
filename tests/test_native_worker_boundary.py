from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_ROOT = ROOT / "src/cue-workbook"
if str(WORKBOOK_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKBOOK_ROOT))

import native  # noqa: E402
import native_backend  # noqa: E402
from models import DEFAULT_WORKBOOK_REQUEST, parse_probe_request  # noqa: E402
from native import CUE_MODULE_VERSION, CUE_REVISION, NativeBindingUnavailable  # noqa: E402


class NativeWorkerBoundaryTests(unittest.TestCase):
    def test_gopy_execution_uses_recorded_worker_interpreter(self) -> None:
        request = parse_probe_request(DEFAULT_WORKBOOK_REQUEST)
        worker_python = Path("/opt/cuestrap/python3.13")
        process = SimpleNamespace(state="exited", exit_code=2, stderr="expected", stdout="")
        with tempfile.TemporaryDirectory() as temporary:
            module_root = Path(temporary) / "cue_native"
            module_root.mkdir()
            with patch.dict(
                "os.environ",
                {"CUESTRAP_GOPY_MODULE_DIR": str(module_root)},
                clear=False,
            ), patch(
                "native_backend.native_worker_python",
                return_value=worker_python,
            ), patch(
                "native_backend.run_process",
                return_value=process,
            ) as run_worker:
                native_backend.observe_gopy_worker(ROOT, request)

        command = run_worker.call_args.args[0]
        self.assertEqual(Path(command[0]), worker_python)
        self.assertEqual(Path(command[1]).name, "gopy_worker.py")
        self.assertNotIn("--gopy-worker", command)

    def test_manifest_binds_exact_worker_python_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = root / "python3.13"
            executable.write_text("placeholder")
            identity = {
                "executable": str(executable.resolve()),
                "abi": "cpython-313",
                "version": "3.13.14 test",
                "versionInfo": [3, 13, 14],
            }
            manifest = {
                "cue": {"revision": CUE_REVISION, "moduleVersion": CUE_MODULE_VERSION},
                "python": identity,
            }
            manifest_path = root / ".deps/manifest.json"
            manifest_path.parent.mkdir()
            manifest_path.write_text(json.dumps(manifest))

            with patch("native._python_identity", return_value=identity):
                self.assertEqual(native.native_worker_python(root), executable.resolve())

            changed = dict(identity)
            changed["abi"] = "cpython-313-changed"
            with patch("native._python_identity", return_value=changed):
                with self.assertRaisesRegex(NativeBindingUnavailable, "identity mismatch"):
                    native.native_worker_python(root)

    def test_manifest_rejects_non_313_worker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = root / "python"
            executable.write_text("placeholder")
            identity = {
                "executable": str(executable.resolve()),
                "abi": "cpython-314",
                "version": "3.14.3 test",
                "versionInfo": [3, 14, 3],
            }
            manifest_path = root / ".deps/manifest.json"
            manifest_path.parent.mkdir()
            manifest_path.write_text(
                json.dumps(
                    {
                        "cue": {"revision": CUE_REVISION, "moduleVersion": CUE_MODULE_VERSION},
                        "python": identity,
                    }
                )
            )
            with patch("native._python_identity", return_value=identity):
                with self.assertRaisesRegex(NativeBindingUnavailable, "must be 3.13"):
                    native.native_worker_python(root)


if __name__ == "__main__":
    unittest.main()
