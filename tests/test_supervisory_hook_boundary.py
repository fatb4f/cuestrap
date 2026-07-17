from __future__ import annotations

import asyncio
import io
import json
import os
import shlex
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_ROOT = ROOT / "src/cue-workbook"
sys.path.insert(0, str(WORKBOOK_ROOT))

import code_mode_client  # noqa: E402
from bootstrap_client.admission import CodeModeAdmissionContract  # noqa: E402
from bootstrap_client.binding import (  # noqa: E402
    digest_file,
    local_client_identity,
    local_skill_identity,
)
from bootstrap_client.generated.models import digest_json, digest_text  # noqa: E402
from bootstrap_client.mcp_adapter import AdapterResult  # noqa: E402
from supervisory_hooks.cli import main as hook_cli_main  # noqa: E402
from supervisory_hooks.controller import execute_controller_request  # noqa: E402
from supervisory_hooks.ledger import DurableLedger  # noqa: E402
from supervisory_hooks.models import PostToolUseInput, PreToolUseInput  # noqa: E402
from supervisory_hooks.policy import project_evidence  # noqa: E402
from supervisory_hooks.routing import (  # noqa: E402
    decode_controller_request,
    encode_controller_request,
    plan_pretool_route,
    restore_posttool_event,
    strict_shell_tokens,
)
from supervisory_hooks.supervisor import Supervisor  # noqa: E402

DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
CODE_MODE_ENDPOINT = "http://127.0.0.1:2718/mcp/server"
WORKBOOK = WORKBOOK_ROOT / "cue-workbook.py"


