## msg 1

---

# Control-loop design

A marimo workbook could have acted as a **supervisory controller around Codex tool use**:

```text
                    ┌─────────────────────────────┐
PreToolUse event ──▶│ normalize + identify call   │
                    │ check state and invariants  │
                    │ estimate cost/risk          │
                    └──────────────┬──────────────┘
                                   │
                  allow / block / narrow / reuse
                                   │
                                   ▼
                              tool execution
                                   │
                                   ▼
                    ┌─────────────────────────────┐
PostToolUse event ─▶│ record raw observation      │
                    │ classify failure            │
                    │ update retry/cost state     │
                    │ derive next admissible step │
                    └─────────────────────────────┘
```

Marimo is suitable for the supervisory surface because it builds a reactive dependency graph from cell definitions and references, rerunning dependent cells when upstream state changes. Its notebooks can also run as ordinary Python scripts or importable modules. ([docs.marimo.io][1])

The important boundary would be:

```text
CUE contracts       = normative policy and verdict semantics
Hook adapter        = synchronous interception and event transport
Marimo workbook     = state projection, diagnosis, caching, and operator UI
Tool                = actual effectful execution
```

The workbook should not itself claim that a test passed. It should consume raw hook observations and calculate whether another call is useful.

## 1. Shared hook envelope

Both hooks would use a closed event schema.

```python
@dataclass(frozen=True)
class ToolIntent:
    session_id: str
    turn_id: str
    tool_use_id: str

    tool: str
    input: dict[str, object]
    cwd: str

    repository: str | None
    head_revision: str | None
    worktree_digest: str | None

    expected_effect: str
    expected_artifacts: tuple[str, ...]
    cost_class: Literal["cheap", "moderate", "expensive", "external"]


@dataclass(frozen=True)
class ToolObservation:
    tool_use_id: str

    started_ns: int
    elapsed_ns: int
    exit_code: int | None

    stdout_digest: str
    stderr_digest: str
    stdout_preview: str
    stderr_preview: str

    workspace_before: str | None
    workspace_after: str | None
    changed_paths: tuple[str, ...]
```

The pre-hook returns:

```python
@dataclass(frozen=True)
class ToolDecision:
    action: Literal[
        "allow",
        "block",
        "reuse",
        "require-narrower-probe",
        "require-state-change",
    ]
    reason_code: str
    explanation: str

    prior_observation_id: str | None = None
    suggested_command: tuple[str, ...] | None = None
    additional_context: str | None = None
```

Your hook requirements already anticipated this split: `PreToolUse` performs action admission, while `PostToolUse` records completed effects as observations and cannot pretend to roll them back. 

## 2. Semantic call fingerprinting

Raw command strings are insufficient. The workbook should compute a normalized fingerprint over:

```text
tool identity
+ normalized argv or structured input
+ effective working directory
+ repository identity
+ HEAD revision
+ relevant worktree-path digests
+ environment/tool versions
+ selected contract or fixture identity
```

For example:

```python
fingerprint = sha256(
    canonical_json(
        {
            "tool": intent.tool,
            "argv": normalize_argv(intent.input),
            "cwd": realpath(intent.cwd),
            "head": intent.head_revision,
            "dependencies": relevant_file_digests,
            "tool_versions": tool_versions,
        }
    )
).hexdigest()
```

This allows the pre-hook to distinguish:

```text
same command + same state        → exact retry
same command + changed files     → legitimate re-evaluation
different command + same failure → possibly same failed hypothesis
```

## 3. Pre-tool controls

### Duplicate-success reuse

When an identical read-only or validation call already succeeded against the same state:

```text
decision: reuse
reason: equivalent-observation-exists
```

The hook injects the prior concise result instead of paying for another shell, GitHub, or model-visible output.

Examples:

* repeated `git rev-parse`;
* repeated remote-ref lookup when the observed ref has not changed;
* repeated `cue eval -e authorityPinned`;
* repeated source-file retrieval at an exact commit;
* repeated digest calculation over unchanged files.

### Failure circuit breaker

For an equivalent call that already failed:

```python
if same_fingerprint and previous.exit_code != 0:
    return ToolDecision(
        action="require-state-change",
        reason_code="exact-failure-retry",
        explanation=(
            "This operation already failed against the current repository "
            "state. Change the subject, command, environment, or hypothesis."
        ),
    )
```

A stricter breaker could trigger after two calls sharing the same normalized failure signature:

```text
failure key =
    executable
  + normalized diagnostic category
  + affected schema/path
  + workspace digest
```

This would have prevented repeated evaluator invocations that differed syntactically but exercised the same contradictory observation construction.

### Prerequisite checks

Before allowing an expensive command, the hook could verify:

```text
binary exists
declared runner exists
working directory is inside the expected CUE module
target package exists
fixture key exists
expected generated input exists
format gate is clean
cheap structural probe has passed
no unresolved earlier blocker dominates this operation
```

In this session, attempting runner-backed admission while `runner/cueprobe` did not exist should have produced:

```text
block:
  reason = runner-capability-unavailable

derived state:
  schemaComplete       = potentially true
  executionEvidence    = absent
  admissionEvaluable   = false
```

That would have prevented both repeated runner investigation and the temptation to insert success-shaped observations as substitutes.

### Progressive validation

The pre-hook should enforce a validation ladder:

```text
L0  path and executable existence
L1  syntax / formatting
L2  target package structural vet
L3  one focused evaluator probe
L4  adversarial evaluator family
L5  complete package DAG
L6  remote verification or publication
```

A level is allowed only after its prerequisites pass or when the call is explicitly diagnostic.

This avoids running the complete DAG while a local evaluator probe is already known to be malformed.

### Output-budget control

