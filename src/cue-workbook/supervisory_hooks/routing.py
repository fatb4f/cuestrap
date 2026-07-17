"""Hook routing between target-workbook actions and a disposable controller workbook."""
from __future__ import annotations

import base64
import binascii
import json
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .controller import ControllerRequest, WORKBOOK_TARGETS, semantic_tool_input
from .execution_transport import (
    ExecutionInvocation,
    classify_execution_argv,
    is_exact_workbook_argv,
    parse_execution_input,
    render_execution_input,
    strict_shell_tokens,
)
from .models import PostToolUseInput, PreToolUseInput
from .policy import classify_tool

ActionCategory = Literal["workbook-centric", "general", "unclassified"]
RouteBehavior = Literal["direct", "rewrite", "redirect", "neutral"]

WORKBOOK_MCP_PREFIX = "mcp__marimo_code_mode__"
_CONTROLLER_CLI = "src/cue-workbook/operation_controller_cli.py"
_EXECUTION_TOOLS = frozenset({"bash", "tool_exec"})


@dataclass(frozen=True)
class RoutePlan:
    category: ActionCategory
    behavior: RouteBehavior
    target_id: str | None = None
    request: ControllerRequest | None = None
    updated_input: dict[str, object] | None = None
    redirect_command: str | None = None
    reason: str | None = None
    semantic_event: PreToolUseInput | None = None


def encode_controller_request(request: ControllerRequest) -> str:
    raw = request.model_dump_json(by_alias=True, exclude_none=True).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_controller_request(payload: str) -> ControllerRequest:
    padding = "=" * (-len(payload) % 4)
    raw = base64.urlsafe_b64decode((payload + padding).encode())
    return ControllerRequest.model_validate(json.loads(raw))


def _relative_working_directory(repository_root: Path, cwd: str) -> str | None:
    root = repository_root.resolve(strict=True)
    candidate = Path(cwd).resolve(strict=False)
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        return None
    return relative.as_posix() or "."


def _controller_tokens(repository_root: Path, request: ControllerRequest) -> tuple[str, ...]:
    root = repository_root.resolve()
    return (
        str(root / ".venv/bin/python"),
        str(root / _CONTROLLER_CLI),
        "--repository-root",
        str(root),
        "--payload",
        encode_controller_request(request),
    )


def _controller_command(repository_root: Path, request: ControllerRequest) -> str:
    return shlex.join(_controller_tokens(repository_root, request))


def _request_from_controller_tokens(
    tokens: tuple[str, ...],
    repository_root: Path,
) -> ControllerRequest | None:
    root = repository_root.resolve()
    expected_prefix = (
        str(root / ".venv/bin/python"),
        str(root / _CONTROLLER_CLI),
        "--repository-root",
        str(root),
        "--payload",
    )
    if len(tokens) != len(expected_prefix) + 1 or tokens[: len(expected_prefix)] != expected_prefix:
        return None
    try:
        return decode_controller_request(tokens[-1])
    except (ValueError, TypeError, json.JSONDecodeError, binascii.Error):
        return None


def _classification_for_request(request: ControllerRequest, repository_root: Path):
    lowered = request.proposed_tool_name.casefold()
    if lowered in _EXECUTION_TOOLS:
        assert request.argv is not None
        return classify_execution_argv(request.argv, repository_root=repository_root)
    tool_name, tool_input = semantic_tool_input(request)
    return classify_tool(tool_name, tool_input, repository_root=repository_root)


def _semantic_pre_event(
    wire_event: PreToolUseInput,
    request: ControllerRequest,
    repository_root: Path,
) -> PreToolUseInput | None:
    classification = _classification_for_request(request, repository_root)
    if not classification.recognized or classification.operation is None:
        return None
    operation = classification.operation
    if operation.target_id != request.target_id or operation.request_digest != request.request_digest:
        return None
    cwd = (repository_root / request.working_directory).resolve(strict=False)
    try:
        cwd.relative_to(repository_root.resolve())
    except ValueError:
        return None
    tool_name, tool_input = semantic_tool_input(request)
    return wire_event.model_copy(
        update={"tool_name": tool_name, "tool_input": tool_input, "cwd": str(cwd)}
    )


def restore_posttool_event(
    event: PostToolUseInput,
    repository_root: Path,
) -> PostToolUseInput:
    """Restore the proposed semantic action from a controller-workbook invocation."""
    invocation = parse_execution_input(event.tool_name, event.tool_input)
    if invocation is None:
        return event
    request = _request_from_controller_tokens(invocation.argv, repository_root)
    if request is None:
        return event
    synthetic_value = event.model_dump(mode="json", exclude={"tool_response"})
    synthetic_value["hook_event_name"] = "PreToolUse"
    synthetic = PreToolUseInput.model_validate(synthetic_value)
    restored = _semantic_pre_event(synthetic, request, repository_root)
    if restored is None:
        return event
    return event.model_copy(
        update={
            "tool_name": restored.tool_name,
            "tool_input": restored.tool_input,
            "cwd": restored.cwd,
        }
    )


def _is_workbook_action(event: PreToolUseInput, invocation: ExecutionInvocation | None) -> bool:
    lowered = event.tool_name.casefold()
    if lowered.startswith(WORKBOOK_MCP_PREFIX):
        return True
    return invocation is not None and is_exact_workbook_argv(invocation.argv)


