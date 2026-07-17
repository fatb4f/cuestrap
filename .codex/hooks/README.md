# CUEstrap supervisory hooks

The project hook recognizes two action categories and routes them through distinct workbook surfaces:

```text
proposed action
    ├── target-workbook action → existing Marimo/code-mode path remains direct
    └── general shell/tool action → fresh disposable operation-controller workbook
```

This is an experimental transport and anti-churn boundary. It is not issue #7's native CUE authority, a complete System B implementation, or a universal Codex interception boundary.

## Target-workbook actions

These remain on the existing target-workbook path:

- Marimo code-mode MCP calls;
- exact constrained `code_mode_client.py` operations;
- exact `workbook_cli.py` evaluation and probe operations through the repository Python.

Workbook routing is structural. A command must invoke the exact adapter and admitted operation. File operations that merely mention `code_mode_client.py` or `workbook_cli.py` remain general actions and are routed through the disposable controller.

The target workbook is the active experiment substrate and canonical interactive iteration record. It does not supervise or authorize its own mutations.

## General actions

Recognized atomic Bash and `tool_exec` actions are denied with the exact command
that instantiates a fresh, request-bound Marimo code-mode runtime from
`src/cue-workbook/operation-controller.py` through
`operation_controller_cli.py`. The agent must re-issue that command; the hook
does not rewrite the original tool input.

The instantiation command returns an exact-session binding and four closed
follow-up commands:

```text
inspect     → request, graph identity, and cell errors
execute     → one claim-protected effect and the complete structured receipt
diagnose    → read-only cell outputs, errors, state identity, and receipt
close       → terminate the disposable loopback-only runtime
```

Only `execute` is restored to the proposed semantic action for supervisory
evidence. `inspect`, `diagnose`, and `close` remain workbook-centric lifecycle
operations. The agent uses these exact commands instead of raw Marimo
`execute_code` calls or a batch subprocess facade.

The controller's reactive graph exposes:

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

Bash input enters this path only when shell parsing and direct argv execution have identical meaning. Compound, piped, redirected, substituted, globbed, brace-expanded, expansion-dependent, malformed, and unknown Bash forms remain outside the controller vocabulary.

`tool_exec` accepts a closed command-bearing input shape. Both transports reduce
to one canonical argv semantic action before provisional evidence reduction.

The controller executes canonical argv with `shell=False`. The initial typed tool adapter supports `apply_patch`; an original `apply_patch` call is denied with the exact controller command because a Codex hook can replace tool input but cannot change the tool kind into Bash or `tool_exec`.

General MCP operations without a typed controller adapter are denied explicitly. They are not silently treated as governed or translated into approximate shell commands.

## Request identity and one-use effect transaction

Each controller request binds:

- session, turn, and operation identity;
- proposed transport tool;
- canonical target and semantic request digest;
- repository-relative working directory;
- bounded timeout;
- exact argv and, where applicable, typed tool input.

All fields are covered by `requestIdentity` and revalidated before execution. Changing working directory, timeout, session, turn, operation ID, target, request digest, argv, or typed input invalidates the request.

Before an effect, the controller creates an exclusive claim. A repeated reactive execution returns the existing receipt rather than executing again. A claim with no terminal receipt produces `claimed-without-receipt` and is never retried automatically.

Durable controller records live under Git's private metadata directory:

```text
$(git rev-parse --git-common-dir)/cuestrap-operation-controller/<operation-key>/
├── request.json
├── claim.json
├── receipt.json
├── code-mode-binding.json
├── code-mode.stdout.log
└── code-mode.stderr.log
```

The request and receipt make the disposable workbook reconstructable. The reactive DAG is the current causal view, not the sole append-only authority.

## Hook state and evidence

The provisional anti-churn supervisor retains separate local state:

```text
$(git rev-parse --git-common-dir)/cuestrap-tool-supervisor/
├── state.json
└── events.jsonl
```

This ledger remains diagnostic. It does not replace the pinned Codex rollout JSONL required by issue #7. Unmatched post events remain tactically inert, and successful observations do not trigger the provisional identical-retry denial.

The host establishes the active supervisory scope when it launches Codex. Set
`CUESTRAP_BOOTSTRAP_SCOPE` to one closed `Scope` JSON document containing the
activity, surface, owned paths, and allowed targets. For example:

```text
{"activity":"implement","surface":"workbook","ownedPaths":["src/cue-workbook/**"],"allowedTargets":["workspace.apply-patch","code-mode.apply-cell-transaction"]}
```

Each hook invocation reconciles durable state to this parent-process value and
records a control transition when it changes. When the variable is absent, the
legacy `CUESTRAP_BOOTSTRAP_PHASE` selects a read-only default scope; that default
has no owned mutation paths. Tool calls cannot update the hook parent's launch
environment, so this restores bounded mutation without an in-band scope command.

A controller-workbook `PostToolUse` event is restored to the canonical semantic
action before anti-churn evidence reduction, so Bash versus `tool_exec` transport
details do not become separate action identities.

## Just boundary

Just is no longer part of governed runtime execution. The `justfile` contains only operator/bootstrap commands:

- `marimo-listener` opens the target-workbook code-mode service;
- `operation-controller` opens the disposable controller template for inspection.

No Just recipe owns admission, tactical conclusions, execution identity, or shell/tool effects.

## Wire and authority boundary

The repository hook emits only supported wire responses:

- `deny` with an actionable exact code-mode instantiation command for a required workbook reproposal or local provisional denial;
- no permission decision for direct or unclassified traffic;
- diagnostic context without manufactured approval on adapter failure.

Python currently performs framing, routing, semantic revalidation, one-use execution, and local evidence correlation. Existing Python anti-churn predicates remain provisional. Issue #7 must move the qualified tactical conclusion into the native CUE pattern and compose it with rollout continuity and exact parent authorization.
