# CUEstrap supervisory hooks

The repository hook recognizes two top-level action categories:

```text
proposed action
    ├── workbook-centric → workbook/code-mode transport remains direct
    └── general          → closed Just recipe transport
```

This is an experimental transport and anti-churn boundary. It is not issue #7's
native CUE authority, a complete System B implementation, or a universal Codex
interception boundary.

## Workbook-centric actions

Workbook operations stay on their native path:

- Marimo code-mode MCP calls;
- constrained `code_mode_client.py` operations;
- `workbook_cli.py` evaluation and probe operations;
- the `marimo-listener` recipe.

The hook does not wrap these operations in another Just recipe. The workbook is
the active substrate and canonical interactive experiment record.

## General actions

Recognized atomic Bash actions are converted into a versioned, digest-bound
recipe request and rewritten with the supported Codex shape:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "updatedInput": {
      "command": "just --justfile /repo/justfile hook-shell-read <payload>"
    }
  }
}
```

The recipe runner:

1. decodes a closed Pydantic request;
2. verifies the expected recipe, target identity, request digest, tool kind, and
   repository-relative working directory;
3. reclassifies the proposed operation against the closed vocabulary;
4. rejects workbook-centric actions at the general recipe boundary;
5. executes validated argv without a shell.

Available recipe transports cover shell reads, Git reads and mutations,
`apply_patch`, bounded workspace mutations, CUE/Python/Go evaluations, and Just
introspection.

Compound, piped, redirected, substituted, expansion-dependent, malformed, and
unknown Bash forms remain outside the recipe vocabulary.

## Non-Bash general tools

Codex can replace a tool's input but cannot change its tool kind. Therefore:

- `apply_patch` is denied with the exact equivalent `hook-apply-patch` command
  that can be re-issued through Bash;
- general MCP calls are denied with the required recipe family so the operation
  can be re-proposed through Bash;
- Marimo code-mode MCP remains direct because it is workbook-centric.

A canonical recipe invocation carries the original semantic request. The hook
restores that proposed request for anti-churn evaluation and PostToolUse
correlation while the effective transport remains the Just command.

## State and evidence

Local experimental state remains under Git's private metadata directory:

```text
$(git rev-parse --git-common-dir)/cuestrap-tool-supervisor/
├── state.json
└── events.jsonl
```

The ledger is diagnostic and provisional. It does not replace the pinned Codex
rollout JSONL required by issue #7. Unmatched post events remain tactically inert.

The repository entrypoint exposes only `hook` and read-only `status`; the
controlled agent cannot invoke `set-scope` or `set-phase` through this CLI.

## Semantic boundary

Python performs framing, routing, normalization, recipe revalidation, and local
evidence correlation. The existing Python anti-churn predicates remain
provisional. Issue #7 must later move the qualified tactical conclusion into the
native CUE pattern and compose it with rollout continuity and parent authority.
