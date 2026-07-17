---
name: cuestrap-code-mode
description: Operate the live CUEstrap controller workbook through Marimo code-mode MCP using the repository's constrained client. Use for exact-session workbook inspection, focused cell execution, durable cell transactions, runtime diagnosis, and raw observation collection during the trusted bootstrap loop.
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

## Use the constrained client

During qualified runs, call only `src/cue-workbook/code_mode_client.py`. Do not call Marimo's `list_sessions` or `execute_code` tools directly and do not edit a live notebook file with filesystem tools.

Every invocation consumes an immutable `bootstrap-run-binding/v1` document. Resolve a session only in `inspect` or `probe`, using a `resolve-session` request whose selection rule is exactly `exactly-one-by-workbook-path`:

The constrained-client admission contract is fixed to the loopback endpoint, this repository root, and these separate operator-artifact roots:

```text
.codex/code-mode/run-bindings/
.codex/code-mode/session-bindings/
.codex/code-mode/requests/
```

Files outside their respective roots are not admitted even when they are elsewhere in the repository.

```bash
.venv/bin/python src/cue-workbook/code_mode_client.py \
  --endpoint http://127.0.0.1:2718/mcp/server \
  --repository-root . \
  --run-binding .codex/code-mode/run-bindings/RUN.json \
  resolve-session .codex/code-mode/requests/RESOLVE.json
```

Retain the issued `bootstrap_client.generated.models.SessionBinding` JSON unchanged. Later invocations receive it explicitly and may not substitute a session ordinal, recent session, or agent-selected session ID.

Capture a bounded state projection:

```bash
.venv/bin/python src/cue-workbook/code_mode_client.py \
  --endpoint http://127.0.0.1:2718/mcp/server \
  --repository-root . \
  --run-binding .codex/code-mode/run-bindings/RUN.json \
  --session-binding .codex/code-mode/session-bindings/SESSION.json \
  capture-state .codex/code-mode/requests/CAPTURE.json
```

Run one focused probe from the approved `variable-repr` or `cell-source` template. The request must declare exactly one subject and its expected observation shape:

```bash
.venv/bin/python src/cue-workbook/code_mode_client.py \
  --endpoint http://127.0.0.1:2718/mcp/server \
  --repository-root . \
  --run-binding .codex/code-mode/run-bindings/RUN.json \
  --session-binding .codex/code-mode/session-bindings/SESSION.json \
  run-focused-probe .codex/code-mode/requests/PROBE.json
```

Apply one replacement-based cell transaction only in `implement`. Copy each `expectedPreimageDigest` and the `expectedWorkbookRevision` from a fresh capture; declare every target cell and replacement source digest:

```bash
.venv/bin/python src/cue-workbook/code_mode_client.py \
  --endpoint http://127.0.0.1:2718/mcp/server \
  --repository-root . \
  --run-binding .codex/code-mode/run-bindings/RUN.json \
  --session-binding .codex/code-mode/session-bindings/SESSION.json \
  apply-cell-transaction .codex/code-mode/requests/TRANSACTION.json
```

The closed operation union is `resolve-session`, `capture-state`, `run-focused-probe`, and `apply-cell-transaction`. There is no raw `execute_code`, arbitrary Python, create/delete/move instruction, or agent-authored MCP request surface.

## Use disposable operation controllers

When the supervisory hook denies a recognized general action with an exact
`operation_controller_cli.py ... serve` command, re-issue that command unchanged.
It starts one request-bound loopback-only Marimo code-mode session and returns an
immutable session binding plus exact `inspect`, `execute`, `diagnose`, and `close`
commands.

- Use `inspect` before execution to capture the bound request, graph identity,
  and cell errors.
- Use `execute` once to claim and perform the effect through the workbook. A
  repeated call replays the terminal receipt instead of repeating the effect.
- Use `diagnose` for read-only cell outputs, errors, state identity, and the full
  structured receipt.
- Use `close` after evidence collection to dispose of the action-scoped runtime.

Do not alter the payload, endpoint, operation name, or emitted commands, and do
not call the disposable server's raw MCP tools. This separate closed lifecycle
does not expand the target-workbook operation union above.

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
