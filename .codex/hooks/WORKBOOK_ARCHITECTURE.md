# Three-workbook controller foundation

Issue #10 and PR #11 establish the first executable slice of the broader System A/System B architecture in issue #8.

The architecture uses three distinct Marimo workbooks with different targets, authority boundaries, and lifetimes.

| Workbook | Lifetime | Responsibility |
|---|---|---|
| Main CUEstrap workbook | Long-lived | System A target and interactive experiment surface |
| Rollout/JSONL controller workbook | Session- or rollout-scoped disposable | System B observation, normalization, correlation, and prospective control frame |
| Operation-controller workbook | One bounded general action | One-use Bash, `tool_exec`, or typed-tool execution and durable receipts |

## Main CUEstrap workbook

The main workbook remains the target-workbook surface. Existing Marimo code-mode, constrained client, and workbook CLI operations continue to act directly on it.

Direct routing is structural: a command must invoke the exact workbook adapter and admitted operation. Merely mentioning `code_mode_client.py` or `workbook_cli.py` as a file operand does not make an action workbook-centric.

It owns the interactive CUEstrap experiment and implementation state. It does not supervise, authorize, or assess its own mutations.

## Rollout/JSONL controller workbook

The rollout controller is the planned session-scoped System B workbook. It will:

- tail committed complete prefixes of the Codex rollout JSONL;
- mechanically normalize bounded runtime records;
- overlay the current provisional `PreToolUse` ingress when it has not yet appeared in the rollout;
- reconcile that provisional ingress with committed rollout records;
- correlate proposed actions, effective actions, dispatches, and terminal observations;
- maintain bounded tactical history, trust-epoch, continuity, and pending-execution projections;
- trigger independent System A recapture after relevant terminal observations;
- persist checkpoints and derived projections without becoming a competing raw event authority.

The rollout JSONL remains the primary System B runtime ledger. The workbook is reconstructable from the raw committed prefix, qualified workbook revision, and narrowly justified controller or parent receipts.

This workbook is deferred beyond PR #11.

## Operation-controller workbook

PR #11 implements the operation-scoped executor for recognized general Bash and `tool_exec` actions, plus exact typed adapters such as `apply_patch`.

```text
closed identity-bound request
    → semantic revalidation
    → bounded working directory
    → pre-state projection
    → one-use claim
    → shell-free argv or typed-tool effect
    → post-state projection
    → terminal receipt
```

Both Bash and `tool_exec` are rewritten to a fresh Marimo runtime. Bash is admitted only when shell parsing and direct argv execution have identical meaning. Globs, brace expansion, substitutions, pipelines, redirections, compound syntax, and other expansion-dependent forms remain outside the controller vocabulary instead of being reinterpreted as literal argv.

Every request field—including session, turn, operation, working directory, timeout, target, semantic request digest, argv, and typed input—is covered by `requestIdentity` and revalidated before execution.

Each action receives a fresh Marimo runtime. Canonical argv executes with `shell=False`; typed tool adapters handle operations that are not argv-native. Durable request, exclusive claim, and terminal receipt records make reactive reruns inert and make the disposable workbook reconstructable.

The operation controller does not own tactical semantics, continuity, parent authorization, System A assessment, or joint outcome composition.

## Combined flow

```text
Codex rollout JSONL
        ↓
rollout/JSONL controller workbook
        ├── committed history projection
        ├── provisional PreToolUse overlay
        ├── issue #7 tactical input
        └── System B readiness/continuity input
                    ↓
             parent composition
                    ↓
        ┌───────────┴───────────┐
        │                       │
target-workbook action   general shell/tool action
        │                       │
main CUEstrap workbook   operation-controller workbook
        │                       │
        └──── observations and receipts ────┘
                    ↓
           rollout normalization
                    ↓
       independent System A recapture
```

## Authority boundary

- The main workbook is the target and interactive development surface.
- The rollout workbook observes and derives the current System B control frame.
- The operation workbook executes exactly one admitted general action.
- Native CUE remains the intended executable semantic authority.
- The parent remains the discretionary authority for exact governed admission.
- Raw rollout, target-state, and receipt evidence retain separate provenance.

PR #11 lays down the executor and routing foundation. Issue #8 expands the rollout controller, System A capture and assessment, System B continuity and conformance, and parent composition independently over this split.