Commands should declare their expected output mode:

```text
scalar       one Boolean, SHA, count, or verdict
diagnostic   bounded stderr around one failure
artifact     full output redirected to a file
interactive  only when explicitly required
```

The pre-hook could reject:

```bash
cue eval ./... -e report
```

when the actual question is only whether one field is true, and propose:

```bash
cue export ./... -e report.sliceAdmission
```

or:

```bash
cue export ./... -e report |
  jq '{sliceAdmission, negativeFixturesComplete, structuralGatesComplete}'
```

Full output would be saved as an artifact with only a digest, path, and bounded preview returned to Codex.

## 4. Post-tool controls

The post-hook should append an immutable observation to JSONL or SQLite:

```json
{
  "schema": "tool-observation/v1",
  "toolUseID": "call-123",
  "fingerprint": "sha256:...",
  "exitCode": 1,
  "failureClass": "cue-bottom-during-probe-construction",
  "workspaceBefore": "sha256:...",
  "workspaceAfter": "sha256:...",
  "changedPaths": [],
  "elapsedMs": 184,
  "outputBytes": 9214
}
```

It would then derive, but not store as raw facts:

```text
retryable without state change: false
same failure count:             3
recommended next operation:     inspect unsuppressed diagnostic
blocked operation family:       complete evaluator suite
```

### Failure clustering

Diagnostics should be normalized by removing unstable data such as:

* timestamps;
* temporary paths;
* line offsets when appropriate;
* generated identifiers;
* command-call IDs.

Then cluster by semantic category:

```text
command-shape-error
missing-capability
wrong-module-root
formatting-dirty
schema-bottom
fixture-identity-mismatch
suppressed-diagnostic
remote-state-unchanged
```

After the first evaluator failure, the workbook should have recognized that stderr was being discarded. It could then block another adversarial-suite call containing `2>/dev/null` and require a single unsuppressed focused probe.

### State invalidation

Prior results remain reusable only while their dependencies are unchanged:

```python
valid = (
    observation.head_revision == current.head_revision
    and observation.dependency_digest == current.dependency_digest
    and observation.tool_version == current.tool_version
)
```

A formatting edit invalidates format and CUE-evaluation observations for affected packages, but does not necessarily invalidate:

* pinned upstream source retrieval;
* issue-body digest;
* remote branch metadata;
* unrelated package checks.

That is more precise than rerunning everything after every patch.

## 5. Workbook layout

A useful `tool_supervisor.py` marimo workbook would have these reactive cells:

```text
1. Authority snapshot
   repository, branch, HEAD, matrix revision, tool versions

2. Hook ledger
   watch JSONL/SQLite projection

3. Normalized operations
   semantic fingerprints and dependency sets

4. Failure clusters
   repeated failures grouped by cause

5. Cost model
   calls, elapsed time, output bytes, remote calls, estimated token exposure

6. Circuit breakers
   currently blocked fingerprints and required state transitions

7. Validation DAG
   completed, invalidated, blocked, and runnable nodes

8. Recommended next probe
   smallest operation that can reduce uncertainty

9. Admission projection
   declarations complete versus evidence complete versus admitted

10. Operator controls
   clear breaker, authorize expensive call, invalidate cache, export evidence
```

`mo.watch.file()` can reactively rerun dependent cells when the hook ledger changes. Marimo also provides persistent disk caching for expensive computations and prevents concurrent duplicate execution of the same cached async call. ([docs.marimo.io][2])

For the control-plane workbook, external operations should use lazy execution, `mo.stop`, disabled autorun, or explicit run controls so opening or editing the workbook cannot accidentally repeat expensive effects. ([docs.marimo.io][3])

## 6. How it would have changed this session

| Session behavior                                  | Pre-hook decision                                   | Post-hook result                              |
| ------------------------------------------------- | --------------------------------------------------- | --------------------------------------------- |
| Search for or invoke missing `cueprobe`           | Block execution after existence probe               | Record `runner-capability-unavailable` once   |
| Repeat admission checks without runner evidence   | Block as dominated by missing capability            | Keep admission evidence incomplete            |
| Run format-sensitive validation before formatting | Require `cue fmt --check` first                     | Invalidate only affected package gates        |
| Repeat malformed evaluator suite                  | Require state change after first equivalent failure | Cluster failures under evaluator construction |
| Suppress CUE diagnostics                          | Reject diagnostic command with discarded stderr     | Require focused unsuppressed probe            |
| Run broad `cue eval` for a few fields             | Rewrite to narrow scalar projection                 | Store full output outside model context       |
| Re-query pinned upstream sources                  | Reuse cached revision-bound result                  | Invalidate only on revision change            |
| Recheck unchanged remote branch                   | Reuse ref observation within state boundary         | Refresh after push or explicit invalidation   |
| Claim admission from placeholder observations     | Block publication/admission projection              | Show `definitionComplete`, `evidenceAbsent`   |

## 7. Implementation boundary

I would not put a full interactive marimo kernel directly in the synchronous hook path. The lower-latency arrangement is:

```text
marimo/workflows/tool_supervisor.py
    importable policy functions
    reactive dashboard
    replay and analysis UI

hooks/tool_control.py
    lightweight CLI
    imports policy functions
    reads current ledger/snapshot
    emits one JSON decision

.kb/tool-control/
    contracts.cue
    policy.cue
    tool-events.jsonl
    derived-state.json
    artifacts/
```

Marimo notebooks can be run as scripts, accept command-line arguments, and expose reusable functions to other Python modules, so one source can support both the hook adapter and interactive workbook. ([docs.marimo.io][4])

The resulting control law is:

```text
allow(tool call)
    only if
        authorized
        ∧ prerequisites satisfied
        ∧ not an unchanged failed retry
        ∧ no equivalent result is reusable
        ∧ cost is proportional to unresolved uncertainty
```

That would not eliminate failures. It would make each distinct failure occur once, preserve it as evidence, and force the next tool call to either change state, test a different hypothesis, or consume a cached result.

[1]: https://docs.marimo.io/guides/reactivity/ "Running cells - marimo"
[2]: https://docs.marimo.io/api/watch/ "Watch - marimo"
[3]: https://docs.marimo.io/guides/expensive_notebooks/ "Expensive notebooks - marimo"
[4]: https://docs.marimo.io/guides/scripts/ "Run notebooks as scripts - marimo"
---

## msg 2

---

# Control-loop placement

Marimo could have acted as a **session controller around Codex**, without becoming part of the #106 kernel–probe–eval semantics:

```text
Codex proposes tool call
        ↓
PreToolUse hook
        ↓
typed event → Marimo controller
        ↓
allow | constrain | reuse cached result | deny | stop
        ↓
tool executes
        ↓
PostToolUse hook
        ↓
typed observation → Marimo controller
        ↓
state update + failure classification + next admissible transition
```

In control-theory terms:

| Role             | Component                                                |
| ---------------- | -------------------------------------------------------- |
| Plant            | Codex, tools and repository                              |
| Controller       | Marimo workflow                                          |
| Actuator         | Pre-tool hook decision                                   |
| Sensor           | Post-tool hook observation                               |
| State estimator  | Session ledger derived from repository and tool evidence |
| Circuit breaker  | Failure and retry policies                               |
| Operator display | Reactive Marimo UI                                       |

This would be **cross-cutting workflow control**, not the deferred #106 Marimo semantic adapter. The workbook would constrain Codex’s behavior while CUE remained authoritative for contracts and validation semantics.

# Contract first

The hooks should exchange closed events rather than prose.

```cue
#PreToolEvent: close({
    sessionID:       string
    turnID:          string
    activeUnit?:     string
    repository:      string
    revision:        string
    worktreeDigest:  string

    tool:            string
    operation:       string
    argumentsDigest: string

    hypothesisID?:   string
    expectedEvidence?: [...string]

    changedPaths?: [...string]
})

#PostToolEvent: close({
    requestDigest: string

    execution: "completed" | "failed" | "timeout" | "cancelled"

    exitCode?: int
    stdoutDigest?: string
    stderrDigest?: string

    changedPaths: [...string]
    revisionAfter: string
    worktreeDigestAfter: string
})

#HookDecision: close({
    disposition:
        "allow" |
        "allow-constrained" |
        "reuse" |
        "deny" |
        "stop"

    reasonCode: string
    explanation: string

    constraints?: {
        allowedPaths?: [...string]
        allowedCommands?: [...string]
        requiredHypothesisID?: string
        requiredEvidence?: [...string]
    }

    contextProjection?: _
})
```

CUE would validate the ingress and compute bounded policy inputs. Python adapters would project those values into typed models consumed by the workbook.

# Workbook state

The workbook needed a persistent session ledger approximately like this:

```text
SessionState
├── active parent issue
├── active child implementation unit
├── directly satisfied requirements
├── dependency closure
├── authoritative artifact allowlist
├── current validation phase
├── repository/worktree digest
├── hypotheses attempted
├── tool-call fingerprints
├── result cache
├── normalized failures
├── semantic-failure count
├── cost counters
├── admitted evidence
└── stop condition
```

The important distinction is between:

```text
raw event
    → classified observation
    → controller state
    → next permitted action
```

The agent should never directly increment, reset or override its own failure count or admission state.

# Pre-tool policies

## 1. Parent-issue scope gate

At the beginning of the session, the controller would have observed:

```text
issue #106:
    canonical parent matrix
    58 P0 requirements
    explicitly not an implementation plan

active child unit:
    absent
```

The pre-hook should therefore have returned:

```text
disposition: stop
reasonCode: parent-requires-child-unit
```

or, in explicitly authorized exploratory mode:

```text
disposition: allow-constrained
constraints:
    status: candidate
    admissionClaimsForbidden: true
    authoritativeArtifactsForbidden: true
```

That alone would have prevented the attempt to implement the whole P0 graph in one pass.

## 2. Artifact allowlist

Every mutation would be checked against the active child issue:

```text
Child A: skill package + kernel
allowed:
    SKILL package metadata
    cue.mod
    kernel contracts
    kernel fixtures

forbidden:
    runner protocol
    LSP client
    suite aggregation
    artifact publication
```

The large patch adding observation, runner, structural-gate and evaluator surfaces would have been denied until their child units were active.

## 3. Retry fingerprinting

Normalize each tool invocation into:

```text
fingerprint =
    tool
    + normalized arguments
    + cwd
    + repository revision
    + worktree digest
    + relevant input-file digests
```

Then apply:

```text
same fingerprint + same inputs
    → reuse cached result

same failure signature + no hypothesis change
    → deny retry

same command + relevant files changed
    → allow re-execution
```

This would eliminate repeated reads, unchanged `cue vet` executions and repeated repository inspections.

## 4. Hypothesis-bound corrections

After a semantic failure, the next mutation would require:

```text
hypothesisID
target definition
kernel analogue
expected changed diagnostic
allowed paths
```

For example:

```text
hypothesisID: probe-spec-disjunction-closure
target: contracts/probe/spec.cue:#ProbeSpec
analogue: contracts/kernel/kernel.cue:<specific pattern>
expectedEvidence:
    - focused fixture succeeds
    - prior failure signature disappears
```

A broad patch touching unrelated evaluator, runner and artifact files would not satisfy this contract.

## 5. Validation transition gate

