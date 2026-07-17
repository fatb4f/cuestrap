"""Operation-scoped execution controller used by the disposable Marimo workbook."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .execution_transport import classify_execution_argv, parse_execution_input
from .models import Digest, NonEmpty, TargetID, digest_json, digest_text
from .policy import classify_tool, repository_state_digest

CONTROLLER_SCHEMA = "cuestrap.operation-controller-request/v0"
MAX_CAPTURE_CHARS = 131_072
WORKBOOK_TARGETS = frozenset(
    {
        "code-mode.resolve-session",
        "code-mode.capture-state",
        "code-mode.run-focused-probe",
        "code-mode.apply-cell-transaction",
        "evaluation.workbook",
    }
)


class _ControllerRequestSubject(BaseModel):
    """Canonical controller request fields covered by request identity."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    schema_version: Literal["cuestrap.operation-controller-request/v0"] = Field(
        default=CONTROLLER_SCHEMA,
        alias="schema",
    )
    operation_id: NonEmpty = Field(alias="operationID")
    session_id: NonEmpty = Field(alias="sessionID")
    turn_id: NonEmpty = Field(alias="turnID")
    target_id: TargetID = Field(alias="targetID")
    request_digest: Digest = Field(alias="requestDigest")
    proposed_tool_name: NonEmpty = Field(alias="proposedToolName")
    working_directory: str = Field(alias="workingDirectory")
    timeout_seconds: int = Field(default=120, alias="timeoutSeconds", ge=1, le=600)
    argv: tuple[NonEmpty, ...] | None = None
    tool_input: object | None = Field(default=None, alias="toolInput")

    @model_validator(mode="after")
    def validate_shape(self) -> "_ControllerRequestSubject":
        path = Path(self.working_directory)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("working directory must be repository-relative")
        lowered = self.proposed_tool_name.casefold()
        if lowered == "bash":
            if not self.argv or self.tool_input is not None:
                raise ValueError("Bash controller requests require argv only")
        elif lowered == "tool_exec":
            if not self.argv or not isinstance(self.tool_input, dict):
                raise ValueError("tool_exec controller requests require argv and toolInput")
            parsed = parse_execution_input(self.proposed_tool_name, self.tool_input)
            if parsed is None or parsed.argv != self.argv:
                raise ValueError("tool_exec argv does not match toolInput")
        elif self.proposed_tool_name == "apply_patch":
            if self.argv is not None or not isinstance(self.tool_input, dict):
                raise ValueError("apply_patch controller requests require toolInput only")
            if not isinstance(self.tool_input.get("command"), str):
                raise ValueError("apply_patch toolInput requires command")
        else:
            raise ValueError("unsupported controller tool")

        return self


class ControllerRequest(_ControllerRequestSubject):
    """Closed request executed once by a fresh controller-workbook runtime."""

    request_identity: Digest = Field(alias="requestIdentity")

    @classmethod
    def build(cls, **values: object) -> "ControllerRequest":
        subject = _ControllerRequestSubject.model_validate(
            {"schema": CONTROLLER_SCHEMA, **values}
        )
        document = subject.model_dump(
            by_alias=True,
            mode="json",
            exclude_none=True,
        )
        document["requestIdentity"] = digest_json(document)
        return cls.model_validate(document)

    @model_validator(mode="after")
    def validate_identity(self) -> "ControllerRequest":
        identity_subject = self.model_dump(
            by_alias=True,
            mode="json",
            exclude={"request_identity"},
            exclude_none=True,
        )
        if self.request_identity != digest_json(identity_subject):
            raise ValueError("controller request identity mismatch")
        return self

    @property
    def identity(self) -> Digest:
        return self.request_identity


