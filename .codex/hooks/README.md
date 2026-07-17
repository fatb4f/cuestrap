# CUEstrap supervisory hooks

The project hook recognizes direct typed adapters and uncovered effects:

```text
proposed action
    ├── Git/CUE/gopls action → existing typed MCP adapter remains direct
    ├── target-workbook action → typed workbook MCP adapter remains direct
    └── uncovered typed effect → typed operation-workbook lifecycle
```

This is an experimental transport and anti-churn boundary. It is not issue #7's native CUE authority, a complete System B implementation, or a universal Codex interception boundary.

## Target-workbook actions

These remain on the typed target-workbook path:

- `workbook.resolve_session` and `workbook.capture_state`;
- `workbook.run_probe` and `workbook.apply_transaction`;
- exact Marimo sessions selected internally by path and immutable binding.

The configured `workbook` MCP server is the agent-facing adapter. It delegates
to Marimo's `list_sessions` and `execute_code` primitives internally. The
code-mode and operation-controller CLIs remain optional operator/test frontends
over the same libraries.

Workbook routing is structural. A call must use an exported workbook MCP tool
and satisfy its closed input schema. File operations that merely mention adapter
or CLI filenames remain ordinary file operations.

The target workbook is the active experiment substrate and canonical interactive iteration record. It does not supervise or authorize its own mutations.

## General actions

The project configuration sets `[features].shell_tool = false`, so Codex does
not offer its default shell tool in a new session. Exact argv operations use
`workbook.bind_operation`; the controller executes them with `shell=False`.
Typed MCP adapters remain direct. A shell-dependent operation requires a
separate explicitly authorized capability and is never an automatic fallback.

The binding tool returns an exact-session binding used by four closed follow-up
tools:

```text
inspect_operation   → request, graph identity, and cell errors
execute_operation   → one claim-protected effect and the structured receipt
collect_diagnosis   → read-only outputs, errors, state identity, and receipt
release_binding     → durably revoke the binding without terminating the shared server
```

The typed `execute_operation` request carries the original controller request,
so supervisory evidence retains the underlying semantic target without
reconstructing it from a CLI process. The other calls remain workbook-centric
lifecycle observations.

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

`tool_exec`, when the host exposes it, accepts a closed command-bearing input
shape. It is optional and is not confused with Git MCP or required as workbook
qualification evidence.

The controller executes canonical argv with `shell=False`. The operation service
also retains the exact `apply_patch` adapter; an original call is denied with a
typed workbook request because a Codex hook cannot replace one tool kind with
another.

Git MCP, CUE LSP, gopls, Marimo code-mode, and workbook MCP operations use their
typed adapters directly. Unknown MCP operations are not translated into shell
commands.

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
└── release.json
```

The request and receipt make the operation binding reconstructable. A durable
release record rejects later inspect, execute, and diagnosis calls with
`binding-released`. The reactive DAG is the current causal view, not the sole
append-only authority.

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

- `deny` with an actionable typed workbook request for a required reproposal or local provisional denial;
- no permission decision for direct or unclassified traffic;
- diagnostic context without manufactured approval on adapter failure.

Python currently performs framing, routing, semantic revalidation, one-use execution, and local evidence correlation. Existing Python anti-churn predicates remain provisional. Issue #7 must move the qualified tactical conclusion into the native CUE pattern and compose it with rollout continuity and exact parent authorization.
