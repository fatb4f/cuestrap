"""Transport routing between workbook actions and closed Just recipes."""
from __future__ import annotations

import base64
import binascii
import json
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import Digest, NonEmpty, PostToolUseInput, PreToolUseInput, TargetID
from .policy import classify_tool

ActionCategory = Literal["workbook-centric", "general", "unclassified"]
RouteBehavior = Literal["direct", "rewrite", "redirect", "neutral"]

RECIPE_SCHEMA = "cuestrap.just-recipe-request/v0"
WORKBOOK_MCP_PREFIX = "mcp__marimo_code_mode__"
WORKBOOK_TARGETS = frozenset(
    {
        "code-mode.resolve-session",
        "code-mode.capture-state",
        "code-mode.run-focused-probe",
        "code-mode.apply-cell-transaction",
        "evaluation.workbook",
    }
)
RECIPE_BY_TARGET: dict[str, str] = {
    "shell.read": "hook-shell-read",
    "git.read": "hook-git-read",
    "git.mutation": "hook-git-mutation",
    "workspace.apply-patch": "hook-apply-patch",
    "workspace.mutation": "hook-workspace-mutation",
    "evaluation.cue": "hook-evaluate-cue",
    "evaluation.python": "hook-evaluate-python",
    "evaluation.go": "hook-evaluate-go",
    "just.list": "hook-just-introspection",
    "just.summary": "hook-just-introspection",
    "just.dump": "hook-just-introspection",
    "just.check": "hook-just-introspection",
}
_SHELL_PUNCTUATION = frozenset(";&|<>")
_UNEXPANDED_SHELL_MARKERS = ("`", "$(", "${", "<(", ">(")


