# CUEstrap

CUEstrap is a temporary single-pattern laboratory for aligning a CUE pattern to
pinned upstream authority. The canonical Marimo workbook records the experiment;
the browserless adapter runs the same probe path in automation.

The repository currently qualifies one narrow native model:

- `cuelang.org/go` at revision `806821e40fae070318600a264d311517e596353b`
  with module target `v0.18.0`;
- a gopy worker built from `go-python/gopy` revision
  `72557f647208599c726c14dc9721a6c850d2e6d9`;
- an independent `cueprobe` process built from the same CUE checkout.

## Repository map

- `pattern/` contains the active CUE pattern surface.
- `runner/bindings/` exposes the narrow gopy facade.
- `runner/cmd/cueprobe/` contains the independent Go probe.
- `src/cue-workbook/cue-workbook.py` is the canonical iteration record.
- `src/cue-workbook/workbook_cli.py` is the browserless and MCP adapter.
- `tests/fixtures/` contains durable probe requests and package fixtures.
- `.codex/AGENTS.md` defines the bootstrap phases and repository contract.

## Locked validation

Use the repository environment created from `pyproject.toml` and `uv.lock`:

```sh
uv sync --locked
uv run --project . --locked --exact -- \
  python src/cue-workbook/workbook_cli.py --validate
uv run --project . --locked --exact -- \
  python -m unittest discover -s tests -v
```

## Native qualification

Native qualification requires Go and network access to fetch the two pinned
source revisions on the first build:

```sh
uv run --project . --locked --exact -- \
  python src/cue-workbook/bootstrap_native.py
(cd runner && go test ./...)
uv run --project . --locked --exact -- \
  python -m unittest -v tests.test_native_harness
uv run --project . --locked --exact -- \
  python src/cue-workbook/workbook_cli.py \
    --probe-request tests/fixtures/pilot-request.json
```

The two native observations are comparable only when their declared and observed
CUE versions match, both current artifacts match one build manifest, and both
observations carry that same manifest digest.