def _build_execution_request(
    event: PreToolUseInput,
    invocation: ExecutionInvocation,
    *,
    target_id: str,
    request_digest: str,
    working_directory: str,
) -> ControllerRequest:
    values: dict[str, object] = {
        "operationID": event.tool_use_id,
        "sessionID": event.session_id,
        "turnID": event.turn_id,
        "targetID": target_id,
        "requestDigest": request_digest,
        "proposedToolName": event.tool_name,
        "workingDirectory": working_directory,
        "argv": invocation.argv,
    }
    if invocation.tool == "tool_exec":
        values["toolInput"] = event.tool_input
    return ControllerRequest.build(**values)


def plan_pretool_route(event: PreToolUseInput, repository_root: Path) -> RoutePlan:
    """Select target-workbook direct transport or disposable-controller transport."""
    lowered = event.tool_name.casefold()
    invocation: ExecutionInvocation | None = None

    if lowered in _EXECUTION_TOOLS:
        invocation = parse_execution_input(event.tool_name, event.tool_input)
        if invocation is None:
            return RoutePlan(
                category="unclassified",
                behavior="neutral",
                reason=(
                    "shell composition, expansion-dependent syntax, or an unsupported tool_exec "
                    "input shape is outside the controller vocabulary"
                ),
            )
        if _is_workbook_action(event, invocation):
            return RoutePlan(category="workbook-centric", behavior="direct")
        request = _request_from_controller_tokens(invocation.argv, repository_root)
        if request is not None:
            semantic_event = _semantic_pre_event(event, request, repository_root)
            if semantic_event is None:
                return RoutePlan(
                    category="general",
                    behavior="redirect",
                    reason="controller payload failed full request and semantic revalidation",
                )
            return RoutePlan(
                category="general",
                behavior="direct",
                target_id=request.target_id,
                request=request,
                semantic_event=semantic_event,
            )

    if _is_workbook_action(event, invocation):
        return RoutePlan(category="workbook-centric", behavior="direct")

    if invocation is not None:
        classification = classify_execution_argv(
            invocation.argv,
            repository_root=repository_root,
        )
    else:
        classification = classify_tool(
            event.tool_name,
            event.tool_input,
            repository_root=repository_root,
        )
    if not classification.recognized or classification.operation is None:
        return RoutePlan(category="unclassified", behavior="neutral")

    operation = classification.operation
    if operation.target_id in WORKBOOK_TARGETS:
        return RoutePlan(
            category="workbook-centric",
            behavior="direct",
            target_id=operation.target_id,
        )

    working_directory = _relative_working_directory(repository_root, event.cwd)
    if working_directory is None:
        return RoutePlan(
            category="general",
            behavior="redirect",
            target_id=operation.target_id,
            reason="the proposed working directory is outside the repository",
        )

    if invocation is not None:
        request = _build_execution_request(
            event,
            invocation,
            target_id=operation.target_id,
            request_digest=operation.request_digest,
            working_directory=working_directory,
        )
        controller_argv = _controller_tokens(repository_root, request)
        updated = render_execution_input(invocation, controller_argv)
        return RoutePlan(
            category="general",
            behavior="rewrite",
            target_id=operation.target_id,
            request=request,
            updated_input=updated,
            redirect_command=shlex.join(controller_argv),
            semantic_event=_semantic_pre_event(event, request, repository_root),
        )

    if event.tool_name == "apply_patch":
        request = ControllerRequest.build(
            operationID=event.tool_use_id,
            sessionID=event.session_id,
            turnID=event.turn_id,
            targetID=operation.target_id,
            requestDigest=operation.request_digest,
            proposedToolName=event.tool_name,
            workingDirectory=working_directory,
            toolInput=event.tool_input,
        )
        command = _controller_command(repository_root, request)
        return RoutePlan(
            category="general",
            behavior="redirect",
            target_id=operation.target_id,
            request=request,
            redirect_command=command,
            reason=(
                "Codex cannot change an apply_patch call into an execution tool; re-issue the "
                f"exact controller-workbook command through Bash or tool_exec: {command}"
            ),
        )

    return RoutePlan(
        category="general",
        behavior="redirect",
        target_id=operation.target_id,
        reason=(
            f"general tool action {operation.target_id!r} has no exact controller adapter; "
            "the action was not executed"
        ),
    )


def render_pretool_response(
    plan: RoutePlan,
    internal_response: dict[str, object],
) -> dict[str, object]:
    """Render only supported Codex PreToolUse wire shapes."""
    specific = internal_response.get("hookSpecificOutput")
    if isinstance(specific, dict) and specific.get("permissionDecision") == "deny":
        return internal_response

    if plan.behavior == "rewrite":
        assert plan.updated_input is not None
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "updatedInput": plan.updated_input,
                "additionalContext": (
                    f"Routed general action {plan.target_id} through a disposable "
                    "operation-controller workbook."
                ),
            }
        }

    if plan.behavior == "redirect":
        reason = plan.reason or "general action requires controller-workbook transport"
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }

    if plan.behavior == "neutral" and plan.reason:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": plan.reason,
            }
        }

    if isinstance(specific, dict) and specific.get("permissionDecision") == "approve":
        sanitized = dict(specific)
        sanitized.pop("permissionDecision", None)
        if set(sanitized) == {"hookEventName"}:
            return {}
        return {**internal_response, "hookSpecificOutput": sanitized}
    return internal_response
