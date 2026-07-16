"""Closed contracts for the phase-aware anti-churn supervisor."""
from __future__ import annotations

import hashlib
import json
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DIGEST_PATTERN = r"^sha256:[0-9a-f]{64}$"
Digest = Annotated[str, Field(pattern=DIGEST_PATTERN)]
NonEmpty = Annotated[str, Field(min_length=1)]
Activity = Literal["inspect", "probe", "implement", "evaluate", "collect-evidence"]
Surface = Literal[
    "authority",
    "pattern",
    "kernel",
    "fixture",
    "probe",
    "runner",
    "workbook",
    "none",
]
ArtifactRole = Literal["owned", "protected", "generated", "runtime-state", "unclassified"]
OperationClass = Literal["read", "probe", "mutation", "evaluation", "transition"]
ObservationChannel = Literal[
    "static-source",
    "runtime",
    "lsp",
    "native-evaluation",
    "code-mode",
    "control",
]
TargetID = Literal[
    "shell.read",
    "git.read",
    "git.mutation",
    "cue.lsp",
    "gopls.read",
    "workspace.apply-patch",
    "workspace.mutation",
    "supervisor.transition",
    "code-mode.resolve-session",
    "code-mode.capture-state",
    "code-mode.run-focused-probe",
    "code-mode.apply-cell-transaction",
    "evaluation.cue",
    "evaluation.python",
    "evaluation.go",
    "evaluation.workbook",
    "just.list",
    "just.summary",
    "just.dump",
    "just.check",
]
DecisionReason = Literal[
    "phase-relevant",
    "new-observation",
    "bounded-correction",
    "unknown-operation",
    "identical-retry",
    "failure-cluster-exhausted",
    "fanout-budget-exceeded",
    "wrong-observation-channel",
    "phase-invalid-churn",
    "mixed-candidate-state",
    "protected-artifact-mutation",
]
DenialReason = Literal[
    "protected-artifact-mutation",
    "mixed-candidate-state",
    "wrong-observation-channel",
    "identical-retry",
    "failure-cluster-exhausted",
    "fanout-budget-exceeded",
    "phase-invalid-churn",
]
PermissionMode = Literal["default", "acceptEdits", "plan", "dontAsk", "bypassPermissions"]
ToolOutcome = Literal["returned", "reported-error", "not-dispatched", "reducer-error"]


DEFAULT_TARGETS_BY_ACTIVITY: dict[Activity, tuple[TargetID, ...]] = {
    "inspect": (
        "shell.read",
        "git.read",
        "cue.lsp",
        "gopls.read",
        "code-mode.resolve-session",
        "code-mode.capture-state",
    ),
    "probe": (
        "shell.read",
        "git.read",
        "cue.lsp",
        "gopls.read",
        "code-mode.resolve-session",
        "code-mode.capture-state",
        "code-mode.run-focused-probe",
    ),
    "implement": (
        "shell.read",
        "git.read",
        "cue.lsp",
        "gopls.read",
        "workspace.apply-patch",
        "code-mode.capture-state",
        "code-mode.apply-cell-transaction",
        "supervisor.transition",
    ),
    "evaluate": (
        "shell.read",
        "git.read",
        "cue.lsp",
        "gopls.read",
        "code-mode.capture-state",
        "code-mode.run-focused-probe",
        "evaluation.cue",
        "evaluation.python",
        "evaluation.go",
        "evaluation.workbook",
        "just.list",
        "just.summary",
        "just.dump",
        "just.check",
        "supervisor.transition",
    ),
    "collect-evidence": (
        "shell.read",
        "git.read",
        "cue.lsp",
        "gopls.read",
        "code-mode.capture-state",
        "just.list",
        "just.summary",
        "just.dump",
        "just.check",
        "supervisor.transition",
    ),
}


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


class HookInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: NonEmpty
    transcript_path: str | None
    cwd: NonEmpty
    hook_event_name: NonEmpty
    model: NonEmpty
    turn_id: NonEmpty
    permission_mode: PermissionMode


class PreToolUseInput(HookInput):
    hook_event_name: Literal["PreToolUse"]
    tool_name: NonEmpty
    tool_use_id: NonEmpty
    tool_input: Any


