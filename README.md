# cuestrap

Temporary single-pattern CUE bootstrap laboratory.

The repository establishes a reusable workflow for aligning one idiomatic CUE pattern to pinned official CUE sources, projecting the minimum required kernel vocabulary, executing reusable semantic probes, and tightening the system through isolated Marimo-workbook iterations.

## Environment

```bash
uv sync --locked
direnv allow
```

`uv sync` is exact by default. `direnv` activates `.venv` and fails when the project and lock are not exactly synchronized. Codex MCP servers independently launch through the same locked `uv` project from `.codex/config.toml`.

## Workbook

```bash
uv run --project . --locked --exact -- \
  marimo edit src/cue-workbook/cue-workbook.py

uv run --project . --locked --exact -- \
  python src/cue-workbook/cue-workbook.py --validate
```

The initial workbook consolidates the reusable parts of the Factory Marimo experiments:

- strict Pydantic protocol models;
- deterministic Hypothesis checks;
- bounded repository coordinates;
- raw subprocess observations and digests;
- CUE CLI and cue-py/libcue backend comparison;
- semantic-subject identity;
- CUE LSP and gopls MCP adapters;
- interactive and browserless execution.

It intentionally excludes issue-specific mutation transactions, candidate generation, admission, coverage, and artifact publication.

## Layout

```text
.codex/       agent policy, skill, and MCP wiring
pattern/      active single pattern and durable fixtures
kernel/       minimum kernel projection for the active pattern
probe/        reusable semantic probe contract
runner/       thin Go runner when required
src/cue-workbook/
              reusable Marimo harness and iteration record
```

## Current pilot

`pattern/pilot.cue` is a harness placeholder only. It carries no claim of upstream alignment or admission. Replace it during a pattern-only session after the authority and single-pattern dependency matrix are selected.