def _pre(
    tool_name: str = "Bash",
    tool_input: object | None = None,
    *,
    tool_use_id: str = "tool-1",
    turn_id: str = "turn-1",
    cwd: Path = ROOT,
) -> PreToolUseInput:
    return PreToolUseInput.model_validate(
        {
            "session_id": "session-1",
            "transcript_path": None,
            "cwd": str(cwd),
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
        self.admission = CodeModeAdmissionContract.for_repository(ROOT)
        self.artifact_temporaries = [
            tempfile.TemporaryDirectory(dir=root)
            for root in (
                self.admission.admitted_run_binding_root,
                self.admission.admitted_session_binding_root,
                self.admission.admitted_request_root,
            )
        ]
        run_root, session_root, request_root = (
            Path(item.name) for item in self.artifact_temporaries
        )
        self.run_binding = run_root / "run.json"
        self.session_binding = session_root / "session.json"
        self.requests = {
            "resolve-session": request_root / "resolve-session.json",
            "capture-state": request_root / "capture-state.json",
        }
        self.wrong_run_binding = session_root / "run.json"
        self.wrong_session_binding = request_root / "session.json"
        self.wrong_request = run_root / "capture-state.json"
        self._write_code_mode_documents()

    def tearDown(self) -> None:
        for temporary in reversed(self.artifact_temporaries):
            temporary.cleanup()
        self.temporary.cleanup()

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        path.write_text(json.dumps(value), encoding="utf-8")

    def _write_code_mode_documents(self) -> None:
        run = {
            "runID": "run-1",
            "attemptID": "attempt-1",
            "phase": "inspect",
            "controller": {
                "sourcePath": str(WORKBOOK),
                "sourceDigest": digest_file(WORKBOOK),
            },
            "target": {
                "repositoryDigest": digest_text("fixture"),
                "workbookPath": str(WORKBOOK),
                "workbookDigest": digest_file(WORKBOOK),
            },
            "client": local_client_identity(ROOT).model_dump(
                by_alias=True, mode="json"
            ),
            "skill": local_skill_identity(ROOT).model_dump(
                by_alias=True, mode="json"
            ),
            "marimo": {
                "engineIdentity": digest_text("marimo"),
                "engineRevision": digest_text("test"),
            },
            "authority": {
                "cueSourceDigest": digest_file(
                    WORKBOOK_ROOT / "bootstrap_client/contracts.cue"
                ),
                "cueEvaluatorDigest": digest_text("fixture"),
            },
        }
        metadata = {
            "name": WORKBOOK.name,
            "path": str(WORKBOOK),
            "session_id": "session-1",
        }
        session = {
            "sessionID": "session-1",
            "workbookPath": str(WORKBOOK),
            "sessionMetadataDigest": digest_json(metadata),
            "resolvedAtSequence": 0,
        }
        resolve = {
            "kind": "resolve-session",
            "operationID": "resolve-1",
            "workbookPath": str(WORKBOOK),
        }
        capture = {"kind": "capture-state", "operationID": "capture-1"}
        for path, value in (
            (self.run_binding, run),
            (self.wrong_run_binding, run),
            (self.session_binding, session),
            (self.wrong_session_binding, session),
            (self.requests["resolve-session"], resolve),
            (self.requests["capture-state"], capture),
            (self.wrong_request, capture),
        ):
            self._write_json(path, value)

    def _code_mode_argv(self, operation: str = "capture-state") -> tuple[str, ...]:
        argv = [
            ".venv/bin/python",
            "src/cue-workbook/code_mode_client.py",
            "--endpoint",
            CODE_MODE_ENDPOINT,
            "--repository-root",
            str(ROOT),
            "--run-binding",
            str(self.run_binding.relative_to(ROOT)),
        ]
        if operation != "resolve-session":
            argv.extend(
                ["--session-binding", str(self.session_binding.relative_to(ROOT))]
            )
        argv.extend((operation, str(self.requests[operation].relative_to(ROOT))))
        return tuple(argv)

    def test_general_bash_is_rewritten_to_disposable_controller_workbook(self) -> None:
        response = _run_wire(_pre(), self.data_dir / "wire")
        specific = response["hookSpecificOutput"]
        self.assertEqual(specific["permissionDecision"], "allow")
        updated = specific["updatedInput"]
        tokens = strict_shell_tokens(updated["command"])
        self.assertIsNotNone(tokens)
        assert tokens is not None
        self.assertEqual(tokens[0], str(ROOT / ".venv/bin/python"))
        self.assertEqual(tokens[1], str(ROOT / "src/cue-workbook/operation_controller_cli.py"))
        self.assertEqual(tokens[2:5], ("--repository-root", str(ROOT), "--payload"))
        request = decode_controller_request(tokens[-1])
        self.assertEqual(request.target_id, "shell.read")
        self.assertEqual(request.argv, ("rg", "hook", "src"))
        self.assertEqual(request.operation_id, "tool-1")
        self.assertEqual(request.working_directory, ".")

    def test_tool_exec_is_rewritten_to_disposable_controller_workbook(self) -> None:
        event = _pre(
            "tool_exec",
            {"argv": ["git", "status"], "yield_time_ms": 1000},
        )
        response = _run_wire(event, self.data_dir / "tool-exec")
        specific = response["hookSpecificOutput"]
        self.assertEqual(specific["permissionDecision"], "allow")
        updated = specific["updatedInput"]
        self.assertEqual(updated["yield_time_ms"], 1000)
        controller_argv = tuple(updated["argv"])
        self.assertEqual(controller_argv[0], str(ROOT / ".venv/bin/python"))
        request = decode_controller_request(controller_argv[-1])
        self.assertEqual(request.proposed_tool_name, "tool_exec")
        self.assertEqual(request.argv, ("git", "status"))
        self.assertEqual(request.tool_input, event.tool_input)

    def test_workbook_bash_action_remains_direct(self) -> None:
        event = _pre(tool_input={"command": shlex.join(self._code_mode_argv())})
        route = plan_pretool_route(event, ROOT)
        self.assertEqual((route.category, route.behavior), ("workbook-centric", "direct"))
        self.assertEqual(_run_wire(event, self.data_dir / "workbook"), {})

    def test_workbook_tool_exec_action_remains_direct(self) -> None:
        event = _pre(
            "tool_exec",
            {"argv": list(self._code_mode_argv("resolve-session"))},
        )
        route = plan_pretool_route(event, ROOT)
        self.assertEqual((route.category, route.behavior), ("workbook-centric", "direct"))

    def test_path_selected_launchers_never_remain_direct(self) -> None:
        shadow = self.data_dir / "shadow-bin"
        shadow.mkdir()
        for executable in ("uv", "just"):
            path = shadow / executable
            path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            path.chmod(0o755)
        uv_argv = (
            "uv",
            "run",
            "--project",
            ".",
            "--locked",
            "--exact",
            "--",
            "python",
            *self._code_mode_argv()[1:],
        )
        with patch.dict(os.environ, {"PATH": f"{shadow}:{os.environ['PATH']}"}):
            for command in (shlex.join(uv_argv), "just marimo-listener"):
                with self.subTest(command=command):
                    route = plan_pretool_route(
                        _pre(tool_input={"command": command}), ROOT
                    )
                    self.assertEqual(
                        (route.category, route.behavior),
                        ("unclassified", "neutral"),
                    )

    def test_workbook_cli_accepts_only_closed_evaluation_modes(self) -> None:
        prefix = (
            ".venv/bin/python",
            "src/cue-workbook/workbook_cli.py",
        )
        admitted = (
            (*prefix, "--validate"),
            (*prefix, "--validate", "--repo-root", str(ROOT)),
            (
                *prefix,
                "--probe-request",
                "tests/fixtures/pilot-request.json",
                "--repo-root",
                str(ROOT),
            ),
        )
        for argv in admitted:
            with self.subTest(argv=argv):
                route = plan_pretool_route(
                    _pre("tool_exec", {"argv": list(argv)}), ROOT
                )
                self.assertEqual(
                    (route.category, route.behavior),
                    ("workbook-centric", "direct"),
                )

        rejected = (
            (*prefix, "--validate", "--serve-mcp", "gopls"),
            (*prefix, "--validate", "--gopy-worker"),
            (*prefix, "--validate", "--cue-py-worker"),
            (
                *prefix,
                "--validate",
                "--probe-request",
                "tests/fixtures/pilot-request.json",
            ),
            (*prefix, "--validate", "--unknown"),
            (*prefix, "--validate", "marimo-passthrough"),
            (*prefix, "--probe-request", "/tmp/request.json"),
            (*prefix, "--validate", "--repo-root", "/tmp"),
        )
        for argv in rejected:
            with self.subTest(argv=argv):
                route = plan_pretool_route(
                    _pre("tool_exec", {"argv": list(argv)}), ROOT
                )
                self.assertEqual(
                    (route.category, route.behavior),
                    ("unclassified", "neutral"),
                )

    def test_code_mode_requires_closed_canonical_coordinates(self) -> None:
        canonical = self._code_mode_argv()

        def replaced(option: str, value: str) -> tuple[str, ...]:
            argv = list(canonical)
            argv[argv.index(option) + 1] = value
            return tuple(argv)

        rejected = (
            replaced("--endpoint", "http://127.0.0.1:9999/mcp/server"),
            replaced("--repository-root", "/tmp"),
            replaced("--run-binding", "/tmp/run.json"),
            replaced("--session-binding", "/tmp/session.json"),
            (*canonical[:-1], "/tmp/request.json"),
            replaced("--run-binding", str(self.wrong_run_binding)),
            replaced("--session-binding", str(self.wrong_session_binding)),
            (*canonical[:-1], str(self.wrong_request)),
            (*canonical, "--unknown", "value"),
            (*canonical, "run-focused-probe", "tests/fixtures/code-mode/probe.json"),
            tuple(
                token
                for index, token in enumerate(canonical)
                if index
                not in {
                    canonical.index("--run-binding"),
                    canonical.index("--run-binding") + 1,
                }
            ),
            canonical[:-1],
            (
                *self._code_mode_argv("resolve-session")[:-2],
                "--session-binding",
                str(self.session_binding),
                *self._code_mode_argv("resolve-session")[-2:],
            ),
        )
        for argv in rejected:
            with self.subTest(argv=argv):
                route = plan_pretool_route(
                    _pre("tool_exec", {"argv": list(argv)}), ROOT
                )
                self.assertEqual(
                    (route.category, route.behavior),
                    ("unclassified", "neutral"),
                )

    def test_canonical_code_mode_invocation_parses_loads_and_calls_mock_adapter(self) -> None:
        argv = self._code_mode_argv("resolve-session")
        args = code_mode_client._parser().parse_args(argv[2:])
        adapter_result = AdapterResult(
            transport_state="returned",
            execution_state="exited",
            payload={
                "sessions": [
                    {
                        "name": WORKBOOK.name,
                        "path": str(WORKBOOK),
                        "session_id": "session-1",
                    }
                ]
            },
        )
        with patch.object(code_mode_client, "MCPAdapter") as adapter_type:
            adapter_type.return_value.list_sessions = AsyncMock(
                return_value=adapter_result
            )
            code, value = asyncio.run(code_mode_client._main_async(args))

        self.assertEqual(code, 0)
        self.assertEqual(value["sessionID"], "session-1")
        adapter_type.assert_called_once_with(CODE_MODE_ENDPOINT)

    def test_cli_rejects_valid_documents_from_the_wrong_admission_roots(self) -> None:
        canonical = self._code_mode_argv()

        def replaced(option: str, value: Path) -> tuple[str, ...]:
            argv = list(canonical)
            argv[argv.index(option) + 1] = str(value)
            return tuple(argv)

        rejected = (
            replaced("--run-binding", self.wrong_run_binding),
            replaced("--session-binding", self.wrong_session_binding),
            (*canonical[:-1], str(self.wrong_request)),
        )
        for argv in rejected:
            with self.subTest(argv=argv):
                args = code_mode_client._parser().parse_args(argv[2:])
                with (
                    patch.object(code_mode_client, "MCPAdapter") as adapter_type,
                    self.assertRaisesRegex(ValueError, "immutable admission contract"),
                ):
                    asyncio.run(code_mode_client._main_async(args))
                adapter_type.assert_not_called()

    def test_workbook_filename_mentions_do_not_bypass_controller(self) -> None:
        for command in (
            "rm src/cue-workbook/code_mode_client.py",
            "cp source workbook_cli.py",
        ):
            with self.subTest(command=command):
                route = plan_pretool_route(_pre(tool_input={"command": command}), ROOT)
                self.assertEqual((route.category, route.behavior), ("general", "rewrite"))
                self.assertEqual(route.target_id, "workspace.mutation")

    def test_workbook_adapter_basenames_outside_canonical_paths_are_not_direct(self) -> None:
        for command in (
            "python /tmp/code_mode_client.py capture-state",
            "python attacker/workbook_cli.py --validate",
        ):
            with self.subTest(command=command):
                route = plan_pretool_route(_pre(tool_input={"command": command}), ROOT)
                self.assertNotEqual(
                    (route.category, route.behavior),
                    ("workbook-centric", "direct"),
                )

    def test_workbook_executor_basenames_outside_admitted_chain_are_not_direct(self) -> None:
        adapter = ROOT / "src/cue-workbook/code_mode_client.py"
        for command in (
            f"/tmp/python {adapter} capture-state",
            f"/tmp/python3 {adapter} capture-state",
            f"/tmp/uv -- /tmp/python {adapter} capture-state",
            (
                f"/tmp/uv run --project . --locked --exact -- python "
                f"{adapter} capture-state"
            ),
            (
                f"uv run --project . --locked --exact -- /tmp/python "
                f"{adapter} capture-state"
            ),
        ):
            with self.subTest(command=command):
                route = plan_pretool_route(_pre(tool_input={"command": command}), ROOT)
                self.assertEqual((route.category, route.behavior), ("unclassified", "neutral"))

    def test_marimo_mcp_action_remains_direct(self) -> None:
        event = _pre(
            "mcp__marimo_code_mode__execute_code",
            {"code": "1 + 1"},
        )
        route = plan_pretool_route(event, ROOT)
        self.assertEqual((route.category, route.behavior), ("workbook-centric", "direct"))
        self.assertEqual(_run_wire(event, self.data_dir / "marimo"), {})

    def test_general_mcp_without_adapter_is_denied_explicitly(self) -> None:
        event = _pre("mcp__git_mcp_server__git_status", {})
        route = plan_pretool_route(event, ROOT)
        self.assertEqual((route.category, route.behavior), ("general", "redirect"))
        response = _run_wire(event, self.data_dir / "git-mcp")
        specific = response["hookSpecificOutput"]
        self.assertEqual(specific["permissionDecision"], "deny")
        self.assertIn("no exact controller adapter", specific["permissionDecisionReason"])

    def test_apply_patch_redirect_carries_exact_controller_command(self) -> None:
        patch_event = _pre(
            "apply_patch",
            {"command": "*** Begin Patch\n*** Update File: justfile\n*** End Patch"},
        )
        route = plan_pretool_route(patch_event, ROOT)
        self.assertEqual((route.category, route.behavior), ("general", "redirect"))
        self.assertIsNotNone(route.redirect_command)
        controller_event = _pre(
            "Bash",
            {"command": route.redirect_command},
            tool_use_id="controller-1",
        )
        controller_route = plan_pretool_route(controller_event, ROOT)
        self.assertEqual((controller_route.category, controller_route.behavior), ("general", "direct"))
        assert controller_route.semantic_event is not None
        self.assertEqual(controller_route.semantic_event.tool_name, "apply_patch")
        self.assertEqual(controller_route.semantic_event.tool_input, patch_event.tool_input)

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

    def test_rewritten_tool_exec_post_restores_canonical_action(self) -> None:
        event = _pre("tool_exec", {"argv": ["git", "status"], "yield-time_ms": 1000})
        route = plan_pretool_route(event, ROOT)
        effective_post = _post(event, {"exit_code": 0}, tool_input=route.updated_input)
        restored = restore_posttool_event(effective_post, ROOT)
        self.assertEqual(restored.tool_name, "Bash")
        self.assertEqual(restored.tool_input, {"command": "git status"})

    def test_controller_executes_once_and_replays_receipt(self) -> None:
        route = plan_pretool_route(_pre(), ROOT)
        request = route.request
        assert request is not None
        completed = Mock(returncode=0, stdout="match\n", stderr="")
        state_root = self.data_dir / "controller"
        with (
            patch("supervisory_hooks.controller.repository_state_digest", side_effect=[DIGEST_A, DIGEST_B]),
            patch("supervisory_hooks.controller.subprocess.run", return_value=completed) as run,
        ):
            first = execute_controller_request(request, ROOT, state_root)
            second = execute_controller_request(request, ROOT, state_root)
        self.assertEqual(first.status, "completed")
        self.assertEqual(second.status, "replayed")
        self.assertEqual(first.return_code, 0)
        self.assertEqual(first.stdout, "match\n")
        run.assert_called_once_with(
            ["rg", "hook", "src"],
            cwd=ROOT,
            check=False,
            stdout=-1,
            stderr=-1,
            text=True,
            timeout=120,
        )
        self.assertEqual(len(tuple(state_root.glob("*/claim.json"))), 1)
        self.assertEqual(len(tuple(state_root.glob("*/receipt.json"))), 1)

    def test_every_controller_field_is_identity_bound(self) -> None:
        route = plan_pretool_route(_pre(), ROOT)
        request = route.request
        assert request is not None
        mutations = {
            "request_digest": "sha256:" + "0" * 64,
            "working_directory": "src",
            "timeout_seconds": 121,
            "session_id": "other-session",
            "turn_id": "other-turn",
            "operation_id": "other-operation",
        }
        tokens = strict_shell_tokens(route.updated_input["command"])
        assert tokens is not None
        for field, value in mutations.items():
            with self.subTest(field=field):
                tampered = request.model_copy(update={field: value})
                command = shlex.join((*tokens[:-1], encode_controller_request(tampered)))
                result = plan_pretool_route(_pre(tool_input={"command": command}), ROOT)
                self.assertEqual((result.category, result.behavior), ("general", "redirect"))
                self.assertIn("revalidation", result.reason)

    def test_shell_expansion_is_not_reinterpreted_as_literal_argv(self) -> None:
        for command in (
            "rm *.tmp",
            "printf '%s\\n' {a,b}",
            "rg $PATTERN src",
            "ls PATH=~/bin",
        ):
            with self.subTest(command=command):
                self.assertIsNone(strict_shell_tokens(command))
                route = plan_pretool_route(_pre(tool_input={"command": command}), ROOT)
                self.assertEqual((route.category, route.behavior), ("unclassified", "neutral"))

    def test_shell_parentheses_are_not_reinterpreted_as_literal_argv(self) -> None:
        for command in (
            "rg (foo) src",
            "rm (target)",
            "printf foo(bar)",
        ):
            with self.subTest(command=command):
                self.assertIsNone(strict_shell_tokens(command))
                route = plan_pretool_route(_pre(tool_input={"command": command}), ROOT)
                self.assertEqual((route.category, route.behavior), ("unclassified", "neutral"))

        quoted = "rg '(foo)' src"
        self.assertEqual(strict_shell_tokens(quoted), ("rg", "(foo)", "src"))
        route = plan_pretool_route(_pre(tool_input={"command": quoted}), ROOT)
        self.assertEqual((route.category, route.behavior), ("general", "rewrite"))

    def test_compound_shell_remains_outside_controller_vocabulary(self) -> None:
        event = _pre(tool_input={"command": "rg hook src | tee output.txt"})
        route = plan_pretool_route(event, ROOT)
        self.assertEqual((route.category, route.behavior), ("unclassified", "neutral"))
        response = _run_wire(event, self.data_dir / "compound")
        specific = response["hookSpecificOutput"]
        self.assertNotIn("permissionDecision", specific)
        self.assertIn("outside the controller vocabulary", specific["additionalContext"])


if __name__ == "__main__":
    unittest.main()
