"""Preimage-bound live-cell replacement request generation."""
from __future__ import annotations

from ..generated.models import ApplyCellTransaction
from .common import RESULT_MARKER, support_code


def cell_transaction_code(operation: ApplyCellTransaction) -> str:
    lines = [
        support_code(),
        "async with _cm.get_context() as _ctx:",
        "    _before = _identity(_ctx)",
        "    _cell_map = {str(_cell.id): _cell for _cell in _ctx.cells}",
    ]
    for target in operation.target_cells:
        lines.extend(
            [
                f"    _actual = _digest_text(_cell_map[{target.cell_id!r}].code)",
                f"    if _actual != {target.expected_preimage_digest!r}:",
                f"        raise RuntimeError('preimage mismatch for cell {target.cell_id}')",
            ]
        )
    for target in operation.target_cells:
        lines.append(f"    _ctx.edit_cell({target.cell_id!r}, code={target.replacement.source!r})")
    lines.extend(
        [
            "    _after = _identity(_ctx)",
            f"_payload = {{'transactionID': {operation.transaction_id!r}, 'before': _before, 'after': _after}}",
            f"print({RESULT_MARKER!r} + _json.dumps(_payload, sort_keys=True, separators=(',', ':')))",
        ]
    )
    return "\n".join(lines)
