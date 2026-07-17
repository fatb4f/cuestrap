# CUEstrap supervisory hooks

The project hook recognizes two action categories and routes them through distinct
workbook surfaces:

```text
proposed action
    ├── target-workbook action → existing Marimo/code-mode path remains direct
    └── general shell/tool action → fresh disposable operation-controller workbook
```

This is an experimental transport and anti-churn boundary. It is not issue #7's
native CUE authority, a complete System B implementation, or a universal Codex
interception boundary.

## Target-workbook actions

These remain on the existing target-workbook path:

- Marimo code-mode MCP calls;
- constrained `code_mode_client.py` operations;
- `workbook_cli.py` evaluation and probe operations;
- the operator-facing `marimo-listener` recipe.

The target workbook is the active experiment substrate and canonical interactive
iteration record. It does not supervise or authorize its own mutations.

## General actions

Recognized atomic Bash actions are rewritten with the supported Codex
`PreToolUse` shape:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "updatedInput": {
      "command": "/repo/.venv/bin/python /repo/src/cue-workbook/operation_controller_cli.py --repository-root /repo --payload <closed-request>"
    }
  }
}
```

The command starts one fresh Marimo runtime from
`src/cue-workbook/operation-controller.py`. Its reactive graph exposes:

```text
closed request
    → semantic revalidation
    → bounded working directory
    → pre-state projection
    → one-use claim
    → shell/tool effect
    → post-state projection
    → terminal receipt
```

The controller executes canonical argv with `shell=False`. The initial typed tool
adapter supports `apply_patch`; an original `apply_patch` call is denied with the
exact controller command because a Codex hook can replace tool input but cannot
change the tool kind to Bash.

General MCP operations without a typed controller adapter are denied explicitly.
They are not silently treated as governed or translated into approximate shell
commands.

Compound, piped, redirected, substituted, expansion-dependent, malformed, and
unknown Bash forms remain outside the controller vocabulary.

## One-use effect transaction

Each controller request binds:

- session, turn, and operation identity;
- proposed tool kind;
- canonical target and request digest;
- repository-relative working directory;
- exact argv or typed tool input;
- a bounded timeout.

Before an effect, the controller creates an exclusive claim. A repeated reactive
execution returns the existing receipt rather than executing again. A claim with
no terminal receipt produces `claimed-without-receipt` and is never retried
automatically.

Durable controller records live under Git's private metadata directory:

```text
$(git rev-parse --git-common-dir)/cuestrap-operation-controller/<operation-key>/
├── request.json
├── claim.json
└── receipt.json
```

The request and receipt make the disposable workbook reconstructable. The
reactive DAG is the current causal view, not the sole append-only authority.

## Hook state and evidence

The provisional anti-churn supervisor retains separate local state:

```text
$(git rev-parse --git-common-dir)/cuestrap-tool-supervisor/
├── state.json
└── events.jsonl
```

This ledger remains diagnostic. It does not replace the pinned Codex rollout
JSONL required by issue #7. Unmatched post events remain tactically inert, and
successful observations do not trigger the provisional identical-retry denial.

A rewritten `PostToolUse` event is restored to the original semantic action before
anti-churn evidence reduction, so controller transport details do not become the
action identity.

## Just boundary

Just is no longer part of governed runtime execution. The `justfile` contains
only operator/bootstrap commands:

- `marimo-listener` opens the target-workbook code-mode service;
- `operation-controller` opens the disposable controller template for inspection.

No Just recipe owns admission, tactical conclusions, execution identity, or
shell/tool effects.

## Wire and authority boundary

The repository hook emits only supported wire responses:

- `allow` plus `updatedInput` for an admitted Bash-to-controller rewrite;
- `deny` with an actionable reason for a required cross-tool reproposal or local
  provisional denial;
- no permission decision for direct or unclassified traffic;
- diagnostic context without manufactured approval on adapter failure.

Python currently performs framing, routing, semantic revalidation, one-use
execution, and local evidence correlation. Existing Python anti-churn predicates
remain provisional. Issue #7 must move the qualified tactical conclusion into the
native CUE pattern and compose it with rollout continuity and exact parent
authorization.
