"""Qualified gopy-worker and independent cueprobe observations."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from models import (
    OBSERVATION_PROTOCOL,
    WORKBOOK_CLI_PATH,
    WORKBOOK_PATH,
    HarnessError,
    HarnessFailure,
    ProbeObservation,
    ProbeRequest,
    SemanticSubject,
    _digest_bytes,
    _digest_file,
    _json_bytes,
    _reject_claimant_fields,
    materialize_subject,
    parse_probe_request,
)
from native import CUE_MODULE_VERSION, CUE_REVISION, GOPY_REVISION, binding_identity, import_bindings
from runtime import run_process


def _payload(repo_root: Path, request: ProbeRequest) -> tuple[dict[str, Any], SemanticSubject]:
    subject, module, files = materialize_subject(repo_root, request)
    return (
        {
            "request": request.model_dump(by_alias=True),
            "subject": subject.model_dump(by_alias=True),
            "moduleRoot": str(module),
            "files": [path.relative_to(module).as_posix() for path in files],
        },
        subject,
    )


def _unavailable(subject: SemanticSubject, backend: str, message: str) -> ProbeObservation:
    return ProbeObservation.model_validate(
        {
            "schema": OBSERVATION_PROTOCOL,
            "probeID": subject.probe_id,
            "backend": backend,
            "subjectDigest": subject.digest,
            "subjectIdentity": subject.model_dump(by_alias=True),
            "state": "unavailable",
            "facts": {"available": False},
            "diagnostics": [{"code": HarnessFailure.BACKEND_UNAVAILABLE.value, "message": message}],
            "commands": [],
            "extensions": {
                "cueRevision": CUE_REVISION,
                "cueModuleVersion": CUE_MODULE_VERSION,
                "gopyRevision": GOPY_REVISION if backend == "gopy-worker" else None,
            },
        }
    )


def _parse_worker_output(stdout: str, subject: SemanticSubject) -> ProbeObservation:
    try:
        value = json.loads(stdout)
        observation = ProbeObservation.model_validate(value)
    except (json.JSONDecodeError, ValidationError) as error:
        raise HarnessError(HarnessFailure.BACKEND_PROTOCOL, str(error)) from error
    if observation.subject_digest != subject.digest:
        raise HarnessError(HarnessFailure.BACKEND_PROTOCOL, "native backend changed semantic subject identity")
    return observation


def _gopy_string_slice(bindings: Any, values: list[str]) -> Any:
    return bindings.go.Slice_string(values)


def _cueprobe_path(repo_root: Path, configured: str | None, platform_name: str) -> Path:
    if configured:
        return Path(configured).resolve()
    name = "cueprobe.exe" if platform_name == "nt" else "cueprobe"
    return (repo_root / "runner" / "bin" / name).resolve()


def observe_gopy_worker(repo_root: Path, request: ProbeRequest) -> ProbeObservation:
    payload, subject = _payload(repo_root, request)
    workbook_root = (repo_root / WORKBOOK_PATH).resolve().parent
    configured = os.environ.get("CUESTRAP_GOPY_MODULE_DIR")
    module_root = Path(configured).resolve() if configured else workbook_root / "cue_native"
    if not module_root.exists():
        return _unavailable(subject, "gopy-worker", f"generated extension missing: {module_root}")
    environment = dict(os.environ)
    import_roots = [module_root.parent, workbook_root] if configured else [workbook_root]
    pythonpath = list(dict.fromkeys(str(path) for path in import_roots))
    if environment.get("PYTHONPATH"):
        pythonpath.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(pythonpath)
    worker = run_process(
        (sys.executable, str((repo_root / WORKBOOK_CLI_PATH).resolve()), "--gopy-worker"),
        cwd=repo_root,
        env=environment,
        input_bytes=_json_bytes(payload),
        timeout=60,
    )
    if worker.state != "exited" or worker.exit_code != 0:
        state = worker.state if worker.state != "exited" else "process-failure"
        observation = _unavailable(subject, "gopy-worker", worker.stderr or state)
        observation.state = state
        observation.facts["available"] = True
        observation.commands.append(worker)
        return observation
    observation = _parse_worker_output(worker.stdout, subject)
    observation.commands.append(worker)
    manifest = repo_root / ".deps" / "manifest.json"
    if manifest.is_file():
        observation.extensions["buildManifestDigest"] = _digest_file(manifest)
    return observation


def observe_cueprobe(repo_root: Path, request: ProbeRequest) -> ProbeObservation:
    payload, subject = _payload(repo_root, request)
    configured = os.environ.get("CUESTRAP_CUEPROBE")
    binary = _cueprobe_path(repo_root, configured, os.name)
    if not binary.is_file():
        return _unavailable(subject, "cueprobe", f"runner missing: {binary}")
    process = run_process(
        (str(binary),),
        cwd=repo_root,
        input_bytes=_json_bytes(payload),
        timeout=60,
    )
    if process.state != "exited" or process.exit_code != 0:
        state = process.state if process.state != "exited" else "process-failure"
        observation = _unavailable(subject, "cueprobe", process.stderr or state)
        observation.state = state
        observation.facts["available"] = True
        observation.commands.append(process)
        return observation
    observation = _parse_worker_output(process.stdout, subject)
    observation.commands.append(process)
    observation.extensions["binaryDigest"] = _digest_file(binary)
    return observation


def compare_native_backends(gopy: ProbeObservation, cueprobe: ProbeObservation) -> dict[str, Any]:
    equivalent_subjects = gopy.subject_digest == cueprobe.subject_digest
    left_engine = (gopy.extensions.get("cueRevision"), gopy.extensions.get("cueModuleVersion"))
    right_engine = (cueprobe.extensions.get("cueRevision"), cueprobe.extensions.get("cueModuleVersion"))
    equivalent_engines = left_engine == right_engine == (CUE_REVISION, CUE_MODULE_VERSION)
    shared = set(gopy.facts).intersection(cueprobe.facts).difference({"available"})
    comparisons = {
        key: {
            "gopyWorker": gopy.facts.get(key),
            "cueprobe": cueprobe.facts.get(key),
            "agrees": gopy.facts.get(key) == cueprobe.facts.get(key),
        }
        for key in sorted(shared)
    }
    available = gopy.facts.get("available") is True and cueprobe.facts.get("available") is True
    if not available:
        state = "capability-gap"
    elif not equivalent_subjects:
        state = "subject-identity-mismatch"
    elif not equivalent_engines:
        state = "engine-identity-mismatch"
    elif not comparisons:
        state = "incomparable"
    elif all(item["agrees"] for item in comparisons.values()):
        state = "shared-facts-equal"
    else:
        state = "shared-facts-differ"
    return {
        "schema": "cuestrap.native-backend-comparison.v0",
        "probeID": gopy.probe_id,
        "state": state,
        "equivalentSubjects": equivalent_subjects,
        "equivalentEngines": equivalent_engines,
        "subjectDigest": gopy.subject_digest if equivalent_subjects else None,
        "engine": {"cueRevision": CUE_REVISION, "cueModuleVersion": CUE_MODULE_VERSION},
        "comparisons": comparisons,
    }


def _lookup(value: Any, path: str | None) -> Any:
    return value if not path else value.Lookup(path)


def _native_observation(payload: dict[str, Any]) -> dict[str, Any]:
    _reject_claimant_fields(payload, "gopy worker request")
    request = parse_probe_request(payload["request"])
    subject = SemanticSubject.model_validate(payload["subject"])
    module_root = str(payload["moduleRoot"])
    files = payload["files"]
    if not isinstance(files, list) or not files or not all(isinstance(item, str) for item in files):
        raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "native worker files are invalid")

    bindings = import_bindings()
    identity = binding_identity(bindings)
    context = bindings.NewContext()
    loader = context.OpenLoader(module_root)
    root = loader.LoadFiles(_gopy_string_slice(bindings, files))
    facts: dict[str, Any] = {"available": True}
    diagnostics: list[dict[str, Any]] = []
    state = "evaluate"

    if root.IsBottom():
        state = "load-error"
        diagnostics = json.loads(root.DiagnosticsJSON())
    else:
        subject_value = _lookup(root, request.subject_expression)
        if subject_value.IsBottom():
            state = "evaluation-error"
            facts["semanticBottom"] = True
            diagnostics = json.loads(subject_value.DiagnosticsJSON())
        elif request.operation == "evaluate":
            if request.concrete_input is not None:
                source = json.dumps(request.concrete_input, ensure_ascii=False, allow_nan=False)
                subject_value = subject_value.Unify(context.CompileString(source, "concrete.json"))
            facts["semanticBottom"] = bool(subject_value.IsBottom())
            facts["kind"] = subject_value.Kind()
            facts["incompleteKind"] = subject_value.IncompleteKind()
            if subject_value.IsBottom():
                state = "evaluate"
                diagnostics = json.loads(subject_value.DiagnosticsJSON())
            else:
                projected = json.loads(subject_value.ProjectJSON().JSON())
                if projected["ok"]:
                    state = "project"
                    raw = projected["json_value"].encode()
                    facts["concrete"] = True
                    facts["concreteValueDigest"] = _digest_bytes(raw)
                else:
                    state = "incomplete"
                    facts["concrete"] = False
                    diagnostics = projected.get("diagnostics", [])
        elif request.operation == "subsumes":
            candidate = _lookup(root, request.candidate_expression)
            if candidate.IsBottom():
                state = "materialization-error"
                diagnostics = json.loads(candidate.DiagnosticsJSON())
            else:
                result = json.loads(subject_value.CheckSubsume(candidate).JSON())
                state = "compare"
                facts["subsumes"] = bool(result["ok"])
                diagnostics = result.get("diagnostics", [])
        else:
            state = "unsupported-operation"
            diagnostics = [{"code": state, "message": f"gopy worker does not implement {request.operation!r}"}]

    return {
        "schema": OBSERVATION_PROTOCOL,
        "probeID": request.probe_id,
        "backend": "gopy-worker",
        "subjectDigest": subject.digest,
        "subjectIdentity": subject.model_dump(by_alias=True),
        "state": state,
        "facts": facts,
        "diagnostics": diagnostics,
        "commands": [],
        "extensions": {
            "mode": "worker",
            "cueRevision": identity["cue_revision"],
            "cueModuleVersion": identity["cue_module_version"],
            "observedCUEModuleVersion": identity.get("observed_cue_module_version"),
            "goVersion": identity.get("go_version"),
            "gopyRevision": GOPY_REVISION,
        },
    }


def gopy_worker_main() -> int:
    try:
        payload = json.load(sys.stdin)
        print(json.dumps(_native_observation(payload), sort_keys=True, separators=(",", ":")))
        return 0
    except Exception as error:
        print(json.dumps({"error": f"{type(error).__name__}: {error}"}), file=sys.stderr)
        return 2
