"""CUE CLI and cue-py/libcue observations over identical semantic subjects."""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from models import (
    OBSERVATION_PROTOCOL,
    PROBE_PROTOCOL,
    WORKBOOK_PATH,
    HarnessError,
    HarnessFailure,
    ProbeObservation,
    ProcessObservation,
    ProbeRequest,
    SemanticSubject,
    _cue_literal,
    _digest_bytes,
    _digest_file,
    _json_bytes,
    _reject_claimant_fields,
    materialize_subject,
    parse_probe_request,
)
from runtime import run_process


def _effective_expression(request: ProbeRequest) -> str:
    expression = f"({request.subject_expression})"
    if request.concrete_input is not None:
        expression = f"({expression}) & ({_cue_literal(request.concrete_input)})"
    return expression


def observe_cli(repo_root: Path, request: ProbeRequest) -> ProbeObservation:
    subject, module, files = materialize_subject(repo_root, request)
    cue = shutil.which("cue")
    if cue is None:
        return ProbeObservation.model_validate(
            {
                "schema": OBSERVATION_PROTOCOL,
                "probeID": request.probe_id,
                "evaluator": "cue-cli",
                "stage": "load",
                "subject": subject.model_dump(by_alias=True),
                "facts": {"available": False},
                "diagnostics": [{"code": HarnessFailure.TOOL_UNAVAILABLE.value, "message": "cue unavailable"}],
                "commands": [],
            }
        )

    relative = [path.relative_to(module).as_posix() for path in files]
    commands: list[ProcessObservation] = []
    if request.operation == "evaluate":
        common = (cue, "eval", "-p", request.package, "-e", _effective_expression(request), *relative)
        evaluated = run_process(common, cwd=module)
        commands.append(evaluated)
        bottom = evaluated.exit_code not in (0, None) or bool(re.search(r"(?m)^\s*_\|_", evaluated.stdout))
        facts: dict[str, Any] = {
            "available": evaluated.exit_code is not None,
            "semanticBottom": bottom,
            "exitCode": evaluated.exit_code,
        }
        stage: Literal["load", "compile", "evaluate", "validate", "project", "compare"] = "evaluate"
        if evaluated.exit_code == 0 and not bottom:
            exported = run_process(
                (cue, "export", "--out", "json", "-p", request.package, "-e", _effective_expression(request), *relative),
                cwd=module,
            )
            commands.append(exported)
            stage = "project"
            if exported.exit_code == 0:
                try:
                    concrete = json.loads(exported.stdout)
                    facts["concrete"] = True
                    facts["concreteValueDigest"] = _digest_bytes(_json_bytes(concrete))
                except json.JSONDecodeError:
                    facts["concrete"] = False
                    facts["invalidJSON"] = True
            else:
                facts["concrete"] = False
        return ProbeObservation.model_validate(
            {
                "schema": OBSERVATION_PROTOCOL,
                "probeID": request.probe_id,
                "evaluator": "cue-cli",
                "stage": stage,
                "subject": subject.model_dump(by_alias=True),
                "facts": facts,
                "diagnostics": [],
                "commands": [item.model_dump(by_alias=True) for item in commands],
            }
        )

    assert request.candidate_expression is not None
    subject_eval = run_process(
        (cue, "eval", "-p", request.package, "-e", request.subject_expression, *relative),
        cwd=module,
    )
    candidate_eval = run_process(
        (cue, "eval", "-p", request.package, "-e", request.candidate_expression, *relative),
        cwd=module,
    )
    unified_eval = run_process(
        (
            cue,
            "eval",
            "-p",
            request.package,
            "-e",
            f"({request.subject_expression}) & ({request.candidate_expression})",
            *relative,
        ),
        cwd=module,
    )
    commands.extend((subject_eval, candidate_eval, unified_eval))
    available = all(item.exit_code is not None for item in commands)
    semantic_bottom = unified_eval.exit_code not in (0, None) or bool(re.search(r"(?m)^\s*_\|_", unified_eval.stdout))
    normal_form_equal = (
        subject_eval.exit_code == 0
        and candidate_eval.exit_code == 0
        and unified_eval.exit_code == 0
        and unified_eval.stdout.strip() == candidate_eval.stdout.strip()
    )
    return ProbeObservation.model_validate(
        {
            "schema": OBSERVATION_PROTOCOL,
            "probeID": request.probe_id,
            "evaluator": "cue-cli",
            "stage": "compare",
            "subject": subject.model_dump(by_alias=True),
            "facts": {
                "available": available,
                "semanticBottom": semantic_bottom,
                "normalFormEqualToCandidate": normal_form_equal,
                "subsumesApproximation": normal_form_equal and not semantic_bottom,
            },
            "diagnostics": [
                {
                    "code": "cli-normal-form-approximation",
                    "message": "CLI subsumption is observed through normalized unification equality; cue-py/Go is the reference operation.",
                }
            ],
            "commands": [item.model_dump(by_alias=True) for item in commands],
        }
    )