class PostToolUseInput(HookInput):
    hook_event_name: Literal["PostToolUse"]
    tool_name: NonEmpty
    tool_use_id: NonEmpty
    tool_input: Any
    tool_response: Any


class ContractModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        extra="forbid",
        frozen=True,
        populate_by_name=True,
    )


class Scope(ContractModel):
    activity: Activity
    surface: Surface
    owned_paths: tuple[NonEmpty, ...] = ()
    allowed_targets: tuple[TargetID, ...]

    @model_validator(mode="after")
    def unique_values(self) -> "Scope":
        if len(set(self.owned_paths)) != len(self.owned_paths):
            raise ValueError("owned paths must be unique")
        if len(set(self.allowed_targets)) != len(self.allowed_targets):
            raise ValueError("allowed targets must be unique")
        return self


def default_scope(activity: Activity = "inspect") -> Scope:
    return Scope(
        activity=activity,
        surface="none",
        owned_paths=(),
        allowed_targets=DEFAULT_TARGETS_BY_ACTIVITY[activity],
    )


class Budgets(ContractModel):
    maximum_failure_cluster_corrections: Annotated[int, Field(ge=1, le=10)] = 2
    maximum_observation_fanout: Annotated[int, Field(ge=1, le=10000)] = 64


class Guidance(ContractModel):
    retry_requires_any: tuple[NonEmpty, ...] = ()
    recommended_targets: tuple[TargetID, ...] = ()


class ProgressEvidence(ContractModel):
    request_changed: bool
    result_changed: bool
    relevant_state_changed: bool
    candidate_changed: bool
    resolved_question_ids: tuple[NonEmpty, ...] = ()
    introduced_question_ids: tuple[NonEmpty, ...] = ()


class CanonicalOperation(ContractModel):
    target_id: TargetID
    operation_class: OperationClass
    request_digest: Digest
    mutating: bool = False
    target_paths: tuple[str, ...] = ()
    artifact_roles: tuple[ArtifactRole, ...] = ()
    observation_channel: ObservationChannel
    fanout: Annotated[int, Field(ge=1)] = 1
    candidate_digest: Digest | None = None
    question_ids: tuple[NonEmpty, ...] = ()


class Classification(ContractModel):
    recognized: bool
    operation: CanonicalOperation | None = None

    @model_validator(mode="after")
    def operation_matches_recognition(self) -> "Classification":
        if self.recognized != (self.operation is not None):
            raise ValueError("recognized classifications require exactly one canonical operation")
        return self


class ObservationSummary(ContractModel):
    target_id: TargetID
    activity: Activity
    request_digest: Digest
    relevant_state_digest: Digest
    result_digest: Digest
    candidate_digest: Digest | None = None
    failure_signature: Digest | None = None
    required_observation_channel: ObservationChannel | None = None
    outcome: ToolOutcome


class LedgerProjection(ContractModel):
    observations: tuple[ObservationSummary, ...] = ()
    active_candidate_digest: Digest | None = None
    active_failure_signature: Digest | None = None
    required_observation_channel: ObservationChannel | None = None
    unresolved_question_ids: tuple[NonEmpty, ...] = ()


class Decision(ContractModel):
    action: Literal["approve", "deny"]
    reason: DecisionReason
    matched_predicates: tuple[DenialReason, ...] = ()
    guidance: Guidance | None = None


class PendingOperation(ContractModel):
    tool_name: NonEmpty
    scope: Scope
    operation: CanonicalOperation
    relevant_state_digest: Digest


class SupervisorState(ContractModel):
    schema_version: Literal["supervisory-state/v2"] = "supervisory-state/v2"
    version: Literal[2] = 2
    scope: Scope = Field(default_factory=default_scope)
    budgets: Budgets = Field(default_factory=Budgets)
    session_id: NonEmpty | None = None
    run_id: Digest | None = None
    attempt_id: NonEmpty | None = None
    pending: dict[str, PendingOperation] = Field(default_factory=dict)
    legacy_state_digest: Digest | None = None


class V1PendingOperation(ContractModel):
    request_digest: Digest
    repository_state_digest: Digest
    tool_name: NonEmpty
    tool_class: NonEmpty
    phase: Activity


