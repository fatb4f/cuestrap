"""Deterministic harness properties and workbook-level execution."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from backends import compare_backends, observe_cli, observe_cue_py
from models import (
    DEFAULT_WORKBOOK_REQUEST,
    OBSERVATION_PROTOCOL,
    HarnessError,
    HarnessFailure,
    ProbeObservation,
    SourceRef,
    _CLAIMANT_KEYS,
    _SAFE_ID,
    materialize_subject,
    parse_probe_request,
)
from runtime import observe_environment


def run_properties(root: Path) -> dict[str, Any]:
    from hypothesis import given, settings, strategies as st

    root = root.resolve(strict=True)
    counters = {"examples": 0}
    default_request = parse_probe_request(DEFAULT_WORKBOOK_REQUEST)
    default_subject, _, _ = materialize_subject(root, default_request)

    @settings(derandomize=True, deadline=None, max_examples=64)
    @given(st.text(min_size=1, max_size=100))
    def bounded_paths_never_escape(value: str) -> None:
        counters["examples"] += 1
        try:
            resolved = SourceRef(path=value).resolve_under(root, must_exist=False)
        except (HarnessError, OSError):
            return
        assert resolved.is_relative_to(root)

    @settings(derandomize=True, deadline=None, max_examples=64)
    @given(st.sampled_from(sorted(_CLAIMANT_KEYS)))
    def claimant_request_fields_are_rejected(key: str) -> None:
        counters["examples"] += 1
        value = dict(DEFAULT_WORKBOOK_REQUEST)
        value[key] = True
        try:
            parse_probe_request(value)
        except HarnessError as error:
            assert error.code == HarnessFailure.CLAIMANT_FIELD_PRESENT
            return
        raise AssertionError(f"claimant request field accepted: {key}")

    @settings(derandomize=True, deadline=None, max_examples=64)
    @given(st.sampled_from(sorted(_CLAIMANT_KEYS)))
    def claimant_observation_fields_are_rejected(key: str) -> None:
        counters["examples"] += 1
        value = {
            "schema": OBSERVATION_PROTOCOL,
            "probeID": default_request.probe_id,
            "backend": "property-test",
            "subjectDigest": default_subject.digest,
            "state": "experimental-state",
            "facts": {key: True},
            "diagnostics": [],
            "commands": [],
            "extensions": {},
        }
        try:
            ProbeObservation.model_validate(value)
        except HarnessError as error:
            assert error.code == HarnessFailure.CLAIMANT_FIELD_PRESENT
            return
        raise AssertionError(f"claimant observation field accepted: {key}")

    @settings(derandomize=True, deadline=None, max_examples=32)
    @given(st.text(min_size=1, max_size=20).filter(lambda value: not bool(_SAFE_ID.fullmatch(value))))
    def unsafe_probe_ids_are_rejected(probe_id: str) -> None:
        counters["examples"] += 1
        value = dict(DEFAULT_WORKBOOK_REQUEST)
        value["probeID"] = probe_id
        try:
            parse_probe_request(value)
        except HarnessError:
            return
        raise AssertionError(f"unsafe probe id accepted: {probe_id!r}")

    json_scalar = st.none() | st.booleans() | st.integers(min_value=-1000, max_value=1000) | st.text(max_size=20)
    json_value = st.recursive(
        json_scalar,
        lambda children: st.lists(children, max_size=3)
        | st.dictionaries(st.text(max_size=9).map(lambda value: f"x{value}"), children, max_size=3),
        max_leaves=8,
    )

    @settings(derandomize=True, deadline=None, max_examples=32)
    @given(json_value)
    def equivalent_subjects_have_deterministic_identities(extension: object) -> None:
        counters["examples"] += 1
        value = dict(DEFAULT_WORKBOOK_REQUEST)
        value["extensions"] = {"generated": extension}
        first, _, _ = materialize_subject(root, parse_probe_request(value))
        second, _, _ = materialize_subject(root, parse_probe_request(value))
        assert first == second
        assert first.digest == second.digest

    @settings(derandomize=True, deadline=None, max_examples=3)
    @given(st.sampled_from(["backend", "state", "unknownEnvelopeField"]))
    def malformed_envelopes_fail_cleanly(key: str) -> None:
        counters["examples"] += 1
        value = dict(DEFAULT_WORKBOOK_REQUEST)
        value[key] = "unexpected"
        try:
            parse_probe_request(value)
        except HarnessError as error:
            assert error.code == HarnessFailure.INVALID_PROTOCOL
            return
        raise AssertionError(f"unknown envelope field accepted: {key}")

    bounded_paths_never_escape()
    claimant_request_fields_are_rejected()
    claimant_observation_fields_are_rejected()
    unsafe_probe_ids_are_rejected()
    equivalent_subjects_have_deterministic_identities()
    malformed_envelopes_fail_cleanly()
    return {"status": "pass", "examples": counters["examples"]}


def run_architecture_validation(root: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    environment = observe_environment(root)
    properties = run_properties(root)
    checks_pass = all(item.get("status") == "pass" for item in environment.checks)
    cue_available = environment.tools.get("cue", {}).get("available") is True
    return {
        "schema": "cuestrap.architecture-validation.v0",
        "status": "pass"
        if environment.locked
        and environment.exact
        and checks_pass
        and properties["status"] == "pass"
        else "fail",
        "environment": environment.model_dump(by_alias=True),
        "properties": properties,
        "requirements": {
            "cueAvailable": cue_available,
            "goplsAvailable": environment.tools.get("gopls", {}).get("available") is True,
        },
    }


def execute_probe(root: Path, raw_request: object) -> dict[str, Any]:
    root = root.resolve(strict=True)
    request = parse_probe_request(raw_request)
    cli = observe_cli(root, request)
    cue_py = observe_cue_py(root, request)
    return {
        "schema": "cuestrap.workbook-result.v0",
        "request": request.model_dump(by_alias=True),
        "cli": cli.model_dump(by_alias=True),
        "cuePy": cue_py.model_dump(by_alias=True),
        "comparison": compare_backends(cli, cue_py),
    }
