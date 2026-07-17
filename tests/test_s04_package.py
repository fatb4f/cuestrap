from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_ROOT = ROOT / "src" / "cue-workbook"
sys.path.insert(0, str(WORKBOOK_ROOT))

from models import OBSERVATION_PROTOCOL, ProbeObservation  # noqa: E402
from s04_package import (  # noqa: E402
    CandidateFixture,
    candidate_probe_request,
    load_problem_package,
    normalize_native_observations,
    package_digest,
)


FIXTURE = ROOT / "tests" / "fixtures" / "s04-lt01-package.json"


def _observation(backend: str, *, subsumes: bool | None, state: str = "compare") -> ProbeObservation:
    facts: dict[str, object] = {"available": True}
    if subsumes is not None:
        facts["subsumes"] = subsumes
    return ProbeObservation.model_validate(
        {
            "schema": OBSERVATION_PROTOCOL,
            "probeID": "s04.lt-01.test",
            "backend": backend,
            "subjectDigest": "sha256:" + "1" * 64,
            "subjectIdentity": {
                "protocol": "cuestrap.subject-identity.v0",
                "probeID": "s04.lt-01.test",
                "digest": "sha256:" + "1" * 64,
                "extensions": {},
            },
            "state": state,
            "facts": facts,
            "diagnostics": [],
            "commands": [],
            "extensions": {},
        }
    )


class S04PackageTests(unittest.TestCase):
    def test_lt01_package_is_closed_and_contains_three_candidates(self) -> None:
        package, raw = load_problem_package(ROOT, FIXTURE.relative_to(ROOT))

        self.assertEqual(package.profile, "s04-kattis-ppf-v0")
        self.assertEqual(package.metadata.family, "LT-01")
        self.assertEqual(
            set(package.candidates),
            {
                "directional-success",
                "reverse-direction-rejection",
                "adversarial-structural-rejection",
            },
        )
        self.assertTrue(package_digest(raw).startswith("sha256:"))

    def test_candidate_adapter_preserves_operand_direction(self) -> None:
        package, _ = load_problem_package(ROOT, FIXTURE.relative_to(ROOT))
        forward = candidate_probe_request(package, package.candidates["directional-success"])
        reverse = candidate_probe_request(package, package.candidates["reverse-direction-rejection"])

        self.assertEqual(forward.subject_expression, "#LT01General")
        self.assertEqual(forward.candidate_expression, "#LT01Specific")
        self.assertEqual(reverse.subject_expression, "#LT01Specific")
        self.assertEqual(reverse.candidate_expression, "#LT01General")

    def test_exact_native_true_normalizes_to_ordering_holds(self) -> None:
        package, _ = load_problem_package(ROOT, FIXTURE.relative_to(ROOT))
        candidate = package.candidates["directional-success"]
        facts = normalize_native_observations(
            candidate,
            "operation-1",
            _observation("gopy-worker", subsumes=True),
            _observation("cueprobe", subsumes=True),
            {
                "state": "shared-facts-equal",
                "equivalentSubjects": True,
                "equivalentEngines": True,
            },
        )

        self.assertEqual(facts[0]["kind"], "orderingHolds")
        self.assertEqual(facts[0]["source"], "observation")
        self.assertTrue(facts[0]["value"])

    def test_exact_native_false_normalizes_to_ordering_rejection(self) -> None:
        package, _ = load_problem_package(ROOT, FIXTURE.relative_to(ROOT))
        candidate = package.candidates["adversarial-structural-rejection"]
        facts = normalize_native_observations(
            candidate,
            "operation-2",
            _observation("gopy-worker", subsumes=False),
            _observation("cueprobe", subsumes=False),
            {
                "state": "shared-facts-equal",
                "equivalentSubjects": True,
                "equivalentEngines": True,
            },
        )

        self.assertEqual(facts[0]["kind"], "orderingDoesNotHold")
        self.assertEqual(facts[0]["caseID"], candidate.case_id)

    def test_capability_gap_cannot_become_semantic_falsity(self) -> None:
        package, _ = load_problem_package(ROOT, FIXTURE.relative_to(ROOT))
        candidate = package.candidates["reverse-direction-rejection"]
        facts = normalize_native_observations(
            candidate,
            "operation-3",
            _observation("gopy-worker", subsumes=None, state="unavailable"),
            _observation("cueprobe", subsumes=None, state="unavailable"),
            {
                "state": "capability-gap",
                "equivalentSubjects": True,
                "equivalentEngines": False,
            },
        )

        self.assertEqual(facts[0]["kind"], "backendCapabilityAbsent")
        self.assertNotEqual(facts[0]["kind"], "orderingDoesNotHold")
        self.assertEqual(facts[0]["status"], "unavailable")

    def test_package_expectations_remain_distinct_from_observations(self) -> None:
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        expected = raw["realization"]["cases"]["directional-success"]["claim"]["expected"][0]

        self.assertEqual(expected["source"], "package")
        with self.assertRaises(Exception):
            CandidateFixture.model_validate({**raw["candidates"]["directional-success"], "unexpected": True})


if __name__ == "__main__":
    unittest.main()
