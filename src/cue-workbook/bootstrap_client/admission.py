"""Immutable coordinates for admitted constrained-client invocations."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

CANONICAL_ENDPOINT = "http://127.0.0.1:2718/mcp/server"
_RUN_BINDING_ROOT = Path(".codex/code-mode/run-bindings")
_SESSION_BINDING_ROOT = Path(".codex/code-mode/session-bindings")
_REQUEST_ROOT = Path(".codex/code-mode/requests")


@dataclass(frozen=True)
class CodeModeAdmissionContract:
    """One repository-anchored, closed code-mode coordinate boundary."""

    canonical_endpoint: str
    canonical_repository_root: Path
    admitted_run_binding_root: Path
    admitted_session_binding_root: Path
    admitted_request_root: Path

    @classmethod
    def for_repository(cls, repository_root: Path) -> CodeModeAdmissionContract:
        root = repository_root.resolve(strict=True)
        return cls(
            canonical_endpoint=CANONICAL_ENDPOINT,
            canonical_repository_root=root,
            admitted_run_binding_root=root / _RUN_BINDING_ROOT,
            admitted_session_binding_root=root / _SESSION_BINDING_ROOT,
            admitted_request_root=root / _REQUEST_ROOT,
        )

    @staticmethod
    def _admitted_file(path: Path, root: Path) -> bool:
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(root)
        except (OSError, ValueError):
            return False
        return resolved.is_file()

    def admits_invocation(
        self,
        *,
        endpoint: str,
        repository_root: Path,
        run_binding: Path,
        session_binding: Path | None,
        request: Path,
        operation: str,
    ) -> bool:
        try:
            proposed_root = repository_root.resolve(strict=True)
        except OSError:
            return False
        if endpoint != self.canonical_endpoint:
            return False
        if proposed_root != self.canonical_repository_root:
            return False
        if not self._admitted_file(run_binding, self.admitted_run_binding_root):
            return False
        if operation == "resolve-session":
            if session_binding is not None:
                return False
        elif session_binding is None or not self._admitted_file(
            session_binding, self.admitted_session_binding_root
        ):
            return False
        return self._admitted_file(request, self.admitted_request_root)

    def require_invocation(
        self,
        *,
        endpoint: str,
        repository_root: Path,
        run_binding: Path,
        session_binding: Path | None,
        request: Path,
        operation: str,
    ) -> None:
        if not self.admits_invocation(
            endpoint=endpoint,
            repository_root=repository_root,
            run_binding=run_binding,
            session_binding=session_binding,
            request=request,
            operation=operation,
        ):
            raise ValueError("code-mode invocation is outside the immutable admission contract")
