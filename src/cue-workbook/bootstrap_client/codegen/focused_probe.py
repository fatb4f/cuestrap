"""Focused scratchpad probe request generation."""
from __future__ import annotations

from ..generated.models import RunFocusedProbe
from .common import RESULT_MARKER, support_code


def focused_probe_code(operation: RunFocusedProbe) -> str:
    template_id = operation.probe.template_id
    parameters = operation.probe.parameters
    render_limit = max(256, min(operation.limits.maximum_output_bytes // 4, 20_000))
    if template_id == "variable-repr":
        name = parameters.variable_name
        expression = f'''_value = _ctx.globals[{name!r}]
_text = repr(_value)
_observation = {{"type": type(_value).__name__, "repr": _text[:{render_limit}], "digest": _digest_text(_text)}}'''
    else:
        cell_id = parameters.cell_id
        expression = f'''_cell_map = {{str(_cell.id): _cell for _cell in _ctx.cells}}
_source = _cell_map[{cell_id!r}].code
_observation = {{"cellID": {cell_id!r}, "sourceDigest": _digest_text(_source)}}'''
    return support_code() + f'''
_ctx = _cm.get_context()
_before = _identity(_ctx)
{expression}
_after = _identity(_ctx)
_payload = {{"engine": _engine_identity(), "before": _before, "after": _after, "observation": _observation}}
print({RESULT_MARKER!r} + _json.dumps(_payload, sort_keys=True, separators=(",", ":")))'''
