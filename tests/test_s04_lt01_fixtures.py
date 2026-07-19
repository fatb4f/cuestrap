from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PATTERN_ROOT = ROOT / "pattern" / "s04"
PACKAGE_ROOT = PATTERN_ROOT / "fixtures" / "lt01"


class LT01FixtureDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        candidate = os.environ.get("CUESTRAP_CUE") or shutil.which("cue")
        if not candidate:
            raise unittest.SkipTest("CUESTRAP_CUE is not configured")
        cls.cue = Path(candidate).resolve(strict=True)
        cls.package_files = tuple(str(path) for path in sorted(PATTERN_ROOT.glob("*.cue")))

    @classmethod
    def _eval(cls, selector: str) -> Any:
        process = subprocess.run(
            (
                str(cls.cue),
                "eval",
                "-c",
                *cls.package_files,
                "-e",
                selector,
                "--out",
                "json",
            ),
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        if process.returncode != 0:
            raise AssertionError(process.stderr)
        return json.loads(process.stdout)

    def test_qualified_contract_is_publishable(self) -> None:
        contract = self._eval("lt01QualifiedContract.contract")
        self.assertEqual(contract["schema"], "s04.consumer-profile-contract.v0")
        self.assertEqual(
            set(contract["realization"]["cases"]),
            {
                "directional-success",
                "reverse-direction-rejection",
                "adversarial-structural",
            },
        )
        self.assertEqual(
            contract["realization"]["claims"]["reverse-claim"]["value"],
            False,
        )
        self.assertEqual(
            contract["realization"]["subjects"]["structural-left"]["source"]["expression"],
            "{a: int, b?: string}",
        )
        self.assertEqual(
            contract["package"]["candidates"]["accepted-reference"]["expectation"],
            "accepted",
        )
        self.assertEqual(
            contract["package"]["candidates"]["rejected-reversed-operands"]["expectation"],
            "rejected",
        )

    def test_manifest_binds_every_package_file_and_tree_digest(self) -> None:
        manifest = self._eval("lt01FixtureDesignManifest")
        declared = {item["path"]: item["digest"] for item in manifest["sourceFiles"].values()}
        actual_paths = {
            str(path.relative_to(ROOT))
            for path in PACKAGE_ROOT.rglob("*")
            if path.is_file()
        }
        self.assertEqual(set(declared), actual_paths)

        tree_lines: list[str] = []
        for repository_path in sorted(declared):
            content = (ROOT / repository_path).read_bytes()
            digest = "sha256:" + hashlib.sha256(content).hexdigest()
            self.assertEqual(declared[repository_path], digest)
            package_path = str((ROOT / repository_path).relative_to(PACKAGE_ROOT))
            tree_lines.append(f"{digest.removeprefix('sha256:')}  {package_path}\n")

        tree_digest = "sha256:" + hashlib.sha256("".join(tree_lines).encode()).hexdigest()
        self.assertEqual(manifest["packageTreeDigest"], tree_digest)

        accepted = (PACKAGE_ROOT / "submissions/accepted/reference.cue").read_bytes()
        rejected = (PACKAGE_ROOT / "submissions/wrong_answer/reversed-operands.cue").read_bytes()
        candidate_digest = "sha256:" + hashlib.sha256(
            hashlib.sha256(accepted).hexdigest().encode()
            + hashlib.sha256(rejected).hexdigest().encode()
        ).hexdigest()
        self.assertEqual(manifest["candidateSetDigest"], candidate_digest)

    def test_package_contains_declarations_but_no_runtime_evidence(self) -> None:
        evidence_files = {
            str(path.relative_to(PACKAGE_ROOT))
            for path in (PACKAGE_ROOT / "evidence").rglob("*")
            if path.is_file()
        }
        self.assertEqual(evidence_files, {"evidence/README.md"})

        forbidden_names = {
            "observation.json",
            "normalized-facts.json",
            "comparison-results.json",
            "judgement.json",
        }
        self.assertFalse(
            forbidden_names & {path.name for path in PACKAGE_ROOT.rglob("*") if path.is_file()}
        )

    def test_case_inputs_and_answers_preserve_direction_and_structure(self) -> None:
        expected = {
            "directional-success": True,
            "reverse-direction-rejection": False,
            "adversarial-structural": True,
        }
        for case_id, expected_value in expected.items():
            payload = json.loads((PACKAGE_ROOT / "data/secret" / f"{case_id}.in").read_text())
            answer = json.loads((PACKAGE_ROOT / "data/secret" / f"{case_id}.ans").read_text())
            self.assertEqual(payload["caseID"], case_id)
            self.assertEqual(payload["direction"], "left-to-right")
            self.assertEqual(answer["expectedValue"], expected_value)

        structural = json.loads(
            (PACKAGE_ROOT / "data/secret/adversarial-structural.in").read_text()
        )
        self.assertEqual(structural["left"], "{a: int, b?: string}")
        self.assertEqual(structural["right"], '{b: "x", a: 1}')


if __name__ == "__main__":
    unittest.main()
