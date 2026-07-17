from __future__ import annotations

import io
import json
import os
import shlex
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_ROOT = ROOT / "src/cue-workbook"
sys.path.insert(0, str(WORKBOOK_ROOT))

from supervisory_hooks.cli import main as hook_cli_main  # noqa: E402
from supervisory_hooks.ledger import DurableLedger  # noqa: E402
from supervisory_hooks.models import PostToolUseInput, PreToolUseInput  # noqa: E402
from supervisory_hooks.policy import project_evidence  # noqa: E402
from supervisory_hooks.recipe_runner import execute as execute_recipe  # noqa: E402
from supervisory_hooks.routing import (  # noqa: E402
    decode_recipe_request,
    encode_recipe_request,
    plan_pretool_route,
    restore_posttool_event,
    strict_shell_tokens,
)
from supervisory_hooks.supervisor import Supervisor  # noqa: E402


def _pre(
    tool_name: str = "Bash",
    tool_input: object | None = None,
    *,
    tool_use_id: str = "tool-1",
    turn_id: str = "turn-1",
) -> PreToolUseInput:
    return PreToolUseInput.model_validate(
        {
            "session_id": "session-1",
            "transcript_path": None,
            "cwd": str(ROOT),
            "hook_event_name": "PreToolUse",
            "model": "gpt-test",
            "turn_id": turn_id,
            "permission_mode": "default",
            "tool_name": tool_name,
            "tool_use_id": tool_use_id,
            "tool_input": tool_input if tool_input is not None else {"command": "rg hook src"},
        }
    )


def _post(pre: PreToolUseInput, response: object, *, tool_input: object | None = None) -> PostToolUseInput:
    value = pre.model_dump(mode="json")
    value["hook_event_name"] = "PostToolUse"
    value["tool_response"] = response
    if tool_input is not None:
        value["tool_input"] = tool_input
    return PostToolUseInput.model_validate(value)


def _run_wire(event: PreToolUseInput, data_dir: Path) -> dict[str, object]:
    with (
        patch.dict(os.environ, {"CUESTRAP_HOOK_DATA_DIR": str(data_dir)}),
        patch("sys.stdin", io.StringIO(event.model_dump_json())),
        patch("sys.stdout", new_callable=io.StringIO) as stdout,
    ):
        result = hook_cli_main(
            ["--repository-root", str(ROOT), "hook"],
            wire_safe=True,
        )
    if result != 0:
        raise AssertionError(f"hook returned {result}")
    return json.loads(stdout.getvalue())


class SupervisoryHookBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temporary.name)
        self.ledger = DurableLedger(self.data_dir / "ledger")
        self.supervisor = Supervisor(ROOT, self.ledger)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_general_bash_is_rewritten_to_digest_bound_just_recipe(self) -> None:
        response = _run_wire(_pre(), self.data_dir / "wire")
        specific = response["hookSpecificOutput"]
        self.assertEqual(specific["permissionDecision"], "allow")
        updated = specific["updatedInput"]
        tokens = strict_shell_tokens(updated["command"])
        self.assertIsNotNone(tokens)
        assert tokens is not None
        self.assertEqual(
            tokens[:4],
            ("just", "--justfile", str(ROOT / "justfile"), "hook-shell-read"),
        )
        request = decode_recipe_request(tokens[4])
        self.assertEqual(request.target_id, "shell.read")
        self.assertEqual(request.argv, ("rg", "hook", "src"))
        self.assertEqual(request.working_directory, ".")

    def test_workbook_bash_action_remains_direct(self) -> None:
        event = _pre(
            tool_input={
                "command": (
                    ".venv/bin/python src/cue-workbook/code_mode_client.py "
                    "capture-state"
                )
            }
        )
        route = plan_pretool_route(event, ROOT)
        self.assertEqual((route.category, route.behavior), ("workbook-centric", "direct"))
        self.assertEqual(_run_wire(event, self.data_dir / "workbook"), {})

    def test_marimo_mcp_action_remains_direct(self) -> None:
        event = _pre(
            "mcp__marimo_code_mode__execute_code",
            {"code": "1 + 1"},
        )
        route = plan_pretool_route(event, ROOT)
        self.assertEqual((route.category, route.behavior), ("workbook-centric", "direct"))
        self.assertEqual(_run_wire(event, self.data_dir / "marimo"), {})

    def test_general_mcp_action_is_redirected_to_recipe_vocabulary(self) -> None:
        event = _pre("mcp__git_mcp_server__git_status", {})
        route = plan_pretool_route(event, ROOT)
        self.assertEqual((route.category, route.behavior), ("general", "redirect"))
        self.assertEqual(route.recipe_id, "hook-git-read")
        response = _run_wire(event, self.data_dir / "git-mcp")
        specific = response["hookSpecificOutput"]
        self.assertEqual(specific["permissionDecision"], "deny")
        self.assertIn("hook-git-read", specific["permissionDecisionReason"])

    def test_apply_patch_redirect_carries_exact_canonical_recipe(self) -> None:
        patch_event = _pre(
            "apply_patch",
            {"command": "*** Begin Patch\n*** Update File: justfile\n*** End Patch"},
        )
        route = plan_pretool_route(patch_event, ROOT)
        self.assertEqual((route.category, route.behavior), ("general", "redirect"))
        self.assertEqual(route.recipe_id, "hook-apply-patch")
        self.assertIsNotNone(route.redirect_command)
        recipe_event = _pre(
            "Bash",
            {"command": route.redirect_command},
            tool_use_id="recipe-1",
        )
        recipe_route = plan_pretool_route(recipe_event, ROOT)
        self.assertEqual((recipe_route.category, recipe_route.behavior), ("general", "direct"))
        assert recipe_route.semantic_event is not None
        self.assertEqual(recipe_route.semantic_event.tool_name, "apply_patch")
        self.assertEqual(recipe_route.semantic_event.tool_input, patch_event.tool_input)

    def test_rewritten_post_restores_original_semantic_action(self) -> None:
        event = _pre()
        route = plan_pretool_route(event, ROOT)
        self.supervisor.handle_pre(event)
        effective_post = _post(event, {"exit_code": 0}, tool_input=route.updated_input)
        restored = restore_posttool_event(effective_post, ROOT)
        self.assertEqual(restored.tool_name, "Bash")
        self.assertEqual(restored.tool_input, {"command": "rg hook src"})
        self.supervisor.handle_post(restored)
        projection = project_evidence(self.ledger.read_records())
        self.assertEqual(len(projection.observations), 1)
        self.assertEqual(projection.observations[0].target_id, "shell.read")
        self.assertEqual(self.ledger.read_state().pending, {})

    def test_recipe_runner_revalidates_and_executes_without_shell(self) -> None:
        route = plan_pretool_route(_pre(), ROOT)
        request = route.request
        assert request is not None
        completed = Mock(returncode=0)
        with patch("supervisory_hooks.recipe_runner.subprocess.run", return_value=completed) as run:
            self.assertEqual(execute_recipe(request, ROOT), 0)
        run.assert_called_once_with(["rg", "hook", "src"], cwd=ROOT, check=False)

    def test_tampered_recipe_payload_fails_semantic_revalidation(self) -> None:
        route = plan_pretool_route(_pre(), ROOT)
        request = route.request
        assert request is not None
        tampered = request.model_copy(update={"request_digest": "sha256:" + "0" * 64})
        command = shlex.join(
            (
                "just",
                "--justfile",
                str(ROOT / "justfile"),
                route.recipe_id,
                encode_recipe_request(tampered),
            )
        )
        result = plan_pretool_route(_pre(tool_input={"command": command}), ROOT)
        self.assertEqual((result.category, result.behavior), ("general", "redirect"))
        self.assertIn("revalidation", result.reason)

    def test_compound_shell_remains_outside_recipe_vocabulary(self) -> None:
        event = _pre(tool_input={"command": "rg hook src | tee output.txt"})
        route = plan_pretool_route(event, ROOT)
        self.assertEqual((route.category, route.behavior), ("unclassified", "neutral"))
        response = _run_wire(event, self.data_dir / "compound")
        specific = response["hookSpecificOutput"]
        self.assertNotIn("permissionDecision", specific)
        self.assertIn("outside the closed recipe vocabulary", specific["additionalContext"])


if __name__ == "__main__":
    unittest.main()