The controller would enforce the declared order:

```text
edit
  → format changed files
  → structural vet
  → concrete positive probe
  → expected-bottom negative probe
  → evaluator fixtures
  → broader package validation
```

It would reject full-suite validation while the focused definition was still failing.

# Post-tool policies

## Failure classification

The post-hook should classify results into distinct types:

```text
syntax failure
structural CUE failure
semantic-model failure
concreteness failure
expected fixture bottom
unexpected fixture acceptance
infrastructure failure
scope violation
repeated unchanged failure
```

This matters because the session’s skill explicitly required one targeted correction after the first semantic failure and termination after the second. The rule existed in the loaded instructions but was not mechanically enforced. 

A post-hook would have produced:

```text
failure 1:
    class: semantic-model
    signature: canonical-value-shape/...

next:
    exactly one targeted correction permitted
```

Then:

```text
failure 2:
    class: semantic-model
    signature: probe-spec-empty-disjunction/...

next:
    stop and report
```

The subsequent conflict-fixture redesign and broader modeling improvisation would never have been admitted.

## Failure signatures

Diagnostics should be normalized rather than compared as raw prose:

```text
signature =
    tool family
    + phase
    + package
    + definition
    + normalized error category
    + relevant source digest
```

Line numbers and incidental diagnostic wording should not define identity.

## State transition

A successful tool call would not automatically advance the workflow. The post-hook would verify that the expected evidence was actually produced:

```text
patch applied successfully
    ≠ semantic correction proved

command exited zero
    ≠ requirement satisfied

file exists
    ≠ artifact role admitted
```

This would have prevented `unitSatisfaction` from being promoted based solely on requirement enumeration. The review found that the value established topology consistency but had no binding to implementations, scenarios, commands or evidence. 

# Expensive-call mitigation

## Content-addressed caches

| Operation            | Cache key                                               |
| -------------------- | ------------------------------------------------------- |
| GitHub issue fetch   | repository + issue + `updated_at` or body digest        |
| Skill read           | path + content digest                                   |
| Kernel read          | path + content digest                                   |
| Repository inventory | revision + worktree digest                              |
| `cue fmt`            | command + declared file digests                         |
| `cue vet`            | command + module/package inputs + file digests          |
| Fixture execution    | fixture ID + contract digest + runner version           |
| Generated context    | active unit + failure state + relevant artifact digests |

The #106 body should have been fetched once, normalized once, and projected down to the active child’s records. Reinjecting the entire 58-requirement matrix into subsequent model turns was unnecessary.

## Context projection

Instead of returning the full workbook state to Codex, the pre-hook should inject only:

```text
active unit
current phase
last failure signature
target definition
one relevant kernel analogue
allowed files
required next evidence
remaining failure budget
```

For the second semantic failure, the projected context could have been under a page rather than carrying the issue body, complete skill instructions and broad repository inventory again.

## Cost budgets

The workbook could track approximate costs by class:

```text
local cached read        0
local uncached read      1
focused validation       1
full package validation  3
GitHub/network fetch     4
large recursive search   4
broad patch + validation 5
```

Policies could then require stronger justification as cost increases:

```text
cost <= 1:
    normally allowed

cost 2–3:
    require active hypothesis

cost >= 4:
    require cache miss and explicit evidence need

repeated cost >= 4:
    deny unless repository state materially changed
```

# Recommended implementation shape

```text
marimo/workflows/codex/tool_loop/
├── controller.py          # pure transition function
├── workbook.py            # reactive inspection and operator UI
├── pre_tool.py            # thin hook adapter
├── post_tool.py           # thin hook adapter
└── .kb/
    ├── event.cue
    ├── state.cue
    ├── policy.cue
    ├── decision.cue
    └── fixtures/
```

The hot-path hooks should **not start a full interactive Marimo server for every tool call**. Instead:

```text
CUE contracts
    → projected Python types/adapters
    → pure controller transition

Marimo workbook
    → imports the same controller
    → visualizes and interrogates state reactively

hooks
    → invoke the controller headlessly
    → persist state under a session-specific runtime directory
```

This preserves one control model without imposing workbook startup and rendering costs on every tool invocation.

# Retrospective outcome for this session

With this controller in place, the likely progression would have been:

```text
1. Load #106
2. Detect parent matrix with no child unit
3. Stop and request/derive child implementation unit
```

Under an explicitly permitted exploratory mode:

```text
1. Admit kernel-only candidate scope
2. Permit kernel migration and focused fixtures
3. Record first semantic failure
4. Permit one targeted correction
5. Record second semantic failure
6. Trip circuit breaker
7. Export blocker report and clean checkpoint
```

The checkpoint could still have been committed, but with mechanically bounded status:

```text
candidate: true
requirementsTopologyValid: true
implementationAdmitted: false
activeChildUnit: absent
stopReason: second-semantic-failure
```

That would have converted the workbook from a passive notebook into a **stateful supervisory controller**, enforcing scope, retry discipline, evidence order and cost bounds that the model’s textual instructions failed to enforce.
---

## msg 3

---

## Recommended architecture

Use the marimo workbook as the **reactive control and evidence surface**, not as the enforcement boundary.

```text
CUE authority
     │ compile
     ▼
Workbook binding ───────────────┐
                                │
marimo UI ◄── event ledger ◄── hook gateway ◄── coding agent
   │                            │
   └── approvals/overrides ─────┘
                                │
                        isolated worktree
                                │
                          repository
```

Three separate planes:

1. **Authority plane** — closed CUE policy defining allowed tools, paths, commands, state transitions, and validators.
2. **Enforcement plane** — pre/post hooks around the agent’s actual tools, operating in a temporary Git worktree.
3. **Workbook plane** — marimo renders state, failures, diffs, evidence, and explicit human overrides.

