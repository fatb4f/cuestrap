from __future__ import annotations

import json
import io
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from typing import get_args
from unittest.mock import patch

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_ROOT = ROOT / "src/cue-workbook"
FIXTURES = WORKBOOK_ROOT / "supervisory_hooks/fixtures"
sys.path.insert(0, str(WORKBOOK_ROOT))

from supervisory_hooks.ledger import DurableLedger, migrate_state_document  # noqa: E402
from supervisory_hooks.cli import main as hook_cli_main  # noqa: E402
from supervisory_hooks.models import (  # noqa: E402
    Activity,
    ArtifactRole,
    Budgets,
    CanonicalOperation,
    CompletedOperation,
    DecisionReason,
    LedgerProjection,
    ObservationSummary,
    PostToolUseInput,
    PreToolUseInput,
    Scope,
    SupervisorState,
    SupervisorStateV1,
    Surface,
    TargetID,
    ObservedResult,
    digest_json,
)
from supervisory_hooks.policy import (  # noqa: E402
    DENIAL_PRECEDENCE,
    classify_tool,
    decide,
    normalize_result,
    project_evidence,
    reduce_observation,
)
from supervisory_hooks.supervisor import Supervisor  # noqa: E402

DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64


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


def _decision(response: dict[str, object]) -> object:
    specific = response.get("hookSpecificOutput")
    return specific.get("permissionDecision") if isinstance(specific, dict) else None


def _scope(
    activity: str = "inspect",
    *,
    targets: tuple[str, ...] = ("shell.read",),
    owned_paths: tuple[str, ...] = (),
) -> Scope:
    return Scope(
        activity=activity,
        surface="workbook" if owned_paths else "none",
        owned_paths=owned_paths,
        allowed_targets=targets,
    )


def _operation(
    *,
    target: str = "shell.read",
    request: str = DIGEST_A,
    candidate: str = DIGEST_B,
    mutating: bool = False,
    roles: tuple[str, ...] = (),
    paths: tuple[str, ...] = (),
    channel: str = "static-source",
    fanout: int = 1,
) -> CanonicalOperation:
    return CanonicalOperation(
        target_id=target,
        operation_class="mutation" if mutating else "read",
        request_digest=request,
        mutating=mutating,
        target_paths=paths,
        artifact_roles=roles,
        observation_channel=channel,
        fanout=fanout,
        candidate_digest=candidate,
    )


def _observation(
    *,
    target: str = "shell.read",
    request: str = DIGEST_A,
    state: str = DIGEST_B,
    candidate: str = DIGEST_B,
    result: str = DIGEST_C,
    failure: str | None = None,
) -> ObservationSummary:
    return ObservationSummary(
        target_id=target,
        activity="inspect",
        request_digest=request,
        relevant_state_digest=state,
        result_digest=result,
        candidate_digest=candidate,
        failure_signature=failure,
        outcome="reported-error" if failure else "returned",
    )


class SupervisoryHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.ledger = DurableLedger(Path(self.temporary.name))
        self.supervisor = Supervisor(ROOT, self.ledger)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_hook_inputs_are_closed(self) -> None:
        fixture = json.loads((FIXTURES / "rejected-extra-field.json").read_text(encoding="utf-8"))
        with self.assertRaises(ValidationError):
            PreToolUseInput.model_validate(fixture)

    def test_protocol_emits_exact_legacy_binary_actions(self) -> None:
        approved = self.supervisor.handle_pre(_pre())
        denied = self.supervisor.handle_pre(
            _pre(
                "apply_patch",
                "*** Begin Patch\n*** Update File: justfile\n*** End Patch",
                tool_use_id="tool-2",
            )
        )
        self.assertEqual(
            approved["hookSpecificOutput"],
            {"hookEventName": "PreToolUse", "permissionDecision": "approve"},
        )
        self.assertEqual(_decision(denied), "deny")

    def test_successful_post_hook_response_is_protocol_neutral(self) -> None:
        event = _pre()
        self.supervisor.handle_pre(event)
        self.assertEqual(self.supervisor.handle_post(_post(event, {"exit_code": 0})), {})

    def test_cli_adapter_emits_protocol_shaped_pre_and_post_json(self) -> None:
        data_dir = str(Path(self.temporary.name) / "cli-ledger")
        event = _pre()
        with (
            patch.dict("os.environ", {"CUESTRAP_HOOK_DATA_DIR": data_dir}),
            patch("sys.stdin", io.StringIO(event.model_dump_json())),
            patch("sys.stdout", new_callable=io.StringIO) as stdout,
        ):
            self.assertEqual(
                hook_cli_main(["--repository-root", str(ROOT), "hook"]),
                0,
            )
        self.assertEqual(_decision(json.loads(stdout.getvalue())), "approve")

        post = _post(event, {"exit_code": 0})
        with (
            patch.dict("os.environ", {"CUESTRAP_HOOK_DATA_DIR": data_dir}),
            patch("sys.stdin", io.StringIO(post.model_dump_json())),
            patch("sys.stdout", new_callable=io.StringIO) as stdout,
        ):
            self.assertEqual(
                hook_cli_main(["--repository-root", str(ROOT), "hook"]),
                0,
            )
        self.assertEqual(json.loads(stdout.getvalue()), {})

    def test_shared_vocabulary_fixture_matches_python_contract(self) -> None:
        fixture = json.loads((FIXTURES / "vocabulary-v2.json").read_text(encoding="utf-8"))
        self.assertEqual(set(fixture["activities"]), set(get_args(Activity)))
        self.assertEqual(set(fixture["surfaces"]), set(get_args(Surface)))
        self.assertEqual(set(fixture["artifactRoles"]), set(get_args(ArtifactRole)))
        self.assertEqual(set(fixture["targetIDs"]), set(get_args(TargetID)))
        self.assertEqual(set(fixture["decisionReasons"]), set(get_args(DecisionReason)))
        self.assertEqual(tuple(fixture["denialPrecedence"]), DENIAL_PRECEDENCE)

    def test_shared_state_fixtures_match_python_contract(self) -> None:
        SupervisorStateV1.model_validate_json((FIXTURES / "state-v1.json").read_text())
        SupervisorState.model_validate_json((FIXTURES / "state-v2.json").read_text())
        minimal = SupervisorState.model_validate_json(
            (FIXTURES / "state-v2-minimal.json").read_text()
        )
        self.assertEqual(minimal.scope.activity, "inspect")
        self.assertEqual(minimal.budgets.maximum_observation_fanout, 64)

    def test_v1_migration_is_idempotent_and_discards_quarantine_semantics(self) -> None:
        raw = json.loads((FIXTURES / "state-v1.json").read_text(encoding="utf-8"))
        migrated = migrate_state_document(raw)
        twice = migrate_state_document(migrated.model_dump(by_alias=True, mode="json"))
        self.assertEqual(migrated, twice)
        self.assertEqual(migrated.scope.activity, "implement")
        self.assertEqual(migrated.scope.surface, "none")
        self.assertEqual(migrated.legacy_state_digest, digest_json(raw))
        serialized = migrated.model_dump(by_alias=True, mode="json")
        self.assertNotIn("quarantined", serialized)
        self.assertNotIn("quarantineReason", serialized)

    def test_invalid_v1_fails_migration_explicitly(self) -> None:
        raw = json.loads((FIXTURES / "state-v1-invalid.json").read_text(encoding="utf-8"))
        with self.assertRaises((ValidationError, ValueError)):
            migrate_state_document(raw)

    def test_migration_preserves_existing_evidence_order_and_identity(self) -> None:
        raw = (FIXTURES / "state-v1.json").read_text(encoding="utf-8")
        self.ledger.state_path.write_text(raw, encoding="utf-8")
        historical = [
            {"schemaVersion": "supervisory-tool-event/v1", "sequence": 3, "kind": "old-a"},
            {"schemaVersion": "supervisory-tool-event/v1", "sequence": 4, "kind": "old-b"},
        ]
        self.ledger.ledger_path.write_text(
            "".join(json.dumps(item) + "\n" for item in historical), encoding="utf-8"
        )
        self.ledger.read_state()
        self.assertEqual(self.ledger.read_records(), historical)
        self.assertEqual(
            json.loads(self.ledger.state_path.read_text())["schemaVersion"],
            "supervisory-state/v2",
        )

    def test_unknown_operation_is_approved_without_control_effects(self) -> None:
        before = self.ledger.read_state()
        response = self.supervisor.handle_pre(
            _pre(tool_input={"command": "opaque-tool --unknown"})
        )
        after = self.ledger.read_state()
        self.assertEqual(_decision(response), "approve")
        self.assertEqual(before, after)
        records = self.ledger.read_records()
        self.assertEqual(records[-1]["kind"], "unclassified-observation")
        self.assertNotIn("failureSignature", records[-1])

    def test_just_introspection_has_narrow_canonical_targets(self) -> None:
        for flag, target in (
            ("--list", "just.list"),
            ("--summary", "just.summary"),
            ("--dump", "just.dump"),
        ):
            classification = classify_tool("Bash", {"command": f"just {flag}"})
            self.assertTrue(classification.recognized)
            self.assertEqual(classification.operation.target_id, target)
        self.assertFalse(
            classify_tool("Bash", {"command": "just marimo-listener"}).recognized
        )
        check = classify_tool("Bash", {"command": "just --fmt --check"})
        self.assertTrue(check.recognized)
        self.assertEqual(check.operation.target_id, "just.check")

    def test_declared_scope_transition_is_approved_from_any_activity(self) -> None:
        classification = classify_tool(
            "Bash",
            {
                "command": (
                    ".venv/bin/python .codex/hooks/cuestrap_tool_supervisor.py "
                    "--repository-root . set-scope implement --surface workbook "
                    "--reason bounded"
                )
            },
        )
        self.assertTrue(classification.recognized)
        decision = decide(
            _scope(activity="inspect", targets=("shell.read",)),
            classification.operation.model_copy(update={"candidate_digest": DIGEST_A}),
            LedgerProjection(),
            Budgets(),
        )
        self.assertEqual(decision.action, "approve")

    def test_equivalent_shell_requests_have_stable_digest(self) -> None:
        first = classify_tool("Bash", {"command": "rg -n value src"}).operation
        second = classify_tool("Bash", {"command": "rg   -n   value   src"}).operation
        changed = classify_tool("Bash", {"command": "rg -n other src"}).operation
        self.assertEqual(first.request_digest, second.request_digest)
        self.assertNotEqual(first.request_digest, changed.request_digest)

    def test_normalized_result_digest_ignores_text_only_changes(self) -> None:
        first = normalize_result({"exit_code": 1, "output": "first diagnostic"})
        second = normalize_result({"exit_code": 1, "output": "different diagnostic"})
        changed = normalize_result({"exit_code": 0, "output": "different diagnostic"})
        self.assertEqual(first.result_digest, second.result_digest)
        self.assertNotEqual(first.result_digest, changed.result_digest)

    def test_reducer_projects_explicit_question_changes(self) -> None:
        observed = normalize_result(
            {
                "exit_code": 0,
                "resolvedQuestionIDs": ["question-1", "question-1"],
                "introducedQuestionIDs": ["question-2"],
                "requiredObservationChannel": "runtime",
            }
        )
        completed = CompletedOperation(
            scope=_scope(),
            operation=_operation(),
            relevant_state_digest=DIGEST_B,
            tool_name="Bash",
        )
        reduced = reduce_observation(LedgerProjection(), completed, observed)
        self.assertEqual(reduced.progress.resolved_question_ids, ("question-1",))
        self.assertEqual(reduced.progress.introduced_question_ids, ("question-2",))
        self.assertEqual(reduced.observation.required_observation_channel, "runtime")

    def test_ledger_replay_reconstructs_questions_and_required_channel(self) -> None:
        event = _pre()
        self.supervisor.handle_pre(event)
        self.supervisor.handle_post(
            _post(
                event,
                {
                    "exit_code": 1,
                    "introducedQuestionIDs": ["question-runtime"],
                    "requiredObservationChannel": "runtime",
                },
            )
        )
        projection = project_evidence(self.ledger.read_records())
        self.assertEqual(projection.unresolved_question_ids, ("question-runtime",))
        self.assertEqual(projection.required_observation_channel, "runtime")
        decision = decide(
            _scope(),
            _operation(request=DIGEST_C, channel="static-source"),
            projection,
            Budgets(),
        )
        self.assertEqual(decision.reason, "wrong-observation-channel")

    def test_identical_retry_is_denied_but_changed_retry_is_approved(self) -> None:
        scope = _scope()
        operation = _operation()
        projection = LedgerProjection(observations=(_observation(),))
        denied = decide(scope, operation, projection, Budgets())
        changed = decide(
            scope,
            operation.model_copy(update={"request_digest": DIGEST_C}),
            projection,
            Budgets(),
        )
        self.assertEqual((denied.action, denied.reason), ("deny", "identical-retry"))
        self.assertEqual(changed.action, "approve")

    def test_denial_reason_precedence_is_stable_and_preserves_all_matches(self) -> None:
        operation = _operation(
            target="workspace.apply-patch",
            mutating=True,
            roles=("protected",),
            paths=(".venv/state",),
            fanout=100,
            channel="static-source",
        )
        projection = LedgerProjection(
            observations=(
                _observation(
                    target="workspace.apply-patch",
                    failure=DIGEST_A,
                ),
            ),
            active_candidate_digest=DIGEST_C,
            active_failure_signature=DIGEST_A,
            required_observation_channel="runtime",
        )
        decision = decide(
            _scope(activity="evaluate", targets=("shell.read",)),
            operation,
            projection,
            Budgets(maximum_failure_cluster_corrections=1, maximum_observation_fanout=1),
        )
        self.assertEqual(decision.reason, "protected-artifact-mutation")
        self.assertEqual(
            decision.matched_predicates,
            tuple(reason for reason in DENIAL_PRECEDENCE if reason in decision.matched_predicates),
        )
        self.assertGreater(len(decision.matched_predicates), 1)

    def test_fanout_wrong_channel_and_phase_invalid_are_closed_predicates(self) -> None:
        fanout = decide(
            _scope(),
            _operation(fanout=65),
            LedgerProjection(),
            Budgets(maximum_observation_fanout=64),
        )
        wrong_channel = decide(
            _scope(),
            _operation(),
            LedgerProjection(required_observation_channel="runtime"),
            Budgets(),
        )
        phase = decide(
            _scope(targets=("git.read",)),
            _operation(),
            LedgerProjection(),
            Budgets(),
        )
        self.assertEqual(fanout.reason, "fanout-budget-exceeded")
        self.assertEqual(wrong_channel.reason, "wrong-observation-channel")
        self.assertEqual(phase.reason, "phase-invalid-churn")

    def test_failure_cluster_exhaustion_uses_bounded_distinct_corrections(self) -> None:
        failure = DIGEST_C
        projection = LedgerProjection(
            observations=(
                _observation(request=DIGEST_A, state=DIGEST_A, candidate=DIGEST_A, failure=failure),
                _observation(request=DIGEST_B, state=DIGEST_B, candidate=DIGEST_B, failure=failure),
            ),
            active_failure_signature=failure,
        )
        operation = _operation(request=DIGEST_C, candidate="sha256:" + "d" * 64)
        decision = decide(
            _scope(),
            operation,
            projection,
            Budgets(maximum_failure_cluster_corrections=2),
        )
        self.assertEqual(decision.reason, "failure-cluster-exhausted")

    def test_reducer_keeps_pre_state_separate_from_post_candidate(self) -> None:
        completed = CompletedOperation(
            scope=_scope(
                activity="implement",
                targets=("workspace.apply-patch",),
                owned_paths=("justfile",),
            ),
            operation=_operation(
                target="workspace.apply-patch",
                candidate=DIGEST_C,
                mutating=True,
                roles=("owned",),
                paths=("justfile",),
            ),
            relevant_state_digest=DIGEST_B,
            tool_name="apply_patch",
        )
        reduced = reduce_observation(
            LedgerProjection(),
            completed,
            ObservedResult(
                outcome="returned",
                result_class="exit-code:0",
                result_digest=DIGEST_A,
            ),
        )
        self.assertEqual(reduced.observation.relevant_state_digest, DIGEST_B)
        self.assertEqual(reduced.observation.candidate_digest, DIGEST_C)

    def test_successful_followup_clears_active_failure_projection(self) -> None:
        event = _pre()
        self.supervisor.handle_pre(event)
        self.supervisor.handle_post(_post(event, {"exit_code": 1}))
        changed = _pre(tool_input={"command": "rg changed src"}, tool_use_id="changed")
        self.supervisor.handle_pre(changed)
        self.supervisor.handle_post(_post(changed, {"exit_code": 0}))
        projection = project_evidence(self.ledger.read_records())
        self.assertIsNone(projection.active_failure_signature)

    def test_protected_mutation_is_denied_locally_then_unrelated_operation_is_approved(self) -> None:
        self.supervisor.set_scope(
            _scope(
                activity="implement",
                targets=("workspace.apply-patch", "shell.read"),
                owned_paths=("justfile",),
            ),
            reason="test bounded implementation",
        )
        denied = self.supervisor.handle_pre(
            _pre(
                "apply_patch",
                "*** Begin Patch\n*** Update File: .venv/state\n*** End Patch",
            )
        )
        approved = self.supervisor.handle_pre(
            _pre(tool_input={"command": "rg hook src"}, tool_use_id="tool-2")
        )
        self.assertEqual(_decision(denied), "deny")
        self.assertEqual(_decision(approved), "approve")

    def test_absolute_workspace_patch_path_normalizes_to_owned_relative_path(self) -> None:
        classification = classify_tool(
            "apply_patch",
            (
                "*** Begin Patch\n"
                f"*** Update File: {ROOT / 'justfile'}\n"
                "*** End Patch"
            ),
            repository_root=ROOT,
        )
        self.assertEqual(classification.operation.target_paths, ("justfile",))
        self.assertEqual(classification.operation.artifact_roles, ("owned",))

    def test_failure_observation_guides_retry_without_quarantine(self) -> None:
        event = _pre()
        self.supervisor.handle_pre(event)
        response = self.supervisor.handle_post(_post(event, {"exit_code": 1, "output": "x"}))
        state = self.ledger.read_state().model_dump(by_alias=True, mode="json")
        self.assertNotIn("quarantined", state)
        self.assertIn("failure-observed", response["hookSpecificOutput"]["additionalContext"])
        repeated = self.supervisor.handle_pre(
            _pre(tool_input={"command": "rg hook src"}, tool_use_id="tool-2")
        )
        self.assertEqual(_decision(repeated), "deny")

    def test_unmatched_post_records_evidence_without_poisoning_control_state(self) -> None:
        event = _pre(tool_use_id="unmatched")
        response = self.supervisor.handle_post(_post(event, {"exit_code": 0}))
        self.assertIn("unmatched-post-observed", response["hookSpecificOutput"]["additionalContext"])
        approved = self.supervisor.handle_pre(
            _pre(tool_input={"command": "rg other src"}, tool_use_id="next")
        )
        self.assertEqual(_decision(approved), "approve")

    def test_reducer_failure_is_local_and_later_state_remains_usable(self) -> None:
        def broken_reducer(*_args: object) -> object:
            raise RuntimeError("deterministic reducer fault")

        supervisor = Supervisor(ROOT, self.ledger, reducer=broken_reducer)
        event = _pre()
        supervisor.handle_pre(event)
        response = supervisor.handle_post(_post(event, {"exit_code": 1}))
        self.assertIn("reducer-error", response["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(self.ledger.read_state().pending, {})
        approved = supervisor.handle_pre(
            _pre(tool_input={"command": "rg changed src"}, tool_use_id="next")
        )
        self.assertEqual(_decision(approved), "approve")

    def test_project_hook_matchers_route_only_supervised_tool_families(self) -> None:
        config = tomllib.loads((ROOT / ".codex/config.toml").read_text(encoding="utf-8"))
        for event in ("PreToolUse", "PostToolUse"):
            matcher = config["hooks"][event][0]["matcher"]
            self.assertNotEqual(matcher, "*")
            self.assertIn("Bash", matcher)
            self.assertIn("apply_patch", matcher)
            self.assertNotIn("update_plan", matcher)


if __name__ == "__main__":
    unittest.main()
