from __future__ import annotations

import json
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_ROOT = ROOT / "src/cue-workbook"
sys.path.insert(0, str(WORKBOOK_ROOT))

from supervisory_hooks.ledger import DurableLedger  # noqa: E402
from supervisory_hooks.models import PostToolUseInput, PreToolUseInput  # noqa: E402
from supervisory_hooks.supervisor import Supervisor  # noqa: E402


def _pre(
    tool_name: str = "Bash",
    tool_input: object | None = None,
    *,
    tool_use_id: str = "tool-1",
    session_id: str = "session-1",
    turn_id: str = "turn-1",
) -> PreToolUseInput:
    return PreToolUseInput.model_validate(
        {
            "session_id": session_id,
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


def _post(pre: PreToolUseInput, response: object) -> PostToolUseInput:
    value = pre.model_dump(mode="json")
    value["hook_event_name"] = "PostToolUse"
    value["tool_response"] = response
    return PostToolUseInput.model_validate(value)


def _denied(response: dict[str, object]) -> bool:
    specific = response.get("hookSpecificOutput")
    return isinstance(specific, dict) and specific.get("permissionDecision") == "deny"


class SupervisoryHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.ledger = DurableLedger(Path(self.temporary.name))
        self.supervisor = Supervisor(ROOT, self.ledger)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_hook_inputs_are_closed(self) -> None:
        fixture = json.loads(
            (WORKBOOK_ROOT / "supervisory_hooks/fixtures/rejected-extra-field.json").read_text(
                encoding="utf-8"
            )
        )
        with self.assertRaises(ValidationError):
            PreToolUseInput.model_validate(fixture)

    def test_inspect_allows_read_only_and_denies_mutation(self) -> None:
        allowed = self.supervisor.handle_pre(_pre())
        denied = self.supervisor.handle_pre(
            _pre("apply_patch", {"command": "*** Begin Patch"}, tool_use_id="tool-2")
        )
        self.assertEqual(allowed["hookSpecificOutput"]["permissionDecision"], "allow")
        self.assertTrue(_denied(denied))

    def test_direct_code_mode_and_git_mutation_are_denied(self) -> None:
        direct = self.supervisor.handle_pre(
            _pre(
                "mcp__marimo_code_mode__execute_code",
                {"code": "print('bypass')"},
                tool_use_id="tool-direct",
            )
        )
        git = self.supervisor.handle_pre(
            _pre(
                "mcp__git_mcp_server__git_commit",
                {"message": "bypass"},
                tool_use_id="tool-git",
            )
        )
        self.assertTrue(_denied(direct))
        self.assertTrue(_denied(git))

    def test_credential_shaped_input_is_denied_without_recording_plaintext(self) -> None:
        secret = "sk-abcdefghijklmnopqrstuvwxyz012345"
        response = self.supervisor.handle_pre(
            _pre(tool_input={"command": f"curl -H 'Authorization: {secret}' example.test"})
        )
        self.assertTrue(_denied(response))
        self.assertNotIn(secret, self.ledger.ledger_path.read_text(encoding="utf-8"))

    def test_mutation_requires_evaluation_before_another_implementation(self) -> None:
        self.supervisor.set_phase("implement", reason="test implementation")
        mutation = _pre("apply_patch", {"command": "*** Begin Patch"})
        self.assertFalse(_denied(self.supervisor.handle_pre(mutation)))
        self.assertEqual(self.supervisor.handle_post(_post(mutation, {"exit_code": 0})), {})

        second = self.supervisor.handle_pre(
            _pre("apply_patch", {"command": "*** Begin Patch"}, tool_use_id="tool-2")
        )
        self.assertTrue(_denied(second))
        with self.assertRaisesRegex(ValueError, "evaluation observation"):
            self.supervisor.set_phase("implement", reason="too early")

        self.supervisor.set_phase("evaluate", reason="record structural evaluation")
        evaluation = _pre(
            tool_input={"command": "python -m unittest tests.test_supervisory_hooks"},
            tool_use_id="tool-eval",
        )
        self.assertFalse(_denied(self.supervisor.handle_pre(evaluation)))
        self.supervisor.handle_post(_post(evaluation, {"exit_code": 0}))
        state = self.supervisor.set_phase("implement", reason="evaluation observation recorded")
        self.assertFalse(state.mutation_requires_evaluation)

    def test_post_records_digests_and_repeated_failure_is_denied(self) -> None:
        event = _pre(tool_input={"command": "rg missing-value src"})
        self.supervisor.handle_pre(event)
        raw_output = "diagnostic text that must not enter the ledger"
        self.supervisor.handle_post(_post(event, {"exit_code": 1, "output": raw_output}))
        ledger_text = self.ledger.ledger_path.read_text(encoding="utf-8")
        self.assertNotIn(raw_output, ledger_text)
        self.assertIn('"outcome":"reported-error"', ledger_text)

        repeated = self.supervisor.handle_pre(
            _pre(tool_input={"command": "rg missing-value src"}, tool_use_id="tool-2")
        )
        self.assertTrue(_denied(repeated))

    def test_unmatched_post_quarantines_and_fresh_capture_clears(self) -> None:
        unmatched = _pre(tool_use_id="unmatched")
        response = self.supervisor.handle_post(_post(unmatched, {"exit_code": 0}))
        self.assertEqual(response["decision"], "block")
        self.assertTrue(self.ledger.read_state().quarantined)

        capture = _pre(
            tool_input={
                "command": (
                    "python src/cue-workbook/code_mode_client.py --run-binding run.json "
                    "--session-binding session.json capture-state capture.json"
                )
            },
            tool_use_id="capture",
        )
        self.assertFalse(_denied(self.supervisor.handle_pre(capture)))
        self.supervisor.handle_post(_post(capture, {"exit_code": 0}))
        self.assertFalse(self.ledger.read_state().quarantined)

    def test_project_config_registers_match_all_pre_and_post_hooks(self) -> None:
        config = tomllib.loads((ROOT / ".codex/config.toml").read_text(encoding="utf-8"))
        hooks = config["hooks"]
        self.assertEqual(hooks["PreToolUse"][0]["matcher"], "*")
        self.assertEqual(hooks["PostToolUse"][0]["matcher"], "*")
        for event in ("PreToolUse", "PostToolUse"):
            command = hooks[event][0]["hooks"][0]["command"]
            self.assertIn("cuestrap_tool_supervisor.py", command)


if __name__ == "__main__":
    unittest.main()