class RecipeRequest(BaseModel):
    """Closed request consumed by one Just recipe and revalidated before execution."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    schema_version: Literal["cuestrap.just-recipe-request/v0"] = Field(
        default=RECIPE_SCHEMA,
        alias="schema",
    )
    recipe_id: NonEmpty = Field(alias="recipeID")
    target_id: TargetID = Field(alias="targetID")
    request_digest: Digest = Field(alias="requestDigest")
    proposed_tool_name: NonEmpty = Field(alias="proposedToolName")
    working_directory: str = Field(alias="workingDirectory")
    argv: tuple[NonEmpty, ...] | None = None
    tool_input: object | None = Field(default=None, alias="toolInput")

    @model_validator(mode="after")
    def validate_shape(self) -> "RecipeRequest":
        path = Path(self.working_directory)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("working directory must be repository-relative")
        if self.proposed_tool_name.casefold() == "bash":
            if not self.argv or self.tool_input is not None:
                raise ValueError("Bash recipe requests require argv only")
        elif self.proposed_tool_name == "apply_patch":
            if self.argv is not None or not isinstance(self.tool_input, dict):
                raise ValueError("apply_patch recipe requests require toolInput only")
            if not isinstance(self.tool_input.get("command"), str):
                raise ValueError("apply_patch toolInput requires command")
        else:
            raise ValueError("unsupported recipe tool")
        return self


@dataclass(frozen=True)
class RoutePlan:
    category: ActionCategory
    behavior: RouteBehavior
    target_id: str | None = None
    recipe_id: str | None = None
    request: RecipeRequest | None = None
    updated_input: dict[str, object] | None = None
    redirect_command: str | None = None
    reason: str | None = None
    semantic_event: PreToolUseInput | None = None


def strict_shell_tokens(command: str) -> tuple[str, ...] | None:
    """Return literal argv only when no shell composition or expansion is required."""
    if not command.strip() or "\n" in command:
        return None
    if any(marker in command for marker in _UNEXPANDED_SHELL_MARKERS):
        return None
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = tuple(lexer)
    except ValueError:
        return None
    if not tokens or any(token and set(token) <= _SHELL_PUNCTUATION for token in tokens):
        return None
    if any("$" in token or token.startswith("~") for token in tokens):
        return None
    return tokens


def encode_recipe_request(request: RecipeRequest) -> str:
    raw = request.model_dump_json(by_alias=True, exclude_none=True).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_recipe_request(payload: str) -> RecipeRequest:
    padding = "=" * (-len(payload) % 4)
    raw = base64.urlsafe_b64decode((payload + padding).encode())
    value = json.loads(raw)
    return RecipeRequest.model_validate(value)


def _relative_working_directory(repository_root: Path, cwd: str) -> str | None:
    root = repository_root.resolve(strict=True)
    candidate = Path(cwd).resolve(strict=False)
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        return None
    return relative.as_posix() or "."


def _recipe_command(repository_root: Path, recipe_id: str, request: RecipeRequest) -> str:
    return shlex.join(
        (
            "just",
            "--justfile",
            str(repository_root.resolve() / "justfile"),
            recipe_id,
            encode_recipe_request(request),
        )
    )


def _request_from_recipe_tokens(
    tokens: tuple[str, ...],
    repository_root: Path,
) -> RecipeRequest | None:
    if len(tokens) != 5 or Path(tokens[0]).name != "just":
        return None
    if tokens[1] != "--justfile":
        return None
    expected_justfile = (repository_root.resolve() / "justfile").resolve()
    if Path(tokens[2]).resolve(strict=False) != expected_justfile:
        return None
    recipe_id, payload = tokens[3], tokens[4]
    if recipe_id not in frozenset(RECIPE_BY_TARGET.values()):
        return None
    try:
        request = decode_recipe_request(payload)
    except (ValueError, TypeError, json.JSONDecodeError, binascii.Error):
        return None
    if request.recipe_id != recipe_id or RECIPE_BY_TARGET.get(request.target_id) != recipe_id:
        return None
    return request


def _semantic_pre_event(
    wire_event: PreToolUseInput,
    request: RecipeRequest,
    repository_root: Path,
) -> PreToolUseInput | None:
    if request.proposed_tool_name.casefold() == "bash":
        assert request.argv is not None
        tool_name = "Bash"
        tool_input: object = {"command": shlex.join(request.argv)}
    else:
        tool_name = request.proposed_tool_name
        tool_input = request.tool_input
    classification = classify_tool(tool_name, tool_input, repository_root=repository_root)
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
    return wire_event.model_copy(
        update={"tool_name": tool_name, "tool_input": tool_input, "cwd": str(cwd)}
    )


def restore_posttool_event(
    event: PostToolUseInput,
    repository_root: Path,
) -> PostToolUseInput:
    """Restore the proposed semantic action from a canonical Just invocation."""
    if event.tool_name.casefold() != "bash" or not isinstance(event.tool_input, dict):
        return event
    command = event.tool_input.get("command", event.tool_input.get("cmd"))
    if not isinstance(command, str):
        return event
    tokens = strict_shell_tokens(command)
    if tokens is None:
        return event
    request = _request_from_recipe_tokens(tokens, repository_root)
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


def _is_workbook_just(tokens: tuple[str, ...]) -> bool:
    return Path(tokens[0]).name == "just" and "marimo-listener" in tokens[1:]


def plan_pretool_route(event: PreToolUseInput, repository_root: Path) -> RoutePlan:
    """Classify one proposed action and select direct or Just-backed transport."""
    lowered = event.tool_name.casefold()
    if lowered.startswith(WORKBOOK_MCP_PREFIX):
        return RoutePlan(category="workbook-centric", behavior="direct")

    tokens: tuple[str, ...] | None = None
    if lowered == "bash" and isinstance(event.tool_input, dict):
        command = event.tool_input.get("command", event.tool_input.get("cmd"))
        if not isinstance(command, str):
            return RoutePlan(category="unclassified", behavior="neutral")
        tokens = strict_shell_tokens(command)
        if tokens is None:
            return RoutePlan(
                category="unclassified",
                behavior="neutral",
                reason="compound or expansion-dependent Bash is outside the closed recipe vocabulary",
            )
        if _is_workbook_just(tokens):
            return RoutePlan(category="workbook-centric", behavior="direct")
        request = _request_from_recipe_tokens(tokens, repository_root)
        if request is not None:
            semantic_event = _semantic_pre_event(event, request, repository_root)
            if semantic_event is None:
                return RoutePlan(
                    category="general",
                    behavior="redirect",
                    reason="canonical recipe payload failed semantic revalidation",
                )
            return RoutePlan(
                category="general",
                behavior="direct",
                target_id=request.target_id,
                recipe_id=request.recipe_id,
                request=request,
                semantic_event=semantic_event,
            )

    classification = classify_tool(
        event.tool_name,
        event.tool_input,
        repository_root=repository_root,
    )
    if not classification.recognized:
        return RoutePlan(category="unclassified", behavior="neutral")

    operation = classification.operation
    assert operation is not None
    if operation.target_id in WORKBOOK_TARGETS:
        return RoutePlan(
            category="workbook-centric",
            behavior="direct",
            target_id=operation.target_id,
        )

    recipe_id = RECIPE_BY_TARGET.get(operation.target_id)
    if recipe_id is None:
        return RoutePlan(
            category="general",
            behavior="redirect",
            target_id=operation.target_id,
            reason=(
                f"general action {operation.target_id!r} has no qualified Just recipe; "
                "re-propose it through a supported Bash recipe vocabulary"
            ),
        )

    working_directory = _relative_working_directory(repository_root, event.cwd)
    if working_directory is None:
        return RoutePlan(
            category="general",
            behavior="redirect",
            target_id=operation.target_id,
            recipe_id=recipe_id,
            reason="the proposed working directory is outside the repository",
        )

    if lowered == "bash":
        assert tokens is not None
        request = RecipeRequest(
            recipeID=recipe_id,
            targetID=operation.target_id,
            requestDigest=operation.request_digest,
            proposedToolName=event.tool_name,
            workingDirectory=working_directory,
            argv=tokens,
        )
        command = _recipe_command(repository_root, recipe_id, request)
        updated = dict(event.tool_input) if isinstance(event.tool_input, dict) else {}
        updated["command"] = command
        updated.pop("cmd", None)
        return RoutePlan(
            category="general",
            behavior="rewrite",
            target_id=operation.target_id,
            recipe_id=recipe_id,
            request=request,
            updated_input=updated,
            redirect_command=command,
        )

    if event.tool_name == "apply_patch":
        request = RecipeRequest(
            recipeID=recipe_id,
            targetID=operation.target_id,
            requestDigest=operation.request_digest,
            proposedToolName=event.tool_name,
            workingDirectory=working_directory,
            toolInput=event.tool_input,
        )
        command = _recipe_command(repository_root, recipe_id, request)
        return RoutePlan(
            category="general",
            behavior="redirect",
            target_id=operation.target_id,
            recipe_id=recipe_id,
            request=request,
            redirect_command=command,
            reason=(
                "Codex cannot change an apply_patch call into Bash; re-issue the exact "
                f"canonical recipe through Bash: {command}"
            ),
        )

    return RoutePlan(
        category="general",
        behavior="redirect",
        target_id=operation.target_id,
        recipe_id=recipe_id,
        reason=(
            "Codex hooks cannot change an MCP tool into Bash; re-propose the equivalent "
            f"operation through the {recipe_id!r} Just recipe"
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
                    f"Routed general action {plan.target_id} through Just recipe "
                    f"{plan.recipe_id}."
                ),
            }
        }

    if plan.behavior == "redirect":
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": plan.reason or "general action requires a Just recipe",
            }
        }

    if not isinstance(specific, dict) or specific.get("permissionDecision") != "approve":
        return internal_response
    sanitized = dict(specific)
    sanitized.pop("permissionDecision", None)
    if plan.reason:
        sanitized["additionalContext"] = plan.reason
    if set(sanitized) == {"hookEventName"}:
        return {}
    return {**internal_response, "hookSpecificOutput": sanitized}
