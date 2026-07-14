---
name: cue-bootstrap
description: Work within the CUEstrap single-pattern bootstrap loop using strict phase isolation, the locked uv/Marimo environment, CUE and Go language-server MCP tools, reusable probes, and raw observations.
---

# CUEstrap bootstrap loop

## Objective

Converge one CUE pattern through a bounded iterative loop:

```text
pinned authority
  -> pattern
  -> minimal kernel projection
  -> durable fixtures
  -> reusable probe
  -> cue-py / CUE CLI / thin Go runner observation
  -> workbook comparison
  -> diagnosis
  -> one controlled correction
```

The workbook is the durable experiment definition and iteration record. Git history records iterations.

## Start every session

1. Confirm the repository root contains `pyproject.toml`, `uv.lock`, `.envrc`, and `.codex/config.toml`.
2. Confirm `python` resolves inside `.venv` or use `uv run --project . --locked --exact`.
3. Read `.codex/AGENTS.md`.
4. State one phase from the session-isolation table.
5. Restrict mutations to that phase's owned surface.

## Reusable harness

Use the canonical notebook at `src/cue-workbook/cue-workbook.py` and its browserless
launcher at `src/cue-workbook/workbook_cli.py` instead of generating validation scripts.

```bash
uv run --project . --locked --exact -- \
  python src/cue-workbook/workbook_cli.py --validate

uv run --project . --locked --exact -- \
  marimo edit src/cue-workbook/cue-workbook.py

uv run --project . --locked --exact -- \
  python src/cue-workbook/workbook_cli.py \
    --probe-request path/to/request.json
```

The workbook provides:

- closed Pydantic request and observation models;
- deterministic Hypothesis harness properties;
- repository-bounded paths;
- subprocess facts and digests;
- semantic-subject identity;
- CUE CLI observations;
- cue-py/libcue worker observations when configured;
- backend comparison;
- persistent CUE LSP and gopls MCP adapters;
- interactive and browserless execution.

## Backend coordinates

The cue-py backend is enabled by explicit pinned coordinates:

```bash
export CUESTRAP_CUE_PY_ROOT=/absolute/path/to/cue-py
export CUESTRAP_LIBCUE_LIBRARY=/absolute/path/to/libcue.so
```

Use `libcue.dylib` on macOS and `cue.dll` on Windows. Do not clone, update, or repin these dependencies inside an execution session.

## Loop rules

- Design fixtures before executing them.
- Execute without mutation.
- Diagnose without correction.
- Correct one surface in a new session.
- Never change a fixture or expected semantic claim merely to make an observation agree.
- Never synthesize success-shaped observations.
- Do not expand beyond the active pattern until the same workflow can be reused unchanged for a second pattern.
