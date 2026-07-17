"""Route typed adapters directly and uncovered effects through a controller workbook."""
from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .controller import ControllerRequest, WORKBOOK_TARGETS, semantic_tool_input
from .execution_transport import (
    ExecutionInvocation,
    classify_execution_argv,
    is_exact_workbook_argv,
    parse_execution_input,
    strict_shell_tokens,
)
from .models import PostToolUseInput, PreToolUseInput
from .policy import classify_tool

ActionCategory = Literal["workbook-centric", "typed-adapter", "general", "unclassified"]
RouteBehavior = Literal["direct", "redirect", "neutral"]

WORKBOOK_MCP_PREFIXES = (
    "mcp__marimo_code_mode__",
    "mcp__workbook__",
)
TYPED_MCP_PREFIXES = (
    "mcp__git_mcp_server__",
    "mcp__cue_lsp__",
    "mcp__gopls__",
)
_CONTROLLER_CLI = "src/cue-workbook/operation_controller_cli.py"
_CODE_MODE_ENDPOINT = "http://127.0.0.1:2718/mcp/server"
_CONTROLLER_OPERATIONS = frozenset({"serve", "inspect", "execute", "diagnose", "close"})
_EXECUTION_TOOLS = frozenset({"bash", "tool_exec"})


@dataclass(frozen=True)
class RoutePlan:
    category: ActionCategory
    behavior: RouteBehavior
    target_id: str | None = None
    request: ControllerRequest | None = None
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


def _has_controller_prefix(tokens: tuple[str, ...], repository_root: Path) -> bool:
    root = repository_root.resolve()
    expected_prefix = (
        str(root / ".venv/bin/python"),
        str(root / _CONTROLLER_CLI),
        "--repository-root",
        str(root),
        "--endpoint",
        _CODE_MODE_ENDPOINT,
        "--payload",
    )
    return (
        len(tokens) >= len(expected_prefix)
        and tokens[: len(expected_prefix)] == expected_prefix
    )


def _controller_operation(
    tokens: tuple[str, ...],
    repository_root: Path,
) -> str | None:
    if not _has_controller_prefix(tokens, repository_root):
        return None
    operation = tokens[-1] if len(tokens) == 9 else None
    return operation if operation in _CONTROLLER_OPERATIONS else None


def _is_controller_invocation(tokens: tuple[str, ...], repository_root: Path) -> bool:
    return _controller_operation(tokens, repository_root) is not None


def _request_from_controller_tokens(
    tokens: tuple[str, ...],
    repository_root: Path,
) -> ControllerRequest | None:
    if not _is_controller_invocation(tokens, repository_root):
        return None
    try:
        return decode_controller_request(tokens[-2])
    except (ValueError, TypeError, json.JSONDecodeError, binascii.Error):
        return None


def _classification_for_request(request: ControllerRequest, repository_root: Path):
    lowered = request.proposed_tool_name.casefold()
    if lowered in _EXECUTION_TOOLS:
        assert request.argv is not None
        return classify_execution_argv(
            request.argv,
            repository_root=repository_root,
            working_directory=repository_root / request.working_directory,
        )
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
    if _controller_operation(invocation.argv, repository_root) != "execute":
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


def _is_workbook_action(
    event: PreToolUseInput,
    invocation: ExecutionInvocation | None,
    repository_root: Path,
) -> bool:
    lowered = event.tool_name.casefold()
    if lowered.startswith(WORKBOOK_MCP_PREFIXES):
        return True
    return invocation is not None and is_exact_workbook_argv(
        invocation.argv,
        repository_root=repository_root,
        working_directory=Path(event.cwd),
    )


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
    """Select a direct typed transport or an uncovered-effect controller."""
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
        if _is_workbook_action(event, invocation, repository_root):
            return RoutePlan(category="workbook-centric", behavior="direct")
        has_controller_prefix = _has_controller_prefix(invocation.argv, repository_root)
        controller_operation = _controller_operation(invocation.argv, repository_root)
        request = _request_from_controller_tokens(invocation.argv, repository_root)
        if has_controller_prefix and request is None:
            return RoutePlan(
                category="general",
                behavior="redirect",
                reason="controller payload failed full request and semantic revalidation",
            )
        if request is not None:
            if controller_operation != "execute":
                return RoutePlan(
                    category="workbook-centric",
                    behavior="direct",
                    target_id=request.target_id,
                    request=request,
                )
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

    if _is_workbook_action(event, invocation, repository_root):
        return RoutePlan(category="workbook-centric", behavior="direct")

    if lowered.startswith(TYPED_MCP_PREFIXES):
        classification = classify_tool(
            event.tool_name,
            event.tool_input,
            repository_root=repository_root,
        )
        if classification.recognized and classification.operation is not None:
            return RoutePlan(
                category="typed-adapter",
                behavior="direct",
                target_id=classification.operation.target_id,
            )

    if invocation is not None:
        classification = classify_execution_argv(
            invocation.argv,
            repository_root=repository_root,
            working_directory=Path(event.cwd),
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
        return RoutePlan(
            category="general",
            behavior="redirect",
            target_id=operation.target_id,
            request=request,
            reason=(
                "reissue the closed request through workbook.bind_operation, then use "
                "workbook.inspect_operation, workbook.execute_operation, "
                "workbook.collect_diagnosis, and workbook.release_binding with the returned "
                "typed binding; request="
                f"{request.model_dump_json(by_alias=True, exclude_none=True)}"
            ),
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
        return RoutePlan(
            category="general",
            behavior="redirect",
            target_id=operation.target_id,
            request=request,
            reason=(
                "reissue the closed request through workbook.bind_operation and continue with "
                "the typed workbook operation lifecycle; request="
                f"{request.model_dump_json(by_alias=True, exclude_none=True)}"
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
