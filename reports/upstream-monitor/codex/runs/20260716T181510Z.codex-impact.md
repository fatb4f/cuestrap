# CUEstrap Codex Contract-Surface Impact Report

## Run identity

- Run ID: `20260716T181510Z`
- Factory revision: `7ab6bc1de901396d4325fa891c064819b54738b8`
- CUEstrap revision: `d246290fd39064b0940839c9f3d683a92a43c9eb`
- Signal: `loop_bootstrap_request`
- Profile: `cuestrap`

## CUEstrap context state

- Profile state: bootstrap; no prior CUEstrap-profile evidence artifact existed.
- All required context reads were resolved at `fatb4f/cuestrap@d246290fd39064b0940839c9f3d683a92a43c9eb`.
- The current controller registers wildcard `PreToolUse` and `PostToolUse` command hooks, validates a fixed permission-mode vocabulary, correlates pre/post events by `tool_use_id`, and gates mutations by phase and evaluation state.
- Configured MCP servers declare `supports_parallel_tool_calls = false`; upstream unified-exec concurrency remains a separate tool-dispatch concern.
- CUEstrap repository state was used as subject context only, never as monitor authority.

## Channel state: main

- Status: `resolved`
- Head commit: `726b6378d2513c25e5e59b1371326be2fe194be4`
- Baseline: initial CUEstrap-profile bootstrap snapshot.
- Current divergence evidence includes permission/sandbox changes, dynamic skill selection, multi-agent lifecycle changes, MCP/code-mode tests, connector metadata APIs, context/world-state instructions, and concurrent unified-exec input handling.

## Channel state: latest-alpha-cli

- Status: `resolved`
- Head commit: `dd1363c67cbf530e362ea8e4c623d66fe97a5bc5`
- Baseline: initial CUEstrap-profile bootstrap snapshot.
- Main is fifteen commits ahead and one behind this independent alpha ref; no state was inferred across channels.

## Purpose impact: supervisory session controller

- Decision: `blocking-gate`.
- The current supervisory controller must be requalified against upstream permission/sandbox changes, dynamic instruction and skill-selection behavior, and concurrent unified-exec event ordering before its coverage claims can be strengthened.
- Matched surfaces: `permission-sandbox-approval`, `tool-dispatch-classification`, `instruction-skill-policy`, `session-turn-identity`, `multi-agent-session-control`.

## Purpose impact: idiomatic CUE workbook harness

- Decision: `contract-update`.
- MCP/code-mode result handling and environment-instruction context state require adapter and observation-contract comparison. No direct CUE engine or Marimo API break was observed in this upstream snapshot.
- Matched surfaces: `mcp-code-mode`, `tool-result-error-semantics`, `context-turn-lifecycle`, `release-channel`.

## Critical

- `bootstrap-permission-sandbox-contract` — `blocking-gate`: upstream permission schemas and sandbox policy changed while CUEstrap closes `permission_mode` and fail-closed admission over a fixed vocabulary. Requalify the CUE and Pydantic ingress models plus policy decisions before claiming compatibility.
- `bootstrap-tool-dispatch-concurrency` — `blocking-gate`: upstream now runs `write_stdin` concurrently across terminal sessions. Requalify pre/post event correlation, pending-operation identity, ordering, and quarantine behavior under concurrent dispatch.
- `bootstrap-instruction-skill-policy` — `blocking-gate`: dynamic skill-selection implementations changed and an implicit-invocation test surface was removed. Recheck the repository instruction chain and phase policy against current invocation behavior.

## High

- `bootstrap-mcp-code-mode-results` — `contract-update`: app metadata reads, connector metadata, code-mode tests, RMCP tests, and event mapping changed. Compare the Marimo MCP adapter and `response_reported_error` assumptions with current result envelopes.
- `bootstrap-context-turn-lifecycle` — `contract-update`: environment instructions entered world state and context history. Compare session continuity, context persistence, compaction, and workbook/controller boundaries.

## Notes

- `bootstrap-multi-agent-session-control` — upstream agent roles, spawn handling, jobs, and notifications changed. The current single-session controller has no multi-agent ownership model; retain this as an explicit future boundary.
- `bootstrap-release-channel-divergence` — preserve independent main and alpha qualification baselines.

## No local action

- Realtime WebRTC removal and build/lockfile churn did not match a declared CUEstrap surface and were not promoted into report items.

## Publication

- Factory run report: `contracts/upstream-monitor/codex/cuestrap-contract-surface/reports/runs/20260716T181510Z.codex-impact.md`
- Factory latest report: `contracts/upstream-monitor/codex/cuestrap-contract-surface/reports/latest.codex-impact.md`
- CUEstrap run report copy: `reports/upstream-monitor/codex/runs/20260716T181510Z.codex-impact.md`
- CUEstrap latest report copy: `reports/upstream-monitor/codex/latest.codex-impact.md`
- Mirror content equivalent: `true`

## Validation notes

- Shared vocabulary, `profiles_cuestrap`, compatibility entrypoint, fixed template, and publication plan were read.
- Exact signal, profile, target repository, context repository, entrypoint, and adapter were admitted.
- Every required context path was read from the current CUEstrap revision.
- Both upstream refs were concretely resolved and kept distinct.
- The profile had no prior evidence; this run establishes the initial baseline.
- No evidence, CUE authority, AGENTS file, prompt, or actuator plumbing was written to CUEstrap.
- Factory and CUEstrap report copies use identical content.
- `issueTargets: {}`; no issue update attempted.
- CUEstrap forbidden attractors were checked with none admitted.
- The GitHub App actuator cannot execute CUE; `cue fmt`, `cue vet`, and `cue export` are not claimed for this run.
- Terminal state: `terminal_success`.