def _cue_py_environment() -> tuple[dict[str, str], Path] | None:
    cue_py_root_value = os.environ.get("CUESTRAP_CUE_PY_ROOT")
    library_value = os.environ.get("CUESTRAP_LIBCUE_LIBRARY")
    if not cue_py_root_value or not library_value:
        return None
    cue_py_root = Path(cue_py_root_value).resolve(strict=True)
    library = Path(library_value).resolve(strict=True)
    if not (cue_py_root / "cue").is_dir() or not library.is_file():
        raise HarnessError(HarnessFailure.INVALID_COORDINATE, "invalid cue-py/libcue coordinates")
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(cue_py_root) + os.pathsep + environment.get("PYTHONPATH", "")
    variable = "PATH" if sys.platform == "win32" else ("DYLD_LIBRARY_PATH" if sys.platform == "darwin" else "LD_LIBRARY_PATH")
    environment[variable] = str(library.parent) + os.pathsep + environment.get(variable, "")
    return environment, library


def _cue_py_payload(repo_root: Path, request: ProbeRequest) -> tuple[dict[str, Any], SemanticSubject]:
    subject, module, files = materialize_subject(repo_root, request)
    sources = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        package_match = re.match(r"\s*package\s+([A-Za-z_][A-Za-z0-9_]*)\s*\n", text)
        if package_match is None or package_match.group(1) != request.package:
            raise HarnessError(HarnessFailure.INVALID_PROTOCOL, f"{path}: package mismatch")
        if re.search(r"(?m)^\s*import(?:\s|\()", text[package_match.end() :]):
            raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "initial cue-py backend does not support imports")
        sources.append(text if not sources else text[package_match.end() :])
    return (
        {
            "schema": PROBE_PROTOCOL,
            "request": request.model_dump(by_alias=True),
            "sources": sources,
            "subject": subject.model_dump(by_alias=True),
            "moduleRoot": str(module),
        },
        subject,
    )


def observe_cue_py(repo_root: Path, request: ProbeRequest) -> ProbeObservation:
    payload, subject = _cue_py_payload(repo_root, request)
    coordinates = _cue_py_environment()
    if coordinates is None:
        return ProbeObservation.model_validate(
            {
                "schema": OBSERVATION_PROTOCOL,
                "probeID": request.probe_id,
                "evaluator": "cue-py/libcue",
                "stage": "load",
                "subject": subject.model_dump(by_alias=True),
                "facts": {"available": False},
                "diagnostics": [
                    {
                        "code": HarnessFailure.BACKEND_UNAVAILABLE.value,
                        "message": "set CUESTRAP_CUE_PY_ROOT and CUESTRAP_LIBCUE_LIBRARY",
                    }
                ],
                "commands": [],
            }
        )
    environment, library = coordinates
    worker = run_process(
        (sys.executable, str((repo_root / WORKBOOK_PATH).resolve()), "--cue-py-worker"),
        cwd=repo_root,
        env=environment,
        input_bytes=_json_bytes(payload),
        timeout=60,
    )
    if worker.exit_code != 0:
        return ProbeObservation.model_validate(
            {
                "schema": OBSERVATION_PROTOCOL,
                "probeID": request.probe_id,
                "evaluator": "cue-py/libcue",
                "stage": "compile",
                "subject": subject.model_dump(by_alias=True),
                "facts": {"available": True, "libcueDigest": _digest_file(library)},
                "diagnostics": [{"code": HarnessFailure.PROCESS_FAILURE.value, "message": worker.stderr}],
                "commands": [worker.model_dump(by_alias=True)],
            }
        )
    try:
        value = json.loads(worker.stdout)
        observation = ProbeObservation.model_validate(value)
    except (json.JSONDecodeError, ValidationError) as error:
        raise HarnessError(HarnessFailure.BACKEND_PROTOCOL, str(error)) from error
    if observation.subject.digest != subject.digest:
        raise HarnessError(HarnessFailure.BACKEND_PROTOCOL, "cue-py worker changed semantic subject identity")
    observation.commands.append(worker)
    observation.facts["libcueDigest"] = _digest_file(library)
    return observation


