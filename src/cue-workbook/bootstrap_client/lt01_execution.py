"""Cueprobe execution, CUE derivation, replay, and evidence for LT-01."""
from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from models import (
    _cue_literal,
    _digest_bytes,
    _json_bytes,
    _reject_claimant_fields,
    parse_probe_request,
)
from native import CUE_MODULE_VERSION, CUE_REVISION, NativeBindingUnavailable, verify_cue_cli
from native_backend import observe_cueprobe
from .lt01_protocol import (
    Action,
    CANDIDATES,
    CASES,
    INTENT_SCHEMA,
    digest_payload,
    judgement_ingress,
    load_resolution_source,
    parse_intent,
    resolve_execution,
)

RAW_SCHEMA = "cuestrap.lt01-raw-execution-record.v0"
REPLAY_SCHEMA = "cuestrap.lt01-replay-record.v0"
RUNNER_OBSERVATION_SCHEMA = "cuestrap.lt01-cueprobe-observation.v0"


def _raw(
    resolution: Mapping[str, Any],
    action: str,
    state: str,
    *,
    facts: Mapping[str, Any] | None = None,
    diagnostics: list[Mapping[str, Any]] | None = None,
    backends: Mapping[str, Any] | None = None,
    transport: str = "returned",
) -> dict[str, Any]:
    if action != resolution["action"]:
        raise ValueError("raw action must match the resolved action")
    fact_values = dict(facts or {})
    diagnostic_values = [dict(item) for item in diagnostics or []]
    if state != "facts-observed" and fact_values:
        raise ValueError("non-fact observation cannot carry facts")
    if state == "facts-observed" and set(fact_values) != {"subsumes"}:
        raise ValueError("facts-observed requires one subsumes fact")
    if state != "facts-observed" and not diagnostic_values:
        raise ValueError("non-fact observation requires diagnostics")
    value = {
        "schema": RAW_SCHEMA,
        "resolutionDigest": resolution["resolutionDigest"],
        "action": action,
        "transportState": transport,
        "observationState": state,
        "facts": fact_values,
        "diagnostics": diagnostic_values,
        "backendObservations": dict(backends or {}),
    }
    _reject_claimant_fields(value, "LT-01 raw execution record")
    return digest_payload(value, "recordDigest")


def _probe_request(resolution: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": "cuestrap.probe-request.v0",
        "probeID": f'lt01.{resolution["candidateID"]}.{resolution["caseID"]}',
        "moduleRoot": ".",
        "package": "submission",
        "files": [{"path": resolution["candidateSourcePath"]}],
        "operation": "subsumes",
        "subjectExpression": resolution["leftSelector"],
        "candidateExpression": resolution["rightSelector"],
        "concreteInput": None,
        "extensions": {
            "resolutionDigest": resolution["resolutionDigest"],
            "operationID": resolution["operationID"],
            "orderedSubjectIDs": [
                resolution["leftSubjectID"],
                resolution["rightSubjectID"],
            ],
            "timeoutMilliseconds": resolution["timeoutMilliseconds"],
            "maximumOutputBytes": resolution["maximumOutputBytes"],
        },
    }


def execute_cueprobe(root: Path, request: object) -> dict[str, Any]:
    parsed = parse_probe_request(request)
    timeout_milliseconds = parsed.extensions.get("timeoutMilliseconds")
    maximum_output_bytes = parsed.extensions.get("maximumOutputBytes")
    if (
        not isinstance(timeout_milliseconds, int)
        or isinstance(timeout_milliseconds, bool)
        or not 0 < timeout_milliseconds <= 300_000
        or not isinstance(maximum_output_bytes, int)
        or isinstance(maximum_output_bytes, bool)
        or not 0 < maximum_output_bytes <= 67_108_864
    ):
        raise ValueError("cueprobe execution limits are missing or outside the closed bounds")
    observation = observe_cueprobe(
        root.resolve(strict=True),
        parsed,
        timeout=timeout_milliseconds / 1000,
        maximum_output_bytes=maximum_output_bytes,
    )
    return {
        "schema": RUNNER_OBSERVATION_SCHEMA,
        "cueprobe": observation.model_dump(by_alias=True),
    }


def _stable_backend_observations(value: Mapping[str, Any]) -> dict[str, Any]:
    """Retain raw facts and stable process evidence without occurrence coordinates."""
    result: dict[str, Any] = {}
    for backend, raw_observation in value.items():
        if not isinstance(raw_observation, Mapping):
            result[str(backend)] = raw_observation
            continue
        observation = dict(raw_observation)
        commands = observation.get("commands")
        if isinstance(commands, list):
            observation["commands"] = [
                {
                    key: command[key]
                    for key in (
                        "state",
                        "exitCode",
                        "stdoutDigest",
                        "stderrDigest",
                    )
                    if isinstance(command, Mapping) and key in command
                }
                for command in commands
                if isinstance(command, Mapping)
            ]
        result[str(backend)] = observation
    return result