Marimo’s current ACP client exposes filesystem read/write callbacks, permission handling, and tool-call notifications. It does not document a general-purpose hook API for intercepting every underlying coding-agent command. The current client advertises file read/write capabilities directly, while tool calls arrive as notification events. Therefore, filesystem operations can be intercepted at the ACP boundary, but shell and patch operations may require agent-native hooks or a sandbox/tool gateway closer to the agent.

## Control state machine

Every tool invocation becomes a transaction:

```text
PROPOSED
   │
   ▼
PRECHECKED ── reject ──► BLOCKED
   │
   ▼
EXECUTED_IN_SANDBOX
   │
   ▼
POSTCHECKED ── fail ───► QUARANTINED
   │
   ▼
ADMITTED
   │
   ▼
APPLIED_TO_WORKTREE
```

The agent never edits the primary worktree directly.

A complete record should contain:

```cue
#ToolTransaction: {
	runID:      #RunID
	sequence:   uint
	workbookID: #WorkbookID

	intent: {
		tool:      #ToolKind
		arguments: _
		cwd:       string
	}

	before: {
		head:        #CommitSHA
		worktreeSHA: #Digest
		fileDigests: [string]: #Digest
	}

	precheck: #HookEvaluation
	execution: #ToolObservation
	postcheck: #HookEvaluation

	decision: "blocked" | "quarantined" | "admitted"
}
```

The workbook reduces these immutable transaction records into the current session state.

## Handling each observed failure

| Failure                                      | Pre-hook control                                                                                                                        | Post-hook control                                                           |
| -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Incorrect working directory/path composition | Resolve repository root once; canonicalize every path; reject paths outside the bound root; forbid manually concatenated absolute paths | Compare actual touched paths with declared mutation scope                   |
| Wrong dependency-proof count                 | Generate expected nodes and edges from the authoritative dependency graph; do not accept hand-entered counts                            | Compare exact sets and edges, not cardinality alone                         |
| Unresolved conditional Booleans              | Require concrete output for exported reports; run `cue eval`/`cue vet -c` against the candidate before mutation                         | Reject any incomplete or non-concrete admission field                       |
| `close`/conjunction modeling failure         | Compile candidate schema in isolation before applying it; run focused closedness fixtures                                               | Execute unknown-field and claimant-injection probes                         |
| Unknown pattern field accepted               | Require every publication boundary to have a generated adversarial unknown-field probe                                                  | Reject unless each probe bottoms for the intended reason                    |
| Lexical self-reference                       | Parse and vet the candidate in a temporary file or worktree; detect cycles before replacement                                           | Run package-wide `cue vet` after the actual edit                            |
| Failed patch applications                    | Bind patch to file digest and exact anchors; perform dry-run; reject stale context                                                      | Verify expected hunks and resulting AST/content before admission            |
| zsh `path` shadowing                         | Execute hooks under a controlled environment; use `env -i` or a noninteractive shell; reserve dangerous shell identifiers               | Record executable resolution and assert required binaries remain resolvable |
| Formatting failure                           | Format candidate content before writing it                                                                                              | Run formatter check on the exact touched-file set                           |

## Specific controls

### 1. Paths: typed resolution rather than shell composition

The pre-hook receives:

```json
{
  "repo_root": "/repo/factory",
  "cwd": ".codex/skills/cue",
  "target": "contracts/lattice/s00/schema.cue"
}
```

It computes:

```text
canonical_target =
    realpath(repo_root / cwd / target)
```

Admission conditions:

```text
canonical_target starts with canonical_repo_root
target exists when operation requires existence
target is inside allowedMutationRoots
target digest matches expected preimage
```

Never let the agent construct:

```bash
"$PWD/$cwd/$path"
```

The gateway resolves paths independently.

### 2. Dependency proofs: sets before counts

Instead of:

```cue
len(dependencyProofs) == 218
```

derive canonical expected identities:

```cue
expectedContainmentProofs: [
	for requirementID, requirement in requirements
	for dependencyID in requirement.dependsOn {
		"\(requirementID):contains:\(dependencyID)"
	},
]

actualProofIDs: [for proof in dependencyProofs { proof.id }]

dependencyProofsComplete:
	list.SortStrings(expectedContainmentProofs) ==
	list.SortStrings(actualProofIDs)
```

Cardinality can remain as a diagnostic, but exact set equality becomes the gate.

### 3. CUE semantic failures: fail before repository mutation

For CUE edits, the gateway should run this sequence in a candidate worktree:

```text
write candidate
      ↓
cue fmt
      ↓
cue vet -c=false affected package
      ↓
cue vet -c concrete report package
      ↓
targeted adversarial probes
      ↓
package regression
```

Only then is the change copied or committed into the actual session worktree.

A semantic-failure controller can enforce the existing stop rule:

```cue
#FailurePolicy: {
	maxConsecutiveSemanticFailures: 2
	actionAtLimit:                   "block-writes"
	resetAfterSuccessfulValidation: true
}
```

This avoids the agent continuing through repeated schema-model failures.

### 4. Patch operations: compare-and-swap

Treat every patch as:

```text
expected file digest
+ expected anchor
+ transformation
+ expected postcondition
```

Example:

```cue
#PatchIntent: {
	path:          string
	expectedSHA256: #SHA256
	anchor: {
		before: string
		occurrences: 1
	}
	postcondition: {
		contains: string
	}
}
```

The hook rejects the patch before execution when:

* the file digest changed;
* the anchor is missing;
* the anchor is ambiguous;
* the patch does not apply cleanly.

After execution, it verifies the expected postcondition and parses the resulting file.

