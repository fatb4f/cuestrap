"""Native execution, CUE derivation, replay, and evidence for LT-01."""
from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from models import _cue_literal, _digest_bytes, _json_bytes, _reject_claimant_fields
from native_validation import execute_native_probe
from .lt01_protocol import (
    Action, CANDIDATES, CASES, INTENT_SCHEMA, digest_payload, judgement_ingress,
    load_resolution_source, parse_intent, resolve_execution,
)

RAW_SCHEMA = "cuestrap.lt01-raw-execution-record.v0"
REPLAY_SCHEMA = "cuestrap.lt01-replay-record.v0"


def _raw(resolution: Mapping[str, Any], action: str, state: str, *, facts=None, diagnostics=None, backends=None, transport="returned") -> dict[str, Any]:
    facts = facts or {}
    diagnostics = diagnostics or []
    if state != "facts-observed" and facts:
        raise ValueError("non-fact observation cannot carry facts")
    if state == "facts-observed" and set(facts) != {"subsumes"}:
        raise ValueError("facts-observed requires one subsumes fact")
    if state != "facts-observed" and not diagnostics:
        raise ValueError("non-fact observation requires diagnostics")
    value = {
        "schema": RAW_SCHEMA, "resolutionDigest": resolution["resolutionDigest"],
        "action": action, "transportState": transport, "observationState": state,
        "facts": facts, "diagnostics": diagnostics, "backendObservations": backends or {},
    }
    _reject_claimant_fields(value, "LT-01 raw execution record")
    return digest_payload(value, "recordDigest")


def _probe_request(resolution: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": "cuestrap.probe-request.v0",
        "probeID": f'lt01.{resolution["candidateID"]}.{resolution["caseID"]}',
        "moduleRoot": ".", "package": "submission",
        "files": [{"path": resolution["candidateSourcePath"]}], "operation": "subsumes",
        "subjectExpression": resolution["leftSelector"], "candidateExpression": resolution["rightSelector"],
        "concreteInput": None,
        "extensions": {"resolutionDigest": resolution["resolutionDigest"], "operationID": resolution["operationID"], "orderedSubjectIDs": [resolution["leftSubjectID"], resolution["rightSubjectID"]]},
    }


def execute_intent(root: Path, value: object, *, source: Mapping[str, Any] | None = None, probe_executor: Callable[[Path, object], dict[str, Any]] = execute_native_probe) -> dict[str, Any]:
    intent = parse_intent(value)
    resolution = resolve_execution(root, intent, source)
    if intent.action == Action.TRANSPORT:
        raw = _raw(resolution, intent.action, "transport-failure", transport="transport-failure", diagnostics=[{"code": "transport-failure", "message": "qualified transport failure witness"}])
    elif intent.action == Action.CAPABILITY:
        raw = _raw(resolution, intent.action, "capability-absent", diagnostics=[{"code": "capability-absent", "message": "required cue-subsumes capability unavailable"}])
    elif intent.action == Action.INVALID:
        raw = _raw(resolution, intent.action, "invalid-observation", diagnostics=[{"code": "invalid-observation", "message": "backend observations were incomparable"}])
    else:
        backends = probe_executor(root.resolve(strict=True), _probe_request(resolution))
        _reject_claimant_fields(backends, "LT-01 backend result")
        comparison = backends.get("nativeComparison", {})
        left = backends.get("gopyWorker", {}).get("facts", {}).get("subsumes")
        right = backends.get("cueprobe", {}).get("facts", {}).get("subsumes")
        if comparison.get("state") == "shared-facts-equal" and isinstance(left, bool) and left == right:
            raw = _raw(resolution, intent.action, "facts-observed", facts={"subsumes": left}, backends=backends)
        elif comparison.get("state") == "capability-gap":
            raw = _raw(resolution, intent.action, "capability-absent", diagnostics=[{"code": "capability-absent", "message": "native backend capability gap"}], backends=backends)
        else:
            raw = _raw(resolution, intent.action, "invalid-observation", diagnostics=[{"code": "invalid-observation", "message": "native backend identities or facts were incomparable"}], backends=backends)
    replay = {"schema": REPLAY_SCHEMA, "resolution": resolution, "rawRecord": raw}
    return digest_payload(replay, "replayDigest")


def derive_judgement(root: Path, replay: Mapping[str, Any], source: Mapping[str, Any], cue_binary: str = "cue") -> dict[str, Any]:
    resolution, raw = replay["resolution"], replay["rawRecord"]
    ingress = judgement_ingress(resolution, raw, source)
    expression = f'(#JudgementDerivation & {{realization: lt01QualifiedContract.contract.realization, ingress: {_cue_literal(ingress)}}}).judgement'
    process = subprocess.run([cue_binary, "export", "./pattern/s04", "-e", expression], cwd=root.resolve(strict=True), capture_output=True, text=True, timeout=60, check=False)
    base = {"schema": "cuestrap.lt01-cue-derivation-result.v0", "resolutionDigest": resolution["resolutionDigest"], "rawRecordDigest": raw["recordDigest"]}
    if process.returncode:
        base.update(state="constraint-failure", diagnostics=[{"code": "cue-derivation-bottom", "message": process.stderr.strip()[:4000]}])
    else:
        base.update(state="judgement-published", judgement=json.loads(process.stdout))
    return digest_payload(base, "resultDigest")


def qualification_evidence(records: list[Mapping[str, Any]], derivations: list[Mapping[str, Any]]) -> dict[str, Any]:
    ordered = sorted(records, key=lambda item: (item["resolution"]["candidateID"], item["resolution"]["caseID"], item["rawRecord"]["action"]))
    return digest_payload({
        "schema": "cuestrap.lt01-qualification-evidence.v0",
        "recordDigests": [item["rawRecord"]["recordDigest"] for item in ordered],
        "replayDigests": [item["replayDigest"] for item in ordered],
        "derivationResultDigests": sorted(item["resultDigest"] for item in derivations),
    }, "evidenceDigest")


def qualify_matrix(root: Path, *, source: Mapping[str, Any] | None = None, probe_executor: Callable[[Path, object], dict[str, Any]] = execute_native_probe, judgement_executor: Callable[[Path, Mapping[str, Any], Mapping[str, Any]], dict[str, Any]] | None = None, cue_binary: str = "cue") -> dict[str, Any]:
    resolved_source = dict(source or load_resolution_source(root, cue_binary))
    records = [execute_intent(root, {"schema": INTENT_SCHEMA, "action": "execute-case", "candidateID": candidate, "caseID": case, "recovery": "none"}, source=resolved_source, probe_executor=probe_executor) for candidate in CANDIDATES for case in CASES]
    records.extend(execute_intent(root, {"schema": INTENT_SCHEMA, "action": action, "candidateID": "accepted-reference", "caseID": "directional-success", "recovery": "stop-indeterminate"}, source=resolved_source, probe_executor=probe_executor) for action in ("report-transport-failure", "report-capability-absence", "report-invalid-observation"))
    derive = judgement_executor or (lambda path, replay, src: derive_judgement(path, replay, src, cue_binary))
    derivations = [derive(root, record, resolved_source) for record in records]
    return {"schema": "cuestrap.lt01-matrix-qualification.v0", "records": records, "derivations": derivations, "evidence": qualification_evidence(records, derivations)}
