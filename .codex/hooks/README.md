# CUEstrap anti-churn hooks

The project hook is an experimental, phase-aware control-loop supervisor. It
reduces repeated commands and over-broad observations; it is not a general
repository security boundary, issue #7's CUE semantic authority, or a complete
System B implementation.

Codex routes only supervised tool families to the hook. Within `Bash`, commands
outside the closed target vocabulary receive no wire-level permission decision,
may be recorded as unclassified evidence, and have no budget, retry,
failure-cluster, or scope effects. Compound, piped, redirected, substituted, or
ambiguous Bash forms are also left unclassified.

## State and evidence

Control state and evidence are separate under Git's private metadata directory:

```text
$(git rev-parse --git-common-dir)/cuestrap-tool-supervisor/
├── state.json    # v2 scope, budgets, session binding, pending operations
└── events.jsonl  # local experimental decisions, observations, and transitions
```

The local JSONL is a provisional diagnostic ledger. It is not the authoritative
issue #7 event source and does not replace the required pinned Codex rollout
JSONL analysis.

The v1 state migrator validates the complete source document, records its
digest, maps `phase` to `scope.activity`, assigns the explicit `none` surface,
and writes v2 atomically. Legacy quarantine and recovery fields have no v2
meaning. Existing evidence records remain byte-for-byte ordered in the ledger.

## Scope transitions

The repository hook entrypoint exposes only `hook` and read-only `status`.
`set-scope` and `set-phase` are intentionally not available through the Codex
hook command surface. Tests or an external host may construct scope state before
a controlled session, but a production operator transition mechanism is
explicitly deferred.

Inspect control state with:

```bash
.venv/bin/python .codex/hooks/cuestrap_tool_supervisor.py \
  --repository-root . status
```

Do not edit `state.json` or `events.jsonl` to manufacture progress. Supervisor
implementation and configuration remain ordinary repository source files.

## Wire behavior

The repository entrypoint emits only currently supported `PreToolUse` shapes:

- no permission decision when the provisional supervisor does not deny;
- `permissionDecision: "deny"` with a reason for a denial;
- `additionalContext` without a manufactured approval when the adapter fails.

The Python package retains an internal `approve` marker for provisional tests,
but the repository-stable hook entrypoint removes it before writing Codex wire
output.

## Decisions

Recognized operations are approved internally unless recorded evidence
establishes a closed provisional denial predicate. At the live hook boundary,
only prior `reported-error` observations participate in the generic
`identical-retry` check; a successful prior observation cannot trigger that
denial.

Primary reasons use this precedence:

```text
protected-artifact-mutation
mixed-candidate-state
wrong-observation-channel
identical-retry
failure-cluster-exhausted
fanout-budget-exceeded
phase-invalid-churn
```

These Python predicates remain experimental. Issue #7's qualified tactical
conclusion must later move to the native CUE pattern and consume a pinned,
normalized rollout evidence stream.

A denial applies only to that operation. It never quarantines, poisons, or
globally restricts the session. Matched `PostToolUse` events append normalized
experimental evidence and may recommend a request, state, candidate, or phase
change before retrying. Unmatched post events are recorded only as unclassified
diagnostics and cannot enter tactical history, retry projections, failure
clusters, or progress calculations. A post-hook or reducer error is recorded
locally and does not affect later tools.

## Coverage boundary

Tool-name matcher routing supervises `Bash`, `apply_patch`/`Edit`/`Write`, the
repository Git MCP server, CUE LSP, and gopls. Other MCP and Codex-native tools
fall through to their native controls. Evidence records retain the coverage
label `codex-supported-hook-event`; the controller does not claim universal
interception.
