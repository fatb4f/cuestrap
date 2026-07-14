"""Repository, run, and exact-path session binding checks."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from .generated.models import (
    BootstrapRunBinding,
    AuthorityIdentity,
    IdentityRevision,
    SessionBinding,
    digest_json,
    digest_text,
)


class SessionMetadata(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    name: str = ""
    path: str
    session_id: str = Field(alias="session_id")


def digest_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def local_client_identity(repository_root: Path) -> IdentityRevision:
    package = repository_root / "src/cue-workbook/bootstrap_client"
    sources = sorted(
        path for path in package.rglob("*") if path.is_file() and path.suffix in {".py", ".cue"}
    )
    revision = digest_json(
        {str(path.relative_to(repository_root)): digest_file(path) for path in sources}
    )
    return IdentityRevision(identity=digest_text("cuestrap.bootstrap-code-mode-client"), revision=revision)


def local_skill_identity(repository_root: Path) -> IdentityRevision:
    skill = repository_root / ".codex/skills/cuestrap-code-mode/SKILL.md"
    return IdentityRevision(
        identity=digest_text("cuestrap-code-mode"),
        revision=digest_file(skill),
    )


def local_cue_authority(repository_root: Path, evaluator_digest: str) -> AuthorityIdentity:
    source = repository_root / "src/cue-workbook/bootstrap_client/contracts.cue"
    return AuthorityIdentity(
        cue_source_digest=digest_file(source),
        cue_evaluator_digest=evaluator_digest,
    )


def repository_path(path: str | Path, repository_root: Path, *, must_exist: bool = True) -> Path:
    root = repository_root.resolve(strict=True)
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve(strict=must_exist)
    if not resolved.is_relative_to(root):
        raise ValueError(f"path is outside repository root: {resolved}")
    return resolved


def validate_run_binding(run: BootstrapRunBinding, repository_root: Path) -> Path:
    workbook = repository_path(run.target.workbook_path, repository_root)
    controller = repository_path(run.controller.source_path, repository_root)
    if not controller.is_file():
        raise ValueError("controller sourcePath is not a file")
    if not workbook.is_file():
        raise ValueError("target workbookPath is not a file")
    if run.marimo.mode != "code-mode":
        raise ValueError("run is not bound to code-mode")
    if run.controller.source_digest != digest_file(controller):
        raise ValueError("controller source digest does not match run binding")
    if run.target.workbook_digest is not None and run.target.workbook_digest != digest_file(workbook):
        raise ValueError("target workbook digest does not match run binding")
    if run.client != local_client_identity(repository_root):
        raise ValueError("client identity or revision does not match run binding")
    if run.skill != local_skill_identity(repository_root):
        raise ValueError("skill identity or revision does not match run binding")
    contracts = repository_root / "src/cue-workbook/bootstrap_client/contracts.cue"
    if run.authority.cue_source_digest != digest_file(contracts):
        raise ValueError("CUE source digest does not match run binding")
    return workbook


def resolve_exact_session(
    sessions: object,
    workbook: Path,
    repository_root: Path,
    *,
    sequence: int,
) -> SessionBinding:
    parsed = TypeAdapter(list[SessionMetadata]).validate_python(sessions)
    expected = repository_path(workbook, repository_root)
    matches: list[SessionMetadata] = []
    for session in parsed:
        try:
            observed = repository_path(session.path, repository_root)
        except (OSError, ValueError):
            continue
        if observed == expected:
            matches.append(session)
    if len(matches) != 1:
        raise RuntimeError(
            f"exact workbook path resolved {len(matches)} sessions; expected one"
        )
    selected = matches[0]
    metadata: dict[str, Any] = selected.model_dump(by_alias=True, mode="json")
    return SessionBinding(
        session_id=selected.session_id,
        workbook_path=str(expected),
        session_metadata_digest=digest_json(metadata),
        resolved_at_sequence=sequence,
    )
