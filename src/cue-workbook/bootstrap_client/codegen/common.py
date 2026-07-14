"""Shared source used only by approved generated code-mode templates."""
from __future__ import annotations

import json

from ..mcp_adapter import AdapterResult

RESULT_MARKER = "CUESTRAP_BOOTSTRAP_CLIENT_JSON:"


def support_code() -> str:
    return '''import hashlib as _hashlib
import json as _json
import marimo as _marimo
import marimo._code_mode as _cm

def _digest_text(_value):
    return "sha256:" + _hashlib.sha256(_value.encode("utf-8", "replace")).hexdigest()

def _digest_json(_value):
    return _digest_text(_json.dumps(_value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))

def _graph_value(_ctx):
    _graph = _ctx.graph
    return {
        "parents": {str(_key): sorted(str(_item) for _item in _value) for _key, _value in _graph.parents.items()},
        "children": {str(_key): sorted(str(_item) for _item in _value) for _key, _value in _graph.children.items()},
        "definitions": {str(_key): sorted(str(_item) for _item in _value) for _key, _value in _graph.definitions.items()},
    }

def _identity(_ctx):
    _cell_digests = {str(_cell.id): _digest_text(_cell.code) for _cell in _ctx.cells}
    _graph_digest = _digest_json(_graph_value(_ctx))
    return {
        "revision": _digest_json({"cellDigests": _cell_digests, "graphDigest": _graph_digest}),
        "cellDigests": _cell_digests,
        "graphDigest": _graph_digest,
    }

def _engine_identity():
    return {
        "engineIdentity": _digest_text("marimo"),
        "engineRevision": _digest_text(_marimo.__version__),
        "mode": "code-mode",
    }
'''


def decode_marked_json(result: AdapterResult) -> dict[str, object] | None:
    candidates = [*result.stdout]
    if isinstance(result.output, str):
        candidates.append(result.output)
    for candidate in reversed(candidates):
        position = candidate.rfind(RESULT_MARKER)
        if position < 0:
            continue
        encoded = candidate[position + len(RESULT_MARKER) :].strip()
        try:
            value = json.loads(encoded)
        except json.JSONDecodeError:
            return None
        return value if isinstance(value, dict) else None
    return None
