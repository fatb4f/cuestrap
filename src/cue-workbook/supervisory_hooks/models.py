"""Typed Codex hook ingress and durable supervisory records."""
from __future__ import annotations

import hashlib
import json
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

DIGEST_PATTERN = r"^sha256:[0-9a-f]{64}$"
Digest = Annotated[str, Field(pattern=DIGEST_PATTERN)]
NonEmpty = Annotated[str, Field(min_length=1)]
Phase = Literal["inspect", "probe", "implement", "evaluate", "collect-evidence"]
PermissionMode = Literal["default", "acceptEdits", "plan", "dontAsk", "bypassPermissions"]
ToolClass = Literal[
    "read-only",
    "evaluation",
    "workspace-mutation",
    "code-mode-read",
    "code-mode-probe",
    "code-mode-mutation",
    "direct-code-mode",
    "git-mutation",
    "external-mcp",
    "supervisor-control",
    "unknown",
]


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


class PendingOperation(ContractModel):
    request_digest: Digest
    repository_state_digest: Digest
    tool_name: NonEmpty
    tool_class: ToolClass
    phase: Phase


class SupervisorState(ContractModel):
    schema_version: Literal["supervisory-state/v1"] = "supervisory-state/v1"
    phase: Phase = "inspect"
    sequence: Annotated[int, Field(ge=0)] = 0
    session_id: NonEmpty | None = None
    run_id: Digest | None = None
    attempt_id: NonEmpty | None = None
    quarantined: bool = False
    quarantine_reason: NonEmpty | None = None
    quarantine_sequence: Annotated[int, Field(ge=0)] | None = None
    mutation_requires_evaluation: bool = False
    last_evaluation_sequence: Annotated[int, Field(ge=0)] | None = None
    pending: dict[str, PendingOperation] = Field(default_factory=dict)
    failed_fingerprints: dict[Digest, Annotated[int, Field(gt=0)]] = Field(default_factory=dict)


class LedgerRecord(ContractModel):
    schema_version: Literal["supervisory-tool-event/v1"] = "supervisory-tool-event/v1"
    kind: NonEmpty
    sequence: Annotated[int, Field(ge=0)]
    recorded_at_nanoseconds: Annotated[int, Field(ge=0)]
    operation_id: NonEmpty


class PreDecisionRecord(LedgerRecord):
    kind: Literal["pre-decision"] = "pre-decision"
    run_id: Digest
    attempt_id: NonEmpty
    session_id: NonEmpty
    turn_id: NonEmpty
    phase: Phase
    tool_name: NonEmpty
    tool_class: ToolClass
    request_digest: Digest
    repository_state_digest: Digest
    decision: Literal["allow", "deny"]
    reason: NonEmpty
    coverage: Literal["codex-supported-hook-event"] = "codex-supported-hook-event"


class PostObservationRecord(LedgerRecord):
    kind: Literal["post-observation"] = "post-observation"
    run_id: Digest
    attempt_id: NonEmpty
    session_id: NonEmpty
    turn_id: NonEmpty
    phase: Phase
    tool_name: NonEmpty
    tool_class: ToolClass
    request_digest: Digest
    response_digest: Digest
    repository_state_digest: Digest
    outcome: Literal["returned", "reported-error", "not-dispatched"]
    redacted: bool
    quarantined: bool
    reason: NonEmpty
    coverage: Literal["codex-supported-hook-event"] = "codex-supported-hook-event"


class ControlTransitionRecord(LedgerRecord):
    kind: Literal["control-transition"] = "control-transition"
    run_id: Digest | None = None
    attempt_id: NonEmpty | None = None
    phase: Phase
    previous_phase: Phase
    reason: NonEmpty


class Classification(ContractModel):
    tool_class: ToolClass
    operation: str | None = None
    mutating: bool = False
    evaluation: bool = False


JsonObject = dict[str, object]