def _cue_py_worker() -> int:
    try:
        payload = json.load(sys.stdin)
        _reject_claimant_fields(payload, "cue-py worker request")
        request = parse_probe_request(payload["request"])
        subject = SemanticSubject.model_validate(payload["subject"])
        sources = payload.get("sources")
        if not isinstance(sources, list) or not sources or not all(isinstance(item, str) for item in sources):
            raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "cue-py worker sources are invalid")
        from cue.context import Context  # type: ignore[import-not-found]

        context = Context()
        source = "\n".join(sources)
        expression = _effective_expression(request)
        source += f"\n_cuestrapSubject: {expression}\n"
        if request.candidate_expression is not None:
            source += f"\n_cuestrapCandidate: {request.candidate_expression}\n"
        compiled = context.compile(source)
        compiled_error = compiled.error()
        if type(compiled_error).__name__ == "Err":
            observation = {
                "schema": OBSERVATION_PROTOCOL,
                "probeID": request.probe_id,
                "evaluator": "cue-py/libcue",
                "stage": "compile",
                "subject": subject.model_dump(by_alias=True),
                "facts": {"available": True, "semanticBottom": True},
                "diagnostics": [{"code": "compile-error", "message": str(compiled_error)}],
                "commands": [],
            }
        else:
            left = compiled.lookup("_cuestrapSubject")
            left_error = left.error()
            bottom = type(left_error).__name__ == "Err"
            facts: dict[str, Any] = {"available": True, "semanticBottom": bottom}
            stage = "evaluate"
            diagnostics: list[dict[str, Any]] = []
            if bottom:
                diagnostics.append({"code": "bottom", "message": str(left_error)})
            elif request.operation == "evaluate":
                try:
                    concrete_json = left.to_json()
                    facts["concrete"] = True
                    facts["concreteValueDigest"] = _digest_bytes(_json_bytes(json.loads(concrete_json)))
                    stage = "project"
                except Exception as error:
                    facts["concrete"] = False
                    diagnostics.append({"code": "incomplete", "message": str(error)[:2000]})
            else:
                right = compiled.lookup("_cuestrapCandidate")
                try:
                    right.check_schema(left)
                    facts["subsumes"] = True
                except Exception as error:
                    facts["subsumes"] = False
                    diagnostics.append({"code": "does-not-subsume", "message": str(error)[:2000]})
                stage = "compare"
            observation = {
                "schema": OBSERVATION_PROTOCOL,
                "probeID": request.probe_id,
                "evaluator": "cue-py/libcue",
                "stage": stage,
                "subject": subject.model_dump(by_alias=True),
                "facts": facts,
                "diagnostics": diagnostics,
                "commands": [],
            }
        print(json.dumps(observation, sort_keys=True, separators=(",", ":")))
        return 0
    except Exception as error:
        print(json.dumps({"error": f"{type(error).__name__}: {error}"}), file=sys.stderr)
        return 2


def compare_backends(cli: ProbeObservation, cue_py: ProbeObservation) -> dict[str, Any]:
    equivalent = cli.subject.digest == cue_py.subject.digest and cli.subject == cue_py.subject
    comparable_keys = {"semanticBottom", "concreteValueDigest", "subsumes"}
    comparisons = {
        key: {
            "cli": cli.facts.get(key),
            "cuePy": cue_py.facts.get(key),
            "agrees": cli.facts.get(key) == cue_py.facts.get(key),
        }
        for key in sorted(comparable_keys)
        if key in cli.facts or key in cue_py.facts
    }
    return {
        "schema": "cuestrap.backend-comparison.v0",
        "probeID": cli.probe_id,
        "equivalentSubjects": equivalent,
        "subjectDigest": cli.subject.digest if equivalent else None,
        "comparisons": comparisons,
        "allComparableFactsAgree": equivalent and all(item["agrees"] for item in comparisons.values()),
    }