def _diagnostics(observation: Mapping[str, Any], fallback: str) -> list[dict[str, str]]:
    values = observation.get("diagnostics")
    if isinstance(values, list) and values:
        return [
            {
                "code": str(item.get("code", "cueprobe-diagnostic")),
                "message": str(item.get("message", fallback)),
            }
            for item in values
            if isinstance(item, Mapping)
        ] or [{"code": "cueprobe-diagnostic", "message": fallback}]
    return [{"code": "cueprobe-diagnostic", "message": fallback}]


def _cueprobe_identity_is_admitted(observation: Mapping[str, Any]) -> bool:
    extensions = observation.get("extensions")
    if not isinstance(extensions, Mapping):
        return False
    return (
        extensions.get("cueRevision") == CUE_REVISION
        and extensions.get("cueModuleVersion") == CUE_MODULE_VERSION
        and extensions.get("observedCUEModuleVersion") == CUE_MODULE_VERSION
        and extensions.get("artifactManifestVerified") is True
        and isinstance(extensions.get("buildManifestDigest"), str)
        and isinstance(extensions.get("artifactDigest"), str)
    )


def execute_intent(
    root: Path,
    value: object,
    *,
    source: Mapping[str, Any] | None = None,
    probe_executor: Callable[[Path, object], dict[str, Any]] = execute_cueprobe,
) -> dict[str, Any]:
    intent = parse_intent(value)
    resolution = resolve_execution(root, intent, source)
    if intent.action == Action.TRANSPORT:
        raw = _raw(
            resolution,
            intent.action,
            "transport-failure",
            transport="transport-failure",
            diagnostics=[
                {
                    "code": "transport-failure",
                    "message": "qualified transport failure witness",
                }
            ],
        )
    elif intent.action == Action.CAPABILITY:
        raw = _raw(
            resolution,
            intent.action,
            "capability-absent",
            diagnostics=[
                {
                    "code": "capability-absent",
                    "message": "required cue-subsumes capability unavailable",
                }
            ],
        )
    elif intent.action == Action.INVALID:
        raw = _raw(
            resolution,
            intent.action,
            "invalid-observation",
            diagnostics=[
                {
                    "code": "invalid-observation",
                    "message": "qualified invalid observation witness",
                }
            ],
        )
    else:
        observed_backends = probe_executor(root.resolve(strict=True), _probe_request(resolution))
        _reject_claimant_fields(observed_backends, "LT-01 backend result")
        backends = _stable_backend_observations(observed_backends)
        observation = backends.get("cueprobe", {})
        if not isinstance(observation, Mapping):
            raw = _raw(
                resolution,
                intent.action,
                "invalid-observation",
                diagnostics=[
                    {
                        "code": "invalid-observation",
                        "message": "cueprobe observation was absent",
                    }
                ],
                backends=backends,
            )
        else:
            facts = observation.get("facts", {})
            available = isinstance(facts, Mapping) and facts.get("available") is True
            subsumes = facts.get("subsumes") if isinstance(facts, Mapping) else None
            state = observation.get("state")
            if not available:
                raw = _raw(
                    resolution,
                    intent.action,
                    "capability-absent",
                    diagnostics=_diagnostics(observation, "cueprobe capability unavailable"),
                    backends=backends,
                )
            elif state in {
                "process-failure",
                "timeout",
                "timed-out",
                "start-error",
                "output-limit-exceeded",
            }:
                raw = _raw(
                    resolution,
                    intent.action,
                    "transport-failure",
                    transport="transport-failure",
                    diagnostics=_diagnostics(observation, "cueprobe process did not return facts"),
                    backends=backends,
                )
            elif (
                state == "compare"
                and isinstance(subsumes, bool)
                and _cueprobe_identity_is_admitted(observation)
            ):
                raw = _raw(
                    resolution,
                    intent.action,
                    "facts-observed",
                    facts={"subsumes": subsumes},
                    backends=backends,
                )
            else:
                raw = _raw(
                    resolution,
                    intent.action,
                    "invalid-observation",
                    diagnostics=_diagnostics(
                        observation,
                        "cueprobe identity or fact shape was invalid",
                    ),
                    backends=backends,
                )
    replay = {"schema": REPLAY_SCHEMA, "resolution": resolution, "rawRecord": raw}
    return digest_payload(replay, "replayDigest")


