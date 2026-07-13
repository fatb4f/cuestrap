# CUEstrap agent contract

CUEstrap is a single-pattern bootstrap laboratory. Work in exactly one phase
per session. Do not combine implementation, fixture design, execution,
diagnosis, and correction in one session.

## Required environment

- Use the repository-root `pyproject.toml` and `uv.lock` only.
- Run Python, Marimo, MCP, and validation commands through
  `uv run --project . --locked --exact`.
- Do not create another virtual environment, requirements file, or inline PEP
  723 dependency block.
- Use the configured `cue_lsp` MCP server for CUE authoring sessions.
- Use the configured `gopls` MCP server for Go runner authoring sessions.

## Session phases

1. `authority`: inspect pinned official CUE sources and record claims only.
2. `pattern`: change one pattern and its traceability only.
3. `fixture-design`: add durable fixtures without changing their subject.
4. `kernel`: project only vocabulary required by the pilot pattern.
5. `probe`: implement one reusable semantic question.
6. `runner`: implement raw execution and transport only.
7. `execution`: run the workbook without source mutation.
8. `diagnosis`: classify a failure without applying a fix.
9. `correction`: apply one accepted correction to one surface.

A session that reaches the boundary of another phase must stop and report the
next phase rather than crossing the boundary.

## Evidence rules

- Backends produce raw facts, stages, diagnostics, identities, and digests.
- Backends must not emit `passed`, `success`, `valid`, `complete`, `admitted`,
  `satisfied`, or equivalent claimant verdicts.
- Do not generate temporary probe files beside production CUE sources.
- Reuse registered files and workbook requests. Temporary process material may
  exist only under a system temporary directory and must not become authority.
- The workbook and its Git history are the iteration record. Promote only
  durable fixtures, regression cases, contracts, and reusable probes.