This turns three failed patch attempts into a single blocked transaction rather than three repository mutations.

### 5. Shell environment isolation

The zsh `path` problem is best prevented by refusing to inherit the interactive shell environment.

Run validation hooks through something equivalent to:

```bash
env -i \
  HOME="$HOME" \
  PATH="/usr/local/bin:/usr/bin:/bin" \
  LANG="C.UTF-8" \
  bash --noprofile --norc -euo pipefail ./hook.sh
```

For commands that must use zsh:

```bash
zsh -dfc '...'
```

The shell-command pre-hook can additionally reject assignments to reserved names:

```text
path
PATH
commands
status
pipestatus
fpath
```

A shell AST parser is preferable to regular expressions.

## Binding a session to a workbook

Use an immutable binding record outside the notebook:

```cue
package workbook

binding: {
	workbookID: "lattice-s00"
	notebook:   "workbooks/lattice_s00.py"

	repository: {
		root:   "."
		remote: "fatb4f/factory"
	}

	authority: {
		path:   "contracts/workbooks/lattice-s00.cue"
		sha256: "..."
	}

	allowedMutationRoots: [
		".codex/skills/cue/contracts/lattice/s00",
	]

	validators: [
		"cue-format",
		"cue-package-vet",
		"s00-concrete-report",
		"s00-adversarial-fixtures",
	]
}
```

At session start, the gateway resolves and freezes:

```text
workbook ID
authority digest
repository root
initial HEAD
agent identity/version
CUE version
run ID
```

Every transaction repeats those bindings. A changed authority digest invalidates the session rather than silently changing its policy.

## Workbook layout

The marimo notebook could contain these reactive sections:

### Authority

Displays:

* contract digest;
* repository and HEAD;
* allowed mutation roots;
* validation graph;
* stop policy;
* current agent/session identities.

### Proposed action

Shows the latest tool intent before execution:

```text
tool: shell
cwd: .codex/skills/cue
command: cue vet -c ./contracts/lattice/s00/report
risk: read-only
precheck: admitted
```

### Transaction ledger

One row per invocation:

| Seq | Tool  | Precheck | Execution | Postcheck          | Decision    |
| --: | ----- | -------- | --------- | ------------------ | ----------- |
|  17 | patch | pass     | exit 0    | CUE self-reference | quarantined |
|  18 | shell | blocked  | —         | —                  | wrong cwd   |
|  19 | write | pass     | exit 0    | all gates pass     | admitted    |

### Failure controller

Tracks:

```text
consecutive semantic failures
patch conflicts
environment failures
scope violations
unresolved CUE values
```

At the configured threshold, the gateway switches to:

```text
read-only diagnosis mode
```

### Evidence surface

Provides the exact:

* command;
* cwd;
* environment digest;
* stdout/stderr;
* exit status;
* before/after file digests;
* Git diff;
* validator results;
* CUE evaluation output.

## Reactive-model constraint

The notebook should consume immutable event snapshots rather than mutate a shared Python list. Marimo derives its dependency DAG from cell definitions and references, but it does not react to in-place object mutation such as `list.append()` or attribute assignment. A new event-list value, sequence counter, or ledger-file digest should therefore be produced for each update.

For example:

```python
events = read_events(run_id)       # returns a new tuple
event_revision = ledger_digest()   # changes after every append
session_state = reduce_events(events, event_revision)
```

Marimo will then re-run dependent status, table, and validation cells deterministically. Its reactive execution is DAG-based, and dependent cells run from the latest definitions.

## Where the hooks should live

### Current practical deployment

```text
marimo
  └─ WebSocket
      └─ stdio-to-ws
          └─ hooked ACP/agent wrapper
              └─ Codex/Claude/Gemini adapter
                  └─ sandboxed tool executor
```

Marimo currently connects to external agents through ACP adapters and can mark cells stale or autorun them when agent edits are saved. The agent feature remains experimental, and custom-agent support is still described as forthcoming.

Therefore:

* **Do not put enforcement only in notebook cells.**
* Intercept ACP filesystem callbacks where possible.
* Use agent-native pre/post hooks for shell and patch calls.
* Otherwise place the agent inside an OS-level sandbox whose executable and filesystem operations are mediated.
* Send all resulting events to the workbook ledger.

## Minimal implementation sequence

1. Define `#WorkbookBinding`, `#ToolIntent`, `#HookEvaluation`, `#ToolObservation`, and `#ToolTransaction` in CUE.
2. Build a small Go gateway that loads the compiled contract and creates an isolated Git worktree per run.
3. Implement `preRead`, `preWrite`, `preShell`, `prePatch`, and corresponding post-hooks.
4. Append canonical JSONL transaction records.
5. Build a marimo workbook that reduces and visualizes that ledger.
6. Add manual `approve`, `reject`, and `enter-read-only-mode` controls.
7. Bind the ACP session and gateway to the workbook ID and authority digest.

The main control invariant is:

```text
No tool result reaches the repository merely because the command succeeded.

A result reaches the repository only when:
preconditions ∧ execution success ∧ postconditions ∧ evidence completeness
```

That would turn the unstable recovery path into a series of isolated, diagnosable, fail-closed transactions.
---

## msg 4

---

# Proposed control architecture

A **single source-controlled Marimo workbook**, invoked in different modes, could have acted as the stateful controller around Codex tool calls:

```text
Codex proposes tool call
        │
        ▼
PreToolUse hook
        │
        ▼
Marimo policy workbook: mode=pre
  ├─ bind authority/repository state
  ├─ classify operation
  ├─ check cache and failure history
  ├─ enforce scope and cost budgets
  └─ allow | rewrite | ask | deny
        │
        ▼
Tool executes
        │
        ▼
PostToolUse hook
        │
        ▼
Marimo policy workbook: mode=post
  ├─ classify observation
  ├─ compare pre/post subjects
  ├─ update persistent ledger/cache
  ├─ detect repeated failure loops
  └─ inject bounded context for next action
```