class ControllerReceipt(BaseModel):
    """Durable terminal receipt returned by the controller workbook."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    schema_version: Literal["cuestrap.operation-controller-receipt/v0"] = Field(
        default="cuestrap.operation-controller-receipt/v0",
        alias="schema",
    )
    operation_id: NonEmpty = Field(alias="operationID")
    request_identity: Digest = Field(alias="requestIdentity")
    target_id: TargetID = Field(alias="targetID")
    status: Literal["completed", "replayed", "claimed-without-receipt"]
    outcome: Literal["returned", "reported-error", "timeout", "unavailable", "indeterminate"]
    return_code: int | None = Field(default=None, alias="returnCode")
    stdout: str = ""
    stderr: str = ""
    stdout_truncated: bool = Field(default=False, alias="stdoutTruncated")
    stderr_truncated: bool = Field(default=False, alias="stderrTruncated")
    pre_state_digest: Digest | None = Field(default=None, alias="preStateDigest")
    post_state_digest: Digest | None = Field(default=None, alias="postStateDigest")
    result_digest: Digest | None = Field(default=None, alias="resultDigest")
    started_at_nanoseconds: int | None = Field(default=None, alias="startedAtNanoseconds")
    finished_at_nanoseconds: int | None = Field(default=None, alias="finishedAtNanoseconds")
    receipt_path: str | None = Field(default=None, alias="receiptPath")


def semantic_tool_input(request: ControllerRequest) -> tuple[str, object]:
    lowered = request.proposed_tool_name.casefold()
    if lowered in {"bash", "tool_exec"}:
        assert request.argv is not None
        import shlex

        return "Bash", {"command": shlex.join(request.argv)}
    return request.proposed_tool_name, request.tool_input


def validate_controller_request(request: ControllerRequest, repository_root: Path) -> None:
    lowered = request.proposed_tool_name.casefold()
    if lowered in {"bash", "tool_exec"}:
        assert request.argv is not None
        classification = classify_execution_argv(
            request.argv,
            repository_root=repository_root,
            working_directory=repository_root / request.working_directory,
        )
    else:
        tool_name, tool_input = semantic_tool_input(request)
        classification = classify_tool(tool_name, tool_input, repository_root=repository_root)
    if not classification.recognized or classification.operation is None:
        raise ValueError("controller request no longer matches the closed operation vocabulary")
    operation = classification.operation
    if operation.target_id in WORKBOOK_TARGETS:
        raise ValueError("target-workbook actions must remain on the workbook-centric path")
    if operation.target_id != request.target_id:
        raise ValueError("controller target identity mismatch")
    if operation.request_digest != request.request_digest:
        raise ValueError("controller request digest mismatch")


def _bounded_cwd(repository_root: Path, relative: str) -> Path:
    root = repository_root.resolve(strict=True)
    candidate = (root / relative).resolve(strict=True)
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("controller working directory escaped repository") from error
    if not candidate.is_dir():
        raise ValueError("controller working directory is not a directory")
    return candidate


def _truncate(value: str) -> tuple[str, bool]:
    if len(value) <= MAX_CAPTURE_CHARS:
        return value, False
    return value[:MAX_CAPTURE_CHARS], True


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(payload)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _read_receipt(path: Path, request: ControllerRequest) -> ControllerReceipt:
    receipt = ControllerReceipt.model_validate_json(path.read_text(encoding="utf-8"))
    if receipt.request_identity != request.identity:
        raise ValueError("operation receipt belongs to a different controller request")
    return receipt.model_copy(update={"status": "replayed"})


def _claim(path: Path, request: ControllerRequest) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "schema": "cuestrap.operation-controller-claim/v0",
                "operationID": request.operation_id,
                "requestIdentity": request.identity,
                "claimedAtNanoseconds": time.time_ns(),
            },
            handle,
            sort_keys=True,
            separators=(",", ":"),
        )
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return True


def _run_argv(request: ControllerRequest, cwd: Path) -> tuple[int, str, str, str]:
    assert request.argv is not None
    if request.argv[:2] == ("command", "-v") and len(request.argv) == 3:
        resolved = shutil.which(request.argv[2])
        if resolved is None:
            return 1, "", "", "reported-error"
        return 0, f"{resolved}\n", "", "returned"
    try:
        completed = subprocess.run(
            list(request.argv),
            cwd=cwd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=request.timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout if isinstance(error.stdout, str) else ""
        stderr = error.stderr if isinstance(error.stderr, str) else ""
        return 124, stdout, stderr or "controller execution timed out\n", "timeout"
    except FileNotFoundError as error:
        return 127, "", f"{error}\n", "unavailable"
    return (
        completed.returncode,
        completed.stdout,
        completed.stderr,
        "returned" if completed.returncode == 0 else "reported-error",
    )


def _run_apply_patch(request: ControllerRequest, cwd: Path) -> tuple[int, str, str, str]:
    assert isinstance(request.tool_input, dict)
    executable = shutil.which("apply_patch")
    if executable is None:
        return 127, "", "apply_patch executable is unavailable\n", "unavailable"
    try:
        completed = subprocess.run(
            [executable],
            cwd=cwd,
            input=request.tool_input["command"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=request.timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout if isinstance(error.stdout, str) else ""
        stderr = error.stderr if isinstance(error.stderr, str) else ""
        return 124, stdout, stderr or "controller execution timed out\n", "timeout"
    return (
        completed.returncode,
        completed.stdout,
        completed.stderr,
        "returned" if completed.returncode == 0 else "reported-error",
    )


def _run_effect(request: ControllerRequest, cwd: Path) -> tuple[int, str, str, str]:
    if request.proposed_tool_name.casefold() in {"bash", "tool_exec"}:
        return _run_argv(request, cwd)
    return _run_apply_patch(request, cwd)


def execute_controller_request(
    request: ControllerRequest,
    repository_root: Path,
    state_root: Path,
) -> ControllerReceipt:
    """Validate, claim, execute once, and persist a reconstructable terminal receipt."""

    root = repository_root.resolve(strict=True)
    validate_controller_request(request, root)
    cwd = _bounded_cwd(root, request.working_directory)

    operation_key = digest_text(
        f"{request.session_id}\0{request.turn_id}\0{request.operation_id}"
    ).removeprefix("sha256:")
    operation_directory = state_root.resolve() / operation_key
    request_path = operation_directory / "request.json"
    claim_path = operation_directory / "claim.json"
    receipt_path = operation_directory / "receipt.json"

    if receipt_path.exists():
        return _read_receipt(receipt_path, request)

    request_document = request.model_dump(by_alias=True, mode="json", exclude_none=True)
    if request_path.exists():
        current = json.loads(request_path.read_text(encoding="utf-8"))
        if current != request_document:
            raise ValueError("operation ID is already bound to a different controller request")
    else:
        _atomic_json(request_path, request_document)

    if not _claim(claim_path, request):
        if receipt_path.exists():
            return _read_receipt(receipt_path, request)
        return ControllerReceipt(
            operationID=request.operation_id,
            requestIdentity=request.identity,
            targetID=request.target_id,
            status="claimed-without-receipt",
            outcome="indeterminate",
            stderr="operation was claimed without a terminal receipt; execution was not repeated",
            receiptPath=str(receipt_path),
        )

    started = time.time_ns()
    pre_state = repository_state_digest(root)
    return_code, stdout, stderr, outcome = _run_effect(request, cwd)
    post_state = repository_state_digest(root)
    finished = time.time_ns()
    stdout, stdout_truncated = _truncate(stdout)
    stderr, stderr_truncated = _truncate(stderr)
    result_digest = digest_json(
        {
            "returnCode": return_code,
            "stdout": stdout,
            "stderr": stderr,
            "outcome": outcome,
            "postStateDigest": post_state,
        }
    )
    receipt = ControllerReceipt(
        operationID=request.operation_id,
        requestIdentity=request.identity,
        targetID=request.target_id,
        status="completed",
        outcome=outcome,
        returnCode=return_code,
        stdout=stdout,
        stderr=stderr,
        stdoutTruncated=stdout_truncated,
        stderrTruncated=stderr_truncated,
        preStateDigest=pre_state,
        postStateDigest=post_state,
        resultDigest=result_digest,
        startedAtNanoseconds=started,
        finishedAtNanoseconds=finished,
        receiptPath=str(receipt_path),
    )
    _atomic_json(receipt_path, receipt.model_dump(by_alias=True, mode="json", exclude_none=True))
    return receipt
