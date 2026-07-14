"""Bounded, read-only state-capture request generation."""
from __future__ import annotations

from ..generated.models import CaptureState, ExplicitCells, StateProjection
from .common import RESULT_MARKER, support_code


def state_capture_code(
    projection: StateProjection,
    *,
    selected_cell_ids: list[str] | None,
    maximum_output_bytes: int,
) -> str:
    selection = repr(selected_cell_ids)
    render_limit = max(256, min(maximum_output_bytes // 4, 20_000))
    return support_code() + f'''
_ctx = _cm.get_context()
_before = _identity(_ctx)
_selection = {selection}
_cell_map = {{str(_cell.id): _cell for _cell in _ctx.cells}}
_selected_ids = sorted(_cell_map) if _selection is None else list(_selection)
_missing = sorted(set(_selected_ids) - set(_cell_map))

def _render(_value):
    _text = repr(_value)
    return {{"type": type(_value).__name__, "repr": _text[:{render_limit}], "digest": _digest_text(_text)}}

def _output(_value):
    if _value is None:
        return None
    return {{"channel": str(_value.channel), "mimetype": str(_value.mimetype), "data": _render(_value.data)}}

_cells = []
if {projection.cells!r}:
    for _cell_id in _selected_ids:
        if _cell_id not in _cell_map:
            continue
        _cell = _cell_map[_cell_id]
        _item = {{"id": _cell_id, "source": _cell.code, "sourceDigest": _digest_text(_cell.code)}}
        if {projection.errors!r}:
            _item["errors"] = [{{"kind": _error.kind, "message": _error.msg}} for _error in _cell.errors]
        if {projection.outputs!r}:
            _item["output"] = _output(_cell.output)
            _item["consoleOutputs"] = [_output(_value) for _value in _cell.console_outputs]
        _cells.append(_item)

_state = {{"cells": _cells, "missingCellIDs": _missing}}
if {projection.graph!r}:
    _state["graph"] = _graph_value(_ctx)
if {projection.variables!r}:
    _state["variables"] = {{str(_key): _render(_value) for _key, _value in sorted(_ctx.globals.items()) if not str(_key).startswith("_")}}
_after = _identity(_ctx)
_payload = {{"engine": _engine_identity(), "before": _before, "after": _after, "state": _state, "truncated": False}}
_encoded = _json.dumps(_payload, sort_keys=True, separators=(",", ":"))
if len(_encoded.encode("utf-8")) > {maximum_output_bytes}:
    for _item in _cells:
        if "source" in _item:
            _item["source"] = _item["source"][:{render_limit}]
            _item["sourceTruncated"] = True
    _payload["truncated"] = True
    _encoded = _json.dumps(_payload, sort_keys=True, separators=(",", ":"))
print({RESULT_MARKER!r} + _encoded)'''


def capture_state_code(operation: CaptureState) -> str:
    selection = operation.cell_selection
    selected = selection.cell_ids if isinstance(selection, ExplicitCells) else None
    return state_capture_code(
        operation.projection,
        selected_cell_ids=selected,
        maximum_output_bytes=operation.maximum_output_bytes,
    )