class SupervisorStateV1(ContractModel):
    schema_version: Literal["supervisory-state/v1"] = "supervisory-state/v1"
    phase: Activity = "inspect"
    sequence: Annotated[int, Field(ge=0)] = 0
    session_id: NonEmpty | None = None
    run_id: Digest | None = None
    attempt_id: NonEmpty | None = None
    quarantined: bool = False
    quarantine_reason: NonEmpty | None = None
    quarantine_sequence: Annotated[int, Field(ge=0)] | None = None
    mutation_requires_evaluation: bool = False
    last_evaluation_sequence: Annotated[int, Field(ge=0)] | None = None
    pending: dict[str, V1PendingOperation] = Field(default_factory=dict)
    failed_fingerprints: dict[Digest, Annotated[int, Field(gt=0)]] = Field(default_factory=dict)


class EvidenceRecord(ContractModel):
    schema_version: Literal["supervisory-evidence/v2"] = "supervisory-evidence/v2"
    kind: NonEmpty
    sequence: Annotated[int, Field(ge=1)]
    recorded_at_nanoseconds: Annotated[int, Field(ge=0)]
    operation_id: NonEmpty


class PreDecisionRecord(EvidenceRecord):
    kind: Literal["pre-decision"] = "pre-decision"
    run_id: Digest
    attempt_id: NonEmpty
    session_id: NonEmpty
    turn_id: NonEmpty
    scope: Scope
    tool_name: NonEmpty
    recognized: Literal[True] = True
    target_id: TargetID
    request_digest: Digest
    relevant_state_digest: Digest
    candidate_digest: Digest | None = None
    action: Literal["approve", "deny"]
    reason: DecisionReason
    matched_predicates: tuple[DenialReason, ...] = ()
    coverage: Literal["codex-supported-hook-event"] = "codex-supported-hook-event"


class UnclassifiedObservationRecord(EvidenceRecord):
    kind: Literal["unclassified-observation"] = "unclassified-observation"
    stage: Literal["pre", "post"]
    session_id: NonEmpty
    turn_id: NonEmpty
    tool_name: NonEmpty
    request_digest: Digest
    result_digest: Digest | None = None
    outcome: ToolOutcome | None = None


class PostObservationRecord(EvidenceRecord):
    kind: Literal["post-observation"] = "post-observation"
    run_id: Digest
    attempt_id: NonEmpty
    session_id: NonEmpty
    turn_id: NonEmpty
    scope: Scope
    tool_name: NonEmpty
    target_id: TargetID
    request_digest: Digest
    relevant_state_digest: Digest
    result_digest: Digest
    candidate_digest: Digest | None = None
    failure_signature: Digest | None = None
    required_observation_channel: ObservationChannel | None = None
    outcome: ToolOutcome
    evidence_status: NonEmpty
    progress: ProgressEvidence
    guidance: Guidance | None = None
    coverage: Literal["codex-supported-hook-event"] = "codex-supported-hook-event"


class ControlTransitionRecord(EvidenceRecord):
    kind: Literal["control-transition"] = "control-transition"
    run_id: Digest | None = None
    attempt_id: NonEmpty | None = None
    previous_scope: Scope
    scope: Scope
    reason: NonEmpty


class ReductionErrorRecord(EvidenceRecord):
    kind: Literal["reduction-error"] = "reduction-error"
    session_id: NonEmpty
    turn_id: NonEmpty
    tool_name: NonEmpty
    request_digest: Digest
    error_digest: Digest


class CompletedOperation(ContractModel):
    scope: Scope
    operation: CanonicalOperation
    relevant_state_digest: Digest
    tool_name: NonEmpty


class ObservedResult(ContractModel):
    outcome: ToolOutcome
    result_class: NonEmpty
    result_digest: Digest
    required_observation_channel: ObservationChannel | None = None
    resolved_question_ids: tuple[NonEmpty, ...] = ()
    introduced_question_ids: tuple[NonEmpty, ...] = ()


class ReducerResult(ContractModel):
    observation: ObservationSummary
    progress: ProgressEvidence
    evidence_status: NonEmpty
    guidance: Guidance | None = None


JsonObject = dict[str, object]
