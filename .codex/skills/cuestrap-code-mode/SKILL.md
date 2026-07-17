---
name: cuestrap-code-mode
description: Operate live CUEstrap workbooks through the typed workbook MCP adapter over Marimo code-mode. Use for exact-session inspection, focused probes, durable cell transactions, operation execution, runtime diagnosis, and raw observation collection during the trusted bootstrap loop.
---

# CUEstrap code-mode bootstrap

Use the live workbook as an orchestrator and observation surface. Let Codex propose, Marimo actuate, native runners observe, and CUE classify.

## Start

1. Read `.codex/AGENTS.md` and `.codex/skills/cuestrap/SKILL.md`.
2. Select exactly one bootstrap phase. Use this skill for `workbook`, `execution`, or `diagnosis`; mutate only during `workbook`.
3. Confirm `pyproject.toml`, `uv.lock`, `.envrc`, and `.codex/config.toml` exist and the interpreter resolves inside `.venv`.
4. Start the canonical workbook in a separate terminal:

```bash
uv run --project . --locked --exact -- \
  marimo edit --headless --no-token --port 2718 --mcp code-mode \
  src/cue-workbook/cue-workbook.py
```

Keep `--no-token` restricted to the loopback-bound bootstrap laboratory. Codex uses the registered `http://127.0.0.1:2718/mcp/server` endpoint.

## Use the typed workbook MCP adapter

During qualified runs, use the configured `workbook` MCP server. It is the
agent-facing adapter and internally uses Marimo's `list_sessions` and
`execute_code` primitives against the shared loopback endpoint. Raw Marimo MCP
remains configured for explicit bootstrap or operator recovery; qualified
workbook operations use the typed adapter. Do not edit a live notebook with
filesystem tools.

The target-workbook tools are:

- `workbook.resolve_session`
- `workbook.capture_state`
- `workbook.run_probe`
- `workbook.apply_transaction`

Each accepts the closed `bootstrap-run-binding/v1`, operation, and exact session
binding as structured MCP arguments. Retain the issued `SessionBinding`
unchanged; never substitute a session ordinal, recent session, or agent-selected
session ID. A probe remains restricted to `variable-repr` or `cell-source`, and
a transaction remains replacement-only and preimage-bound.

The operation-controller tools are:

- `workbook.bind_operation`
- `workbook.inspect_operation`
- `workbook.execute_operation`
- `workbook.collect_diagnosis`
- `workbook.release_binding`

When a recognized uncovered effect is denied, pass the closed request object to
`bind_operation`. Use the returned `ControllerCodeModeBinding` unchanged for the
remaining calls. Inspect before execution, execute once, collect diagnosis after
the terminal receipt, and release the binding at the end. A repeated execution
replays the durable receipt rather than repeating the effect.
Release is durable: later inspect, execute, or diagnosis calls using that
binding fail with `binding-released`.

`src/cue-workbook/code_mode_client.py` and
`src/cue-workbook/operation_controller_cli.py` are optional operator, CI, and
adapter-test frontends over the same libraries. They are not the agent-facing
workbook protocol and supervisory routing must not emit CLI commands.

The adapter exposes no raw `execute_code`, arbitrary Python, create/delete/move
instruction, or agent-authored MCP request surface.

Use the run phase as a dispatch boundary:

- `inspect`: resolve and capture only.
- `probe`: resolve, capture, and one approved scratchpad probe.
- `implement`: capture and one bounded replacement transaction.
- `evaluate`: capture and approved probes; native runners remain separate explicit adapters.
- `collect-evidence`: read-only capture and serialization only.

After a transaction, capture a fresh state before proposing another transaction. After quarantine, do not mutate until a fresh capture produces new preimages.

## Preserve the authority boundary

- Treat the client envelope as a raw observation, not a semantic verdict.
- Never translate runtime completion into `valid`, `passed`, `admitted`, or an equivalent claim.
- Preserve the run, attempt, controller, skill, client, session, workbook, cell, engine, request, generated-code, output, and CUE-authority identities.
- Let CUE and the native runners derive conclusions from observations.
- Diagnose in a separate session from execution. Apply one accepted correction in a later phase.

## Qualify the path

Perform these independently and retain each JSON envelope:

1. Resolve exactly one session and capture selected cells, graph, and errors; require no changed live-cell identities.
2. Run one approved focused scratchpad probe; record execution and shape facts while requiring live-cell identities to remain unchanged.
3. Submit one preimage-bound replacement transaction; require `structuralResult: applied-as-declared`, then run evaluation separately.

If session selection is zero or ambiguous, stop and correct the live-session binding. A released probe observation is not a semantically passing probe, and `applied-as-declared` is not a valid-workbook conclusion.
