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

Inspect the one session bound to the canonical workbook path:

```bash
uv run --project . --locked --exact -- \
  python src/cue-workbook/code_mode_client.py \
  --workbook src/cue-workbook/cue-workbook.py inspect
```

Run exactly one existing cell by stable cell ID:

```bash
uv run --project . --locked --exact -- \
  python src/cue-workbook/code_mode_client.py \
  --workbook src/cue-workbook/cue-workbook.py run-cell CELL_ID
```

Submit a closed transaction from JSON:

```bash
uv run --project . --locked --exact -- \
  python src/cue-workbook/code_mode_client.py \
  --workbook src/cue-workbook/cue-workbook.py transact REQUEST.json
```

Use schema `cuestrap.marimo-cell-transaction.v0`. Allowed operations are `create`, `edit`, `delete`, `move`, and `run`. For `edit` or `delete`, copy `expectedCodeDigest` from the latest inspection; the client re-reads and verifies it inside the transaction. Keep batches focused and at most 16 operations.

## Preserve the authority boundary

- Treat the client envelope as a raw observation, not a semantic verdict.
- Never translate runtime completion into `valid`, `passed`, `admitted`, or an equivalent claim.
- Preserve the envelope's session, workbook, cell, engine, request, output, and file digests.
- Let CUE and the native runners derive conclusions from observations.
- Diagnose in a separate session from execution. Apply one accepted correction in a later phase.

## Qualify the path

Perform these independently and retain each JSON envelope:

1. Run `inspect`; require one exact workbook session and record cells, graph, variables, outputs, and errors.
2. Run one stable cell ID with `run-cell`; inspect the post-execution capture.
3. Submit one focused source transaction; verify the requested cell identity in the capture and require `observation.durability.state` to be `observed`.

If session selection is zero or ambiguous, stop and correct the live-session binding. If durability remains `unchanged`, do not describe the transaction as durable.
