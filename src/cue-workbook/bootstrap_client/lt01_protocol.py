"""Closed manifest-resolved LT-01 protocol for the canonical workbook."""
from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from models import HarnessError, HarnessFailure, _digest_bytes, _json_bytes, _reject_claimant_fields

INTENT_SCHEMA = "cuestrap.lt01-execution-intent.v0"
RESOLUTION_SCHEMA = "cuestrap.lt01-resolved-execution.v0"
PROVENANCE_COMMIT = "781801e6500bcef92169b8748ae82166bae56c88"
INPUT_CONTRACT_DIGEST = "sha256:0b756609d6b5f17be6c062b2ec7e15d1f22be0bece9702a2fea140f1d806e217"
PACKAGE_DIGEST = "sha256:6fccb0d98d54b1f4d662219076da7e56b8179f95be4680c8c59c035b1823d82e"
CANDIDATE_SET_DIGEST = "sha256:9a2672ff42dd3da4e5956090a683992eec880a70b7a5062003b59cb938710ffe"
CANDIDATES = ("accepted-reference", "rejected-reversed-operands")
CASES = ("directional-success", "reverse-direction-rejection", "adversarial-structural")
SEMANTIC_ARTIFACT_IDS = {
    "realization": "lt01-realization",
    "projection": "lt01-projection",
    "contract": "lt01-consumer-profile",
}


class Action(StrEnum):
    EXECUTE = "execute-case"
    CAPABILITY = "report-capability-absence"
    TRANSPORT = "report-transport-failure"
    INVALID = "report-invalid-observation"


class Recovery(StrEnum):
    NONE = "none"
    RETRY = "retry"
    REFRESH = "refresh-capabilities"
    STOP = "stop-indeterminate"
    HUMAN = "request-human-review"


class ExecutionIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    schema_: Literal[INTENT_SCHEMA] = Field(alias="schema")
    action: Action
    candidate_id: Literal[*CANDIDATES] = Field(alias="candidateID")
    case_id: Literal[*CASES] = Field(alias="caseID")
    recovery: Recovery = Recovery.NONE

    @model_validator(mode="before")
    @classmethod
    def no_claimant_fields(cls, value: object) -> object:
        _reject_claimant_fields(value, "LT-01 intent")
        return value


def digest_payload(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    result = deepcopy(dict(value))
    result[field] = _digest_bytes(_json_bytes({key: item for key, item in result.items() if key != field}))
    return result


def parse_intent(value: object) -> ExecutionIntent:
    try:
        return ExecutionIntent.model_validate(value)
    except ValidationError as error:
        raise HarnessError(HarnessFailure.INVALID_PROTOCOL, str(error)) from error


def load_resolution_source(root: Path, cue_binary: str = "cue") -> dict[str, Any]:
    process = subprocess.run(
        [cue_binary, "export", "./pattern/s04", "-e", "lt01ExecutionResolutionSource"],
        cwd=root.resolve(strict=True), capture_output=True, text=True, timeout=60, check=False,
    )
    if process.returncode:
        raise HarnessError(HarnessFailure.PROCESS_FAILURE, process.stderr.strip() or "CUE export failed")
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "CUE resolution source was not JSON") from error
    if not isinstance(result, dict):
        raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "resolution source must be an object")
    return result


def _validate_handoff(value: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = value["manifest"]
    realization = value["realization"]
    package = value["package"]
    semantic_artifacts = value["semanticArtifacts"]

    if manifest["inputContractDigest"] != INPUT_CONTRACT_DIGEST:
        raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "qualified input contract digest mismatch")
    if manifest["packageTreeDigest"] != PACKAGE_DIGEST or package["packageDigest"] != PACKAGE_DIGEST:
        raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "package tree digest mismatch")
    if manifest["candidateSetDigest"] != CANDIDATE_SET_DIGEST:
        raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "candidate set digest mismatch")
    if semantic_artifacts != manifest["semanticArtifacts"]:
        raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "semantic artifact identities disagree")
    for kind, artifact_id in SEMANTIC_ARTIFACT_IDS.items():
        if semantic_artifacts[kind]["artifactID"] != artifact_id:
            raise HarnessError(HarnessFailure.INVALID_PROTOCOL, f"{kind} artifact identity mismatch")
    if semantic_artifacts["realization"]["digest"] != _digest_bytes(_json_bytes(realization)):
        raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "realization content digest mismatch")
    return dict(manifest), dict(realization), dict(package)


