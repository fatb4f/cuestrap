"""Phase-sensitive structural eligibility checks."""
from __future__ import annotations

from pathlib import Path

from .binding import repository_path
from .generated.models import (
    AllowDecision,
    ApplyCellTransaction,
    BootstrapOperation,
    BootstrapRunBinding,
    CaptureState,
    DenyDecision,
    ExplicitCells,
    PreOperationDecision,
    ResolveSession,
    RunFocusedProbe,
    SessionBinding,
    WorkbookStateIdentity,
    contains_credential_material,
    digest_json,
)

_PHASE_OPERATIONS = {
    "inspect": {"resolve-session", "capture-state"},
    "probe": {"resolve-session", "capture-state", "run-focused-probe"},
    "implement": {"capture-state", "apply-cell-transaction"},
    "evaluate": {"capture-state", "run-focused-probe"},
    "collect-evidence": {"capture-state"},
}


def evaluate_pre_hook(
    run: BootstrapRunBinding,
    operation: BootstrapOperation,
    *,
    repository_root: Path,
    session: SessionBinding | None,
    expected_state: WorkbookStateIdentity | None = None,
    defer_transaction_state: bool = False,
) -> PreOperationDecision:
    request = operation.model_dump(by_alias=True, mode="json")
    request_digest = digest_json(request)
    if operation.kind not in _PHASE_OPERATIONS[run.phase]:
        return DenyDecision(reason=f"operation {operation.kind} is not permitted in {run.phase}")
    try:
        workbook = repository_path(run.target.workbook_path, repository_root)
    except (OSError, ValueError) as error:
        return DenyDecision(reason=f"run target is not repository-bound: {error}")
    if contains_credential_material(request):
        return DenyDecision(reason="operation contains credential-shaped material")
    if isinstance(operation, ResolveSession):
        try:
            requested = repository_path(operation.workbook_path, repository_root)
        except (OSError, ValueError) as error:
            return DenyDecision(reason=f"session target is not repository-bound: {error}")
        if requested != workbook:
            return DenyDecision(reason="session target does not match run workbook")
        return AllowDecision(request_digest=request_digest)
    if session is None:
        return DenyDecision(reason="operation requires a current session binding")
    try:
        bound_workbook = repository_path(session.workbook_path, repository_root)
    except (OSError, ValueError) as error:
        return DenyDecision(reason=f"session workbook is not repository-bound: {error}")
    if bound_workbook != workbook:
        return DenyDecision(reason="session binding does not match run workbook")
    if isinstance(operation, RunFocusedProbe):
        try:
            subject = repository_path(operation.subject.workbook_path, repository_root)
        except (OSError, ValueError) as error:
            return DenyDecision(reason=f"probe subject is not repository-bound: {error}")
        if subject != workbook:
            return DenyDecision(reason="probe subject does not match run workbook")
        if len(operation.subject.cell_ids) + len(operation.subject.variable_names) != 1:
            return DenyDecision(reason="focused probe must bind exactly one declared subject")
    if isinstance(operation, CaptureState):
        if operation.maximum_output_bytes > operation.limits.maximum_output_bytes:
            return DenyDecision(reason="capture output bound exceeds operation output limit")
        selection = operation.cell_selection
        if isinstance(selection, ExplicitCells) and expected_state is not None:
            missing = sorted(set(selection.cell_ids) - set(expected_state.cell_digests))
            if missing:
                return DenyDecision(reason=f"capture references unknown cell IDs: {missing}")
    if isinstance(operation, ApplyCellTransaction):
        if defer_transaction_state:
            return AllowDecision(request_digest=request_digest)
        if expected_state is None:
            return DenyDecision(reason="transaction requires a fresh pre-state")
        if operation.expected_workbook_revision != expected_state.revision:
            return DenyDecision(reason="stale workbook revision")
        for target in operation.target_cells:
            if len(target.replacement.source.encode()) > operation.limits.maximum_output_bytes:
                return DenyDecision(reason=f"replacement source exceeds bound: {target.cell_id}")
            actual = expected_state.cell_digests.get(target.cell_id)
            if actual is None:
                return DenyDecision(reason=f"target cell does not exist: {target.cell_id}")
            if actual != target.expected_preimage_digest:
                return DenyDecision(reason=f"stale preimage for cell {target.cell_id}")
    return AllowDecision(request_digest=request_digest)