The workbook would be the **controller, observer, cache and debugging surface**. It should not become semantic authority. CUE contracts and the admitted runner would remain responsible for semantic verdicts.

Codex already provides the necessary hook surfaces. `PreToolUse` receives the tool name, input, working directory, session and turn identifiers; it can block a call, rewrite its input, or add model context. `PostToolUse` receives both the original input and the tool response and can block continuation or return corrective context.   The output protocol exposes `permissionDecision`, `updatedInput`, and `additionalContext` for pre-hooks, and additional context for post-hooks.

## 1. Bind every call to a semantic subject

At session start, or on the first pre-hook call, the workbook would calculate:

```python
subject_key = sha256(canonical_json({
    "policy_version": policy_digest,
    "authority": authority_file_digests,
    "head": head_commit,
    "index_tree": index_tree_digest,
    "worktree": relevant_file_digests,
    "tool": canonical_tool_name,
    "input": normalized_tool_input,
    "toolchain": {
        "cue": cue_version,
        "go": go_version,
        "workbook": workbook_digest,
    },
}))
```

The important distinction is:

```text
request identity = tool + normalized arguments

subject identity = request identity + all state that can change its result
```

This prevents incorrect caching while allowing exact repeated calls to be suppressed.

The existing requirements already state the key invariant: pre- and post-operation source digests must agree, and source changes must suppress semantic facts. They also state that CLI failure cannot prove semantic bottom. 

## 2. `PreToolUse` as the controller

### Authority revision fence

Before any mutation or semantic validation:

```text
current authority digest == session-bound authority digest
```

In the analyzed session, `tmp/emergency-slice.v0.2.md` changed during execution. A pre-hook should then have denied further semantic claims:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Authority changed since the session subject was bound.",
    "additionalContext": "Re-read the revised slice, recompute scope closure, and establish a new subject."
  }
}
```

This turns an easily missed status change into a hard state transition:

```text
BOUND → AUTHORITY_CHANGED → REBIND_REQUIRED
```

### Duplicate-failure suppression

The workbook ledger would retain:

```python
FailureRecord(
    request_digest=...,
    subject_digest=...,
    failure_class="cue-syntax",
    diagnostic_digest=...,
    attempts=3,
)
```

The next identical request under the identical subject would be denied:

```text
same request
AND same subject
AND previous deterministic failure
AND no relevant source changed
→ do not execute
```

The hook would inject the cached result and the required state change:

```text
This exact validation has already failed against the same source tree.
Last failure: eval/probe.cue syntax error.
Modify that file or change the command before retrying.
```

This would have prevented several nearly identical format/vet/export calls.

### Semantic-operation classification

Every command would first be classified:

```text
read
structural_gate
semantic_probe
mutation
publication
environment_probe
unknown
```

Policy examples:

| Proposed call                                     | Pre-hook response                             |
| ------------------------------------------------- | --------------------------------------------- |
| `cue fmt --check`                                 | Allow as structural evidence                  |
| `cue vet`                                         | Allow as structural evidence                  |
| `cue eval authority & mutation`, expecting exit 1 | Mark diagnostic-only or rewrite to `cueprobe` |
| Sixteen shell probes in a loop                    | Rewrite to one runner request                 |
| `git commit` with `AM`/`MM` paths                 | Deny                                          |
| Broad `ALL_TOOLS` dump                            | Deny and request targeted discovery           |
| Same failed validation without source change      | Return cached failure                         |

The session’s 16 exit-code probes should never have been permitted to acquire semantic labels such as `*-bottom: PASS`. The requirements explicitly separate semantic-bottom observations from CLI failure. 

### Input rewriting and batching

A pre-hook can return an `updatedInput`, so the workbook could replace repetitive shell fan-out with a bounded command. Codex resolves competing input rewrites and uses the last completed valid rewrite.

For example:

```text
Proposed:
for expression in 16 expressions:
    cue eval ... -e expression

Rewritten:
cueprobe run --request /tmp/unit-a-probes.json \
             --output /tmp/unit-a-observations.json
```

Benefits:

* one process startup;
* one module load;
* one source digest calculation;
* one structured observation bundle;
* no diagnostic parsing;
* no repeated model/tool round trips.

### Worktree/index coherence gate

Before `apply_patch`, staging, committing, or final validation, derive:

```python
RepoState(
    staged_paths=...,
    unstaged_paths=...,
    overlapping_paths=staged_paths & unstaged_paths,
)
```

Policy:

```text
overlapping staged/unstaged paths
AND proposed action is commit/publication/final-verdict
→ deny
```

The session ended with multiple `AM` and `MM` paths. A hook could have prevented any claim that the index represented the reviewed candidate.

### Cost envelope

The workbook could assign an estimated call cost:

```python
cost = (
    process_start_weight
    + input_bytes_weight
    + requested_output_tokens
    + expected_fanout * fanout_weight
    + network_call_weight
)
```

Then enforce:

```text
duplicate read with unchanged subject          → cache
output limit above policy                      → rewrite
tool-schema enumeration without name filter   → deny
more than N probes through shell               → batch
full repository diff when path set is known    → narrow
```

The huge `ALL_TOOLS` enumeration is a clear example: the pre-hook could have rewritten it to a targeted tool search rather than emitting tens of thousands of truncated tokens.

## 3. `PostToolUse` as observer and state estimator

### Typed outcome classification

The post-hook would convert raw results into a closed outcome vocabulary:

```text
success
structural_failure
semantic_observation
semantic_bottom
subject_changed
timeout
infrastructure_failure
protocol_failure
policy_violation
```

Critically:

```python
if tool == "exec" and exit_code != 0:
    outcome = "structural_failure"
    # Never infer semantic_bottom from stderr or exit code.
