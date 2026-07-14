"""Effect comparison and structurally neutral result disposition."""
from __future__ import annotations

import json
from collections.abc import Mapping

from pydantic import ValidationError

from .generated.models import (
    ApplyCellTransaction,
    BootstrapOperation,
    BootstrapRunBinding,
    EffectObservation,
    ExecutionObservation,
    ObservationShape,
    OutputObservation,
    QuarantineDisposition,
    RawCodeModeObservation,
    ReleaseDisposition,
    ReleaseRedactedDisposition,
    RequestIdentity,
    SessionBinding,
    StructuralResult,
    TransportObservation,
    WorkbookStateIdentity,
    contains_credential_material,
    digest_json,
    digest_text,
)
from .mcp_adapter import AdapterResult


def parse_identity(value: object) -> WorkbookStateIdentity | None:
    try:
        return WorkbookStateIdentity.model_validate(value)
    except ValidationError:
        return None


def changed_cells(
    before: WorkbookStateIdentity | None,
    after: WorkbookStateIdentity | None,
) -> list[str]:
    if before is None or after is None:
        return []
    all_ids = set(before.cell_digests) | set(after.cell_digests)
    return sorted(
        cell_id
        for cell_id in all_ids
        if before.cell_digests.get(cell_id) != after.cell_digests.get(cell_id)
    )


def shape_matches(value: object, shape: ObservationShape) -> bool:
    matches = {
        "object": isinstance(value, Mapping),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }[shape.kind]
    if not matches:
        return False
    return not isinstance(value, Mapping) or all(key in value for key in shape.required_keys)


def structural_result(
    operation: ApplyCellTransaction,
    before: WorkbookStateIdentity | None,
    after: WorkbookStateIdentity | None,
) -> StructuralResult:
    if after is None:
        return "post-state-unavailable"
    if before is None:
        return "not-applied"
    declared = {target.cell_id for target in operation.target_cells}
    changed = set(changed_cells(before, after))
    if not changed:
        return "not-applied"
    if any(cell_id not in after.cell_digests for cell_id in declared):
        return "cell-identity-changed"
    if changed - declared:
        return "unexpected-cell-change"
    matching = {
        target.cell_id
        for target in operation.target_cells
        if after.cell_digests.get(target.cell_id) == target.replacement.source_digest
    }
    if matching == declared and changed == declared:
        return "applied-as-declared"
    return "partially-applied"


def build_observation(
    *,
    run: BootstrapRunBinding,
    operation: BootstrapOperation,
    session: SessionBinding,
    request_digest: str,
    generated_code: str,
    adapter_result: AdapterResult,
    decoded_value: object,
    before: WorkbookStateIdentity | None,
    after: WorkbookStateIdentity | None,
    sequence: int,
    expected_shape: ObservationShape | None = None,
    force_truncated: bool = False,
) -> RawCodeModeObservation:
    stdout_text = "\n".join(adapter_result.stdout)
    stderr_text = "\n".join(adapter_result.stderr)
    output_text = json.dumps(decoded_value, sort_keys=True, ensure_ascii=False, default=repr)
    limits = operation.limits
    truncated = force_truncated or any(
        (
            len(output_text.encode()) > limits.maximum_output_bytes,
            len(stdout_text.encode()) > limits.maximum_stdout_bytes,
            len(stderr_text.encode()) > limits.maximum_stderr_bytes,
        )
    )
    redacted = contains_credential_material(
        {"value": decoded_value, "stdout": stdout_text, "stderr": stderr_text}
    )
    changed = changed_cells(before, after)
    if operation.kind == "apply-cell-transaction":
        declared_effect = "live-cells"
        declared_cells = {target.cell_id for target in operation.target_cells}
    elif operation.kind == "run-focused-probe":
        declared_effect = "scratchpad"
        declared_cells = set()
    else:
        declared_effect = "read-only"
        declared_cells = set()
    observed_effect = (
        "live-cells" if changed else "none" if declared_effect == "live-cells" else declared_effect
    )
    unexpected = sorted(set(changed) - declared_cells)
    exception_text = adapter_result.exception_text
    return RawCodeModeObservation(
        run_id=run.run_id,
        attempt_id=run.attempt_id,
        operation_id=operation.operation_id,
        session=session,
        request=RequestIdentity(
            operation_kind=operation.kind,
            request_digest=request_digest,
            generated_code_digest=digest_text(generated_code),
        ),
        transport=TransportObservation(state=adapter_result.transport_state),
        execution=ExecutionObservation(
            state=adapter_result.execution_state,
            exception_type=adapter_result.exception_type,
            exception_digest=digest_text(exception_text) if exception_text else None,
        ),
        output=OutputObservation(
            value_digest=digest_text(output_text) if decoded_value is not None else None,
            stdout_digest=digest_text(stdout_text) if stdout_text else None,
            stderr_digest=digest_text(stderr_text) if stderr_text else None,
            truncated=truncated,
            redacted=redacted,
            shape_matched=(
                shape_matches(decoded_value, expected_shape) if expected_shape is not None else None
            ),
        ),
        before=before,
        after=after,
        effects=EffectObservation(
            declared=declared_effect,
            observed=observed_effect,
            changed_cell_ids=changed,
            unexpected_changed_cell_ids=unexpected,
        ),
        structural_result=(
            structural_result(operation, before, after)
            if isinstance(operation, ApplyCellTransaction)
            else None
        ),
        recorded_at_sequence=sequence,
    )


def disposition(observation: RawCodeModeObservation, observation_id: str):
    if observation.output.truncated:
        return QuarantineDisposition(
            observation_id=observation_id, reason="bounded output limit exceeded"
        )
    if observation.request.operation_kind != "resolve-session" and observation.after is None:
        return QuarantineDisposition(
            observation_id=observation_id, reason="required post-state is unavailable"
        )
    if observation.execution.state == "exited" and observation.output.value_digest is None:
        return QuarantineDisposition(
            observation_id=observation_id, reason="result cannot be associated with generated request"
        )
    if observation.effects.unexpected_changed_cell_ids:
        return QuarantineDisposition(
            observation_id=observation_id, reason="observed effects exceed declared cells"
        )
    if observation.effects.declared != "live-cells" and observation.effects.changed_cell_ids:
        return QuarantineDisposition(
            observation_id=observation_id, reason="read-only or scratchpad operation changed live cells"
        )
    if (
        observation.structural_result is not None
        and observation.structural_result != "applied-as-declared"
    ):
        return QuarantineDisposition(
            observation_id=observation_id,
            reason=f"transaction structural result: {observation.structural_result}",
        )
    if observation.output.redacted:
        return ReleaseRedactedDisposition(observation_id=observation_id)
    return ReleaseDisposition(observation_id=observation_id)
