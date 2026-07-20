from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "cue-workbook"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bootstrap_client.lt01_execution import execute_intent, qualify_matrix  # noqa: E402
from bootstrap_client.lt01_protocol import (  # noqa: E402
    CANDIDATE_SET_DIGEST,
    INPUT_CONTRACT_DIGEST,
    INTENT_SCHEMA,
    PACKAGE_DIGEST,
    HarnessError,
    judgement_ingress,
    parse_intent,
    resolve_execution,
)


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest_json(value: object) -> str:
    return digest(canonical_json(value).encode())


class LT01ExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        accepted = self.root / "pattern/s04/fixtures/lt01/submissions/accepted/reference.cue"
        rejected = self.root / "pattern/s04/fixtures/lt01/submissions/wrong_answer/reversed-operands.cue"
        accepted.parent.mkdir(parents=True)
        rejected.parent.mkdir(parents=True)
        accepted.write_text("accepted-reference\n")
        rejected.write_text("rejected-reversed-operands\n")
        self.accepted = digest(accepted.read_bytes())
        self.rejected = digest(rejected.read_bytes())
        self.source = self._source()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _source(self) -> dict[str, object]:
        plans: dict[str, object] = {}
        cases: dict[str, object] = {}
        package_cases: dict[str, object] = {}
        bindings: dict[str, object] = {}
        normal: dict[str, object] = {}
        compare: dict[str, object] = {}
        for stem, case_id, left, right in (
            ("directional", "directional-success", "directional-left", "directional-right"),
            ("reverse", "reverse-direction-rejection", "reverse-left", "reverse-right"),
            ("structural", "adversarial-structural", "structural-left", "structural-right"),
        ):
            plans[f"{stem}-plan"] = {
                "operations": [{
                    "operationID": f"{stem}-operation",
                    "kind": "subsumes",
                    "left": {"subjectID": left},
                    "right": {"subjectID": right},
                    "direction": "left-to-right",
                    "produces": [f"{stem}-raw"],
                }]
            }
            cases[case_id] = {
                "planID": f"{stem}-plan",
                "subjectIDs": [left, right],
                "normalizationRuleIDs": [f"normalize-{stem}"],
                "comparisonRuleIDs": [f"compare-{stem}"],
                "requiredCapabilityIDs": ["cue-subsumes"],
                "outcomeConstraint": {
                    "permitted": ["satisfied", "rejected", "indeterminate"],
                    "required": "satisfied",
                },
            }
            package_cases[case_id] = {"caseID": case_id}
            bindings[case_id] = {
                "bindingID": case_id,
                "realizationCaseID": case_id,
                "packageCaseID": case_id,
            }
            normal[f"normalize-{stem}"] = {
                "observationFactID": f"{stem}-raw",
                "normalizedFactID": f"{stem}-normalized",
                "normalizedPredicate": "subsumes",
            }
            compare[f"compare-{stem}"] = {
                "expectedFactID": f"{stem}-expected",
                "normalizedFactID": f"{stem}-normalized",
                "operator": "equals",
                "resultPredicate": f"{stem}-matches",
            }

        realization = {
            "realizationID": "lt01-realization",
            "cases": cases,
            "plans": plans,
            "normalizationRules": normal,
            "comparisonRules": compare,
        }
        package = {
            "packageDigest": PACKAGE_DIGEST,
            "metadata": {"limits": {"time_limit": 1, "output": 64}},
            "cases": package_cases,
            "candidates": {
                "accepted-reference": {
                    "sourcePath": "submissions/accepted/reference.cue",
                    "evidencePath": "evidence/candidates/accepted-reference",
                },
                "rejected-reversed-operands": {
                    "sourcePath": "submissions/wrong_answer/reversed-operands.cue",
                    "evidencePath": "evidence/candidates/rejected-reversed-operands",
                },
            },
        }
        projection = {
            "projectionID": "lt01-projection",
            "caseBindings": bindings,
        }
        contract = {
            "contractID": "lt01-consumer-profile",
            "realization": realization,
            "package": package,
            "projection": projection,
        }
        semantic_payloads = {
            "realization": canonical_json(realization),
            "projection": canonical_json(projection),
            "contract": canonical_json(contract),
        }
        semantic_artifacts = {
            "realization": {
                "artifactID": "lt01-realization",
                "digest": digest(semantic_payloads["realization"].encode()),
            },
            "projection": {
                "artifactID": "lt01-projection",
                "digest": digest(semantic_payloads["projection"].encode()),
            },
            "contract": {
                "artifactID": "lt01-consumer-profile",
                "digest": digest(semantic_payloads["contract"].encode()),
            },
        }
        manifest = {
            "schema": "s04.lt01-fixture-design-manifest.v0",
            "trackingIssue": 18,
            "parentIssue": 12,
            "inputContractDigest": INPUT_CONTRACT_DIGEST,
            "packageTreeDigest": PACKAGE_DIGEST,
            "candidateSetDigest": CANDIDATE_SET_DIGEST,
            "packageRoot": "pattern/s04/fixtures/lt01",
            "semanticArtifacts": semantic_artifacts,
            "sourceFiles": {},
            "produces": ["LT01MinimalPPFPackage.v0"],
            "nextConsumer": "lt-01-execution-judgement-slice",
        }
        return {
            "manifest": manifest,
            "realization": realization,
            "package": package,
            "semanticArtifacts": copy.deepcopy(semantic_artifacts),
            "semanticCanonicalJSON": semantic_payloads,
            "caseBindings": bindings,
            "semanticAuthorityID": "s04-semantic",
            "observerAuthorityID": "cuestrap-observer",
            "candidates": {
                "accepted-reference": {
                    "candidateID": "accepted-reference",
                    "sourcePath": "pattern/s04/fixtures/lt01/submissions/accepted/reference.cue",
                    "digest": self.accepted,
                },
                "rejected-reversed-operands": {
                    "candidateID": "rejected-reversed-operands",
                    "sourcePath": "pattern/s04/fixtures/lt01/submissions/wrong_answer/reversed-operands.cue",
                    "digest": self.rejected,
                },
            },
        }

    @staticmethod
    def intent(
        candidate: str = "accepted-reference",
        case: str = "directional-success",
        action: str = "execute-case",
    ) -> dict[str, str]:
        return {
            "schema": INTENT_SCHEMA,
            "action": action,
            "candidateID": candidate,
            "caseID": case,
            "recovery": "none",
        }

    @staticmethod
    def _cueprobe_result(request: dict[str, object], *, verified: bool = True) -> dict[str, object]:
        reverse = str(request["probeID"]).endswith("reverse-direction-rejection")
        rejected = "rejected-reversed-operands" in str(request["probeID"])
        value = rejected if reverse else True
        return {
            "schema": "cuestrap.lt01-cueprobe-observation.v0",
            "cueprobe": {
                "state": "compare",
                "facts": {"available": True, "subsumes": value},
                "diagnostics": [],
                "extensions": {
                    "cueRevision": "806821e40fae070318600a264d311517e596353b",
                    "cueModuleVersion": "v0.18.0",
                    "observedCUEModuleVersion": "v0.18.0",
                    "artifactManifestVerified": verified,
                    "buildManifestDigest": "sha256:" + "5" * 64,
                    "artifactDigest": "sha256:" + "6" * 64,
                },
            },
        }

    @classmethod
    def probe(cls, _root: Path, request: dict[str, object]) -> dict[str, object]:
        return cls._cueprobe_result(request)

    @classmethod
    def unverified_probe(cls, _root: Path, request: dict[str, object]) -> dict[str, object]:
        return cls._cueprobe_result(request, verified=False)

    @staticmethod
    def derive(_root: Path, replay: dict[str, object], _source: dict[str, object]) -> dict[str, str]:
        resolution = replay["resolution"]
        raw = replay["rawRecord"]
        assert isinstance(resolution, dict) and isinstance(raw, dict)
        result_digest = digest((str(resolution["resolutionDigest"]) + str(raw["recordDigest"])).encode())
        return {"state": "cue-replay", "resultDigest": result_digest}

    def test_intent_rejects_manifest_resolved_fields(self) -> None:
        value = self.intent()
        value["operationID"] = "forged"
        with self.assertRaises(HarnessError):
            parse_intent(value)

    def test_resolution_is_semantic_manifest_case_and_candidate_bound(self) -> None:
        resolved = resolve_execution(
            self.root,
            parse_intent(self.intent(case="reverse-direction-rejection")),
            self.source,
        )
        self.assertEqual(
            (resolved["operationID"], resolved["leftSubjectID"], resolved["rightSubjectID"]),
            ("reverse-operation", "reverse-left", "reverse-right"),
        )
        self.assertEqual((resolved["action"], resolved["recovery"]), ("execute-case", "none"))

        stale_package = copy.deepcopy(self.source)
        stale_package["manifest"]["packageTreeDigest"] = "sha256:" + "0" * 64
        with self.assertRaises(HarnessError):
            resolve_execution(self.root, parse_intent(self.intent()), stale_package)

        stale_semantic = copy.deepcopy(self.source)
        stale_semantic["semanticCanonicalJSON"]["projection"] += " "
        with self.assertRaises(HarnessError):
            resolve_execution(self.root, parse_intent(self.intent()), stale_semantic)

        stale_case = copy.deepcopy(self.source)
        stale_case["caseBindings"]["directional-success"]["packageCaseID"] = "adversarial-structural"
        with self.assertRaises(HarnessError):
            resolve_execution(self.root, parse_intent(self.intent()), stale_case)

        candidate = self.root / self.source["candidates"]["accepted-reference"]["sourcePath"]
        candidate.write_text("changed\n")
        with self.assertRaises(HarnessError):
            resolve_execution(self.root, parse_intent(self.intent()), self.source)

    def test_matrix_has_six_executions_and_three_fact_empty_witnesses(self) -> None:
        result = qualify_matrix(
            self.root,
            source=self.source,
            probe_executor=self.probe,
            judgement_executor=self.derive,
        )
        self.assertEqual(len(result["records"]), 9)
        normal = [
            record for record in result["records"]
            if record["rawRecord"]["observationState"] == "facts-observed"
        ]
        witnesses = [
            record for record in result["records"]
            if record["rawRecord"]["observationState"] != "facts-observed"
        ]
        self.assertEqual(len(normal), 6)
        self.assertEqual(
            {record["rawRecord"]["observationState"] for record in witnesses},
            {"transport-failure", "capability-absent", "invalid-observation"},
        )
        self.assertTrue(all(not record["rawRecord"]["facts"] for record in witnesses))
        reverse = next(
            record for record in normal
            if record["resolution"]["candidateID"] == "rejected-reversed-operands"
            and record["resolution"]["caseID"] == "reverse-direction-rejection"
        )
        self.assertEqual(reverse["rawRecord"]["facts"], {"subsumes": True})
        self.assertEqual(len(result["evidence"]["rawRecordDigests"]), 9)
        self.assertEqual(
            len(result["evidence"]["stableReplayProjectionDigests"]),
            9,
        )

    def test_unverified_cueprobe_artifact_is_invalid_observation(self) -> None:
        replay = execute_intent(
            self.root,
            self.intent(),
            source=self.source,
            probe_executor=self.unverified_probe,
        )
        self.assertEqual(replay["rawRecord"]["observationState"], "invalid-observation")
        self.assertEqual(replay["rawRecord"]["facts"], {})

    def test_ingress_contains_no_python_semantic_result(self) -> None:
        replay = execute_intent(
            self.root,
            self.intent(),
            source=self.source,
            probe_executor=self.probe,
        )
        ingress = judgement_ingress(replay["resolution"], replay["rawRecord"], self.source)
        encoded = json.dumps(ingress, sort_keys=True)
        for field in ('"outcome"', '"comparisonResults"', '"normalizedFactSet"'):
            self.assertNotIn(field, encoded)

    def test_replay_is_deterministic(self) -> None:
        left = execute_intent(self.root, self.intent(), source=self.source, probe_executor=self.probe)
        right = execute_intent(self.root, self.intent(), source=self.source, probe_executor=self.probe)
        self.assertEqual(left["replayDigest"], right["replayDigest"])

    def test_recovery_is_bound_into_resolution_and_replay(self) -> None:
        original = self.intent()
        retried = self.intent()
        retried["recovery"] = "retry"
        left = execute_intent(self.root, original, source=self.source, probe_executor=self.probe)
        right = execute_intent(self.root, retried, source=self.source, probe_executor=self.probe)
        self.assertNotEqual(
            left["resolution"]["resolutionDigest"],
            right["resolution"]["resolutionDigest"],
        )
        self.assertNotEqual(left["replayDigest"], right["replayDigest"])

    def test_raw_occurrences_bind_to_one_stable_replay_projection(self) -> None:
        def observed_at(stamp: str):
            def probe(_root: Path, request: dict[str, object]) -> dict[str, object]:
                result = self._cueprobe_result(request)
                result["cueprobe"]["commands"] = [{
                    "state": "exited",
                    "argv": [f"/machine/{stamp}/cueprobe"],
                    "cwd": f"/machine/{stamp}/checkout",
                    "startedAt": stamp,
                    "finishedAt": stamp,
                    "exitCode": 0,
                    "stdout": "observation",
                    "stderr": "",
                    "stdoutDigest": "sha256:" + "7" * 64,
                    "stderrDigest": "sha256:" + "8" * 64,
                }]
                return result

            return probe

        left = execute_intent(
            self.root,
            self.intent(),
            source=self.source,
            probe_executor=observed_at("2026-01-01T00:00:00Z"),
        )
        right = execute_intent(
            self.root,
            self.intent(),
            source=self.source,
            probe_executor=observed_at("2026-01-01T00:00:01Z"),
        )
        self.assertNotEqual(
            left["rawRecord"]["recordDigest"],
            right["rawRecord"]["recordDigest"],
        )
        self.assertNotEqual(left["replayDigest"], right["replayDigest"])
        self.assertEqual(
            left["stableReplayProjection"]["projectionDigest"],
            right["stableReplayProjection"]["projectionDigest"],
        )
        self.assertNotEqual(
            left["stableReplayProjection"]["bindingDigest"],
            right["stableReplayProjection"]["bindingDigest"],
        )
        self.assertEqual(
            left["stableReplayProjection"]["rawRecordDigest"],
            left["rawRecord"]["recordDigest"],
        )
        command = left["rawRecord"]["backendObservations"]["cueprobe"]["commands"][0]
        self.assertEqual(
            set(command),
            {
                "state",
                "argv",
                "cwd",
                "startedAt",
                "finishedAt",
                "exitCode",
                "stdout",
                "stderr",
                "stdoutDigest",
                "stderrDigest",
            },
        )

    def test_manifest_limits_reach_the_probe_request(self) -> None:
        captured: dict[str, object] = {}

        def probe(_root: Path, request: dict[str, object]) -> dict[str, object]:
            captured.update(request)
            return self._cueprobe_result(request)

        execute_intent(self.root, self.intent(), source=self.source, probe_executor=probe)
        self.assertEqual(
            captured["extensions"],
            {
                "resolutionDigest": resolve_execution(
                    self.root,
                    parse_intent(self.intent()),
                    self.source,
                )["resolutionDigest"],
                "operationID": "directional-operation",
                "orderedSubjectIDs": ["directional-left", "directional-right"],
                "timeoutMilliseconds": 1000,
                "maximumOutputBytes": 64 * 1024 * 1024,
            },
        )

    def test_runtime_process_states_are_transport_failures(self) -> None:
        for state in ("timeout", "start-error", "output-limit-exceeded"):
            def probe(_root: Path, request: dict[str, object], state: str = state) -> dict[str, object]:
                result = self._cueprobe_result(request)
                result["cueprobe"]["state"] = state
                result["cueprobe"]["facts"] = {"available": True}
                result["cueprobe"]["diagnostics"] = [{"code": state, "message": state}]
                return result

            replay = execute_intent(
                self.root,
                self.intent(),
                source=self.source,
                probe_executor=probe,
            )
            self.assertEqual(replay["rawRecord"]["observationState"], "transport-failure")
            self.assertEqual(replay["rawRecord"]["facts"], {})


if __name__ == "__main__":
    unittest.main()
