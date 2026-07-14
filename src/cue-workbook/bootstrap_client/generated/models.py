"""Generated projection of ``../contracts.cue``. Do not edit by hand."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DIGEST_PATTERN = r"^sha256:[0-9a-f]{64}$"


def digest_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def digest_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode()).hexdigest()}"


def _camel(name: str) -> str:
    head, *tail = name.split("_")
    return head + "".join(
        "ID" if item == "id" else "IDs" if item == "ids" else item.title()
        for item in tail
    )


class ContractModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        extra="forbid",
        frozen=True,
        populate_by_name=True,
    )


Digest = Annotated[str, Field(pattern=DIGEST_PATTERN)]
NonEmpty = Annotated[str, Field(min_length=1)]
RepositoryPath = NonEmpty
CellID = NonEmpty
VariableName = Annotated[str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")]
BootstrapPhase = Literal["inspect", "probe", "implement", "evaluate", "collect-evidence"]
OperationKind = Literal[
    "resolve-session", "capture-state", "run-focused-probe", "apply-cell-transaction"
]
CodeModeEffect = Literal["none", "read-only", "scratchpad", "live-cells"]


class IdentityRevision(ContractModel):
    identity: Digest
    revision: Digest


class ControllerIdentity(ContractModel):
    source_path: RepositoryPath
    source_digest: Digest


class TargetIdentity(ContractModel):
    repository_digest: Digest
    workbook_path: RepositoryPath
    workbook_digest: Digest | None = None


class MarimoIdentity(ContractModel):
    engine_identity: Digest
    engine_revision: Digest
    mode: Literal["code-mode"] = "code-mode"


class AuthorityIdentity(ContractModel):
    cue_source_digest: Digest
    cue_evaluator_digest: Digest


class BootstrapRunBinding(ContractModel):
    schema_version: Literal["bootstrap-run-binding/v1"] = "bootstrap-run-binding/v1"
    run_id: NonEmpty
    attempt_id: NonEmpty
    phase: BootstrapPhase
    controller: ControllerIdentity
    target: TargetIdentity
    client: IdentityRevision
    skill: IdentityRevision
    marimo: MarimoIdentity
    authority: AuthorityIdentity


class SessionBinding(ContractModel):
    session_id: NonEmpty
    workbook_path: RepositoryPath
    session_metadata_digest: Digest
    resolved_by: Literal["exact-workbook-path"] = "exact-workbook-path"
    resolved_at_sequence: Annotated[int, Field(ge=0)]


class ExecutionLimits(ContractModel):
    timeout_milliseconds: Annotated[int, Field(gt=0, le=300_000)] = 30_000
    maximum_output_bytes: Annotated[int, Field(gt=0, le=1_048_576)] = 262_144
    maximum_stdout_bytes: Annotated[int, Field(gt=0, le=1_048_576)] = 65_536
    maximum_stderr_bytes: Annotated[int, Field(gt=0, le=1_048_576)] = 65_536


class StateProjection(ContractModel):
    cells: bool = True
    graph: bool = True
    variables: bool = False
    outputs: bool = False
    errors: bool = True


class AllCells(ContractModel):
    kind: Literal["all"] = "all"


class ExplicitCells(ContractModel):
    kind: Literal["explicit"] = "explicit"
    cell_ids: Annotated[list[CellID], Field(min_length=1)]

    @model_validator(mode="after")
    def unique_cells(self) -> ExplicitCells:
        if len(self.cell_ids) != len(set(self.cell_ids)):
            raise ValueError("cellIDs must be unique")
        return self


CellSelection = Annotated[AllCells | ExplicitCells, Field(discriminator="kind")]


class ResolveSession(ContractModel):
    kind: Literal["resolve-session"] = "resolve-session"
    operation_id: NonEmpty
    workbook_path: RepositoryPath
    selection_rule: Literal["exactly-one-by-workbook-path"] = "exactly-one-by-workbook-path"
    limits: ExecutionLimits = Field(default_factory=ExecutionLimits)


class CaptureState(ContractModel):
    kind: Literal["capture-state"] = "capture-state"
    operation_id: NonEmpty
    projection: StateProjection = Field(default_factory=StateProjection)
    cell_selection: CellSelection = Field(default_factory=AllCells)
    maximum_output_bytes: Annotated[int, Field(gt=0, le=1_048_576)] = 262_144
    limits: ExecutionLimits = Field(default_factory=ExecutionLimits)


class ProbeSubject(ContractModel):
    workbook_path: RepositoryPath
    cell_ids: list[CellID] = Field(default_factory=list)
    variable_names: list[VariableName] = Field(default_factory=list)


class ProbeParameters(ContractModel):
    variable_name: VariableName | None = None
    cell_id: CellID | None = None


class Probe(ContractModel):
    template_id: Literal["variable-repr", "cell-source"]
    parameters: ProbeParameters

    @model_validator(mode="after")
    def parameters_match_template(self) -> Probe:
        if self.template_id == "variable-repr":
            if self.parameters.variable_name is None or self.parameters.cell_id is not None:
                raise ValueError("variable-repr requires only variableName")
        elif self.parameters.cell_id is None or self.parameters.variable_name is not None:
            raise ValueError("cell-source requires only cellID")
        return self


class ObservationShape(ContractModel):
    kind: Literal["object", "array", "string", "number", "boolean", "null"]
    required_keys: list[str] = Field(default_factory=list)


class RunFocusedProbe(ContractModel):
    kind: Literal["run-focused-probe"] = "run-focused-probe"
    operation_id: NonEmpty
    question_id: NonEmpty
    subject: ProbeSubject
    probe: Probe
    expected_observation_shape: ObservationShape
    limits: ExecutionLimits = Field(default_factory=ExecutionLimits)

    @model_validator(mode="after")
    def probe_is_bound_to_subject(self) -> RunFocusedProbe:
        parameters = self.probe.parameters
        if parameters.cell_id is not None and parameters.cell_id not in self.subject.cell_ids:
            raise ValueError("probe cellID must be declared in subject.cellIDs")
        if (
            parameters.variable_name is not None
            and parameters.variable_name not in self.subject.variable_names
        ):
            raise ValueError("probe variableName must be declared in subject.variableNames")
        return self


class Replacement(ContractModel):
    source: str
    source_digest: Digest

    @model_validator(mode="after")
    def digest_matches_source(self) -> Replacement:
        if self.source_digest != digest_text(self.source):
            raise ValueError("sourceDigest does not match replacement source")
        return self


class TargetCell(ContractModel):
    cell_id: CellID
    expected_preimage_digest: Digest
    replacement: Replacement


class ApplyCellTransaction(ContractModel):
    kind: Literal["apply-cell-transaction"] = "apply-cell-transaction"
    operation_id: NonEmpty
    transaction_id: NonEmpty
    target_cells: Annotated[list[TargetCell], Field(min_length=1, max_length=16)]
    expected_workbook_revision: Digest
    post_capture: StateProjection = Field(default_factory=StateProjection)
    limits: ExecutionLimits = Field(default_factory=ExecutionLimits)

    @model_validator(mode="after")
    def unique_cells(self) -> ApplyCellTransaction:
        cell_ids = [target.cell_id for target in self.target_cells]
        if len(cell_ids) != len(set(cell_ids)):
            raise ValueError("targetCells must contain unique cellIDs")
        return self


BootstrapOperation = Annotated[
    ResolveSession | CaptureState | RunFocusedProbe | ApplyCellTransaction,
    Field(discriminator="kind"),
]


class WorkbookStateIdentity(ContractModel):
    revision: Digest
    cell_digests: dict[CellID, Digest]
    graph_digest: Digest


class RequestIdentity(ContractModel):
    operation_kind: OperationKind
    request_digest: Digest
    generated_code_digest: Digest


class TransportObservation(ContractModel):
    state: Literal["returned", "transport-error", "timed-out"]


class ExecutionObservation(ContractModel):
    state: Literal["exited", "raised", "not-executed"]
    exception_type: str | None = None
    exception_digest: Digest | None = None


class OutputObservation(ContractModel):
    value_digest: Digest | None = None
    stdout_digest: Digest | None = None
    stderr_digest: Digest | None = None
    truncated: bool
    redacted: bool
    shape_matched: bool | None = None


class EffectObservation(ContractModel):
    declared: CodeModeEffect
    observed: CodeModeEffect
    changed_cell_ids: list[CellID]
    unexpected_changed_cell_ids: list[CellID]


class ObservationArtifact(ContractModel):
    kind: NonEmpty
    digest: Digest


StructuralResult = Literal[
    "applied-as-declared",
    "not-applied",
    "partially-applied",
    "unexpected-cell-change",
    "cell-identity-changed",
    "post-state-unavailable",
]


class RawCodeModeObservation(ContractModel):
    schema_version: Literal["raw-code-mode-observation/v1"] = "raw-code-mode-observation/v1"
    run_id: NonEmpty
    attempt_id: NonEmpty
    operation_id: NonEmpty
    session: SessionBinding
    request: RequestIdentity
    transport: TransportObservation
    execution: ExecutionObservation
    output: OutputObservation
    before: WorkbookStateIdentity | None = None
    after: WorkbookStateIdentity | None = None
    effects: EffectObservation
    structural_result: StructuralResult | None = None
    artifacts: list[ObservationArtifact] = Field(default_factory=list)
    recorded_at_sequence: Annotated[int, Field(ge=0)]


class ReleaseDisposition(ContractModel):
    kind: Literal["release"] = "release"
    observation_id: Digest


class ReleaseRedactedDisposition(ContractModel):
    kind: Literal["release-redacted"] = "release-redacted"
    observation_id: Digest


class QuarantineDisposition(ContractModel):
    kind: Literal["quarantine"] = "quarantine"
    observation_id: Digest
    reason: NonEmpty


PostOperationDisposition = Annotated[
    ReleaseDisposition | ReleaseRedactedDisposition | QuarantineDisposition,
    Field(discriminator="kind"),
]


class AllowDecision(ContractModel):
    kind: Literal["allow"] = "allow"
    request_digest: Digest


class AllowWithConstraintsDecision(ContractModel):
    kind: Literal["allow-with-constraints"] = "allow-with-constraints"
    request_digest: Digest
    constraints: ExecutionLimits


class DenyDecision(ContractModel):
    kind: Literal["deny"] = "deny"
    reason: NonEmpty


PreOperationDecision = AllowDecision | AllowWithConstraintsDecision | DenyDecision


_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(?:sk|rk|pk)-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]\s*['\"]?[^\s'\"]+"),
)


def contains_credential_material(value: object) -> bool:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return any(pattern.search(encoded) is not None for pattern in _SECRET_PATTERNS)
