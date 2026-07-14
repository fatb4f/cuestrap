# CUEstrap agent contract

This repository is a temporary single-pattern bootstrap laboratory. Its purpose is to establish a repeatable loop for aligning one CUE pattern to pinned upstream authority, projecting the minimum kernel vocabulary, executing reusable probes, and tightening the pattern, kernel, probe, runner, and workbook through controlled iterations.

## Environment

- Use the repository-root `pyproject.toml`, `uv.lock`, `.venv`, and `.envrc`.
- Run Python through `uv run --project . --locked --exact` or the activated direnv environment.
- Do not create another virtual environment, `requirements.txt`, PEP 723 dependency block, or ad-hoc validator script.
- `src/cue-workbook/cue-workbook.py` is the canonical iteration record;
  `src/cue-workbook/workbook_cli.py` is its browserless command surface.
- Use the configured `cue_lsp` MCP tools for CUE source work and `gopls` MCP tools for Go binding/runner work.

## Native engine identity

All admitted native surfaces compile against:

```text
cue-lang/cue@806821e40fae070318600a264d311517e596353b
module/language target v0.18.0
go-python/gopy@72557f647208599c726c14dc9721a6c850d2e6d9
```

The gopy worker and `cueprobe` must report the same CUE revision and module target. Observations from mismatched engines are incomparable.

Direct mode may retain live Go-backed proxy objects in Marimo, but it is exploratory only. Accepted qualification runs import the same extension in a child Python process; native handles never cross that process boundary. `cue-py/libcue` is not an admitted workbook backend.

## Session isolation

Every mutating session selects exactly one phase. Do not combine implementation, fixture design, execution, diagnosis, and correction in one session.

| Phase | Allowed work | Forbidden work |
| --- | --- | --- |
| authority | Inspect and pin official CUE sources; record locators and claims | Pattern, fixture, probe, runner, or workbook mutations |
| pattern | Modify one pattern and its traceability | Fixture design, probe changes, runner changes, semantic correction during execution |
| kernel | Modify only the minimal kernel projection required by the active pattern | General lattice expansion or unrelated vocabulary |
| fixture-design | Add or revise durable registered fixtures | Pattern/kernel corrections, runner changes, changing expectations after execution |
| probe | Implement one reusable semantic operation and its closed request/observation protocol | Pattern or fixture mutation; claimant-authored verdicts |
| runner | Implement the Go binding facade or independent cueprobe raw execution surface | Admission decisions, pattern edits, fixture redesign |
| workbook | Improve direct/worker adapters and Marimo orchestration | Pattern-semantic corrections or issue-specific admission logic |
| execution | Run the workbook and collect raw observations | Source mutations of any kind |
| diagnosis | Classify failures and propose one correction | Applying the correction |
| correction | Apply one accepted correction to one owned surface | Redesigning another layer or running a broad fix loop |

## Scope

The bootstrap scope is one pattern, one minimal kernel projection, one reusable probe family, one native binding boundary, one independent process runner, and one workbook.

Do not introduce candidate systems, package-wide admission, coverage aggregation, artifact bundles, generalized conformance reports, or knowledge-graph infrastructure.

## Validation discipline

- Durable fixtures belong under the active pattern or probe surface; do not create temporary fixture files beside production CUE.
- Controlled runtime material may be generated only by the workbook and must not become a second source of truth.
- Runner and backend observations contain raw facts, diagnostics, identities, and process states. They do not contain `success`, `passed`, `valid`, `complete`, `admitted`, or equivalent claimant verdicts.
- CUE LSP and gopls observations are advisory. Native CUE API operations remain the semantic execution surface.
- Before ending a mutating session, run the narrowest structural check for the owned surface. Full-loop execution belongs to a later execution-only session.
