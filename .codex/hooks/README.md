# CUEstrap anti-churn hooks

The project hook is a phase-aware control-loop supervisor. It reduces repeated
commands and over-broad observations; it is not a general repository security
boundary.

Codex routes only supervised tool families to the hook. Within `Bash`, commands
outside the closed target vocabulary receive `approve`, may be recorded as
unclassified evidence, and have no budget, retry, failure-cluster, or scope
effects.

## State and evidence

Control state and evidence are separate under Git's private metadata directory:

```text
$(git rev-parse --git-common-dir)/cuestrap-tool-supervisor/
├── state.json    # v2 scope, budgets, session binding, pending operations
└── events.jsonl  # append-only decisions, observations, and transitions
```

The v1 state migrator validates the complete source document, records its
digest, maps `phase` to `scope.activity`, assigns the explicit `none` surface,
and writes v2 atomically. Legacy quarantine and recovery fields have no v2
meaning. Existing evidence records remain byte-for-byte ordered in the ledger.

## Operator scope transitions

Set all scope dimensions through the declared command, outside Codex tool
dispatch:

```bash
.venv/bin/python .codex/hooks/cuestrap_tool_supervisor.py \
  --repository-root . set-scope implement \
  --surface workbook \
  --owned-path 'src/cue-workbook/supervisory_hooks/**' \
  --owned-path tests/test_supervisory_hooks.py \
  --allowed-target shell.read \
  --allowed-target git.read \
  --allowed-target cue.lsp \
  --allowed-target workspace.apply-patch \
  --reason "begin one bounded supervisor implementation"
```

`set-phase` remains as a compatibility command. It selects the activity's
default targets with surface `none`; new operator workflows should use
`set-scope` so ownership is explicit.

Inspect control state with:

```bash
.venv/bin/python .codex/hooks/cuestrap_tool_supervisor.py \
  --repository-root . status
```

Do not edit `state.json` or `events.jsonl` to manufacture progress. Supervisor
implementation and configuration are ordinary owned source files and may be
changed during a bounded implementation scope.

## Decisions

Recognized operations are approved unless recorded evidence establishes a
closed denial predicate. Primary reasons use this precedence:

```text
protected-artifact-mutation
mixed-candidate-state
wrong-observation-channel
identical-retry
failure-cluster-exhausted
fanout-budget-exceeded
phase-invalid-churn
```

A denial applies only to that operation. It never quarantines, poisons, or
globally restricts the session. The post-hook appends normalized evidence and
may recommend a request, state, candidate, or phase change before retrying. A
post-hook or reducer error is recorded locally and does not affect later tools.

## Coverage boundary

Tool-name matcher routing supervises `Bash`, `apply_patch`/`Edit`/`Write`, the
repository Git MCP server, CUE LSP, and gopls. Other MCP and Codex-native tools
fall through to their native controls. Evidence records retain the coverage
label `codex-supported-hook-event`; the controller does not claim universal
interception.
