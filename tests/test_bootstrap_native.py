from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_ROOT = ROOT / "src/cue-workbook"
sys.path.insert(0, str(WORKBOOK_ROOT))

import bootstrap_native  # noqa: E402


class BootstrapNativeTests(unittest.TestCase):
    def test_gopy_build_is_staged_inside_the_runner_module(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runner = root / "runner"
            tools = root / "tools"
            extension = root / "workbook" / "cue_native"
            runner.mkdir()
            tools.mkdir()
            extension.parent.mkdir()

            def generate(*args: str, **kwargs: object) -> None:
                output = next(item.removeprefix("-output=") for item in args if item.startswith("-output="))
                generated = Path(output)
                self.assertTrue(generated.is_relative_to(runner))
                generated.mkdir(parents=True)
                (generated / "bindings.py").write_text("# generated\n", encoding="utf-8")

            with patch("bootstrap_native.run", side_effect=generate):
                bootstrap_native.build_extension(root / "gopy", runner, tools, extension)

            self.assertTrue((extension / "bindings.py").is_file())
            self.assertFalse((runner / "bin" / "cue_native").exists())


if __name__ == "__main__":
    unittest.main()
