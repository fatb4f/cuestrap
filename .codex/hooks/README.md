# CUEstrap supervisory hooks

The project config registers `cuestrap_tool_supervisor.py` for every Codex
`PreToolUse` and `PostToolUse` event that the current Codex release supports.
The hook validates closed event models, enforces the active bootstrap phase,
and records request/result digests in an append-only ledger under Git's private
metadata directory:

```text
$(git rev-parse --git-common-dir)/cuestrap-tool-supervisor/
```

Set the phase from an operator terminal, outside Codex tool dispatch:

```bash
.venv/bin/python .codex/hooks/cuestrap_tool_supervisor.py \
  --repository-root . set-phase implement \
  --reason "begin one bounded implementation tranche"
```

Inspect the structural state with:

```bash
.venv/bin/python .codex/hooks/cuestrap_tool_supervisor.py \
  --repository-root . status
```

The first hook event binds the Codex session as the run and its turn as the
attempt. A new session resets to `inspect`. A mutation closes the mutation gate
until an evaluation-phase observation is recorded. A successful constrained
`capture-state` observation clears quarantine.

Codex hooks currently intercept Bash, `apply_patch`, and MCP calls, but do not
intercept every unified shell or non-MCP tool path. The ledger records its
coverage as `codex-supported-hook-event`; it is not described as a universal
security boundary.