def resolve_execution(root: Path, intent: ExecutionIntent, source: Mapping[str, Any] | None = None) -> dict[str, Any]:
    repo = root.resolve(strict=True)
    value = deepcopy(dict(source or load_resolution_source(repo)))
    _reject_claimant_fields(value, "LT-01 resolution source")
    manifest, realization, package = _validate_handoff(value)

    binding = value["caseBindings"].get(intent.case_id)
    if not isinstance(binding, dict) or binding.get("bindingID") != intent.case_id:
        raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "case binding identity mismatch")
    if binding.get("realizationCaseID") != intent.case_id or binding.get("packageCaseID") != intent.case_id:
        raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "case binding coordinates mismatch")
    if intent.case_id not in realization["cases"] or intent.case_id not in package["cases"]:
        raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "case is absent from the qualified handoff")

    candidate = value["candidates"][intent.candidate_id]
    package_candidate = package["candidates"][intent.candidate_id]
    expected_source_path = f'{manifest["packageRoot"]}/{package_candidate["sourcePath"]}'
    if candidate["candidateID"] != intent.candidate_id or candidate["sourcePath"] != expected_source_path:
        raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "candidate coordinates mismatch")
    candidate_path = (repo / candidate["sourcePath"]).resolve(strict=True)
    try:
        candidate_path.relative_to(repo)
    except ValueError as error:
        raise HarnessError(HarnessFailure.PATH_ESCAPE, "candidate path escapes repository") from error
    if _digest_bytes(candidate_path.read_bytes()) != candidate["digest"]:
        raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "candidate content digest mismatch")

    case = realization["cases"][intent.case_id]
    operations = realization["plans"][case["planID"]]["operations"]
    if len(operations) != 1:
        raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "case must resolve to one operation")
    operation = operations[0]
    if (operation["kind"], operation["direction"]) != ("subsumes", "left-to-right"):
        raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "operation is outside LT-01")
    if operation["left"]["subjectID"] not in case["subjectIDs"] or operation["right"]["subjectID"] not in case["subjectIDs"]:
        raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "ordered operation subjects escape the selected case")

    limits = package["metadata"]["limits"]
    result = {
        "schema": RESOLUTION_SCHEMA,
        "provenanceCommit": PROVENANCE_COMMIT,
        "manifestDigest": _digest_bytes(_json_bytes(manifest)),
        "inputContractDigest": manifest["inputContractDigest"],
        "realizationID": realization["realizationID"],
        "realizationDigest": manifest["semanticArtifacts"]["realization"]["digest"],
        "projectionDigest": manifest["semanticArtifacts"]["projection"]["digest"],
        "contractDigest": manifest["semanticArtifacts"]["contract"]["digest"],
        "packageDigest": manifest["packageTreeDigest"],
        "candidateSetDigest": manifest["candidateSetDigest"],
        "candidateID": intent.candidate_id,
        "candidateDigest": candidate["digest"],
        "candidateSourcePath": candidate["sourcePath"],
        "caseID": intent.case_id,
        "operationID": operation["operationID"],
        "operationKind": operation["kind"],
        "direction": operation["direction"],
        "leftSubjectID": operation["left"]["subjectID"],
        "rightSubjectID": operation["right"]["subjectID"],
        "leftSelector": f'candidate.cases."{intent.case_id}".left',
        "rightSelector": f'candidate.cases."{intent.case_id}".right',
        "observationFactID": operation["produces"][0],
        "normalizationRuleIDs": list(case["normalizationRuleIDs"]),
        "comparisonRuleIDs": list(case["comparisonRuleIDs"]),
        "semanticAuthorityID": value["semanticAuthorityID"],
        "observerAuthorityID": value["observerAuthorityID"],
        "capabilityIDs": list(case["requiredCapabilityIDs"]),
        "timeoutMilliseconds": int(limits["time_limit"] * 1000),
        "maximumOutputBytes": int(limits["output"] * 1024 * 1024),
        "evidencePath": f'{package_candidate["evidencePath"]}/{intent.case_id}',
    }
    return digest_payload(result, "resolutionDigest")


def observation_record(resolution: Mapping[str, Any], raw: Mapping[str, Any]) -> dict[str, Any]:
    if raw["resolutionDigest"] != resolution["resolutionDigest"]:
        raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "raw record is not resolution-bound")
    observation_id = f'{resolution["candidateID"]}-{resolution["caseID"]}-observation'
    facts: dict[str, Any] = {}
    if raw["observationState"] == "facts-observed":
        fact_id = resolution["observationFactID"]
        facts[fact_id] = {
            "factID": fact_id, "observationID": observation_id,
            "predicate": resolution["operationKind"], "observedValue": raw["facts"]["subsumes"],
            "sourceRecordDigest": raw["recordDigest"],
        }
    result = {
        "schema": "s04.observation-record.v0", "observationID": observation_id,
        "caseID": resolution["caseID"], "observerAuthorityID": resolution["observerAuthorityID"],
        "sourceRecordDigest": raw["recordDigest"], "state": raw["observationState"], "facts": facts,
    }
    if raw["diagnostics"]:
        result["diagnostics"] = raw["diagnostics"]
    return result


def judgement_ingress(resolution: Mapping[str, Any], raw: Mapping[str, Any], source: Mapping[str, Any]) -> dict[str, Any]:
    realization = source["realization"]
    normal = {key: realization["normalizationRules"][key] for key in resolution["normalizationRuleIDs"]}
    compare = {key: realization["comparisonRules"][key] for key in resolution["comparisonRuleIDs"]}
    result = {
        "requestID": f'{resolution["candidateID"]}-{resolution["caseID"]}-request',
        "judgementID": f'{resolution["candidateID"]}-{resolution["caseID"]}-judgement',
        "evaluator": {"cueRevision": "806821e40fae070318600a264d311517e596353b", "languageVersion": "v0.18.0", "relationID": "s04.derive-semantic-judgement.v0", "facadeDigest": _digest_bytes(b"s04.derive-semantic-judgement.v0")},
        "realizationDigest": resolution["realizationDigest"], "caseID": resolution["caseID"],
        "semanticAuthorityID": resolution["semanticAuthorityID"], "packageDigest": resolution["packageDigest"],
        "candidateDigest": resolution["candidateDigest"], "observation": observation_record(resolution, raw),
        "normalizedFactSetID": f'{resolution["candidateID"]}-{resolution["caseID"]}-facts',
        "normalizedFactSetDigest": _digest_bytes(_json_bytes({"observation": raw["recordDigest"], "rules": normal})),
        "normalizationRuleSetDigest": _digest_bytes(_json_bytes(normal)),
        "comparisonRuleSetDigest": _digest_bytes(_json_bytes(compare)),
        "normalizationRuleIDs": resolution["normalizationRuleIDs"], "comparisonRuleIDs": resolution["comparisonRuleIDs"],
    }
    result["derivationInputDigest"] = _digest_bytes(_json_bytes(result))
    return result
