"""Public closed-operation bootstrap code-mode client."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .binding import resolve_exact_session, validate_run_binding
from .codegen import capture_state_code, cell_transaction_code, focused_probe_code
from .codegen.capture_state import state_capture_code
from .codegen.common import decode_marked_json
from .generated.models import (
    AllowDecision,
    ApplyCellTransaction,
    BootstrapRunBinding,
    CaptureState,
    EffectObservation,
    ExecutionObservation,
    OutputObservation,
    QuarantineDisposition,
    RawCodeModeObservation,
    RequestIdentity,
    ResolveSession,
    SessionBinding,
    StateProjection,
    TransportObservation,
    WorkbookStateIdentity,
    digest_json,
    digest_text,
)
from .mcp_adapter import AdapterResult, MCPAdapter
from .post_hook import build_observation, disposition, parse_identity
from .pre_hook import evaluate_pre_hook
from .recorder import MemoryObservationRecorder


class PreHookDenied(RuntimeError):
    pass


class QuarantinedObservation(RuntimeError):
    def __init__(
        self,
        observation: RawCodeModeObservation,
        result: QuarantineDisposition,
    ) -> None:
        super().__init__(result.reason)
        self.observation = observation
        self.disposition = result


class BootstrapCodeModeClient:
    def __init__(
        self,
        run: BootstrapRunBinding,
        repository_root: Path,
        adapter: MCPAdapter,
        *,
        recorder: MemoryObservationRecorder | None = None,
        session_binding: SessionBinding | None = None,
    ) -> None:
        self.run = run
        self.repository_root = repository_root.resolve(strict=True)
        self.workbook = validate_run_binding(run, self.repository_root)
        self.adapter = adapter
        self.recorder = recorder or MemoryObservationRecorder()
        self._session: SessionBinding | None = session_binding
        self._mutation_gate_open = True
        self._quarantined = False

    @property
    def session_binding(self) -> SessionBinding | None:
        return self._session

    def _pre_hook(
        self,
        operation: Any,
        *,
        expected_state: WorkbookStateIdentity | None = None,
        defer_transaction_state: bool = False,
    ) -> str:
        decision = evaluate_pre_hook(
            self.run,
            operation,
            repository_root=self.repository_root,
            session=self._session,
            expected_state=expected_state,
            defer_transaction_state=defer_transaction_state,
        )
        if not isinstance(decision, AllowDecision):
            reason = getattr(decision, "reason", "operation was denied")
            raise PreHookDenied(reason)
        return decision.request_digest

    def _record_and_release(self, observation: RawCodeModeObservation) -> RawCodeModeObservation:
        observation_id = self.recorder.record(observation)
        result = disposition(observation, observation_id)
        if isinstance(result, QuarantineDisposition):
            self._quarantined = True
            self._mutation_gate_open = False
            raise QuarantinedObservation(observation, result)
        return observation

    @staticmethod
    def _engine_matches(run: BootstrapRunBinding, decoded: object) -> bool:
        if not isinstance(decoded, dict):
            return False
        engine = decoded.get("engine")
        if not isinstance(engine, dict):
            return False
        return (
            engine.get("engineIdentity") == run.marimo.engine_identity
            and engine.get("engineRevision") == run.marimo.engine_revision
            and engine.get("mode") == run.marimo.mode
        )

    async def resolve_session(self, operation: ResolveSession) -> SessionBinding:
        request_digest = self._pre_hook(operation)
        result = await self.adapter.list_sessions(
            timeout_milliseconds=operation.limits.timeout_milliseconds
        )
        sessions = result.payload.get("sessions")
        if result.transport_state != "returned" or not isinstance(sessions, list):
            raise RuntimeError("list_sessions did not return a session list")
        binding = resolve_exact_session(
            sessions,
            self.workbook,
            self.repository_root,
            sequence=self.recorder.next_sequence,
        )
        observation = RawCodeModeObservation(
            run_id=self.run.run_id,
            attempt_id=self.run.attempt_id,
            operation_id=operation.operation_id,
            session=binding,
            request=RequestIdentity(
                operation_kind=operation.kind,
                request_digest=request_digest,
                generated_code_digest=digest_text(""),
            ),
            transport=TransportObservation(state=result.transport_state),
            execution=ExecutionObservation(state=result.execution_state),
            output=OutputObservation(
                value_digest=digest_json(sessions),
                truncated=len(json.dumps(sessions).encode()) > operation.limits.maximum_output_bytes,
                redacted=False,
            ),
            effects=EffectObservation(
                declared="read-only",
                observed="read-only",
                changed_cell_ids=[],
                unexpected_changed_cell_ids=[],
            ),
            recorded_at_sequence=self.recorder.next_sequence,
        )
        self._record_and_release(observation)
        self._session = binding
        return binding

    async def _execute_capture_code(
        self,
        code: str,
        *,
        timeout_milliseconds: int,
    ) -> tuple[AdapterResult, dict[str, object] | None]:
        if self._session is None:
            raise PreHookDenied("operation requires a current session binding")
        result = await self.adapter.execute_code(
            self._session.session_id,
            code,
            timeout_milliseconds=timeout_milliseconds,
        )
        return result, decode_marked_json(result)

    async def _validate_current_session(self, *, timeout_milliseconds: int) -> None:
        if self._session is None:
            raise PreHookDenied("operation requires a current session binding")
        result = await self.adapter.list_sessions(timeout_milliseconds=timeout_milliseconds)
        sessions = result.payload.get("sessions")
        if result.transport_state != "returned" or not isinstance(sessions, list):
            self._session = None
            raise PreHookDenied("current session binding could not be checked")
        current = resolve_exact_session(
            sessions,
            self.workbook,
            self.repository_root,
            sequence=self._session.resolved_at_sequence,
        )
        if current != self._session:
            self._session = None
            raise PreHookDenied("session binding no longer identifies the exact workbook")

    async def capture_state(self, operation: CaptureState) -> RawCodeModeObservation:
        request_digest = self._pre_hook(operation)
        await self._validate_current_session(
            timeout_milliseconds=operation.limits.timeout_milliseconds
        )
        code = capture_state_code(operation)
        result, decoded = await self._execute_capture_code(
            code, timeout_milliseconds=operation.limits.timeout_milliseconds
        )
        before = parse_identity(decoded.get("before")) if decoded else None
        after = parse_identity(decoded.get("after")) if decoded else None
        state = decoded.get("state") if decoded else None
        if isinstance(state, dict) and state.get("missingCellIDs"):
            after = None
        if decoded and not self._engine_matches(self.run, decoded):
            after = None
        observation = build_observation(
            run=self.run,
            operation=operation,
            session=self._session,
            request_digest=request_digest,
            generated_code=code,
            adapter_result=result,
            decoded_value=state,
            before=before,
            after=after,
            sequence=self.recorder.next_sequence,
            force_truncated=bool(decoded and decoded.get("truncated")),
        )
        released = self._record_and_release(observation)
        self._quarantined = False
        self._mutation_gate_open = True
        return released

    async def run_focused_probe(self, operation) -> RawCodeModeObservation:
        request_digest = self._pre_hook(operation)
        await self._validate_current_session(
            timeout_milliseconds=operation.limits.timeout_milliseconds
        )
        code = focused_probe_code(operation)
        result, decoded = await self._execute_capture_code(
            code, timeout_milliseconds=operation.limits.timeout_milliseconds
        )
        before = parse_identity(decoded.get("before")) if decoded else None
        after = parse_identity(decoded.get("after")) if decoded else None
        value = decoded.get("observation") if decoded else None
        if decoded and not self._engine_matches(self.run, decoded):
            after = None
        observation = build_observation(
            run=self.run,
            operation=operation,
            session=self._session,
            request_digest=request_digest,
            generated_code=code,
            adapter_result=result,
            decoded_value=value,
            before=before,
            after=after,
            sequence=self.recorder.next_sequence,
            expected_shape=operation.expected_observation_shape,
            force_truncated=bool(decoded and decoded.get("truncated")),
        )
        return self._record_and_release(observation)

    async def apply_cell_transaction(
        self,
        operation: ApplyCellTransaction,
    ) -> RawCodeModeObservation:
        if self._quarantined:
            raise PreHookDenied("transaction gate is quarantined; capture fresh state first")
        if not self._mutation_gate_open:
            raise PreHookDenied("capture fresh state before another live-cell transaction")
        self._pre_hook(operation, defer_transaction_state=True)
        await self._validate_current_session(
            timeout_milliseconds=operation.limits.timeout_milliseconds
        )
        pre_code = state_capture_code(
            StateProjection(cells=False, graph=False, variables=False, outputs=False, errors=False),
            selected_cell_ids=None,
            maximum_output_bytes=operation.limits.maximum_output_bytes,
        )
        pre_result, pre_decoded = await self._execute_capture_code(
            pre_code, timeout_milliseconds=operation.limits.timeout_milliseconds
        )
        before = parse_identity(pre_decoded.get("after")) if pre_decoded else None
        request_digest = self._pre_hook(operation, expected_state=before)
        code = cell_transaction_code(operation)
        transaction_result, transaction_decoded = await self._execute_capture_code(
            code, timeout_milliseconds=operation.limits.timeout_milliseconds
        )
        post_code = state_capture_code(
            operation.post_capture,
            selected_cell_ids=None,
            maximum_output_bytes=operation.limits.maximum_output_bytes,
        )
        post_result, post_decoded = await self._execute_capture_code(
            post_code, timeout_milliseconds=operation.limits.timeout_milliseconds
        )
        after = parse_identity(post_decoded.get("after")) if post_decoded else None
        if (
            not pre_decoded
            or not post_decoded
            or not self._engine_matches(self.run, pre_decoded)
            or not self._engine_matches(self.run, post_decoded)
        ):
            after = None
        combined_result = AdapterResult(
            transport_state=(
                transaction_result.transport_state
                if post_result.transport_state == "returned"
                else post_result.transport_state
            ),
            execution_state=transaction_result.execution_state,
            output=transaction_result.output,
            stdout=[*transaction_result.stdout, *post_result.stdout],
            stderr=[*transaction_result.stderr, *post_result.stderr],
            errors=[*transaction_result.errors, *post_result.errors],
            exception_type=transaction_result.exception_type,
            exception_text=transaction_result.exception_text,
            payload=transaction_result.payload,
        )
        observation = build_observation(
            run=self.run,
            operation=operation,
            session=self._session,
            request_digest=request_digest,
            generated_code=code,
            adapter_result=combined_result,
            decoded_value=transaction_decoded,
            before=before,
            after=after,
            sequence=self.recorder.next_sequence,
            force_truncated=bool(
                (transaction_decoded and transaction_decoded.get("truncated"))
                or (post_decoded and post_decoded.get("truncated"))
            ),
        )
        self._mutation_gate_open = False
        return self._record_and_release(observation)
