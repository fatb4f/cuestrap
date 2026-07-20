from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PATTERN_ROOT = ROOT / "pattern" / "s04"
PACKAGE_ROOT = PATTERN_ROOT / "fixtures" / "lt01"

CASE_IDENTITIES = {
    "directional-success": {
        "planID": "directional-plan",
        "operationID": "directional-operation",
        "expectedFactID": "directional-expected",
        "normalizationRuleID": "normalize-directional",
        "comparisonRuleID": "compare-directional",
        "observationFactID": "directional-raw",
    },
    "reverse-direction-rejection": {
        "planID": "reverse-plan",
        "operationID": "reverse-operation",
        "expectedFactID": "reverse-expected",
        "normalizationRuleID": "normalize-reverse",
        "comparisonRuleID": "compare-reverse",
        "observationFactID": "reverse-raw",
    },
    "adversarial-structural": {
        "planID": "structural-plan",
        "operationID": "structural-operation",
        "expectedFactID": "structural-expected",
        "normalizationRuleID": "normalize-structural",
        "comparisonRuleID": "compare-structural",
        "observationFactID": "structural-raw",
    },
}


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

    @staticmethod
    def _load_case_fixture(case_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        payload = json.loads((PACKAGE_ROOT / "data/secret" / f"{case_id}.in").read_text())
        answer = json.loads((PACKAGE_ROOT / "data/secret" / f"{case_id}.ans").read_text())
        return payload, answer

    def _assert_case_chain(
        self,
        realization: dict[str, Any],
        case_id: str,
        payload: dict[str, Any],
        answer: dict[str, Any],
    ) -> None:
        identities = CASE_IDENTITIES[case_id]
        case = realization["cases"][case_id]
        self.assertEqual(case["planID"], identities["planID"])
        self.assertEqual(case["expectedFactIDs"], [identities["expectedFactID"]])
        self.assertEqual(case["normalizationRuleIDs"], [identities["normalizationRuleID"]])
        self.assertEqual(case["comparisonRuleIDs"], [identities["comparisonRuleID"]])

        plan = realization["plans"][case["planID"]]
        self.assertEqual(len(plan["operations"]), 1)
        operation = plan["operations"][0]
        self.assertEqual(operation["operationID"], identities["operationID"])
        self.assertEqual(operation["kind"], payload["operation"])
        self.assertEqual(operation["direction"], payload["direction"])

        ordered_refs = [operation["left"], operation["right"]]
        ordered_subject_ids = [item["subjectID"] for item in ordered_refs]
        self.assertEqual(case["subjectIDs"], ordered_subject_ids)
        self.assertEqual(
            realization["subjects"][ordered_subject_ids[0]]["source"]["expression"],
            payload["left"],
        )
        self.assertEqual(
            realization["subjects"][ordered_subject_ids[1]]["source"]["expression"],
            payload["right"],
        )

        normalization = realization["normalizationRules"][identities["normalizationRuleID"]]
        self.assertEqual(normalization["observationFactID"], identities["observationFactID"])
        self.assertEqual(operation["produces"], [normalization["observationFactID"]])

        expected_fact = realization["expectedFacts"][identities["expectedFactID"]]
        claim = realization["claims"][expected_fact["claimID"]]
        self.assertEqual(claim["operands"], ordered_refs)
        self.assertEqual(claim["predicate"], payload["operation"])
        self.assertEqual(expected_fact["predicate"], answer["predicate"])
        self.assertEqual(claim["value"], answer["expectedValue"])
        self.assertEqual(expected_fact["expectedValue"], answer["expectedValue"])

        comparison = realization["comparisonRules"][identities["comparisonRuleID"]]
        self.assertEqual(comparison["expectedFactID"], identities["expectedFactID"])
        self.assertEqual(comparison["normalizedFactID"], normalization["normalizedFactID"])

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

    def test_manifest_binds_semantic_artifact_identities(self) -> None:
        contract = self._eval("lt01QualifiedContract.contract")
        identity_evidence = self._eval("lt01SemanticIdentityEvidence")
        manifest = self._eval("lt01FixtureDesignManifest")

        expected_payloads = {
            "realization": contract["realization"],
            "projection": {
                key: value
                for key, value in contract["projection"].items()
                if key != "projectionDigest"
            },
            "contract": {
                key: value for key, value in contract.items() if key != "contractDigest"
            },
        }
        expected_ids = {
            "realization": contract["realization"]["realizationID"],
            "projection": contract["projection"]["projectionID"],
            "contract": contract["contractID"],
        }

        for artifact_kind, expected_payload in expected_payloads.items():
            evidence = identity_evidence[artifact_kind]
            digest = "sha256:" + hashlib.sha256(evidence["canonicalJSON"].encode()).hexdigest()
            self.assertEqual(evidence["canonicalPayload"], expected_payload)
            self.assertEqual(evidence["artifactID"], expected_ids[artifact_kind])
            self.assertEqual(evidence["digest"], digest)
            self.assertEqual(
                manifest["semanticArtifacts"][artifact_kind],
                {"artifactID": expected_ids[artifact_kind], "digest": digest},
            )

        self.assertEqual(contract["contractDigest"], identity_evidence["contract"]["digest"])
        self.assertEqual(
            contract["projection"]["projectionDigest"],
            identity_evidence["projection"]["digest"],
        )
        self.assertEqual(
            contract["projection"]["realizationDigest"],
            identity_evidence["realization"]["digest"],
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

    def test_case_inputs_and_answers_bind_ordered_semantic_chain(self) -> None:
        realization = self._eval("lt01QualifiedContract.contract.realization")
        for case_id in CASE_IDENTITIES:
            payload, answer = self._load_case_fixture(case_id)
            self.assertEqual(payload["caseID"], case_id)
            self.assertEqual(answer["caseID"], case_id)
            self._assert_case_chain(realization, case_id, payload, answer)

        structural, _ = self._load_case_fixture("adversarial-structural")
        self.assertEqual(structural["left"], "{a: int, b?: string}")
        self.assertEqual(structural["right"], '{b: "x", a: 1}')

    def test_reverse_operand_swap_regression_is_rejected(self) -> None:
        realization = self._eval("lt01QualifiedContract.contract.realization")
        mutated = deepcopy(realization)
        operation = mutated["plans"]["reverse-plan"]["operations"][0]
        operation["left"], operation["right"] = operation["right"], operation["left"]
        payload, answer = self._load_case_fixture("reverse-direction-rejection")

        with self.assertRaises(AssertionError):
            self._assert_case_chain(
                mutated,
                "reverse-direction-rejection",
                payload,
                answer,
            )


if __name__ == "__main__":
    unittest.main()
