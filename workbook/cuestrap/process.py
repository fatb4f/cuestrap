from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from .models import EnvironmentIdentity, ProcessObservation
from .protocol import digest_bytes, digest_file


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_process(
    argv: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
    input_text: str | None = None,
    timeout: float = 30,
) -> ProcessObservation:
    started = _now()
    try:
        completed = subprocess.run(
            list(argv),
            cwd=cwd,
            env=dict(env) if env is not None else None,
            input=input_text,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=timeout,
        )
        exit_code: int | None = completed.returncode
        stdout, stderr = completed.stdout, completed.stderr
    except (OSError, subprocess.TimeoutExpired) as error:
        exit_code = None
        stdout, stderr = "", f"{type(error).__name__}: {error}"
    return ProcessObservation.model_validate(
        {
            "argv": list(argv),
            "cwd": str(cwd.resolve()),
            "startedAt": started,
            "finishedAt": _now(),
            "exitCode": exit_code,
            "stdout": stdout[:20000],
            "stderr": stderr[:20000],
            "stdoutDigest": digest_bytes(stdout.encode()),
            "stderrDigest": digest_bytes(stderr.encode()),
        }
    )


def _version(repo_root: Path, argv: Sequence[str]) -> str:
    if shutil.which(argv[0]) is None:
        return "unavailable"
    result = run_process(argv, cwd=repo_root, timeout=10)
    text = (result.stdout or result.stderr).strip().splitlines()
    return text[0] if result.exit_code == 0 and text else f"error:{result.exit_code}"


def environment_identity(repo_root: Path, *, verify_lock: bool = True) -> EnvironmentIdentity:
    repo_root = repo_root.resolve(strict=True)
    pyproject = repo_root / "pyproject.toml"
    lock = repo_root / "uv.lock"
    lock_check = None
    sync_check = None
    locked = False
    if verify_lock and shutil.which("uv") and pyproject.is_file() and lock.is_file():
        lock_check = run_process(("uv", "lock", "--check", "--project", str(repo_root)), cwd=repo_root)
        sync_check = run_process(
            ("uv", "sync", "--check", "--locked", "--exact", "--project", str(repo_root)),
            cwd=repo_root,
            env={**os.environ, "UV_PROJECT_ENVIRONMENT": os.environ.get("UV_PROJECT_ENVIRONMENT", str(repo_root / ".venv"))},
        )
        locked = lock_check.exit_code == 0 and sync_check.exit_code == 0

    versions = {
        "python": sys.version.split()[0],
        "uv": _version(repo_root, ("uv", "--version")),
        "marimo": _version(repo_root, ("marimo", "--version")),
        "cue": _version(repo_root, ("cue", "version")),
        "go": _version(repo_root, ("go", "version")),
        "gopls": _version(repo_root, ("gopls", "version")),
    }
    return EnvironmentIdentity.model_validate(
        {
            "schema": "cuestrap.environment.v0",
            "repoRoot": str(repo_root),
            "pythonExecutable": str(Path(sys.executable).resolve()),
            "pythonPrefix": str(Path(sys.prefix).resolve()),
            "uvProjectEnvironment": os.environ.get("UV_PROJECT_ENVIRONMENT"),
            "virtualEnv": os.environ.get("VIRTUAL_ENV"),
            "pyprojectDigest": digest_file(pyproject) if pyproject.is_file() else None,
            "lockDigest": digest_file(lock) if lock.is_file() else None,
            "lockCheck": lock_check.model_dump(by_alias=True) if lock_check else None,
            "syncCheck": sync_check.model_dump(by_alias=True) if sync_check else None,
            "toolVersions": versions,
            "locked": locked,
        }
    )
