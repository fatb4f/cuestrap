from __future__ import annotations

import copy, hashlib, json, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "cue-workbook"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bootstrap_client.lt01_protocol import (  # noqa: E402
    CANDIDATE_SET_DIGEST, INTENT_SCHEMA, PACKAGE_DIGEST, HarnessError,
    judgement_ingress, parse_intent, resolve_execution,
)
from bootstrap_client.lt01_execution import execute_intent, qualify_matrix  # noqa: E402


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


class LT01ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        accepted = self.root / "pattern/s04/fixtures/lt01/submissions/accepted/reference.cue"
        rejected = self.root / "pattern/s04/fixtures/lt01/submissions/wrong_answer/reversed-operands.cue"
        accepted.parent.mkdir(parents=True); rejected.parent.mkdir(parents=True)
        accepted.write_text("accepted-reference\n"); rejected.write_text("rejected-reversed-operands\n")
        self.accepted, self.rejected = digest(accepted.read_bytes()), digest(rejected.read_bytes())
        self.source = self._source()

    def tearDown(self): self.temp.cleanup()

    def _source(self):
        plans = {}
        cases = {}
        normal = {}
        compare = {}
        for stem, case, left, right in (
            ("directional", "directional-success", "directional-left", "directional-right"),
            ("reverse", "reverse-direction-rejection", "reverse-left", "reverse-right"),
            ("structural", "adversarial-structural", "structural-left", "structural-right"),
        ):
            plans[f"{stem}-plan"] = {"operations": [{"operationID": f"{stem}-operation", "kind": "subsumes", "left": {"subjectID": left}, "right": {"subjectID": right}, "direction": "left-to-right", "produces": [f"{stem}-raw"]}]}
            cases[case] = {"planID": f"{stem}-plan", "normalizationRuleIDs": [f"normalize-{stem}"], "comparisonRuleIDs": [f"compare-{stem}"], "requiredCapabilityIDs": ["cue-subsumes"]}
            normal[f"normalize-{stem}"] = {"observationFactID": f"{stem}-raw", "normalizedFactID": f"{stem}-normalized", "normalizedPredicate": "subsumes"}
            compare[f"compare-{stem}"] = {"expectedFactID": f"{stem}-expected", "normalizedFactID": f"{stem}-normalized", "operator": "equals", "resultPredicate": f"{stem}-matches"}
        return {
            "manifest": {"schema": "s04.lt01-fixture-design-manifest.v0", "trackingIssue": 18, "parentIssue": 12, "inputContractDigest": "sha256:"+"1"*64, "packageTreeDigest": PACKAGE_DIGEST, "candidateSetDigest": CANDIDATE_SET_DIGEST, "packageRoot": "pattern/s04/fixtures/lt01", "semanticArtifacts": {"realization": {"artifactID": "lt01-realization", "digest": "sha256:"+"2"*64}, "projection": {"artifactID": "lt01-projection", "digest": "sha256:"+"3"*64}, "contract": {"artifactID": "lt01-contract", "digest": "sha256:"+"4"*64}}, "sourceFiles": {}, "produces": ["LT01MinimalPPFPackage.v0"], "nextConsumer": "lt-01-execution-judgement-slice"},
            "realization": {"realizationID": "lt01-realization", "cases": cases, "plans": plans, "normalizationRules": normal, "comparisonRules": compare},
            "package": {"metadata": {"limits": {"time_limit": 1, "output": 64}}, "candidates": {"accepted-reference": {"evidencePath": "evidence/candidates/accepted-reference"}, "rejected-reversed-operands": {"evidencePath": "evidence/candidates/rejected-reversed-operands"}}},
            "semanticAuthorityID": "s04-semantic", "observerAuthorityID": "cuestrap-observer",
            "candidates": {"accepted-reference": {"candidateID": "accepted-reference", "sourcePath": "pattern/s04/fixtures/lt01/submissions/accepted/reference.cue", "digest": self.accepted}, "rejected-reversed-operands": {"candidateID": "rejected-reversed-operands", "sourcePath": "pattern/s04/fixtures/lt01/submissions/wrong_answer/reversed-operands.cue", "digest": self.rejected}},
        }

    @staticmethod
    def intent(candidate="accepted-reference", case="directional-success", action="execute-case"):
        return {"schema": INTENT_SCHEMA, "action": action, "candidateID": candidate, "caseID": case, "recovery": "none"}

    @staticmethod
    def probe(_root, request):
        value = "rejected-reversed-operands.reverse-direction-rejection" not in request["probeID"]
        return {"schema": "cuestrap.workbook-result.v0", "request": request, "cli": {}, "gopyWorker": {"facts": {"subsumes": value}}, "cueprobe": {"facts": {"subsumes": value}}, "nativeComparison": {"state": "shared-facts-equal"}}

    @staticmethod
    def derive(_root, replay, _source):
        return {"state": "cue-replay", "resultDigest": digest((replay["resolution"]["resolutionDigest"]+replay["rawRecord"]["recordDigest"]).encode())}

    def test_intent_rejects_manifest_resolved_fields(self):
        value = self.intent(); value["operationID"] = "forged"
        with self.assertRaises(HarnessError): parse_intent(value)

    def test_resolution_is_manifest_and_candidate_bound(self):
        resolved = resolve_execution(self.root, parse_intent(self.intent(case="reverse-direction-rejection")), self.source)
        self.assertEqual((resolved["operationID"], resolved["leftSubjectID"], resolved["rightSubjectID"]), ("reverse-operation", "reverse-left", "reverse-right"))
        stale = copy.deepcopy(self.source); stale["manifest"]["packageTreeDigest"] = "sha256:"+"0"*64
        with self.assertRaises(HarnessError): resolve_execution(self.root, parse_intent(self.intent()), stale)
        (self.root / self.source["candidates"]["accepted-reference"]["sourcePath"]).write_text("changed\n")
        with self.assertRaises(HarnessError): resolve_execution(self.root, parse_intent(self.intent()), self.source)

    def test_matrix_has_six_executions_and_three_fact_empty_witnesses(self):
        result = qualify_matrix(self.root, source=self.source, probe_executor=self.probe, judgement_executor=self.derive)
        self.assertEqual(len(result["records"]), 9)
        normal = [r for r in result["records"] if r["rawRecord"]["observationState"] == "facts-observed"]
        witnesses = [r for r in result["records"] if r["rawRecord"]["observationState"] != "facts-observed"]
        self.assertEqual(len(normal), 6)
        self.assertEqual({r["rawRecord"]["observationState"] for r in witnesses}, {"transport-failure", "capability-absent", "invalid-observation"})
        self.assertTrue(all(not r["rawRecord"]["facts"] for r in witnesses))
        reverse = next(r for r in normal if r["resolution"]["candidateID"] == "rejected-reversed-operands" and r["resolution"]["caseID"] == "reverse-direction-rejection")
        self.assertEqual(reverse["rawRecord"]["facts"], {"subsumes": False})
        self.assertEqual(len(result["evidence"]["recordDigests"]), 9)

    def test_ingress_contains_no_python_semantic_result(self):
        replay = execute_intent(self.root, self.intent(), source=self.source, probe_executor=self.probe)
        ingress = judgement_ingress(replay["resolution"], replay["rawRecord"], self.source)
        encoded = json.dumps(ingress, sort_keys=True)
        for field in ('"outcome"', '"comparisonResults"', '"normalizedFactSet"'):
            self.assertNotIn(field, encoded)

    def test_replay_is_deterministic(self):
        left = execute_intent(self.root, self.intent(), source=self.source, probe_executor=self.probe)
        right = execute_intent(self.root, self.intent(), source=self.source, probe_executor=self.probe)
        self.assertEqual(left["replayDigest"], right["replayDigest"])


if __name__ == "__main__": unittest.main()
