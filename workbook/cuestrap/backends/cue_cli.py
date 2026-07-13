from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import ProbeObservation, ProbeRequest, SemanticSubject
from ..process import run_process
from ..protocol import bounded_files, bounded_path, digest_file, digest_json


def _operand_source(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True)


def build_subject(repo_root: Path, request: ProbeRequest) -> SemanticSubject:
    module_root = bounded_path(repo_root, request.module_root)
    files = bounded_files(module_root, request.files)
    file_digests = {path.relative_to(module_root).as_posix(): digest_file(path) for path in files}
    components = {
        "schema": "cuestrap.semantic-subject.v0",
        "moduleRoot": str(module_root),
        "files": sorted(file_digests),
        "fileDigests": file_digests,
        "operation": request.operation,
        "expression": request.expression,
        "operandDigest": None if request.operand is None else digest_json(request.operand),
    }
    return SemanticSubject.model_validate({**components, "digest": digest_json(components)})


def _effective_expression(request: ProbeRequest) -> str:
    if request.operation == "unify":
        return f"({request.expression}) & ({_operand_source(request.operand)})"
    return request.expression


def execute_cue_cli(repo_root: Path, request: ProbeRequest) -> ProbeObservation:
    subject = build_subject(repo_root, request)
    module_root = Path(subject.module_root)
    files = subject.files
    if request.operation == "subsume":
        return ProbeObservation.model_validate(
            {
                "schema": "cuestrap.probe-observation.v0",
                "probeID": request.probe_id,
                "backend": "cue-cli",
                "stage": "subsume",
                "state": "unavailable",
                "semanticBottom": None,
                "subject": subject.model_dump(by_alias=True),
                "facts": {"reason": "directional subsumption is not inferred from CLI exit status"},
                "diagnostic": "use cue-py/libcue or the later Go reference runner",
                "process": None,
            }
        )

    expression = _effective_expression(request)
    argv = ["cue", "eval", *files, "-e", expression]
    process = run_process(argv, cwd=module_root)
    if process.exit_code is None:
        state = "unavailable"
        bottom = None
        stage = "compile"
    elif process.exit_code != 0:
        state = "rejected"
        bottom = True
        stage = "validate" if request.operation == "validate" else request.operation
    else:
        state = "completed"
        bottom = False
        stage = request.operation
    return ProbeObservation.model_validate(
        {
            "schema": "cuestrap.probe-observation.v0",
            "probeID": request.probe_id,
            "backend": "cue-cli",
            "stage": stage,
            "state": state,
            "semanticBottom": bottom,
            "subject": subject.model_dump(by_alias=True),
            "facts": {
                "exitCode": process.exit_code,
                "stdoutDigest": process.stdout_digest,
                "stderrDigest": process.stderr_digest,
            },
            "diagnostic": (process.stderr or process.stdout).strip()[:4000],
            "process": process.model_dump(by_alias=True),
        }
    )
