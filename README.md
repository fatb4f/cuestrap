# cuestrap

`cuestrap` is a temporary, single-pattern CUE bootstrap laboratory. Its first
product is a reusable Marimo workbook and disciplined iteration loop, not a
complete pattern catalog, kernel, runner, or admission framework.

## Boundaries

- `pattern/`: one pilot pattern at a time.
- `kernel/`: only the vocabulary required by the pilot.
- `probe/`: reusable semantic questions, separate from fixtures and verdicts.
- `runner/`: the later thin Go isolation/reference backend.
- `workbook/`: the executable iteration record, validation harness, CUE CLI and
  `cue-py/libcue` adapters, and MCP-to-LSP bridge.
- `.codex/`: project-local agent policy and MCP wiring.

Issue-specific candidate generation, patch promotion, package admission,
coverage aggregation, and artifact bundles are intentionally excluded.

## Environment

```sh
uv sync --locked --exact
direnv allow
uv run --locked --exact marimo edit workbook/cue_workbook.py
```

The shell guard and Codex MCP configuration both resolve through the same
root-managed `.venv`. Do not create another virtual environment or use direct
`pip install` commands.

## Browserless validation

```sh
uv run --locked --exact python workbook/cue_workbook.py --validate
```

The validation path performs strict Pydantic parsing, deterministic Hypothesis
properties, bounded-path checks, environment identity inspection, and an
optional CUE CLI smoke probe over the durable harness fixture.

## CUE bindings

`cue-py` and `libcue` remain external pinned checkouts. Configure them with:

```sh
export CUE_PY_ROOT=/absolute/path/to/cue-py
export LIBCUE_LIBRARY=/absolute/path/to/libcue.so
```

The workbook treats the CUE CLI as the reference backend and compares
`cue-py/libcue` only when the binding is available. Raw backends emit facts and
diagnostics; expectation and admission decisions stay outside backend output.
