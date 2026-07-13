# CUEstrap agent contract

This repository is a temporary single-pattern bootstrap laboratory. Its purpose is to establish a repeatable loop for aligning one CUE pattern to pinned upstream authority, projecting the minimum kernel vocabulary, executing reusable probes, and tightening the pattern, kernel, probe, runner, and workbook through controlled iterations.

## Environment

- Use the repository-root `pyproject.toml`, `uv.lock`, `.venv`, and `.envrc`.
- Run Python through `uv run --project . --locked --exact` or the activated direnv environment.
- Do not create another virtual environment, `requirements.txt`, PEP 723 dependency block, or ad-hoc validator script.
- `src/cue-workbook/cue-workbook.py` is the reusable harness and iteration record.
- Use the configured `cue_lsp` MCP tools for CUE source work and `gopls` MCP tools for Go runner work.

## Session isolation

Every mutating session selects exactly one phase. Do not combine implementation, fixture design, execution, diagnosis, and correction in one session.

| Phase | Allowed work | Forbidden work |
| --- | --- | --- |
| authority | Inspect and pin official CUE sources; record locators and claims | Pattern, fixture, probe, runner, or workbook mutations |
| pattern | Modify one pattern and its traceability | Fixture design, probe changes, runner changes, semantic correction during execution |
| kernel | Modify only the minimal kernel projection required by the active pattern | General lattice expansion or unrelated vocabulary |
| fixture-design | Add or revise durable registered fixtures | Pattern/kernel corrections, runner changes, changing expectations after execution |
| probe | Implement one reusable semantic operation and its closed request/observation protocol | Pattern or fixture mutation; claimant-authored verdicts |
| runner | Implement raw semantic execution and failure classification | Admission decisions, pattern edits, fixture redesign |
| workbook | Improve the reusable Marimo harness and backend adapters | Pattern-semantic corrections or issue-specific admission logic |
| execution | Run the workbook and collect raw observations | Source mutations of any kind |
| diagnosis | Classify failures and propose one correction | Applying the correction |
| correction | Apply one accepted correction to one owned surface | Redesigning another layer or running a broad fix loop |

## Scope

The bootstrap scope is one pattern, one minimal kernel projection, one reusable probe family, one thin runner boundary, and one workbook.

Do not introduce candidate systems, package-wide admission, coverage aggregation, artifact bundles, generalized conformance reports, or knowledge-graph infrastructure.

## Validation discipline

- Durable fixtures belong under the active pattern or probe surface; do not create temporary fixture files beside production CUE.
- Controlled runtime material may be generated only by the workbook and must not become a second source of truth.
- Runner and backend observations contain raw facts, diagnostics, identities, and process states. They do not contain `success`, `passed`, `valid`, `complete`, `admitted`, or equivalent claimant verdicts.
- CUE LSP and gopls observations are advisory. CUE semantic operations remain the validation authority.
- Before ending a mutating session, run the narrowest structural check for the owned surface. Full-loop execution belongs to a later execution-only session.
