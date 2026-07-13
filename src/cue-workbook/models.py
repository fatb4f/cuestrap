"""Closed CUEstrap protocols, bounded coordinates, and semantic-subject identity."""
from __future__ import annotations

import hashlib
import json
import re
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

WORKBOOK_PATH = Path("src/cue-workbook/cue-workbook.py")
PROBE_PROTOCOL = "cuestrap.probe-request.v0"
OBSERVATION_PROTOCOL = "cuestrap.probe-observation.v0"
ENVIRONMENT_PROTOCOL = "cuestrap.environment.v0"
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_CLAIMANT_KEYS = frozenset(
    {
        "success",
        "passed",
        "valid",
        "complete",
        "admitted",
        "admission",
        "canonicalReady",
        "expectationSatisfied",
    }
)


class HarnessFailure(StrEnum):
    INVALID_COORDINATE = "invalid-coordinate"
    PATH_ESCAPE = "path-escape"
    INVALID_PROTOCOL = "invalid-protocol"
    CLAIMANT_FIELD_PRESENT = "claimant-field-present"
    TOOL_UNAVAILABLE = "tool-unavailable"
    PROCESS_FAILURE = "process-failure"
    BACKEND_UNAVAILABLE = "backend-unavailable"
    BACKEND_PROTOCOL = "backend-protocol"
    LSP_FAILURE = "lsp-failure"


class HarnessError(RuntimeError):
    def __init__(self, code: HarnessFailure, message: str) -> None:
        super().__init__(message)
        self.code = code

    def encode(self) -> dict[str, str]:
        return {"code": self.code.value, "message": str(self)[:500]}


class SourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)

    def resolve_under(self, root: Path, *, must_exist: bool = True) -> Path:
        candidate = (root / self.path).resolve(strict=must_exist)
        try:
            candidate.relative_to(root.resolve(strict=True))
        except ValueError as error:
            raise HarnessError(HarnessFailure.PATH_ESCAPE, f"path escapes root: {self.path}") from error
        return candidate


class ProbeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal[PROBE_PROTOCOL] = Field(alias="schema")
    probe_id: str = Field(alias="probeID", min_length=1)
    module_root: str = Field(alias="moduleRoot", default=".", min_length=1)
    package: str = Field(min_length=1)
    files: list[SourceRef] = Field(min_length=1, max_length=16)
    operation: Literal["evaluate", "subsumes"]
    subject_expression: str = Field(alias="subjectExpression", min_length=1)
    candidate_expression: str | None = Field(alias="candidateExpression", default=None)
    concrete_input: Any | None = Field(alias="concreteInput", default=None)

    @model_validator(mode="after")
    def validate_shape(self) -> "ProbeRequest":
        if not _SAFE_ID.fullmatch(self.probe_id):
            raise ValueError("probeID is not a safe identifier")
        if self.operation == "subsumes" and not self.candidate_expression:
            raise ValueError("subsumes requires candidateExpression")
        if self.operation == "evaluate" and self.candidate_expression is not None:
            raise ValueError("evaluate forbids candidateExpression")
        return self


class ProcessObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    argv: list[str]
    cwd: str
    started_at: str = Field(alias="startedAt")
    finished_at: str = Field(alias="finishedAt")
    exit_code: int | None = Field(alias="exitCode")
    stdout: str
    stderr: str
    stdout_digest: str = Field(alias="stdoutDigest")
    stderr_digest: str = Field(alias="stderrDigest")


class SemanticSubject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol: Literal[PROBE_PROTOCOL]
    probe_id: str = Field(alias="probeID")
    operation: Literal["evaluate", "subsumes"]
    module_root: str = Field(alias="moduleRoot")
    package: str
    files: list[str]
    file_digests: dict[str, str] = Field(alias="fileDigests")
    subject_expression: str = Field(alias="subjectExpression")
    candidate_expression: str | None = Field(alias="candidateExpression")
    concrete_input_digest: str | None = Field(alias="concreteInputDigest")
    digest: str


class ProbeObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: Literal[OBSERVATION_PROTOCOL] = Field(alias="schema")
    probe_id: str = Field(alias="probeID")
    evaluator: str
    stage: Literal["load", "compile", "evaluate", "validate", "project", "compare"]
    subject: SemanticSubject
    facts: dict[str, Any]
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)
    commands: list[ProcessObservation] = Field(default_factory=list)


class EnvironmentReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: Literal[ENVIRONMENT_PROTOCOL] = Field(alias="schema")
    root: str
    python_executable: str = Field(alias="pythonExecutable")
    python_prefix: str = Field(alias="pythonPrefix")
    virtual_environment: str | None = Field(alias="virtualEnvironment")
    uv_project_environment: str | None = Field(alias="uvProjectEnvironment")
    project_digest: str = Field(alias="projectDigest")
    lock_digest: str = Field(alias="lockDigest")
    locked: bool
    exact: bool
    tools: dict[str, dict[str, Any]]
    checks: list[dict[str, Any]]


DEFAULT_WORKBOOK_REQUEST: dict[str, Any] = {
    "schema": PROBE_PROTOCOL,
    "probeID": "pilot.placeholder",
    "moduleRoot": ".",
    "package": "bootstrap",
    "files": [{"path": "pattern/pilot.cue"}],
    "operation": "evaluate",
    "subjectExpression": "#Pilot",
    "candidateExpression": None,
    "concreteInput": None,
}


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _digest_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _digest_file(path: Path) -> str:
    if not path.is_file():
        raise HarnessError(HarnessFailure.INVALID_COORDINATE, f"missing file: {path}")
    return _digest_bytes(path.read_bytes())


def _reject_claimant_fields(value: object, label: str = "payload") -> None:
    if isinstance(value, dict):
        forbidden = sorted(_CLAIMANT_KEYS.intersection(value))
        if forbidden:
            raise HarnessError(
                HarnessFailure.CLAIMANT_FIELD_PRESENT,
                f"claimant field in {label}: {forbidden[0]}",
            )
        for child in value.values():
            _reject_claimant_fields(child, label)
    elif isinstance(value, list):
        for child in value:
            _reject_claimant_fields(child, label)


def parse_probe_request(value: object) -> ProbeRequest:
    _reject_claimant_fields(value, "probe request")
    try:
        return ProbeRequest.model_validate(value)
    except ValidationError as error:
        raise HarnessError(HarnessFailure.INVALID_PROTOCOL, str(error)) from error


def _safe_module_root(repo_root: Path, relative: str) -> Path:
    candidate = (repo_root / relative).resolve(strict=True)
    try:
        candidate.relative_to(repo_root.resolve(strict=True))
    except ValueError as error:
        raise HarnessError(HarnessFailure.PATH_ESCAPE, f"module root escapes repository: {relative}") from error
    if not candidate.is_dir():
        raise HarnessError(HarnessFailure.INVALID_COORDINATE, f"module root is not a directory: {relative}")
    return candidate


def _cue_literal(value: object) -> str:
    if value is None or isinstance(value, (bool, int, float, str)):
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    if isinstance(value, list):
        return "[" + ", ".join(_cue_literal(item) for item in value) + "]"
    if isinstance(value, dict):
        fields = []
        for key, item in value.items():
            if not isinstance(key, str):
                raise HarnessError(HarnessFailure.INVALID_PROTOCOL, "CUE object keys must be strings")
            fields.append(f"{json.dumps(key)}: {_cue_literal(item)}")
        return "close({" + ", ".join(fields) + "})"
    raise HarnessError(HarnessFailure.INVALID_PROTOCOL, f"unsupported concrete input: {type(value).__name__}")


def materialize_subject(repo_root: Path, request: ProbeRequest) -> tuple[SemanticSubject, Path, list[Path]]:
    module = _safe_module_root(repo_root, request.module_root)
    paths: list[Path] = []
    relative_files: list[str] = []
    digests: dict[str, str] = {}
    for item in request.files:
        path = item.resolve_under(module)
        if not path.is_file() or path.is_symlink():
            raise HarnessError(HarnessFailure.INVALID_COORDINATE, f"probe source is not a regular file: {item.path}")
        relative = path.relative_to(module).as_posix()
        paths.append(path)
        relative_files.append(relative)
        digests[relative] = _digest_file(path)
    components = {
        "protocol": PROBE_PROTOCOL,
        "probeID": request.probe_id,
        "operation": request.operation,
        "moduleRoot": request.module_root,
        "package": request.package,
        "files": relative_files,
        "fileDigests": digests,
        "subjectExpression": request.subject_expression,
        "candidateExpression": request.candidate_expression,
        "concreteInputDigest": None
        if request.concrete_input is None
        else _digest_bytes(_json_bytes(request.concrete_input)),
    }
    subject = SemanticSubject.model_validate({**components, "digest": _digest_bytes(_json_bytes(components))})
    return subject, module, paths
