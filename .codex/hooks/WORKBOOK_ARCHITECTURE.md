# Three-workbook controller foundation

Issue #10 and PR #11 establish the first executable slice of the broader System A/System B architecture in issue #8.

The architecture uses three distinct Marimo workbooks with different targets, authority boundaries, and lifetimes.

| Workbook | Lifetime | Responsibility |
|---|---|---|
| Main CUEstrap workbook | Long-lived | System A target and interactive experiment surface |
| Rollout/JSONL controller workbook | Session- or rollout-scoped disposable | System B observation, normalization, correlation, and prospective control frame |
| Operation-controller workbook | One bounded general action binding | One-use uncovered effect and durable receipts through the workbook MCP adapter |

## Main CUEstrap workbook

The main workbook remains the target-workbook surface. The agent uses the typed
`workbook` MCP adapter, which selects an exact session and delegates to the
shared Marimo code-mode endpoint. CLIs remain operator and test frontends.

Direct routing is structural: a call must use an exported workbook MCP tool and
satisfy its closed structured schema. Merely mentioning an adapter or CLI
filename as a file operand does not make an action workbook-centric.

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

The operation-scoped executor handles recognized effects that do not already
have an adequate typed adapter. Git, CUE LSP, gopls, and workbook operations stay
on their direct MCP transports.

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

Codex does not expose its default shell tool because the project configuration
sets `[features].shell_tool = false`. Exact argv and other recognized uncovered
effects use a closed request object for `workbook.bind_operation`. The agent continues through typed
`inspect_operation`, `execute_operation`, `collect_diagnosis`, and
`release_binding` calls using the returned immutable binding. The hook does not
rewrite an original action or execute the effect itself. Shell parsing is not a
fallback transport.

Every request field—including session, turn, operation, working directory, timeout, target, semantic request digest, argv, and typed input—is covered by `requestIdentity` and revalidated before execution.

The configured workbook MCP server uses the existing loopback-only Marimo
code-mode endpoint as a multi-session substrate. A binding records endpoint,
workbook path and digest, session ID and digest, request identity, and resolution
sequence. Canonical argv executes with `shell=False` from the workbook's typed
`execute_operation`; inspection and diagnosis expose raw state and receipts
without repeating the effect. Durable request, binding, exclusive claim, and
terminal receipt records make reactive reruns inert.
Release writes a durable revocation record; subsequent bound operations fail
with `binding-released` while the shared Marimo server remains live.

`operation_controller_cli.py` is a thin optional frontend over the same service
library for operator debugging, CI, and MCP-server qualification. It is not the
agent-facing adapter.

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
target-workbook action   uncovered shell/tool action
        │                       │
workbook MCP adapter     workbook MCP adapter
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
