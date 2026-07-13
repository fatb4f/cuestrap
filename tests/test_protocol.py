from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workbook"))

from cuestrap.models import ProbeRequest  # noqa: E402
from cuestrap.protocol import ProtocolError, bounded_path, reject_claimant_fields  # noqa: E402


class ProtocolTests(unittest.TestCase):
    def test_claimant_fields_are_rejected(self) -> None:
        with self.assertRaises(ProtocolError):
            reject_claimant_fields({"facts": {"passed": True}})

    def test_paths_are_bounded(self) -> None:
        with self.assertRaises(ProtocolError):
            bounded_path(ROOT, "../outside", must_exist=False)

    def test_unify_requires_operand(self) -> None:
        with self.assertRaises(ValueError):
            ProbeRequest.model_validate(
                {
                    "schema": "cuestrap.probe-request.v0",
                    "probeID": "x",
                    "moduleRoot": ".",
                    "files": ["tests/fixtures/basic.cue"],
                    "operation": "unify",
                    "expression": "valid",
                }
            )


if __name__ == "__main__":
    unittest.main()
