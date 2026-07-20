"""Locked environment and raw subprocess observations."""
from __future__ import annotations

import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from models import EnvironmentReport, HarnessError, HarnessFailure, ProcessObservation, _digest_bytes, _digest_file


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _terminate(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _run_bounded(
    argv: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str] | None,
    input_bytes: bytes | None,
    timeout: float,
    maximum_output_bytes: int,
) -> tuple[str, int | None, bytes, bytes]:
    if maximum_output_bytes <= 0:
        raise ValueError("maximum_output_bytes must be positive")

    stdin_file = tempfile.TemporaryFile() if input_bytes is not None else None
    if stdin_file is not None:
        stdin_file.write(input_bytes)
        stdin_file.seek(0)

    process: subprocess.Popen[bytes] | None = None
    try:
        process = subprocess.Popen(
            list(argv),
            cwd=cwd,
            env=dict(env) if env is not None else None,
            stdin=stdin_file,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert process.stdout is not None and process.stderr is not None

        chunks: queue.Queue[tuple[str, bytes]] = queue.Queue(maxsize=4)
        stop_reading = threading.Event()

        def read_stream(name: str, stream: Any) -> None:
            while not stop_reading.is_set():
                try:
                    chunk = os.read(stream.fileno(), 8192)
                except OSError:
                    return
                if not chunk:
                    return
                while not stop_reading.is_set():
                    try:
                        chunks.put((name, chunk), timeout=0.01)
                        break
                    except queue.Full:
                        continue

        readers = [
            threading.Thread(
                target=read_stream,
                args=(name, stream),
                daemon=True,
            )
            for name, stream in (
                ("stdout", process.stdout),
                ("stderr", process.stderr),
            )
        ]
        for reader in readers:
            reader.start()

        captured = {"stdout": bytearray(), "stderr": bytearray()}
        captured_bytes = 0
        deadline = time.monotonic() + timeout
        state = "exited"

        while True:
            remaining_time = deadline - time.monotonic()
            if remaining_time <= 0 and process.poll() is None:
                state = "timeout"
                stop_reading.set()
                _terminate(process)
                break

            try:
                name, chunk = chunks.get(timeout=max(0.001, min(0.01, remaining_time)))
            except queue.Empty:
                if process.poll() is not None and not any(
                    reader.is_alive() for reader in readers
                ):
                    break
                continue

            capture_count = min(
                len(chunk),
                maximum_output_bytes + 1 - captured_bytes,
            )
            if capture_count > 0:
                captured[name].extend(chunk[:capture_count])
                captured_bytes += capture_count
            if captured_bytes > maximum_output_bytes:
                state = "output-limit-exceeded"
                stop_reading.set()
                _terminate(process)
                break

        stop_reading.set()
        process.stdout.close()
        process.stderr.close()
        for reader in readers:
            reader.join(timeout=0.5)
        if process.poll() is None:
            _terminate(process)
        return (
            state,
            process.returncode,
            bytes(captured["stdout"]),
            bytes(captured["stderr"]),
        )
    finally:
        if process is not None and process.poll() is None:
            _terminate(process)
        if stdin_file is not None:
            stdin_file.close()


def run_process(
    argv: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
    input_bytes: bytes | None = None,
    timeout: float = 60,
    maximum_output_bytes: int | None = None,
) -> ProcessObservation:
    started = _now()
    try:
        if maximum_output_bytes is None:
            completed = subprocess.run(
                list(argv),
                cwd=cwd,
                env=dict(env) if env is not None else None,
                input=input_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=timeout,
            )
            state = "exited"
            exit_code: int | None = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        else:
            state, exit_code, stdout, stderr = _run_bounded(
                argv,
                cwd=cwd,
                env=env,
                input_bytes=input_bytes,
                timeout=timeout,
                maximum_output_bytes=maximum_output_bytes,
            )
    except subprocess.TimeoutExpired as error:
        state = "timeout"
        exit_code = None
        stdout = error.stdout or b""
        stderr = error.stderr or f"{type(error).__name__}: {error}".encode()
    except OSError as error:
        state = "start-error"
        exit_code = None
        stdout = b""
        stderr = f"{type(error).__name__}: {error}".encode()
    return ProcessObservation.model_validate(
        {
            "state": state,
            "argv": list(argv),
            "cwd": str(cwd),
            "startedAt": started,
            "finishedAt": _now(),
            "exitCode": exit_code,
            "stdout": stdout.decode("utf-8", "replace"),
            "stderr": stderr.decode("utf-8", "replace"),
            "stdoutDigest": _digest_bytes(stdout),
            "stderrDigest": _digest_bytes(stderr),
        }
    )


def _tool_observation(root: Path, argv: Sequence[str]) -> dict[str, Any]:
    executable = shutil.which(argv[0])
    if executable is None:
        return {"available": False, "argv": list(argv)}
    result = run_process(argv, cwd=root, timeout=10)
    return {
        "available": result.exit_code == 0,
        "executable": str(Path(executable).resolve()),
        "executableDigest": _digest_file(Path(executable).resolve()),
        "version": (result.stdout or result.stderr).strip()[:1000],
        "observation": result.model_dump(by_alias=True),
    }


def observe_environment(root: Path) -> EnvironmentReport:
    root = root.resolve(strict=True)
    project = root / "pyproject.toml"
    lock = root / "uv.lock"
    if not project.is_file() or not lock.is_file():
        raise HarnessError(HarnessFailure.INVALID_COORDINATE, "pyproject.toml and uv.lock are required")

    checks: list[dict[str, Any]] = []
    uv = shutil.which("uv")
    if uv is None:
        checks.append({"id": "uv-available", "status": "blocked", "reason": "uv unavailable"})
        locked = exact = False
    else:
        lock_check = run_process((uv, "lock", "--check", "--project", str(root)), cwd=root)
        # uv sync is exact by default; --inexact is intentionally not used.
        sync_check = run_process(
            (uv, "sync", "--check", "--locked", "--project", str(root)),
            cwd=root,
            env=os.environ,
        )
        locked = lock_check.exit_code == 0
        exact = sync_check.exit_code == 0
        checks.extend(
            [
                {"id": "uv-lock", "status": "pass" if locked else "fail", "observation": lock_check.model_dump(by_alias=True)},
                {"id": "uv-exact-sync", "status": "pass" if exact else "fail", "observation": sync_check.model_dump(by_alias=True)},
            ]
        )

    environment = os.environ.get("UV_PROJECT_ENVIRONMENT")
    virtual = os.environ.get("VIRTUAL_ENV")
    expected = (root / ".venv").resolve()
    executable = Path(sys.executable).resolve()
    prefix = Path(sys.prefix).resolve()
    active = prefix.is_relative_to(expected) if expected.exists() else False
    checks.append(
        {
            "id": "canonical-interpreter",
            "status": "pass" if active else "fail",
            "expected": str(expected),
            "observed": str(prefix),
        }
    )

    tools = {
        "uv": _tool_observation(root, ("uv", "--version")),
        "cue": _tool_observation(root, ("cue", "version")),
        "go": _tool_observation(root, ("go", "version")),
        "gopls": _tool_observation(root, ("gopls", "version")),
        "direnv": _tool_observation(root, ("direnv", "version")),
    }
    return EnvironmentReport.model_validate(
        {
            "schema": "cuestrap.environment.v0",
            "root": str(root),
            "pythonExecutable": str(executable),
            "pythonPrefix": str(prefix),
            "virtualEnvironment": virtual,
            "uvProjectEnvironment": environment,
            "projectDigest": _digest_file(project),
            "lockDigest": _digest_file(lock),
            "locked": locked,
            "exact": exact,
            "tools": tools,
            "checks": checks,
        }
    )
