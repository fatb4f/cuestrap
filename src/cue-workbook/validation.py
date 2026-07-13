"""Deterministic harness properties and workbook-level execution."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from backends import compare_backends, observe_cli, observe_cue_py
from models import DEFAULT_WORKBOOK_REQUEST, HarnessError, HarnessFailure, SourceRef, _CLAIMANT_KEYS, _SAFE_ID, parse_probe_request
from runtime import observe_environment


def run_properties() -> dict[str, Any]:
    from hypothesis import given, settings, strategies as st

    counters = {"examples": 0}

    @settings(derandomize=True, deadline=None, max_examples=64)
    @given(st.text(min_size=1, max_size=100))
    def bounded_paths_never_escape(value: str) -> None:
        counters["examples"] += 1
        root = Path.cwd().resolve()
        try:
            resolved = SourceRef(path=value).resolve_under(root, must_exist=False)
        except (HarnessError, OSError):
            return
        assert resolved.is_relative_to(root)

    @settings(derandomize=True, deadline=None, max_examples=64)
    @given(st.sampled_from(sorted(_CLAIMANT_KEYS)))
    def claimant_fields_are_rejected(key: str) -> None:
        counters["examples"] += 1
        value = dict(DEFAULT_WORKBOOK_REQUEST)
        value[key] = True
        try:
            parse_probe_request(value)
        except HarnessError as error:
            assert error.code == HarnessFailure.CLAIMANT_FIELD_PRESENT
            return
        raise AssertionError(f"claimant field accepted: {key}")

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

    bounded_paths_never_escape()
    claimant_fields_are_rejected()
    unsafe_probe_ids_are_rejected()
    return {"status": "pass", "examples": counters["examples"]}


def run_architecture_validation(root: Path) -> dict[str, Any]:
    environment = observe_environment(root)
    properties = run_properties()
    checks_pass = all(item.get("status") == "pass" for item in environment.checks)
    return {
        "schema": "cuestrap.architecture-validation.v0",
        "status": "pass" if environment.locked and environment.exact and checks_pass and properties["status"] == "pass" else "fail",
        "environment": environment.model_dump(by_alias=True),
        "properties": properties,
    }


def execute_probe(root: Path, raw_request: object) -> dict[str, Any]:
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
