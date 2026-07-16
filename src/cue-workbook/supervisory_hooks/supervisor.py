"""PreToolUse controller and replayable PostToolUse evidence reducer."""
from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path

from .ledger import DurableLedger
from .models import (
    Activity,
    CompletedOperation,
    ControlTransitionRecord,
    Decision,
    Guidance,
    PendingOperation,
    PostObservationRecord,
    PostToolUseInput,
    PreDecisionRecord,
    PreToolUseInput,
    ReducerResult,
    ReductionErrorRecord,
    Scope,
    SupervisorState,
    UnclassifiedObservationRecord,
    default_scope,
    digest_json,
    digest_text,
)
from .policy import (
    classify_tool,
    decide,
    normalize_result,
    project_evidence,
    reduce_observation,
    repository_state_digest,
)


def _approve_response() -> dict[str, object]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "approve",
        }
    }


def _deny_response(decision: Decision) -> dict[str, object]:
    reason = decision.reason
    if decision.guidance is not None:
        reason = f"{reason}: {decision.guidance.model_dump_json(by_alias=True)}"
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _post_guidance_response(status: str, guidance: Guidance | None = None) -> dict[str, object]:
    payload: dict[str, object] = {"evidenceStatus": status}
    if guidance is not None:
        payload.update(guidance.model_dump(by_alias=True, mode="json"))
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": json.dumps(payload, sort_keys=True, separators=(",", ":")),
        }
    }


