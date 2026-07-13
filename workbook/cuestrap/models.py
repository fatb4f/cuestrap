from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ProcessObservation(StrictModel):
    argv: list[str]
    cwd: str
    started_at: str = Field(alias="startedAt")
    finished_at: str = Field(alias="finishedAt")
    exit_code: int | None = Field(alias="exitCode")
    stdout: str
    stderr: str
    stdout_digest: str = Field(alias="stdoutDigest")
    stderr_digest: str = Field(alias="stderrDigest")


class EnvironmentIdentity(StrictModel):
    schema_: Literal["cuestrap.environment.v0"] = Field(alias="schema")
    repo_root: str = Field(alias="repoRoot")
    python_executable: str = Field(alias="pythonExecutable")
    python_prefix: str = Field(alias="pythonPrefix")
    uv_project_environment: str | None = Field(alias="uvProjectEnvironment")
    virtual_env: str | None = Field(alias="virtualEnv")
    pyproject_digest: str | None = Field(alias="pyprojectDigest")
    lock_digest: str | None = Field(alias="lockDigest")
    lock_check: ProcessObservation | None = Field(alias="lockCheck")
    sync_check: ProcessObservation | None = Field(alias="syncCheck")
    tool_versions: dict[str, str] = Field(alias="toolVersions")
    locked: bool


class SemanticSubject(StrictModel):
    schema_: Literal["cuestrap.semantic-subject.v0"] = Field(alias="schema")
    module_root: str = Field(alias="moduleRoot")
    files: list[str]
    file_digests: dict[str, str] = Field(alias="fileDigests")
    operation: Literal["compile", "lookup", "unify", "validate", "subsume"]
    expression: str
    operand_digest: str | None = Field(alias="operandDigest")
    digest: str


class ProbeRequest(StrictModel):
    schema_: Literal["cuestrap.probe-request.v0"] = Field(alias="schema")
    probe_id: str = Field(alias="probeID", min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    module_root: str = Field(alias="moduleRoot", min_length=1)
    files: list[str] = Field(min_length=1)
    operation: Literal["compile", "lookup", "unify", "validate", "subsume"]
    expression: str = Field(min_length=1)
    operand: Any | None = None
    backend: Literal["cue-cli", "cue-py", "both"] = "both"

    @model_validator(mode="after")
    def operation_has_required_operand(self) -> "ProbeRequest":
        if self.operation in {"unify", "subsume"} and self.operand is None:
            raise ValueError(f"{self.operation} requires operand")
        return self


class ProbeObservation(StrictModel):
    schema_: Literal["cuestrap.probe-observation.v0"] = Field(alias="schema")
    probe_id: str = Field(alias="probeID")
    backend: Literal["cue-cli", "cue-py/libcue"]
    stage: Literal["load", "compile", "lookup", "unify", "validate", "subsume", "project"]
    state: Literal["completed", "rejected", "incomplete", "unavailable", "infrastructure-failure"]
    semantic_bottom: bool | None = Field(alias="semanticBottom")
    subject: SemanticSubject
    facts: dict[str, Any]
    diagnostic: str
    process: ProcessObservation | None = None


class BackendComparison(StrictModel):
    schema_: Literal["cuestrap.backend-comparison.v0"] = Field(alias="schema")
    probe_id: str = Field(alias="probeID")
    equivalent_subject: bool = Field(alias="equivalentSubject")
    agrees: bool | None
    cue_cli: ProbeObservation | None = Field(alias="cueCLI")
    cue_py: ProbeObservation | None = Field(alias="cuePy")
