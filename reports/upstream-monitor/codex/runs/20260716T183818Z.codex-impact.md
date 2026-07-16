# CUEstrap Codex Contract-Surface Impact Report

## Run identity

- Run ID: `20260716T183818Z`
- Factory revision: `9fa1955d6676b0f9de95fe89700f3bb41569fab0`
- CUEstrap revision: `34d179bf014b09e988fb1e5256a255b64c178e8e`
- Signal: `loop_bootstrap_request`
- Profile: `cuestrap`

## CUEstrap context state

- Every required context path was resolved and reread at `fatb4f/cuestrap@34d179bf014b09e988fb1e5256a255b64c178e8e`.
- The supervisory context still closes `PreToolUse` and `PostToolUse` ingress, a fixed permission-mode vocabulary, `tool_use_id` pre/post correlation, phase-sensitive mutation gates, and post-result quarantine.
- The workbook context remains a gopy-backed Marimo harness with an isolated qualified probe path and exploratory direct mode.
- The CUEstrap repository revision advanced from the prior run; classification used the current required files rather than the prior report copy.
- CUEstrap repository state was used as subject context only, never as monitor authority.

## Channel state: main

- Status: `resolved`
- Head commit: `5331d20f6ef9b80ee4153132a70d4989780d916d`
- Prior channel head: `726b6378d2513c25e5e59b1371326be2fe194be4`
- Relation to prior channel state: four commits ahead, zero behind.
- New commits cover code-mode image-output validation, active-turn environment stability during settings updates, and restoration/validation of sub-agent role state.
- Evidence was classified only as `main`; no alpha state was imported.

## Channel state: latest-alpha-cli

- Status: `resolved`
- Head commit: `f84f9a6406cc55b210395f71b4c6aed236fc7ebb`
- Workspace version: `0.145.0-alpha.18`
- Prior channel head: `dd1363c67cbf530e362ea8e4c623d66fe97a5bc5`
- Relation to prior channel state: diverged; fourteen commits ahead and one behind the recorded alpha baseline.
- Concrete alpha delta paths include permission schemas, configuration aliases, dynamic skill selection, environment instructions, MCP/RMCP handling, session state, and multi-agent lifecycle code.
- The divergent history was preserved explicitly; no head or content was inferred from `main`.

## Purpose impact: supervisory session controller

- Decision: `blocking-gate`.
- Main changes turn-scoped project-instruction loading through captured environment state, while alpha changes permission/configuration and dynamic instruction/skill surfaces. Requalification is required before the controller can claim coverage for either current channel.
- Main and alpha also changed sub-agent/session state; these remain an unsupported ownership boundary rather than evidence of current multi-agent coverage.
- Matched surfaces: `permission-sandbox-approval`, `instruction-skill-policy`, `session-turn-identity`, `context-turn-lifecycle`, `multi-agent-session-control`.

## Purpose impact: idiomatic CUE workbook harness

- Decision: `contract-update`.
- Main now rejects malformed or unsupported code-mode image outputs with a dedicated error and requires `data:` image URLs. Alpha also changed MCP/RMCP and context-state paths.
- Compare the Marimo adapter and raw result/error observation contracts with the new code-mode and MCP envelopes. No direct CUE engine or Marimo API change was observed in this delta.
- Matched surfaces: `mcp-code-mode`, `tool-result-error-semantics`, `context-turn-lifecycle`, `release-channel`.

## Critical

- `main-active-turn-instruction-context` — `blocking-gate`: main now preserves each turn's captured environment selection while loading project instructions, so settings changes apply only to later turns. Requalify the repository instruction chain, turn identity, and context-boundary assumptions against this turn-scoped behavior.
- `alpha-permission-contract-delta` — `blocking-gate`: the current alpha history changes app-server permission schemas, core permission configuration, config aliases, and sandbox-related policy paths. Requalify the closed CUE/Pydantic `permission_mode` ingress and fail-closed admission policy against `latest-alpha-cli`.
- `alpha-instruction-skill-delta` — `blocking-gate`: the current alpha history changes dynamic skill-selector implementations and related invocation surfaces. Recheck repository instruction loading and session-phase constraints before treating alpha skill behavior as covered.

## High

- `main-code-mode-image-output-contract` — `contract-update`: commit `5331d20f6ef9b80ee4153132a70d4989780d916d` requires `data:` URLs for code-mode image output and converts malformed or unsupported image values into explicit tool-call errors. Compare workbook result normalization and error classification with this envelope.
- `alpha-mcp-context-contract` — `contract-update`: the alpha delta changes RMCP tests, MCP tool-call handling, environment-instruction world state, session state, and app metadata APIs. Requalify raw observations and context persistence independently from main.

## Notes

- `multi-agent-state-delta` — both channels changed sub-agent role, spawn, notification, or resume behavior. CUEstrap still binds one supervisory session/attempt and should retain multi-agent ownership as an explicit unsupported boundary.
- `alpha-release-divergence` — `latest-alpha-cli` now resolves to `0.145.0-alpha.18` after a divergent history update. Preserve this head as its own baseline and do not derive alpha support from main.

## No local action

- Build graph, lockfile, sample, TUI-debug, realtime-WebRTC removal, and other unmatched churn were not promoted because they did not satisfy a declared CUEstrap surface plus local-impact requirement.

## Publication

- Factory run report: `contracts/upstream-monitor/codex/cuestrap-contract-surface/reports/runs/20260716T183818Z.codex-impact.md`
- Factory latest report: `contracts/upstream-monitor/codex/cuestrap-contract-surface/reports/latest.codex-impact.md`
- CUEstrap run report copy: `reports/upstream-monitor/codex/runs/20260716T183818Z.codex-impact.md`
- CUEstrap latest report copy: `reports/upstream-monitor/codex/latest.codex-impact.md`
- Mirror content equivalent: `true`

## Validation notes

- Shared vocabulary, every `profiles_cuestrap` CUE file, the compatibility entrypoint, fixed report template, publication plan, and assertions were read.
- Exact signal, profile, target repository, context repository, entrypoint, and adapter were admitted.
- Every required CUEstrap context path was read from revision `34d179bf014b09e988fb1e5256a255b64c178e8e`.
- Both upstream refs were concretely resolved and compared only with their own prior channel heads.
- The alpha history divergence was recorded rather than normalized or inferred.
- Factory report/evidence paths and CUEstrap report-copy paths match the publication plan.
- Factory and CUEstrap run/latest report contents are byte-equivalent.
- No evidence, CUE authority, AGENTS file, prompt, or actuator plumbing was written to CUEstrap.
- `issueTargets: {}`; no issue update was attempted.
- All declared forbidden attractors were checked; none were admitted.
- The GitHub App actuator cannot execute CUE; `cue fmt`, `cue vet`, and `cue export` are not claimed for this run.
- Terminal state: `terminal_success`.
