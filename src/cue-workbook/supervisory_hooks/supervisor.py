"""Stateful PreToolUse/PostToolUse controller for supported Codex hook events."""
from __future__ import annotations

import time
from pathlib import Path

from .ledger import DurableLedger
from .models import (
    Classification,
    ControlTransitionRecord,
    PendingOperation,
    Phase,
    PostObservationRecord,
    PostToolUseInput,
    PreDecisionRecord,
    PreToolUseInput,
    SupervisorState,
    digest_json,
    digest_text,
)
from .policy import (
    classify_tool,
    contains_credential_material,
    decide,
    fingerprint,
    repository_state_digest,
    response_reported_error,
)


def _allow_response() -> dict[str, object]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
    }


def _deny_response(reason: str) -> dict[str, object]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _quarantine_response(reason: str) -> dict[str, object]:
    return {
        "decision": "block",
        "reason": reason,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": reason,
        },
    }


class Supervisor:
    def __init__(self, repository_root: Path, ledger: DurableLedger) -> None:
        self.repository_root = repository_root.resolve(strict=True)
        self.ledger = ledger

    def _bind(self, state: SupervisorState, *, session_id: str, turn_id: str) -> SupervisorState:
        if state.session_id is None:
            return state.model_copy(
                update={
                    "session_id": session_id,
                    "run_id": digest_json(
                        {"repository": str(self.repository_root), "sessionID": session_id}
                    ),
                    "attempt_id": turn_id,
                }
            )
        if state.session_id != session_id:
            return state.model_copy(
                update={
                    "phase": "inspect",
                    "session_id": session_id,
                    "run_id": digest_json(
                        {"repository": str(self.repository_root), "sessionID": session_id}
                    ),
                    "attempt_id": turn_id,
                    "quarantined": False,
                    "quarantine_reason": None,
                    "quarantine_sequence": None,
                    "mutation_requires_evaluation": False,
                    "last_evaluation_sequence": None,
                    "pending": {},
                    "failed_fingerprints": {},
                }
            )
        return state.model_copy(update={"attempt_id": turn_id})

    def _cwd_is_bound(self, cwd: str) -> bool:
        try:
            Path(cwd).resolve(strict=True).relative_to(self.repository_root)
        except (OSError, ValueError):
            return False
        return True

    def handle_pre(self, event: PreToolUseInput) -> dict[str, object]:
        request_digest = digest_json({"toolName": event.tool_name, "toolInput": event.tool_input})
        repository_digest = repository_state_digest(self.repository_root)
        classification = classify_tool(event.tool_name, event.tool_input)
        with self.ledger.transaction() as transaction:
            state = self._bind(
                transaction.state,
                session_id=event.session_id,
                turn_id=event.turn_id,
            )
            if not self._cwd_is_bound(event.cwd):
                allowed, reason = False, "hook working directory is outside the bound repository"
            elif contains_credential_material(event.tool_input):
                allowed, reason = False, "tool input contains credential-shaped material"
            elif event.tool_use_id in state.pending:
                allowed, reason = False, "tool use ID already has a pending allowed operation"
            else:
                allowed, reason = decide(
                    state,
                    classification,
                    request_digest=request_digest,
                    repository_state_digest=repository_digest,
                )

            sequence = transaction.next_sequence()
            if allowed:
                pending = dict(state.pending)
                pending[event.tool_use_id] = PendingOperation(
                    request_digest=request_digest,
                    repository_state_digest=repository_digest,
                    tool_name=event.tool_name,
                    tool_class=classification.tool_class,
                    phase=state.phase,
                )
                state = state.model_copy(update={"pending": pending})
            transaction.state = state.model_copy(update={"sequence": sequence})
            transaction.append(
                PreDecisionRecord(
                    sequence=sequence,
                    recorded_at_nanoseconds=time.time_ns(),
                    run_id=transaction.state.run_id,
                    attempt_id=event.turn_id,
                    operation_id=event.tool_use_id,
                    session_id=event.session_id,
                    turn_id=event.turn_id,
                    phase=transaction.state.phase,
                    tool_name=event.tool_name,
                    tool_class=classification.tool_class,
                    request_digest=request_digest,
                    repository_state_digest=repository_digest,
                    decision="allow" if allowed else "deny",
                    reason=reason,
                )
            )
        return _allow_response() if allowed else _deny_response(reason)

    def handle_post(self, event: PostToolUseInput) -> dict[str, object]:
        request_digest = digest_json({"toolName": event.tool_name, "toolInput": event.tool_input})
        response_digest = digest_json(event.tool_response)
        repository_digest = repository_state_digest(self.repository_root)
        classification = classify_tool(event.tool_name, event.tool_input)
        reported_error = response_reported_error(event.tool_response)
        redacted = contains_credential_material(event.tool_response)

        with self.ledger.transaction() as transaction:
            state = self._bind(
                transaction.state,
                session_id=event.session_id,
                turn_id=event.turn_id,
            )
            pending = dict(state.pending)
            expected = pending.pop(event.tool_use_id, None)
            quarantine_reason: str | None = None
            if expected is None:
                quarantine_reason = "post event has no matching allowed pre-tool decision"
            elif expected.request_digest != request_digest or expected.tool_name != event.tool_name:
                quarantine_reason = "post event does not match its recorded pre-tool request"
            elif expected.tool_class != classification.tool_class:
                quarantine_reason = "tool classification changed between pre and post events"
            elif redacted:
                quarantine_reason = "tool response contained credential-shaped material and was redacted"
            elif classification.mutating and expected.phase != "implement":
                quarantine_reason = "observed mutation was not admitted in the implement phase"

            sequence = transaction.next_sequence()
            updates: dict[str, object] = {"pending": pending, "sequence": sequence}
            if quarantine_reason is not None:
                updates.update(
                    {
                        "quarantined": True,
                        "quarantine_reason": quarantine_reason,
                        "quarantine_sequence": sequence,
                    }
                )
            elif (
                classification.tool_class == "code-mode-read"
                and classification.operation == "capture-state"
                and not reported_error
            ):
                updates.update(
                    {
                        "quarantined": False,
                        "quarantine_reason": None,
                        "quarantine_sequence": None,
                    }
                )
            if classification.mutating and not reported_error:
                updates["mutation_requires_evaluation"] = True
            if classification.evaluation and state.phase == "evaluate" and not reported_error:
                updates.update(
                    {
                        "mutation_requires_evaluation": False,
                        "last_evaluation_sequence": sequence,
                    }
                )

            failures = dict(state.failed_fingerprints)
            if reported_error:
                before_digest = (
                    expected.repository_state_digest if expected is not None else repository_digest
                )
                key = fingerprint(state.phase, request_digest, before_digest)
                failures[key] = failures.get(key, 0) + 1
            updates["failed_fingerprints"] = failures
            transaction.state = state.model_copy(update=updates)

            outcome = "reported-error" if reported_error else "returned"
            reason = quarantine_reason or (
                "tool response reported an error" if reported_error else "tool response was recorded"
            )
            transaction.append(
                PostObservationRecord(
                    sequence=sequence,
                    recorded_at_nanoseconds=time.time_ns(),
                    run_id=transaction.state.run_id,
                    attempt_id=event.turn_id,
                    operation_id=event.tool_use_id,
                    session_id=event.session_id,
                    turn_id=event.turn_id,
                    phase=state.phase,
                    tool_name=event.tool_name,
                    tool_class=classification.tool_class,
                    request_digest=request_digest,
                    response_digest=response_digest,
                    repository_state_digest=repository_digest,
                    outcome=outcome,
                    redacted=redacted,
                    quarantined=quarantine_reason is not None,
                    reason=reason,
                )
            )
        return _quarantine_response(quarantine_reason) if quarantine_reason else {}

    def set_phase(self, phase: Phase, *, reason: str) -> SupervisorState:
        if not reason.strip():
            raise ValueError("phase transition reason must be nonempty")
        with self.ledger.transaction() as transaction:
            state = transaction.state
            if phase == "implement" and state.quarantined:
                raise ValueError("cannot enter implement while supervisory state is quarantined")
            if phase == "implement" and state.mutation_requires_evaluation:
                raise ValueError("cannot re-enter implement before an evaluation observation")
            previous = state.phase
            sequence = transaction.next_sequence()
            transaction.state = state.model_copy(update={"phase": phase, "sequence": sequence})
            transaction.append(
                ControlTransitionRecord(
                    sequence=sequence,
                    recorded_at_nanoseconds=time.time_ns(),
                    operation_id=f"operator-phase-{sequence}",
                    run_id=state.run_id,
                    attempt_id=state.attempt_id,
                    phase=phase,
                    previous_phase=previous,
                    reason=reason,
                )
            )
            return transaction.state

    def status(self) -> dict[str, object]:
        state = self.ledger.read_state()
        return state.model_dump(by_alias=True, mode="json")
