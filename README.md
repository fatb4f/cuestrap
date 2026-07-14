# cuestrap

Temporary single-pattern CUE bootstrap laboratory.

The repository establishes a reusable workflow for aligning one idiomatic CUE pattern to pinned official CUE sources, projecting the minimum required kernel vocabulary, executing reusable semantic probes, and tightening the system through isolated Marimo-workbook iterations.

## Native CUE architecture

```text
CUE v0.18 Go API
  -> purpose-built Go binding facade
  -> gopy-generated CPython extension
       -> direct Marimo mode with live Go-backed Context/Loader/Value proxies
       -> isolated Python worker for accepted qualification
  -> independent cueprobe executable
  -> immutable observations and parity checks in Marimo
```

Pinned identities:

```text
cue-lang/cue@806821e40fae070318600a264d311517e596353b
CUE language/module target: v0.18.0
go-python/gopy@72557f647208599c726c14dc9721a6c850d2e6d9
```

The generated binding and `cueprobe` both compile against the same exact local CUE checkout. `cue-py/libcue` is not part of the admitted workbook execution path. The CUE CLI remains supplemental structural evidence.

## Environment

```bash
uv sync --locked
direnv allow
```

`uv sync` is exact by default. `direnv` activates `.venv` and fails when the project and lock are not exactly synchronized. Codex MCP servers independently launch through the same locked root `uv` project.

The native build additionally requires Go 1.25+ and `pybindgen` in the locked Python environment. The bootstrap fails closed when either is missing; it never installs into an ad-hoc environment.

## Build the native surfaces

```bash
uv run --project . --locked --exact -- \
  python src/cue-workbook/bootstrap_native.py
```

The bootstrap command:

1. checks out the exact CUE and gopy commits under `.deps/`;
2. verifies `runner/go.mod` resolves CUE to that checkout;
3. generates `src/cue-workbook/cue_native/` against the active locked interpreter;
4. builds `runner/bin/cueprobe`;
5. verifies the extension-reported CUE identity; and
6. records source, Python ABI, Go version, extension, and binary identities in `.deps/manifest.json`.

Generated native artifacts and `runner/go.sum` are intentionally not committed.

## Workbook

```bash
uv run --project . --locked --exact -- \
  marimo edit src/cue-workbook/cue-workbook.py

uv run --project . --locked --exact -- \
  python src/cue-workbook/cue-workbook.py --validate
```

### Interactive mode

Marimo imports the gopy extension directly and may retain live Go-backed `Context`, `Loader`, and `Value` proxies. This mode is exploratory only because a fatal native fault would terminate the notebook kernel.

### Qualified mode

The workbook starts a fresh Python worker that imports the same extension and returns only the existing closed observation envelope. It executes the same registered request through the independent `cueprobe` process. The parent retains process state, stderr, digests, subject identity, engine identity, and shared-fact comparisons.

Missing extension or runner artifacts produce typed `unavailable` observations and a `capability-gap`; they do not crash Marimo and do not imply semantic bottom.

## Layout

```text
.codex/                    agent policy and MCP wiring
pattern/                   active single pattern and durable fixtures
kernel/                    minimum kernel projection
probe/                     reusable semantic probe contract
runner/
  bindings/                narrow gopy-facing Go facade
  cmd/cueprobe/            independent one-shot evaluator
src/cue-workbook/
  cue-workbook.py          canonical Marimo/browserless entrypoint
  native.py                direct exploratory binding surface
  native_backend.py        isolated worker and cueprobe adapters
  native_validation.py     admitted workbook result surface
  bootstrap_native.py      pinned native build transaction
```

## Current pilot

`pattern/pilot.cue` remains a harness placeholder. It carries no claim of upstream alignment or admission. Replace it during a pattern-only session after the authority and single-pattern dependency matrix are selected.

## Deferred

- persistent-worker lifecycle qualification;
- complete diagnostic/loading/subsumption/resource/failure assertion catalogs;
- second-pattern reuse proof;
- package-wide admission, coverage, artifact publication, and knowledge-graph machinery;
- deletion of non-admitted cue-py compatibility code after downstream migration.