class Supervisor:
    def __init__(
        self,
        repository_root: Path,
        ledger: DurableLedger,
        *,
        reducer: Callable[..., ReducerResult] = reduce_observation,
    ) -> None:
        self.repository_root = repository_root.resolve(strict=True)
        self.ledger = ledger
        self.reducer = reducer

    def _bind(self, state: SupervisorState, *, session_id: str, turn_id: str) -> SupervisorState:
        run_id = digest_json({"repository": str(self.repository_root), "sessionID": session_id})
        if (
            state.session_id == session_id
            and state.attempt_id == turn_id
            and state.run_id == run_id
        ):
            return state
        return state.model_copy(
            update={"session_id": session_id, "run_id": run_id, "attempt_id": turn_id}
        )

    def _record_unclassified_pre(self, event: PreToolUseInput) -> None:
        with self.ledger.transaction() as transaction:
            sequence = transaction.next_sequence()
            transaction.append(
                UnclassifiedObservationRecord(
                    sequence=sequence,
                    recorded_at_nanoseconds=time.time_ns(),
                    operation_id=event.tool_use_id,
                    stage="pre",
                    session_id=event.session_id,
                    turn_id=event.turn_id,
                    tool_name=event.tool_name,
                    request_digest=digest_json(
                        {"toolName": event.tool_name, "toolInput": event.tool_input}
                    ),
                )
            )

    def _record_unclassified_post(self, event: PostToolUseInput) -> None:
        with self.ledger.transaction() as transaction:
            sequence = transaction.next_sequence()
            transaction.append(
                UnclassifiedObservationRecord(
                    sequence=sequence,
                    recorded_at_nanoseconds=time.time_ns(),
                    operation_id=event.tool_use_id,
                    stage="post",
                    session_id=event.session_id,
                    turn_id=event.turn_id,
                    tool_name=event.tool_name,
                    request_digest=digest_json(
                        {"toolName": event.tool_name, "toolInput": event.tool_input}
                    ),
                    result_digest=digest_json(event.tool_response),
                    outcome=normalize_result(event.tool_response).outcome,
                )
            )

    def handle_pre(self, event: PreToolUseInput) -> dict[str, object]:
        classification = classify_tool(
            event.tool_name,
            event.tool_input,
            repository_root=self.repository_root,
        )
        if not classification.recognized:
            self._record_unclassified_pre(event)
            return _approve_response()

        operation = classification.operation
        assert operation is not None

        with self.ledger.transaction() as transaction:
            state = self._bind(
                transaction.state,
                session_id=event.session_id,
                turn_id=event.turn_id,
            )
            relevant_paths = tuple(
                dict.fromkeys((*state.scope.owned_paths, *operation.target_paths))
            )
            relevant_state_digest = repository_state_digest(
                self.repository_root,
                relevant_paths,
            )
            operation = operation.model_copy(update={"candidate_digest": relevant_state_digest})
            projection = project_evidence(transaction.history)
            decision = decide(state.scope, operation, projection, state.budgets)
            if decision.action == "approve":
                pending = dict(state.pending)
                pending[event.tool_use_id] = PendingOperation(
                    tool_name=event.tool_name,
                    scope=state.scope,
                    operation=operation,
                    relevant_state_digest=relevant_state_digest,
                )
                state = state.model_copy(update={"pending": pending})
            transaction.state = state
            sequence = transaction.next_sequence()
            assert state.run_id is not None
            transaction.append(
                PreDecisionRecord(
                    sequence=sequence,
                    recorded_at_nanoseconds=time.time_ns(),
                    operation_id=event.tool_use_id,
                    run_id=state.run_id,
                    attempt_id=event.turn_id,
                    session_id=event.session_id,
                    turn_id=event.turn_id,
                    scope=state.scope,
                    tool_name=event.tool_name,
                    target_id=operation.target_id,
                    request_digest=operation.request_digest,
                    relevant_state_digest=relevant_state_digest,
                    candidate_digest=operation.candidate_digest,
                    action=decision.action,
                    reason=decision.reason,
                    matched_predicates=decision.matched_predicates,
                )
            )
        return _approve_response() if decision.action == "approve" else _deny_response(decision)

    def handle_post(self, event: PostToolUseInput) -> dict[str, object]:
        classification = classify_tool(
            event.tool_name,
            event.tool_input,
            repository_root=self.repository_root,
        )
        if not classification.recognized:
            self._record_unclassified_post(event)
            return {}

        observed = normalize_result(event.tool_response)
        request_digest = digest_json({"toolName": event.tool_name, "toolInput": event.tool_input})
        with self.ledger.transaction() as transaction:
            state = self._bind(
                transaction.state,
                session_id=event.session_id,
                turn_id=event.turn_id,
            )
            pending = dict(state.pending)
            expected = pending.pop(event.tool_use_id, None)
            state = state.model_copy(update={"pending": pending})
            transaction.state = state

            if expected is None:
                operation = classification.operation
                assert operation is not None
                relevant_paths = tuple(
                    dict.fromkeys((*state.scope.owned_paths, *operation.target_paths))
                )
                current_state_digest = repository_state_digest(
                    self.repository_root,
                    relevant_paths,
                )
                operation = operation.model_copy(update={"candidate_digest": current_state_digest})
                completed = CompletedOperation(
                    scope=state.scope,
                    operation=operation,
                    relevant_state_digest=current_state_digest,
                    tool_name=event.tool_name,
                )
                unmatched = True
            else:
                relevant_paths = tuple(
                    dict.fromkeys(
                        (*expected.scope.owned_paths, *expected.operation.target_paths)
                    )
                )
                current_state_digest = repository_state_digest(
                    self.repository_root,
                    relevant_paths,
                )
                completed = CompletedOperation(
                    scope=expected.scope,
                    operation=expected.operation.model_copy(
                        update={"candidate_digest": current_state_digest}
                    ),
                    relevant_state_digest=expected.relevant_state_digest,
                    tool_name=expected.tool_name,
                )
                unmatched = False

            projection = project_evidence(transaction.history)
            try:
                reduced = self.reducer(projection, completed, observed)
            except Exception as error:  # reducer faults become local evidence, never control state
                sequence = transaction.next_sequence()
                transaction.append(
                    ReductionErrorRecord(
                        sequence=sequence,
                        recorded_at_nanoseconds=time.time_ns(),
                        operation_id=event.tool_use_id,
                        session_id=event.session_id,
                        turn_id=event.turn_id,
                        tool_name=event.tool_name,
                        request_digest=request_digest,
                        error_digest=digest_text(f"{type(error).__name__}:{error}"),
                    )
                )
                return _post_guidance_response("reducer-error")

            sequence = transaction.next_sequence()
            assert state.run_id is not None
            evidence_status = "unmatched-post-observed" if unmatched else reduced.evidence_status
            transaction.append(
                PostObservationRecord(
                    sequence=sequence,
                    recorded_at_nanoseconds=time.time_ns(),
                    operation_id=event.tool_use_id,
                    run_id=state.run_id,
                    attempt_id=event.turn_id,
                    session_id=event.session_id,
                    turn_id=event.turn_id,
                    scope=completed.scope,
                    tool_name=completed.tool_name,
                    target_id=reduced.observation.target_id,
                    request_digest=reduced.observation.request_digest,
                    relevant_state_digest=reduced.observation.relevant_state_digest,
                    result_digest=reduced.observation.result_digest,
                    candidate_digest=reduced.observation.candidate_digest,
                    failure_signature=reduced.observation.failure_signature,
                    required_observation_channel=(
                        reduced.observation.required_observation_channel
                    ),
                    outcome=reduced.observation.outcome,
                    evidence_status=evidence_status,
                    progress=reduced.progress,
                    guidance=reduced.guidance,
                )
            )
        if reduced.guidance is not None or unmatched:
            return _post_guidance_response(evidence_status, reduced.guidance)
        return {}

    def set_scope(self, scope: Scope, *, reason: str) -> SupervisorState:
        if not reason.strip():
            raise ValueError("scope transition reason must be nonempty")
        with self.ledger.transaction() as transaction:
            state = transaction.state
            previous = state.scope
            transaction.state = state.model_copy(update={"scope": scope})
            sequence = transaction.next_sequence()
            transaction.append(
                ControlTransitionRecord(
                    sequence=sequence,
                    recorded_at_nanoseconds=time.time_ns(),
                    operation_id=f"operator-scope-{sequence}",
                    run_id=state.run_id,
                    attempt_id=state.attempt_id,
                    previous_scope=previous,
                    scope=scope,
                    reason=reason,
                )
            )
            return transaction.state

    def set_phase(self, activity: Activity, *, reason: str) -> SupervisorState:
        """Compatibility transition; new callers should provide an explicit scope."""
        return self.set_scope(default_scope(activity), reason=reason)

    def status(self) -> dict[str, object]:
        state = self.ledger.read_state()
        return state.model_dump(by_alias=True, mode="json")
