from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

CLAIMANT_KEYS = frozenset(
    {
        "success",
        "passed",
        "valid",
        "complete",
        "admitted",
        "admission",
        "satisfied",
        "canonicalReady",
    }
)


class ProtocolError(RuntimeError):
    pass


def digest_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def digest_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return digest_bytes(encoded)


def digest_file(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise ProtocolError(f"not a regular file: {path}")
    return digest_bytes(path.read_bytes())


def bounded_path(root: Path, value: str | Path, *, must_exist: bool = True) -> Path:
    root = root.resolve(strict=True)
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve(strict=must_exist)
    if not (resolved == root or resolved.is_relative_to(root)):
        raise ProtocolError(f"path escapes root: {value}")
    return resolved


def bounded_files(root: Path, values: Iterable[str]) -> list[Path]:
    result = [bounded_path(root, value) for value in values]
    if not result:
        raise ProtocolError("at least one file is required")
    if any(not item.is_file() for item in result):
        raise ProtocolError("all coordinates must be files")
    return result


def reject_claimant_fields(value: Any, label: str = "payload") -> None:
    if isinstance(value, dict):
        forbidden = CLAIMANT_KEYS.intersection(value)
        if forbidden:
            raise ProtocolError(f"claimant field in {label}: {sorted(forbidden)[0]}")
        for child in value.values():
            reject_claimant_fields(child, label)
    elif isinstance(value, list):
        for child in value:
            reject_claimant_fields(child, label)


def load_closed_json(path: Path, *, schema: str, fields: set[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProtocolError(f"invalid JSON: {path}") from error
    if not isinstance(value, dict) or value.get("schema") != schema:
        raise ProtocolError(f"schema mismatch: {path}")
    if set(value) != fields:
        raise ProtocolError(f"open or incomplete payload: {path}")
    reject_claimant_fields(value, path.name)
    return value


def run_deterministic_properties(repo_root: Path) -> dict[str, Any]:
    from hypothesis import given, settings, strategies as st

    repo_root = repo_root.resolve(strict=True)
    counters = {"examples": 0}

    @settings(derandomize=True, deadline=None, max_examples=48)
    @given(st.text(min_size=1, max_size=80))
    def paths_never_escape(value: str) -> None:
        counters["examples"] += 1
        try:
            resolved = bounded_path(repo_root, value, must_exist=False)
        except (OSError, ProtocolError, ValueError):
            return
        assert resolved == repo_root or resolved.is_relative_to(repo_root)

    @settings(derandomize=True, deadline=None, max_examples=24)
    @given(st.sampled_from(sorted(CLAIMANT_KEYS)))
    def claimant_fields_are_rejected(key: str) -> None:
        counters["examples"] += 1
        try:
            reject_claimant_fields({"facts": {key: True}})
        except ProtocolError:
            return
        raise AssertionError(f"claimant field was accepted: {key}")

    paths_never_escape()
    claimant_fields_are_rejected()
    return {"status": "pass", "examples": counters["examples"]}
