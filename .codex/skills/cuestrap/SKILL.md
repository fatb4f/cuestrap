---
name: cuestrap
description: Operate the single-pattern CUE bootstrap loop through phase-isolated sessions and the locked Marimo workbook.
---

# CUEstrap

## Objective

Align one CUE pattern to pinned official sources, project the minimum kernel
vocabulary, ask reusable semantic questions, execute them through controlled
backends, and refine the loop without inventing ad hoc validators or fixtures.

## Mandatory start

1. Read `.codex/AGENTS.md`.
2. Name exactly one session phase.
3. Run `uv run --project . --locked --exact python workbook/cue_workbook.py --validate`.
4. Use CUE LSP for CUE files or gopls for Go files before reporting completion.

## Loop

`authority -> pattern -> fixture-design -> kernel -> probe -> runner -> execution -> diagnosis -> correction`

Each arrow is a session boundary. Execution never mutates source. Diagnosis
never applies a correction. Correction changes one accepted surface and stops.

## Prohibited expansion

Do not add package-wide admission, candidate promotion, artifact bundles,
coverage aggregation, generalized conformance suites, or a knowledge graph
until a second pattern reuses the first pattern's workflow without redesign.