def derive_judgement(
    root: Path,
    replay: Mapping[str, Any],
    source: Mapping[str, Any],
    cue_binary: str | None = None,
) -> dict[str, Any]:
    resolution, raw = replay["resolution"], replay["rawRecord"]
    ingress = judgement_ingress(resolution, raw, source)
    try:
        evaluator = verify_cue_cli(cue_binary)
    except (NativeBindingUnavailable, OSError) as error:
        return digest_payload(
            {
                "schema": "cuestrap.lt01-cue-derivation-result.v0",
                "resolutionDigest": resolution["resolutionDigest"],
                "rawRecordDigest": raw["recordDigest"],
                "state": "evaluator-identity-failure",
                "diagnostics": [
                    {
                        "code": "cue-evaluator-identity",
                        "message": str(error)[:4000],
                    }
                ],
            },
            "resultDigest",
        )
    expression = (
        "(#JudgementDerivation & {"
        "realization: lt01QualifiedContract.contract.realization, "
        f"ingress: {_cue_literal(ingress)}"
        "}).judgement"
    )
    process = subprocess.run(
        [evaluator["path"], "export", "./pattern/s04", "-e", expression],
        cwd=root.resolve(strict=True),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    base = {
        "schema": "cuestrap.lt01-cue-derivation-result.v0",
        "resolutionDigest": resolution["resolutionDigest"],
        "rawRecordDigest": raw["recordDigest"],
        "derivationInputDigest": ingress["derivationInputDigest"],
        "evaluator": {
            key: value for key, value in evaluator.items() if key != "path"
        },
    }
    if process.returncode:
        base.update(
            state="constraint-failure",
            diagnostics=[
                {
                    "code": "cue-derivation-bottom",
                    "message": process.stderr.strip()[:4000],
                }
            ],
        )
    else:
        try:
            judgement = json.loads(process.stdout)
        except json.JSONDecodeError as error:
            base.update(
                state="evaluator-protocol-failure",
                diagnostics=[
                    {
                        "code": "cue-evaluator-json",
                        "message": str(error)[:4000],
                    }
                ],
            )
        else:
            expected_bindings = {
                "schema": "s04.semantic-judgement.v0",
                "judgementID": ingress["judgementID"],
                "derivationInputDigest": ingress["derivationInputDigest"],
                "evaluator": ingress["evaluator"],
                "realizationDigest": ingress["realizationDigest"],
                "caseID": ingress["caseID"],
                "semanticAuthorityID": ingress["semanticAuthorityID"],
                "packageDigest": ingress["packageDigest"],
                "candidateDigest": ingress["candidateDigest"],
                "observationDigest": ingress["observation"]["sourceRecordDigest"],
            }
            if not isinstance(judgement, Mapping) or any(
                judgement.get(key) != value for key, value in expected_bindings.items()
            ):
                base.update(
                    state="evaluator-protocol-failure",
                    diagnostics=[
                        {
                            "code": "cue-judgement-binding",
                            "message": "published judgement does not match its derivation ingress",
                        }
                    ],
                )
            else:
                base.update(state="judgement-published", judgement=judgement)
    return digest_payload(base, "resultDigest")


def qualification_evidence(
    records: list[Mapping[str, Any]],
    derivations: list[Mapping[str, Any]],
) -> dict[str, Any]:
    ordered = sorted(
        records,
        key=lambda item: (
            item["resolution"]["candidateID"],
            item["resolution"]["caseID"],
            item["rawRecord"]["action"],
        ),
    )
    return digest_payload(
        {
            "schema": "cuestrap.lt01-qualification-evidence.v0",
            "recordDigests": [item["rawRecord"]["recordDigest"] for item in ordered],
            "replayDigests": [item["replayDigest"] for item in ordered],
            "derivationResultDigests": sorted(
                item["resultDigest"] for item in derivations
            ),
        },
        "evidenceDigest",
    )


def qualify_matrix(
    root: Path,
    *,
    source: Mapping[str, Any] | None = None,
    probe_executor: Callable[[Path, object], dict[str, Any]] = execute_cueprobe,
    judgement_executor: Callable[
        [Path, Mapping[str, Any], Mapping[str, Any]], dict[str, Any]
    ]
    | None = None,
    cue_binary: str | None = None,
) -> dict[str, Any]:
    resolved_source = dict(source or load_resolution_source(root, cue_binary))
    records = [
        execute_intent(
            root,
            {
                "schema": INTENT_SCHEMA,
                "action": "execute-case",
                "candidateID": candidate,
                "caseID": case,
                "recovery": "none",
            },
            source=resolved_source,
            probe_executor=probe_executor,
        )
        for candidate in CANDIDATES
        for case in CASES
    ]
    records.extend(
        execute_intent(
            root,
            {
                "schema": INTENT_SCHEMA,
                "action": action,
                "candidateID": "accepted-reference",
                "caseID": "directional-success",
                "recovery": "stop-indeterminate",
            },
            source=resolved_source,
            probe_executor=probe_executor,
        )
        for action in (
            "report-transport-failure",
            "report-capability-absence",
            "report-invalid-observation",
        )
    )
    derive = judgement_executor or (
        lambda path, replay, src: derive_judgement(path, replay, src, cue_binary)
    )
    derivations = [derive(root, record, resolved_source) for record in records]
    return {
        "schema": "cuestrap.lt01-matrix-qualification.v0",
        "records": records,
        "derivations": derivations,
        "evidence": qualification_evidence(records, derivations),
    }
