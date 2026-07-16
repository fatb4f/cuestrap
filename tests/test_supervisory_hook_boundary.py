from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_ROOT = ROOT / "src/cue-workbook"
sys.path.insert(0, str(WORKBOOK_ROOT))

from supervisory_hooks.cli import main as hook_cli_main  # noqa: E402
from supervisory_hooks.ledger import DurableLedger  # noqa: E402
from supervisory_hooks.models import PostToolUseInput, PreToolUseInput  # noqa: E402
from supervisory_hooks.policy import project_evidence  # noqa: E402
from supervisory_hooks.supervisor import Supervisor  # noqa: E402


def _pre(
    command: str,
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
            "tool_name": "Bash",
            "tool_use_id": tool_use_id,
            "tool_input": {"command": command},
        }
    )


def _post(pre: PreToolUseInput, response: object) -> PostToolUseInput:
    value = pre.model_dump(mode="json")
    value["hook_event_name"] = "PostToolUse"
    value["tool_response"] = response
    return PostToolUseInput.model_validate(value)


def _decision(response: dict[str, object]) -> object:
    specific = response.get("hookSpecificOutput")
    return specific.get("permissionDecision") if isinstance(specific, dict) else None


class SupervisoryHookBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.ledger = DurableLedger(Path(self.temporary.name) / "ledger")
        self.supervisor = Supervisor(ROOT, self.ledger)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_wire_safe_cli_omits_nondecision(self) -> None:
        event = _pre("rg hook src")
        with (
            patch.dict(
                os.environ,
                {"CUESTRAP_HOOK_DATA_DIR": str(Path(self.temporary.name) / "wire")},
            ),
            patch("sys.stdin", io.StringIO(event.model_dump_json())),
            patch("sys.stdout", new_callable=io.StringIO) as stdout,
        ):
            self.assertEqual(
                hook_cli_main(
                    ["--repository-root", str(ROOT), "hook"],
                    wire_safe=True,
                ),
                0,
            )
        self.assertEqual(json.loads(stdout.getvalue()), {})

    def test_wire_safe_cli_preserves_supported_deny(self) -> None:
        event = PreToolUseInput.model_validate(
            {
                **_pre("rg hook src", tool_use_id="unused").model_dump(mode="json"),
                "tool_name": "apply_patch",
                "tool_use_id": "patch-1",
                "tool_input": {
                    "command": "*** Begin Patch\n*** Update File: justfile\n*** End Patch"
                },
            }
        )
        with (
            patch.dict(
                os.environ,
                {"CUESTRAP_HOOK_DATA_DIR": str(Path(self.temporary.name) / "deny")},
            ),
            patch("sys.stdin", io.StringIO(event.model_dump_json())),
            patch("sys.stdout", new_callable=io.StringIO) as stdout,
        ):
            self.assertEqual(
                hook_cli_main(
                    ["--repository-root", str(ROOT), "hook"],
                    wire_safe=True,
                ),
                0,
            )
        response = json.loads(stdout.getvalue())
        self.assertEqual(_decision(response), "deny")

    def test_repository_hook_cli_exposes_no_transition_commands(self) -> None:
        with self.assertRaises(SystemExit):
            hook_cli_main(
                [
                    "--repository-root",
                    str(ROOT),
                    "set-scope",
                    "implement",
                ],
                wire_safe=True,
            )

    def test_ambiguous_shell_form_is_unclassified(self) -> None:
        response = self.supervisor.handle_pre(_pre("rg hook src | tee output.txt"))
        self.assertEqual(_decision(response), "approve")
        self.assertEqual(self.ledger.read_state().pending, {})
        records = self.ledger.read_records()
        self.assertEqual(records[-1]["kind"], "unclassified-observation")

    def test_successful_observation_does_not_trigger_identical_retry(self) -> None:
        first = _pre("rg hook src")
        self.supervisor.handle_pre(first)
        self.supervisor.handle_post(_post(first, {"exit_code": 0}))

        repeated = self.supervisor.handle_pre(
            _pre("rg hook src", tool_use_id="tool-2")
        )
        self.assertEqual(_decision(repeated), "approve")

    def test_failed_observation_still_triggers_provisional_identical_retry(self) -> None:
        first = _pre("rg hook src")
        self.supervisor.handle_pre(first)
        self.supervisor.handle_post(_post(first, {"exit_code": 1}))

        repeated = self.supervisor.handle_pre(
            _pre("rg hook src", tool_use_id="tool-2")
        )
        self.assertEqual(_decision(repeated), "deny")

    def test_unmatched_post_is_tactically_inert(self) -> None:
        event = _pre("rg hook src", tool_use_id="unmatched")
        response = self.supervisor.handle_post(_post(event, {"exit_code": 1}))
        self.assertIn(
            "unmatched-post-observed",
            response["hookSpecificOutput"]["additionalContext"],
        )
        records = self.ledger.read_records()
        self.assertEqual(records[-1]["kind"], "unclassified-observation")
        self.assertEqual(project_evidence(records).observations, ())
        self.assertEqual(self.ledger.read_state().pending, {})


if __name__ == "__main__":
    unittest.main()