```

Only the admitted semantic runner could produce a candidate `semantic_bottom` fact, and CUE would still derive the final verdict.

### Pre/post digest fence

After execution:

```python
if pre_subject.source_digests != current_source_digests:
    observation = {
        "outcome": "subject_changed",
        "semanticFacts": None,
    }
```

This would have caught:

* authority changes;
* concurrent edits;
* commands that mutate files while also being treated as validators;
* stale validations following patch application.

### Failure clustering

Rather than presenting every failure as new context, the workbook would cluster by:

```python
failure_signature = hash({
    "stage": stage,
    "tool": tool,
    "normalized_diagnostic": diagnostic_class,
    "affected_paths": paths,
})
```

A Marimo view could show:

| Signature                        | Count | Last state change | Next admissible action                          |
| -------------------------------- | ----: | ----------------- | ----------------------------------------------- |
| CUE syntax in `eval/probe.cue`   |     3 | None              | Edit syntax                                     |
| Conflict fixture bottoms package |     2 | Fixture edited    | Separate operand fixture from destructive probe |
| Missing runner                   |     4 | None              | Implement runner; stop shell simulation         |
| Authority changed                |     1 | Slice modified    | Rebind session                                  |

This makes the control failure visible: repeated calls are no longer interpreted as progress.

### Corrective context injection

Post-hooks can supply additional model context.  A failed destructive fixture validation could therefore return:

```text
The package fails because the destructive conjunction is loaded as ordinary
package data. Do not remove the kernel binding and retry the same package gate.
Keep independently valid operands in the fixture and execute the destructive
conjunction through the admitted runner.
```

That would have prevented the add–fail–remove loop around `#DestructiveConflict`.

## 4. Why Marimo is suitable

A Marimo notebook is a reactive dataflow graph, so changing the event, repository digest, or policy input reruns only dependent cells rather than an opaque end-to-end script. It can also be executed programmatically with `app.run(defs=...)`, allowing the same source to serve hook mode and an interactive diagnostic UI. ([docs.marimo.io][1])

The physical surface could remain one admitted file:

```text
marimo/workflows/codex/tool_guard.py
```

with modes:

```text
--phase pre
--phase post
--phase report
```

Logical cell groups:

```text
hook input
→ protocol validation
→ repository snapshot
→ authority binding
→ command classification
→ cache lookup
→ policy decision
→ observation classification
→ ledger update
→ hook JSON projection
→ interactive views
```

For expensive deterministic calculations, use persistent caching rather than only in-process caching. Marimo supports both memory and persistent cache mechanisms, and expensive execution can be explicitly gated. ([docs.marimo.io][2])

A cache entry should be reusable only when all relevant subject components match:

```python
@mo.persistent_cache
def evaluate_read_only_call(
    request_digest: str,
    authority_digest: str,
    source_digest: str,
    environment_digest: str,
    policy_digest: str,
) -> Observation:
    ...
```

Never cache mutations, permission decisions, GitHub writes, or results whose subjects cannot be reconstructed.

## 5. Illustrative hook binding

Codex hook configuration supports matcher groups and command handlers with timeouts and status messages.

```toml
[[hooks.PreToolUse]]
matcher = "exec"
hooks = [{
  type = "command",
  command = "uv run python marimo/workflows/codex/tool_guard.py --phase pre",
  timeout = 5,
  statusMessage = "Checking repository and tool policy"
}]

[[hooks.PostToolUse]]
matcher = "exec"
hooks = [{
  type = "command",
  command = "uv run python marimo/workflows/codex/tool_guard.py --phase post",
  timeout = 10,
  statusMessage = "Classifying and recording tool result"
}]
```

Equivalent matcher groups would cover patching and GitHub tools. The exact matcher names should be pinned to the canonical tool names exposed by the Codex version in use.

For lower latency, the hooks could call a local Unix-socket process that imports the Marimo app once. The simpler first implementation would start it per hook and rely on persistent cache storage.

# Direct mitigation of this session

| Session failure                            | Workbook control                                               |
| ------------------------------------------ | -------------------------------------------------------------- |
| Wrong path/workdir and immediate retry     | Resolve paths pre-call; cache deterministic failure            |
| Repeated format/vet/export loops           | Deny identical failed request until source digest changes      |
| Sixteen exit-code “bottom” probes          | Semantic-class gate; batch through admitted runner             |
| Large tool-schema dumps                    | Output/fan-out budget; rewrite to targeted discovery           |
| Authority changed mid-session              | Pre/post digest fence; force rebind                            |
| Destructive fixture added then removed     | Failure-cluster guidance preserving runner boundary            |
| Hard-coded `provisional` admission switch  | Static policy warning: admission must derive from observations |
| Staged and unstaged versions diverged      | Block final validation, commit and publication                 |
| Repeated repository rereads                | Content-addressed read cache                                   |
| Tool result context repeatedly reprocessed | Typed observation ledger and concise injected context          |

The central control rule would have been:

```text
No relevant state change
    ⇒ no identical expensive retry.

State changed during observation
    ⇒ no semantic fact.

Wrong observation channel
    ⇒ no semantic classification.

Mixed candidate state
    ⇒ no final validation or publication.
```

That would have reduced both execution count and model-context churn while making the remaining tool calls materially informative.

[1]: https://docs.marimo.io/api/app/ "App - marimo"
[2]: https://docs.marimo.io/guides/expensive_notebooks/ "Expensive notebooks - marimo"
---
