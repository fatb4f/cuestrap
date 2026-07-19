# Cuestrap Governed Repository Controller

## Architecture and Contract Proposal

| Field | Value |
|---|---|
| Status | Draft for review |
| Scope | Normalization of all concepts currently expressed under `docs/` |
| Intended audience | Architecture, contract, implementation, security, and agent-control reviewers |
| Normative language | `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT`, and `MAY` are used as requirement terms |
| Primary authorities | OSCAL lifecycle resources, CUE constraints, and Git object identity |
| Primary controlled plant | Governed repository state and its linked governance/evidence graph |

## Overview

Cuestrap is a proof-carrying controller for governed repository state. It combines OSCAL lifecycle semantics, CUE admission contracts, and Git object identity so that every proposal, decision, effect, observation, and publication can be traced to an immutable source snapshot and a pinned contract revision.

The architecture separates authority from execution:

- **OSCAL** defines governance objects, lifecycle identity, control relationships, assessments, findings, risks, and remediation state.
- **CUE** defines the executable contract lattice: structural narrowing, semantic closure, authorization, transition guards, evidence requirements, and effect bounds.
- **Git** records exact content, checkpoints, receipts, accepted state, and authorized publication.
- **System A** owns authority resolution, admission, capability narrowing, result validation, settlement, and publication.
- **System B** proposes, observes, evaluates, and executes only through an admitted bounded capability.
- **Marimo** owns the live reactive Python DAG; DuckDB, GUAC, generated types, policy engines, and LLM runtimes remain projections or bounded adapters.

### Implementation status boundary

The repository currently implements only a **partial System B foundation**:

| Implemented on `main` | Required before System B is complete |
|---|---|
| Main target workbook and typed workbook adapter | Session-scoped rollout/JSONL controller workbook |
| One-operation Marimo controller with identity-bound request, claim, release, and receipt records | Committed-complete-prefix tailing of the Codex rollout JSONL |
| `PreToolUse` and `PostToolUse` hook ingress with local pre/post correlation for recognized calls | Reconciliation of provisional hook ingress with committed rollout records |
| Hook-local `state.json` and diagnostic `events.jsonl` ledger | DuckDB raw, normalized, causal, continuity, checkpoint, and evidence-manifest projections |
| Provisional Python anti-churn predicates | Native CUE System B readiness, continuity, conformance, and effect-attribution conclusions |
| Typed operation execution through a bounded workbook capability | Exact parent composition of System A, System B, tactical, and authorization conclusions |

The hook-local ledger MUST be treated as provisional diagnostic evidence. It MUST NOT be described as the Codex rollout ledger, a complete streaming analytics implementation, or a complete System B control plane.

The governing control loop is:

```text
observe immutable state
    → construct and freeze a candidate proposal
    → qualify identity, authority, evidence, state, and effects
    → grant an exact bounded capability
    → execute and collect receipts
    → validate postconditions and settlement
    → commit accepted OSCAL state and evidence to Git
```

This document specifies that authority allocation, the operation and transition contracts, checkpoint and settlement semantics, the constrained Git mutation boundary, the reactive playbook model, adapter-generation rules, conformance properties, and the implementation decisions still requiring review.

## Table of contents

### Foundation

- [1. Proposal](#1-proposal)
- [2. Review objectives](#2-review-objectives)
- [3. Non-goals](#3-non-goals)
- [4. Core invariants](#4-core-invariants)
- [5. Authority hierarchy](#5-authority-hierarchy)
- [6. Identity model](#6-identity-model)
- [7. Canonical domain model](#7-canonical-domain-model)
- [8. Controlled plant and state model](#8-controlled-plant-and-state-model)
- [9. System decomposition](#9-system-decomposition)

### Transition and execution contracts

- [10. Snapshot and checkpoint model](#10-snapshot-and-checkpoint-model)
- [11. Transition protocol](#11-transition-protocol)
- [12. Admission law](#12-admission-law)
- [13. Effect model](#13-effect-model)
- [14. Authorization model](#14-authorization-model)
- [15. Evidence and provenance boundary](#15-evidence-and-provenance-boundary)
- [16. System B runtime telemetry and streaming analytics](#16-system-b-runtime-telemetry-and-streaming-analytics)
- [17. Settlement](#17-settlement)
- [18. Reactive playbook model](#18-reactive-playbook-model)
- [19. Failure, correction, extraction, and continuity](#19-failure-correction-extraction-and-continuity)
- [20. Constrained Git mutation and publication boundary](#20-constrained-git-mutation-and-publication-boundary)

### Services, projections, and adapters

- [21. Supply-chain and evidence services](#21-supply-chain-and-evidence-services)
- [22. Generation and adapter architecture](#22-generation-and-adapter-architecture)
- [23. Python and LLM adapter profile](#23-python-and-llm-adapter-profile)
- [24. Structural validation and compatibility](#24-structural-validation-and-compatibility)
- [25. Query and graph materialization](#25-query-and-graph-materialization)

### Delivery and review

- [26. End-to-end reconciliation loop](#26-end-to-end-reconciliation-loop)
- [27. Minimal vertical slice](#27-minimal-vertical-slice)
- [28. Proposed implementation stages](#28-proposed-implementation-stages)
- [29. Required conformance properties](#29-required-conformance-properties)
- [30. Review decisions required](#30-review-decisions-required)
- [31. Source normalization map](#31-source-normalization-map)
- [32. Compact normative formulation](#32-compact-normative-formulation)
- [33. Proposed decision](#33-proposed-decision)

## 1. Proposal

Cuestrap SHOULD be implemented as a **governed repository controller** with the following compact contract:

```text
Cuestrap
    = OSCAL lifecycle semantics
    + CUE executable contracts
    + Git immutable state and transition ledger
    + one authority/admission plane
    + one bounded proposal/execution plane
    + one constrained mutation boundary
    + proof-carrying observations, decisions, and publications
    + generated or bounded adapters that cannot widen authority
```

The OSCAL Component Definition, specialized by a Cuestrap CUE profile, is the canonical capability and operation publication surface. It is not paired with an independently authored API authority.

The architecture MUST distinguish three kinds of truth:

1. **Semantic and governance truth** — OSCAL resources and stable OSCAL identities.
2. **Admissibility truth** — CUE constraints, relation closure, authorization rules, transition guards, and publication requirements.
3. **State and content truth** — immutable Git objects, digests, commits, and qualified lifecycle artifacts.

All other surfaces—including Marimo, DuckDB, GUAC, Pydantic, JSON Schema, OpenAPI, GraphQL, MCP, CLI, DSPy, model providers, constrained decoders, and policy engines—MUST be subordinate projections, evaluators, or bounded adapters.

## 2. Review objectives

This proposal resolves five recurring ambiguities in the source documents:

1. **OSCAL versus CUE authority** — OSCAL owns lifecycle objects and semantic identity; CUE owns executable admissibility. Neither is reducible to the other.
2. **Git versus runtime state** — Git and committed OSCAL artifacts are authoritative. Runtime databases and notebook state are projections.
3. **Marimo authority** — Marimo owns the actual live Python dependency graph and its execution semantics, but it does not own governance policy, authorization, or publication.
4. **Agent discretion** — models and DSPy rank or instantiate pre-admitted alternatives; they do not create operational policy or authorize effects.
5. **Component Definition as API** — the official OSCAL Component Definition remains structurally valid OSCAL; Cuestrap adds a CUE-governed capability/operation profile using OSCAL identities and extension points. Generated transports are projections of that combined contract.

## 3. Non-goals

The initial architecture is not:

- a general-purpose autonomous-agent framework;
- a parallel workflow database that competes with Git;
- an independently authored OpenAPI, GraphQL, Python, or finite-state-machine authority;
- a system in which reactive recomputation can trigger unqualified effects;
- a semantic graph whose derived node IDs replace OSCAL UUIDs or Git identities;
- a model-driven replanner with unrestricted action synthesis;
- a claim that every OSCAL concept must be forced into an HTTP endpoint shape.

## 4. Core invariants

The following invariants are normative.

### 4.1 Single authority chain

```text
official OSCAL structural model
        ↓
resolved OSCAL lifecycle closure
        ↓
Cuestrap CUE profile and semantic constraints
        ↓
qualified operation or transition
        ↓
bounded execution capability
        ↓
execution receipt and evidence binding
        ↓
validated resulting OSCAL closure
        ↓
Git commit and authorized reference publication
```

A downstream projection MUST NOT redefine an upstream meaning.

### 4.2 Frozen-before-qualified

Every proposal that may influence authority, graph topology, repository mutation, assessment conclusions, or publication MUST be normalized, frozen, and content-addressed before qualification.

### 4.3 No authority by successful execution

Successful model inference, notebook execution, policy evaluation, tool invocation, or shell exit status MUST NOT by itself establish admission, evidence, settlement, or publication authority.

### 4.4 No ambient mutation authority

Effectful adapters MUST receive a narrowed capability bound to an exact operation, subject, source snapshot, contract revision, effect set, and execution epoch. They MUST NOT receive ambient repository or provider authority when a narrower capability is possible.

### 4.5 No derived parallel authority

The following are explicitly non-authoritative:

- mutable branch names without a resolved commit;
- GUAC node IDs;
- DuckDB rows and views;
- Marimo in-memory values;
- generated Pydantic classes;
- JSON Schema, OpenAPI, or GraphQL projections;
- DSPy scores or model recommendations;
- provider-native structured-output acceptance;
- Minder or other policy-engine conclusions before binding and qualification.

## 5. Authority hierarchy

| Tier | Authority | Canonical responsibility |
|---|---|---|
| 0 | Git OIDs and cryptographic digests | Exact content, tree, commit, artifact, receipt, and attestation identity |
| 1 | Official OSCAL resources and UUIDs | Governance objects, lifecycle identity, imports, links, controls, implementations, assessments, findings, risks, remediation |
| 2 | CUE contracts and Cuestrap profiles | Structural narrowing, semantic relations, operation contracts, authorization, state transitions, evidence requirements, effect bounds |
| 3 | Qualified operational evidence | Observations, receipts, attestations, SBOMs, test results, counterexamples, Assessment Results |
| 4 | Materialized query projections | GUAC, DuckDB, indexes, caches, analytical views |
| 5 | Generated and transport projections | Go, Python, Pydantic, Hypothesis, JSON Schema, OpenAPI, GraphQL, CLI, MCP, reports, dashboards |

A higher-numbered tier MAY be regenerated or replaced. It MUST NOT redefine a lower-numbered tier.

## 6. Identity model

Cuestrap MUST preserve distinct identity domains rather than collapse them.

| Identity | Meaning |
|---|---|
| OSCAL UUID | Stable semantic and lifecycle identity |
| CUE-qualified identifier | Stable contract vocabulary identity |
| Git blob OID | Exact atomic content identity |
| Git tree OID | Exact package or component closure |
| Git commit OID | Coherent repository-state identity |
| pURL or VCS URI | Software/package identity |
| Attestation subject digest | Exact claim-subject identity |
| GUAC node ID | Derived local graph-index identity |

A complete authoritative reference SHOULD include enough coordinates to prevent mutable-pointer ambiguity:

```cue
#AuthoritativeReference: {
	repository: string & != ""
	commit:     #Digest
	path:       string

	blob?: #Digest
	tree?: #Digest

	oscalUUID?: string
	cueID?:     string
}
```

A branch such as `main` MAY be used for discovery, but MUST be resolved to an immutable commit before qualification.

Identity equivalence MUST be declared or admitted by CUE policy. GUAC or another correlation engine MAY propose equivalence evidence but MUST NOT establish canonical equivalence independently.

## 7. Canonical domain model

### 7.1 OSCAL lifecycle roles

Cuestrap SHOULD use OSCAL models as one governed lifecycle:

| OSCAL model | Cuestrap role |
|---|---|
| Catalog | Governance vocabulary and required guarantees |
| Profile | Selected, parameterized, and narrowed requirements |
| Component Definition | Reusable governed capabilities and operation publication |
| System Security Plan | Concrete component, deployment, responsibility, and inheritance binding |
| Assessment Plan | Evaluation contract: subjects, tasks, inputs, predicates, and evidence requirements |
| Assessment Results | Qualified activities, observations, findings, and risks |
| POA&M | Corrective transition, milestone, evidence, and reassessment lifecycle |

### 7.2 Component Definition API profile

The phrase “Component Definition is the API” is normalized as follows:

> The official OSCAL Component Definition is the canonical capability publication resource. A Cuestrap CUE profile overlays a closed operation contract onto OSCAL-identified components, capabilities, control implementations, properties, links, and extension points. All generated callable surfaces derive from that combined OSCAL/CUE closure.

This avoids two invalid extremes:

- treating the Component Definition as mere prose linked to a separate API authority;
- claiming that arbitrary operation fields are native official OSCAL fields when they are actually Cuestrap profile semantics.

### 7.3 Operation contract

The canonical operation model SHOULD expose at least the following contract:

```cue
#OperationMode: "query" | "command" | "transition"

#Operation: {
	operationID: string & != ""
	mode:        #OperationMode

	input:  _
	output: _
	errors: [string]: _

	reads:  [...#ResourceSelector]
	writes: [...#MutationClass]

	requires: [...#Assertion]
	ensures:  [...#Assertion]

	authorization: #AuthorizationPolicy
	controlRefs:   [...#ControlReference]

	effects: {
		class:   #EffectClass
		allowed: [...#Effect]
		forbidden?: [...#Effect]
	}

	evidence: {
		required: [...#EvidenceRequirement]
		produces: [...#EvidenceType]
	}

	transition?: {
		from:       #StateConstraint
		event:      string & != ""
		to:         #StateConstraint
		invariants: [...#Assertion]
	}
}
```

An operation MAY project to a Go method, CLI command, MCP tool, HTTP endpoint, workflow action, assessment procedure, evidence collector, Git mutation, policy query, remediation procedure, or human-governed transition.

The operation contract—not the transport—defines meaning.

## 8. Controlled plant and state model

The controlled plant is the governed repository graph:

```text
RepositoryState
├── immutable Git object graph
├── references and publication pointers
├── index, worktree, and untracked workspace state
├── proposal and conflict graph
├── pull-request, review, and check state
├── OSCAL governance and lifecycle graph
├── evidence, SBOM, provenance, and attestation graph
└── actor, role, trust-epoch, and publication context
```

The current authoritative lifecycle state MUST be reconstructible as a deterministic fold over:

```text
Git history
+ committed OSCAL lifecycle artifacts
+ qualified transition decisions
+ qualified execution and publication receipts
```

A runtime database MAY accelerate reconstruction, but MUST be disposable.

## 9. System decomposition

### 9.1 System A — authority, target, ledger, and admission plane

System A owns:

- authoritative Git and committed OSCAL state;
- desired-state publication;
- pinned contract revisions;
- actor and authority context;
- frozen proposal registry;
- transition admission or rejection;
- narrowed capability issuance;
- returned-result validation;
- settlement and publication decisions;
- accepted reference updates.

System A MUST be the only plane that can publish a candidate result as authoritative repository state.

### 9.2 System B — proposal, telemetry, evaluation, and bounded execution plane

System B owns:

- candidate proposals and bounded playbook instantiations;
- the session-scoped runtime observation plane;
- mechanically normalized Codex rollout records;
- provisional hook-ingress reconciliation;
- dispatch, terminal-result, and operation-receipt correlation;
- pending-operation, continuity-epoch, and execution-conformance projections;
- test and assessment execution;
- evidence collection;
- remediation execution under granted capability;
- counterexamples and diagnostics;
- execution receipts;
- candidate resulting state.

System B runtime evidence MUST preserve this source hierarchy:

```text
Codex rollout JSONL committed complete prefix
    = primary System B runtime ledger

operation-controller request, binding, claim, release, and receipt records
    = authoritative controller-side execution records

PreToolUse and PostToolUse hook ingress
    = provisional low-latency observations pending reconciliation

DuckDB relations and Marimo values
    = reconstructable analytical projections
```

System B MUST NOT:

- redefine policy or contract meaning;
- widen its capability;
- repair or manufacture evidence to satisfy closure;
- promote provisional hook ingress into committed runtime truth without reconciliation;
- mutate protected state outside the grant;
- publish authoritative state;
- treat raw output or a DuckDB query result as qualified evidence.

### 9.3 Marimo — live reactive execution and inspection plane

The architecture uses three distinct Marimo lifetimes:

| Workbook | Lifetime | Responsibility |
|---|---|---|
| Main CUEstrap workbook | Long-lived | System A target, implementation, and interactive experiment surface |
| Rollout/JSONL controller workbook | Session- or rollout-scoped | System B committed-prefix ingestion, hook reconciliation, DuckDB projection, continuity, and evidence-manifest construction |
| Operation-controller workbook | One bounded action | Identity-bound pre-state, one-use effect, post-state, and durable execution receipts |

Marimo is authoritative for the actual live Python dependency graphs it constructs:

- cell dependency analysis;
- invalidation;
- scheduling;
- reactive execution;
- stale-state propagation;
- graph settlement.

The rollout controller MUST be reconstructable from the committed raw source prefix, its qualified workbook revision, controller receipts, and projection receipts. The main workbook MUST NOT supervise or authorize its own mutations. The operation workbook MUST remain one-use and capability-bound.

Marimo is not authoritative for:

- governance semantics;
- operation admission;
- actor authorization;
- evidence qualification;
- System B readiness, continuity, conformance, or effect-attribution conclusions;
- Git publication.

A CUE-admitted playbook MAY compile to a bounded Marimo source mutation. Marimo then reconstructs and executes the resulting DAG.

### 9.4 DuckDB — required System B analytical materialization

The first complete System B implementation MUST use DuckDB to maintain incremental, queryable projections of:

- immutable raw-record coordinates and digests;
- committed rollout prefixes and source generations;
- mechanically normalized runtime events;
- provisional hook ingress and reconciliation status;
- proposed, effective, dispatched, terminal, and receipted action correlations;
- pending and abandoned operations;
- continuity and trust epochs;
- operation-base, prior-settled, and candidate deltas;
- evidence manifests and projection receipts;
- historical evaluation corpora and settlement metrics.

DuckDB MUST remain reconstructible from authoritative records. SQL and materialized views MUST NOT emit authoritative `approve`, `eligible`, `conformant`, `settled`, or equivalent semantic conclusions. They provide closed facts to native CUE evaluation.

### 9.5 DSPy and models — bounded proposal/ranking plane

DSPy MAY:

- compile model-facing programs;
- rank a CUE-derived eligible playbook subset;
- score candidate mappings or transitions;
- report matched signals, conflicts, uncertainty, or abstention;
- optimize prompts, demonstrations, and model parameters against admitted metrics.

DSPy and models MUST NOT:

- create a new playbook during execution;
- remove a precondition;
- widen authority or effects;
- reinterpret missing evidence as approval;
- change the operation objective;
- mutate the repository or Marimo graph directly;
- publish findings, risks, or state.

### 9.6 Parent authority

A human or external authority MUST authorize material changes outside the delegated operation envelope, including changes to:

- objective;
- authority scope;
- accepted risk;
- external resources;
- operation topology;
- execution contract.

Such a change MUST suspend or terminate the current bounded operation and start a new operation contract.

### 9.7 Current implementation boundary

The current repository contains the main workbook, typed workbook adapter, operation-controller workbook, hook-local supervisor state, and a diagnostic append-only hook ledger. It does not yet contain the rollout/JSONL controller workbook or DuckDB dependency and schema required by this proposal.

No implementation report MAY claim complete System B supervision, streaming analytics, readiness, continuity, conformance, effect attribution, or settlement until Section 16 is implemented and qualified end to end.

## 10. Snapshot and checkpoint model

Every bounded operation MUST use three distinct immutable anchors.

```cue
#OperationAnchors: {
	operationBase: #RepositorySnapshot
	priorSettled:  #RepositorySnapshot
	candidate:     #RepositorySnapshot
}
```

### 10.1 Operation base

The operation base is the admitted repository snapshot at operation start. It is the pre-operation last-known-good state.

If relevant initial state is dirty, untracked, or external, startup MUST either capture an explicit qualified base checkpoint or reject the operation.

### 10.2 Prior settled checkpoint

The prior settled checkpoint is the most recent candidate that completed execution, postcondition validation, evidence qualification, and settlement.

It advances only after settlement.

### 10.3 Candidate checkpoint

The candidate checkpoint is the exact program, repository tree, relevant projected state, and evidence prefix currently under evaluation.

A rejected, failed, or indeterminate candidate remains durable evidence but MUST NOT advance `priorSettled`.

### 10.4 Required deltas

Every transition evaluation SHOULD receive:

```text
localTransitionDelta
    = candidate − priorSettled

cumulativeOperationDelta
    = candidate − operationBase

priorSettledCumulativeDelta
    = priorSettled − operationBase
```

These deltas answer different questions and MUST NOT be conflated.

### 10.5 Two-record checkpointing

Every authority-bearing evaluation SHOULD produce two immutable records:

1. **Candidate checkpoint or commit** — captures the exact program/tree, relevant state projections, operation base, prior settled anchor, DAG revision, objective revision, evidence-prefix identity, and evaluator identity.
2. **Decision receipt** — binds the candidate to its qualification disposition, reasons, eligible-playbook-set digest, selected playbook when applicable, resulting graph revision, and eventual settlement status.

The qualification verdict MUST NOT be retroactively written into the candidate record. The candidate establishes what was evaluated; the decision receipt establishes what was concluded about it.

A new qualification epoch SHOULD close when a material authority-bearing boundary changes, including:

- relevant program or repository state;
- evidence-prefix identity;
- objective revision;
- remaining budgets;
- continuity or trust epoch;
- eligible playbook-set revision;
- disposition boundary;
- proposed DAG or graph mutation.

## 11. Transition protocol

The source term “AOT conclusion” is replaced by the explicit term **Transition Qualification Decision**.

### 11.1 Request

```cue
#TransitionRequest: {
	from: #RepositorySnapshot

	operation: #OperationReference
	input:     _
	targets:   [...#GraphIdentity]

	actor:     #ActorReference
	authority: #AuthorityContext
	evidence:  [...#EvidenceReference]
}
```

### 11.2 Proposal

```cue
#TransitionProposal: {
	requestDigest: #Digest
	contract:      #AuthoritativeReference

	preconditions:  [...#Assertion]
	operations:     [...#GraphOperation]
	postconditions: [...#Assertion]
	expected:       #RepositoryProjection

	producer: {
		kind:     "model" | "human" | "deterministic"
		identity: string
	}

	frozen: true
	digest: #Digest
}
```

### 11.3 Qualification decision

```cue
#TransitionDisposition:
	"admitted" |
	"denied" |
	"indeterminate" |
	"continuity-lost"

#TransitionQualificationDecision: {
	proposalDigest: #Digest
	disposition:    #TransitionDisposition
	reasons:        [...#Reason]

	sourceCurrent:   bool
	identityClosure: bool
	authorityClosure: bool
	evidenceClosure: bool
	invariantsHold:  bool

	capability?: #ExecutionCapability
	decisionDigest: #Digest
}
```

### 11.4 Capability grant

An admitted decision MUST issue a capability narrowed by:

- operation identity;
- actor identity;
- exact source snapshot;
- contract revision;
- targets and resource selectors;
- permitted mutation classes;
- permitted effects;
- budgets;
- trust epoch;
- execution epoch;
- expiry or single-use semantics.

### 11.5 Execution receipt

```cue
#ExecutionReceipt: {
	decisionDigest: #Digest
	capabilityDigest: #Digest

	executor: #ActorReference
	toolchain: #ToolchainIdentity
	epoch:     #ExecutionEpoch

	observedReads:  [...#ObservedRead]
	attemptedWrites: [...#ObservedWrite]
	producedArtifacts: [...#ArtifactReference]
	rawOutputs: [...#RawOutputReference]

	candidateResult: #RepositoryProjection
	receiptDigest:   #Digest
}
```

### 11.6 Result validation and settlement

System A MUST validate:

```text
receipt matches decision and capability
∧ source snapshot remained admissible
∧ writes remained inside effect bounds
∧ artifacts and outputs match their digests
∧ required evidence is provenance-bound
∧ postconditions hold
∧ protected invariants hold
∧ resulting OSCAL closure is admitted
∧ publication conditions hold
```

Only then MAY System A construct the authoritative commit and move the authorized reference.

## 12. Admission law

Admission is conjunctive, not score-based.

```text
AdmittedTransition
    = current immutable source snapshot
    ∧ pinned trusted contract revision
    ∧ official OSCAL structural validity
    ∧ generated CUE structural validity
    ∧ Cuestrap semantic and relation closure
    ∧ valid actor and authority context
    ∧ valid operation and input
    ∧ valid lifecycle state
    ∧ current continuity epoch
    ∧ required evidence closure
    ∧ permitted mutation vocabulary
    ∧ bounded effects and budgets
    ∧ protected invariants
    ∧ negative witnesses remain rejected
    ∧ valid projected resulting state
    ∧ publication requirements
```

No model score, policy score, confidence, or utility estimate may compensate for a failed hard conjunct.

## 13. Effect model

```cue
#EffectClass:
	"pure" |
	"proposal" |
	"qualification" |
	"observation" |
	"effect" |
	"publication"
```

| Class | Rule |
|---|---|
| `pure` | Reactive and cacheable |
| `proposal` | Reactive but non-authoritative; MUST be frozen before qualification |
| `qualification` | Evaluated against immutable inputs and contract identity |
| `observation` | Bound to an explicit source, trust, and execution epoch |
| `effect` | Requires an exact narrowed capability |
| `publication` | Requires complete result and publication qualification |

An effectful or publication operation MUST NOT execute merely because an upstream reactive value changed.

## 14. Authorization model

Authorization is model-native operation admission, not only endpoint ACL evaluation.

```cue
#AuthorizationContext: {
	actor:            #ActorReference
	operation:        #OperationReference
	subjects:         [...#GraphIdentity]
	lifecycleState:   #StateConstraint
	contractRevision: #AuthoritativeReference
	input:            _
	requestedEffects: [...#Effect]
	executionContext: #ExecutionContext
}
```

Authorization answers:

> May actor A invoke operation O against subjects S, under contract revision C, from lifecycle state L, with input I, producing only effects E in execution context X?

Role permission is necessary but not sufficient. Transition validity, evidence, continuity, and effect bounds are independently necessary.

## 15. Evidence and provenance boundary

Raw output becomes evidence only through explicit binding and qualification.

```text
raw execution output
    ↓ bind producer, subject, source, contract, toolchain, epochs, and digest
candidate OSCAL observation
    ↓ semantic and evidence qualification
qualified evidence
    ↓ lifecycle construction
Assessment Results / finding / risk / remediation evidence
```

A candidate observation MUST be bindable to:

- proposal and decision digests;
- operation identity;
- actor, evaluator, and executor identities;
- authority context;
- source and contract revisions;
- toolchain identity;
- trust and execution epochs;
- artifact digests;
- trace or receipt identity.

No component may manufacture an observation or reinterpret unavailable evidence merely to satisfy closure.

## 16. System B runtime telemetry and streaming analytics

System B requires a session-scoped telemetry plane between raw Codex execution and authoritative CUE/parent composition.

```text
Codex rollout JSONL ───────────────────────────────┐
                                                  │
PreToolUse/PostToolUse provisional ingress ───────┤
                                                  ├─→ rollout-controller Marimo DAG
operation-controller records and receipts ────────┤          │
                                                  │          ▼
target-workbook observations ─────────────────────┘    DuckDB projection
                                                             │
                                                             ▼
                                                   closed CUE subjects
                                                             │
                                                             ▼
                                              readiness / continuity /
                                              conformance / attribution
```

### 16.1 Source authority and precedence

The telemetry plane MUST preserve four distinct source classes:

1. **Codex rollout committed prefix** — primary System B runtime ledger.
2. **Operation-controller records** — authoritative controller-side request, binding, claim, release, and terminal receipt evidence.
3. **Hook ingress** — provisional low-latency `PreToolUse` and `PostToolUse` observations.
4. **DuckDB and Marimo projections** — disposable, reconstructable materializations.

A hook observation MUST NOT silently become the canonical runtime event merely because it arrived first. A successful hook-local decision MUST NOT establish governed admission. A positive post-hook result MUST NOT establish conformance, attribution, settlement, or authorization.

### 16.2 Committed-complete-prefix contract

The rollout controller MUST ingest only complete JSONL records from an immutable identified prefix.

```cue
#RolloutPrefix: close({
	path: string & != ""

	sourceIdentity: close({
		device?:    uint
		inode?:     uint
		generation: string & != ""
	})

	byteStart: uint
	byteEnd:   uint

	lastCompleteRecordEnd: uint
	recordCount:           uint

	prefixDigest:         #Digest
	previousPrefixDigest?: #Digest

	completeLinesOnly: true
})
```

The reader MUST:

- stop at the last complete newline-delimited record;
- retain byte ranges and raw digests for every record;
- detect source replacement, truncation, rotation, or incompatible generation change;
- advance its cursor atomically only after durable materialization succeeds;
- produce the same projection when replaying the same prefix;
- close the current continuity epoch on an unexplained source discontinuity.

A trailing partial line MUST remain unconsumed and MUST NOT influence a control conclusion.

### 16.3 Raw-record and normalized-event identity

```cue
#RawRuntimeRecord: close({
	source: "codex-rollout" | "pre-hook" | "post-hook" |
		"operation-controller" | "target-workbook"

	sourceIdentity: string & != ""
	byteStart?:     uint
	byteEnd?:       uint
	lineNumber?:    uint

	rawDigest: #Digest
	payload:   _
})

#RuntimeStage:
	"proposed" |
	"pre-observed" |
	"dispatched" |
	"started" |
	"returned" |
	"failed" |
	"cancelled" |
	"indeterminate"

#NormalizedRuntimeEvent: close({
	eventID: string & != ""

	sessionID: string & != ""
	turnID?:   string & != ""
	toolUseID?: string & != ""

	stage: #RuntimeStage

	proposedAction?:  #CanonicalAction
	effectiveAction?: #CanonicalAction

	sourceRefs: [#RawRecordReference, ...#RawRecordReference]

	provisional: bool
	committed:   bool

	eventDigest: #Digest
})
```

Normalization MUST be mechanical, deterministic, versioned, and idempotent. Python, Pydantic, Marimo, and DuckDB MAY frame and correlate records but MUST NOT manufacture semantic readiness, continuity, conformance, attribution, admission, or authorization.

### 16.4 Provisional hook reconciliation

The controller MUST model hook ingress as an overlay on the committed rollout prefix.

```text
PreToolUse received
    → provisional-pre

matching rollout proposal committed
    → pre-reconciled

dispatch/start evidence committed
    → dispatched

PostToolUse received
    → provisional-terminal

matching rollout terminal committed
    → terminal-reconciled

operation-controller receipt bound
    → effect-correlated

all required identities and records consistent
    → continuity-preserved
```

The following cases MUST remain explicit rather than being normalized into success:

| Condition | Required projection |
|---|---|
| Provisional event has no committed counterpart | `pending` or `continuity-indeterminate` |
| Committed controlled event has no required hook coverage | `coverage-gap` |
| Same tool-use identity maps to different semantic requests | `identity-conflict` |
| Terminal hook event lacks qualified dispatch/start evidence | `effect-attribution-unresolved` |
| Controller claim exists without a terminal receipt | `claimed-without-receipt` |
| Terminal records disagree | `terminal-conflict` |
| Rollout source is replaced, truncated, or rebased unexpectedly | `continuity-lost` and a closed epoch |
| Unknown or unsupported tool event occurs inside required coverage | `coverage-gap` or `indeterminate`, never implicit approval |

Provisional records MAY support immediate fail-closed restrictions. Expansive authority MUST wait for committed-record reconciliation and exact parent composition.

### 16.5 DuckDB materialization contract

The initial implementation SHOULD expose at least these relations:

| Relation | Purpose |
|---|---|
| `raw_records` | Immutable source coordinates, raw payloads or payload references, and digests |
| `rollout_prefixes` | Source generation, committed byte cursor, prefix chain, and projection status |
| `normalized_events` | Mechanically normalized runtime events |
| `hook_ingress` | Provisional pre/post observations and reconciliation state |
| `controller_records` | Requests, bindings, claims, releases, and receipts |
| `action_correlations` | Proposed/effective/dispatch/start/terminal/receipt linkage |
| `pending_operations` | Operations lacking a qualified terminal state |
| `continuity_epochs` | Source, hook, controller, and supervision continuity boundaries |
| `checkpoint_deltas` | Operation-base, prior-settled, candidate, and relevant-state comparisons |
| `evidence_manifests` | Exact closed facts selected for CUE evaluation |
| `projection_receipts` | Input prefix, projector identity, schema revision, and output digest |

Incremental ingestion MUST follow one atomic logical transaction:

```text
lock source cursor
    → identify complete new prefix
    → hash exact bytes
    → parse bounded records
    → insert raw records idempotently
    → normalize mechanically
    → reconcile provisional hook ingress
    → refresh causal, pending, and continuity projections
    → construct evidence manifest and projection receipt
    → atomically advance cursor
```

Duplicate ingestion MUST be inert. A transaction failure MUST leave the prior cursor and materialization valid. Database corruption or incompatible schema revision MUST force rebuild or an explicit unavailable state; it MUST NOT silently continue from uncertain projections.

### 16.6 Rollout-controller Marimo DAG

The session-scoped rollout workbook MUST own the reactive dependency topology for:

```text
source identity
    → committed-prefix tail
    → raw-record validation
    → incremental DuckDB ingestion
    → provisional hook overlay
    → action and receipt correlation
    → continuity projection
    → checkpoint and delta projection
    → evidence-manifest construction
    → native CUE evaluation
    → parent-composition input
```

The workbook SHOULD expose:

- source generation, cursor, prefix digest, and incomplete-tail status;
- raw, committed, provisional, and reconciled event counts;
- unreconciled or conflicting hook events;
- pending, abandoned, or claim-without-receipt operations;
- proposed, effective, dispatched, terminal, and receipted action identities;
- current continuity epoch and reasons for any gap or loss;
- operation base, prior settled checkpoint, candidate checkpoint, and deltas;
- selected evidence-manifest digest;
- native CUE request, engine identity, raw conclusion, and diagnostics;
- settlement and parent-composition blockers.

Reactive reruns MUST be idempotent. A source or projection change MAY trigger recomputation, but MUST NOT directly trigger an effectful operation.

### 16.7 System B evidence manifest and semantic conclusion

```cue
#SystemBEvidenceManifest: close({
	rolloutPrefix: #RolloutPrefix

	rawRecordSetDigest:      #Digest
	normalizedEventSetDigest: #Digest
	actionCorrelationDigest:  #Digest
	controllerRecordDigest:   #Digest

	continuityEpoch: #ContinuityEpoch
	pendingOperations: [...#PendingOperationReference]
	coverageGaps:      [...#CoverageGap]
	conflicts:         [...#RuntimeConflict]

	operationBase: #RepositorySnapshot
	priorSettled:  #RepositorySnapshot
	candidate:     #RepositorySnapshot

	projectionReceipt: #ProjectionReceipt
})
```

Native CUE MUST evaluate the closed manifest and produce technical System B conclusions such as readiness, trusted continuity, execution conformance, and effect attribution. DuckDB queries, Python reducers, and Marimo cells MUST NOT own those conclusions.

The parent composition layer MUST bind the exact System B manifest and conclusion digests with System A eligibility, the tactical conclusion, the operation order, and parent authorization. A later successful result MUST NOT retroactively authorize an action initiated without that exact composition.

### 16.8 Completion gate

System B MUST NOT be described as complete until all of the following are implemented and qualified:

```text
committed-prefix tailing
∧ complete-line and source-generation safety
∧ durable incremental DuckDB projection
∧ provisional pre/post hook reconciliation
∧ controller receipt and dispatch correlation
∧ continuity epochs and gap handling
∧ closed System B evidence manifests
∧ native CUE readiness/continuity/conformance/attribution
∧ exact parent composition
∧ restart, replay, truncation, conflict, and partial-line tests
```

## 17. Settlement

Admission to execute is not settlement.

```text
candidate checkpoint
    ↓
transition qualification admitted
    ↓
playbook or direct operation executed
    ↓
terminal observations collected
    ↓
postconditions and evidence qualified
    ↓
settlement decision
    ↓
authoritative Git publication
```

A candidate MAY become the next settled checkpoint only when:

```text
required execution completed
∧ the relevant rollout prefix is closed and projection-receipted
∧ required provisional hook ingress is reconciled or explicitly qualified as a gap
∧ dispatch, terminal records, and controller receipts are correlated
∧ no unresolved identity or terminal conflicts remain
∧ Marimo graph is settled when Marimo is involved
∧ no relevant stale descendants remain
∧ System B continuity and conformance are qualified by native CUE
∧ effect evidence and attribution are qualified
∧ postconditions hold
∧ continuity remains trusted
∧ resulting OSCAL closure is admitted
∧ publication succeeds at the authorized reference
```

Possible operational states SHOULD include:

```text
proposed
qualified
running
stale
suspended
blocked
failed
indeterminate
continuity-lost
settlement-pending
settled
published
```

## 18. Reactive playbook model

A playbook is a versioned, CUE-admitted graph-rewrite contract associated with an OSCAL-identified capability or operation. It is not a free-form agent plan.

```cue
#MutationBase:
	"operation-base" |
	"prior-settled" |
	"candidate"

#GraphMutationKind:
	"advance" |
	"insert" |
	"replace" |
	"prune" |
	"fork" |
	"join" |
	"suspend" |
	"resume" |
	"rebase" |
	"compensate" |
	"extract" |
	"terminate"

#Playbook: {
	playbookID: string & != ""
	version:    string & != ""

	applicability: #Predicate
	base:          #MutationBase
	mutations:     [...#GraphMutation]

	retains:     [...#NodeSelector]
	invalidates: [...#NodeSelector]
	inserts:     [...#NodeTemplate]
	activates:   [...#NodeSelector]
	suspends:    [...#NodeSelector]

	authority: #AuthorityEnvelope
	budgets:   #BudgetRequirements

	requires: [...#Assertion]
	ensures:  [...#Assertion]

	expectedSettlement: #StateConstraint
}
```

### 18.1 Mutation meanings

| Mutation | Meaning |
|---|---|
| `advance` | Activate an admitted successor after a completed transition |
| `insert` | Add evidence, correction, approval, or validation nodes |
| `replace` | Supersede an invalid future subgraph with an admitted alternative |
| `prune` | Remove invalid, unauthorized, or unreachable continuation |
| `fork` | Create bounded parallel branches |
| `join` | Reconcile branches under an explicit completion rule |
| `suspend` | Freeze effectful continuation while preserving state |
| `resume` | Reactivate after qualification |
| `rebase` | Establish a fresh qualified state anchor and rebuild continuation |
| `compensate` | Apply corrective effects for a previously settled transition |
| `extract` | Preserve admissible evidence or products from an incomplete branch |
| `terminate` | Close the bounded operation with a typed disposition |

### 18.2 Eligibility before ranking

CUE MUST derive the eligible playbook subset before DSPy or a model receives candidates.

Eligibility SHOULD include:

```text
trigger compatibility
∧ failure-class compatibility
∧ objective compatibility
∧ continuity requirements
∧ authority envelope
∧ evidence availability
∧ epoch compatibility
∧ budget availability
∧ permitted graph mutation classes
```

The exact selected instance MUST be revalidated against the latest immutable checkpoint immediately before graph or source mutation.

### 18.3 Bounded replacement versus material replan

A predefined alternative inside the existing authority envelope MAY be selected as a bounded replacement.

A change to objective, authority, topology, accepted risk, external resources, or execution contract is a material replan and MUST create a new operation boundary.

## 19. Failure, correction, extraction, and continuity

Failure handling SHOULD preserve separate outcomes:

- objective outcome;
- correction outcome;
- extraction outcome;
- continuation disposition.

A major failure SHOULD follow a typed sequence:

```text
qualified failure
    ↓
invalid continuation pruned or suspended
    ↓
corrective playbook
    ↓
invariants restored or safe degraded state established
    ↓
extraction playbook
    ↓
admissible evidence and partial products preserved
    ↓
termination or handoff to a fresh operation
```

Continuity loss MUST suspend automatic effectful continuation. Recovery requires requalification, rebase, or termination.

System B continuity MUST be considered lost or indeterminate when required runtime evidence cannot be reconstructed, including unexplained rollout truncation or replacement, a committed/provisional identity conflict, missing dispatch evidence, a claim without receipt, incompatible terminal records, or an unqualified projection rebuild.

### 19.1 Reference failure scenario: incomplete upstream coverage

A canonical bounded-failure example is an upstream monitor required to classify two independent channels when one exact channel head cannot be established.

```text
objective
    classify both required upstream channels

qualified failure
    exact independent channel identity unavailable

invalid continuation
    complete semantic classification
    canonical publication
    latest-pointer advancement

corrective playbook
    acquire exact reference evidence through another admitted source

extraction playbook
    retain qualified partial observations and diagnostics

forbidden
    infer the missing reference
    manufacture completeness
    publish a successful canonical bundle
```

An anti-churn evaluator MAY inspect effective semantic action, relevant state, qualified terminal evidence, continuity, and correction/uncertainty budgets. Its conclusion MAY constrain playbook eligibility but MUST NOT independently authorize execution or mutate the operation.

## 20. Constrained Git mutation and publication boundary

Only a constrained Git adapter MAY mutate authoritative repository state.

Its closed vocabulary SHOULD include:

```text
read object
resolve reference
construct blob
construct tree
construct commit
verify object identity
update authorized proposal reference
push authorized branch
publish authorized pull request
```

The adapter MUST:

1. inspect a pinned snapshot;
2. resolve exact identities;
3. read affected objects;
4. construct candidate objects without moving authoritative references;
5. validate CUE and OSCAL invariants;
6. run required qualification probes;
7. construct the candidate commit;
8. verify the resulting graph and digests;
9. move only the reference named by the capability;
10. publish only after publication qualification.

Models, DSPy, Marimo, Minder, GUAC, and generated clients MUST NOT bypass this boundary.

## 21. Supply-chain and evidence services

### 21.1 SBOM

SBOMs are first-class typed implementation evidence. They MAY remain SPDX or CycloneDX artifacts, but their lifecycle MUST be bound into OSCAL subjects and operations.

Representative operations include:

```text
component.generate-sbom
component.validate-sbom
component.compare-sbom
component.publish-sbom
component.ingest-sbom
component.resolve-dependencies
component.evaluate-vulnerabilities
component.attest-sbom
```

An SBOM does not define authorization, transition guards, or controller state.

### 21.2 Attestations

Attestations bind typed claims to immutable subjects and SHOULD include:

```text
predicate type
+ subject digest
+ producer identity
+ operation identity
+ source revision
+ contract revision
+ execution context
+ signature or verification material
```

Attestations supplement Git and OSCAL lifecycle records; they do not replace semantic qualification.

### 21.3 GUAC

GUAC MAY materialize a repository-scoped software and evidence graph for:

- software identity correlation;
- dependency traversal;
- provenance and vulnerability queries;
- attestation discovery;
- evidence correlation;
- supply-chain lineage.

GUAC MUST NOT become the semantic, authorization, lifecycle, API, or transition authority.

### 21.4 Minder and policy engines

Minder MAY act as an evaluator and bounded remediation adapter. Its rules and profiles are derived execution configuration. Its results become candidate observations or findings.

Minder MUST NOT independently select authoritative policy, widen scope, establish final OSCAL state, or publish remediation success as verified control effectiveness.

### 21.5 Legacy Apercue disposition

Apercue is not retained as an independent architectural authority. Its responsibilities are normalized as follows:

| Former responsibility | Normalized authority |
|---|---|
| Semantic object model | OSCAL |
| Constraint system | CUE |
| API contract | Cuestrap Component Definition profile |
| State history | Git |
| Artifact identity | Git OIDs and digests |
| Dependency inventory | SBOM |
| Provenance and execution claims | Attestations and receipts |
| Supply-chain graph | GUAC |
| Query and reporting | Generated or derived projections |
| Optional semantic-web output | Deterministic projector |

Reusable Apercue projection patterns MAY survive as non-authoritative generators, provided they emit deterministic receipts and cannot redefine canonical identity or semantics.

## 22. Generation and adapter architecture

Generation flows one way:

```text
Official OSCAL structure
+ Cuestrap OSCAL profile
+ CUE semantic contract
        ├── Go types and interfaces
        ├── constrained Git clients
        ├── Python/Pydantic models
        ├── Hypothesis strategies
        ├── JSON Schema
        ├── OpenAPI or GraphQL adapters
        ├── CLI and MCP tools
        ├── workflow bindings
        ├── fixtures and assertions
        └── documentation
```

Generated surfaces MAY be lossy. They MUST NOT widen the canonical CUE lattice.

Every generator SHOULD emit a deterministic projection receipt:

```cue
#ProjectionReceipt: {
	modelDigest:       #Digest
	projectorIdentity: string
	projectorVersion:  string
	projectorDigest:   #Digest
	outputTreeDigest:  #Digest
	byteStable:        bool
	concrete:          true
}
```

## 23. Python and LLM adapter profile

The technology inventory in `awesome-llm-json.md` is normalized into replaceable layers rather than one flat dependency list.

### 23.1 Contract and runtime boundary

```text
CUE authoritative contract
    ↓
JSON Schema or generated Python schema projection
    ↓
Pydantic runtime representation
    ↓
model-facing adapter
    ↓
candidate result
    ↓
CUE revalidation
```

Pydantic validity establishes only Python-boundary validity.

### 23.2 Recommended roles

| Layer | Candidate | Role |
|---|---|---|
| Python schema boundary | Pydantic | Generated types, serialization, runtime validation, editor support |
| Agent/tool runtime | PydanticAI | Typed tools and output boundary |
| Single-call extraction | Instructor | Narrow schema-first extraction and corrective retry adapter |
| LM-program optimization | DSPy | Optimize model-facing implementation among admitted contracts |
| Provider normalization | LiteLLM or direct provider adapter | Access normalization only, not enforcement |
| Local structured inference | SGLang with XGrammar or llguidance | Provider/runtime constrained decoding |
| Optional constrained generation | Outlines or Guidance | Replaceable generation adapter |
| Telemetry evidence | OpenTelemetry/OpenInference | Trace and model-call evidence projection |

Magentic and BAML SHOULD be studied as function-projection and generated-client references. They SHOULD NOT become parallel schema authorities unless the architecture is deliberately revised.

LangChain, LlamaIndex, Marvin, and similar broad frameworks MAY be integration layers, but SHOULD NOT be core contract dependencies.

Normalization or autocorrection MUST produce a transformation proposal and evidence. It MUST NOT silently convert invalid original output into proof of validity.

### 23.3 External standards and transport profile

External standards MAY be used behind Cuestrap operations without becoming canonical authority:

| Standard/protocol | Normalized role |
|---|---|
| CACAO | Playbook and workflow-graph precedent; domain ontology is not adopted wholesale |
| OpenC2 | Optional cyber-defense actuator transport; not a universal command language |
| STIX/TAXII | Threat-intelligence evidence representation and exchange |
| CSAF/VEX | Vulnerability advisory and applicability evidence |
| SARIF | Analyzer finding interchange |
| OSLC | Linked lifecycle-resource projection |
| TOSCA | Topology/deployment adapter when required |
| XACML | Optional policy-decision adapter; CUE remains admission authority |
| CloudEvents/CDEvents | Event transport and vocabulary |
| MCP | Tool/resource/prompt exposure generated from admitted operations |
| A2A | Remote-agent task and artifact exchange under bounded capabilities |
| Workflow runtimes | Durable execution adapter when Marimo alone is insufficient |

Transport acceptance or remote-agent completion MUST still return through the same request, capability, receipt, evidence, settlement, and publication contracts.

## 24. Structural validation and compatibility

Official OSCAL validation remains an independent gate.

```text
pinned NIST Metaschema revision
    ↓
official generated schemas and validators
    ↓
pinned generated CUE structural package
    ↓
hand-authored Cuestrap semantic overlays
```

Cuestrap-admissible OSCAL is:

```text
official OSCAL structural validity
∧ generated CUE structural validity
∧ Cuestrap profile constraints
∧ semantic relation closure
∧ lifecycle invariants
∧ publication qualification
```

Generated schema packages MUST NOT be hand-edited.

Validator disagreements MUST be recorded in a compatibility ledger with exact tool and revision identities. They MUST NOT be silently patched at an adapter boundary.

## 25. Query and graph materialization

The semantic graph is derived from OSCAL and qualified evidence relationships.

Representative relations include:

```text
Control ─requires────────▶ Capability
Profile ─specializes─────▶ Requirement
Component ─provides──────▶ Operation
Operation ─implements────▶ Requirement
SSP binding ─instantiates▶ Component
Assessment task ─invokes─▶ Operation
Observation ─result-of───▶ Invocation
Finding ─evaluates───────▶ Requirement
Risk ─derived-from───────▶ Finding
POA&M item ─selects──────▶ Remediation operation
SBOM ─describes──────────▶ Component implementation
Attestation ─asserts-about▶ Artifact or transition
```

Derived edges MAY be materialized in GUAC or DuckDB. OSCAL UUIDs and Git/digest identities remain authoritative.

DuckDB additionally materializes the System B temporal and causal graph defined in Section 16. Its rows MUST retain raw-source references and projection-receipt identity. GUAC remains the broader software/evidence graph; DuckDB remains the session and historical analytical projection. Neither may substitute local IDs or inferred joins for canonical OSCAL, Git, operation, tool-use, receipt, or digest identity.

## 26. End-to-end reconciliation loop

```text
1. Resolve repository, rollout source, controller-record, and contract identities.
2. Tail only the committed complete prefix of the Codex rollout JSONL.
3. Ingest raw records idempotently and retain exact source coordinates and digests.
4. Overlay current provisional PreToolUse/PostToolUse ingress.
5. Correlate proposed, effective, dispatched, started, terminal, and receipted actions.
6. Materialize DuckDB pending-operation, continuity-epoch, checkpoint, and delta views.
7. Construct a closed System B evidence manifest and projection receipt.
8. Evaluate System B readiness, continuity, conformance, and attribution through native CUE.
9. Observe repository, collaboration, governance, and System A evidence state.
10. Resolve an immutable Git snapshot and OSCAL closure.
11. Load the pinned Component Definition API profile and CUE contract.
12. Derive current lifecycle, target eligibility, and continuity state.
13. Compare current state with Catalog/Profile requirements and desired OSCAL state.
14. Receive or construct a candidate request.
15. Derive the permitted operation or eligible playbook subset.
16. Permit deterministic, human, or model proposal generation inside that subset.
17. Normalize, freeze, and digest the proposal.
18. Construct a candidate checkpoint.
19. Compose System A eligibility, System B readiness/continuity, tactical conclusion, exact order, and parent authorization.
20. Deny, suspend, or issue a narrowed capability for the exact bundle and epochs.
21. Execute through System B and the relevant bounded adapter.
22. Collect raw outputs, artifacts, traces, hook ingress, controller records, and receipts.
23. Advance and reconcile the committed rollout prefix.
24. Rebuild the DuckDB projection and System B evidence manifest.
25. Bind candidate observations to provenance and evaluate post-operation System B conformance and attribution through CUE.
26. Validate System A postconditions, invariants, and resulting OSCAL closure.
27. Evaluate joint settlement.
28. Construct and verify Git objects through the constrained adapter.
29. Move only the authorized reference and publish only qualified state.
30. Advance the settled anchor.
31. Update disposable GUAC, DuckDB, report, and transport projections.
```

Control-theoretically:

```text
reference signal
    = Catalog/Profile requirements + desired OSCAL state

controller law
    = Component Definition operations + CUE admission rules

plant
    = governed repository and collaboration graph

observation
    = Git state + qualified Assessment Results + supply-chain evidence

error signal
    = findings + risks + failed constraints + continuity failures

control input
    = admitted bounded operation

corrective lifecycle
    = POA&M and corrective playbooks

next authoritative state
    = validated and published Git commit
```

## 27. Minimal vertical slice

The first implementation SHOULD prove the complete authority chain and the missing System B telemetry chain with one narrow scenario.

1. Pin one official OSCAL model, Metaschema revision, native CUE engine, and validation toolchain.
2. Define one Cuestrap Component Definition capability and one operation.
3. Capture one immutable operation base and one prior-settled checkpoint.
4. Provide a bounded Codex rollout JSONL fixture containing a proposed action, dispatch/start record, and terminal record.
5. Tail only its committed complete prefix and preserve byte ranges, generation identity, and prefix digest.
6. Ingest the prefix into DuckDB and emit a projection receipt.
7. Inject one provisional `PreToolUse` event and reconcile it with the committed proposal.
8. Inject one provisional `PostToolUse` event and reconcile it with the committed terminal record.
9. Bind one operation-controller request, claim, and terminal receipt to the same effective action.
10. Materialize action correlation, pending-operation, continuity-epoch, checkpoint, and delta views.
11. Construct one closed System B evidence manifest.
12. Evaluate readiness and trusted continuity through native CUE.
13. Construct one bounded transition request and frozen proposal.
14. Qualify System A eligibility, the tactical conclusion, System B readiness, exact parent authorization, and the complete bundle identity.
15. Issue one narrowed execution capability.
16. Execute one bounded operation through the operation-controller workbook.
17. Advance the rollout prefix, rebuild DuckDB, and evaluate conformance and effect attribution through native CUE.
18. Emit one execution receipt and one attestation.
19. Bind one observation into Assessment Results.
20. Apply one admitted mutation through the constrained Git adapter.
21. Evaluate settlement and publish only after both systems and the parent composition agree.
22. Replay the complete slice and verify equivalent identities, projections, conclusions, and resulting state.
23. Add negative fixtures for a partial trailing JSON line, unmatched post-hook event, claim without receipt, source truncation, and conflicting semantic request identity.

## 28. Proposed implementation stages

### Stage 0 — vocabulary and contract kernel

- Freeze identifiers, digests, references, actors, resource selectors, effects, assertions, evidence references, epochs, runtime stages, correlation states, and dispositions.
- Establish closed CUE definitions and negative fixtures.
- Define which OSCAL extension points carry Cuestrap operation-profile data.

### Stage 1 — canonical raw observation

- Implement Git object and repository snapshot observation.
- Define rollout source generation, complete-prefix, raw-record, hook-ingress, and controller-record identities.
- Resolve mutable references to immutable identities.
- Produce deterministic snapshot and raw-prefix digests.

### Stage 2 — System B telemetry and streaming analytics

- Add DuckDB to the locked environment and define versioned migrations.
- Implement the session-scoped rollout/JSONL Marimo controller workbook.
- Tail committed complete prefixes with atomic cursor advancement and rotation/truncation handling.
- Materialize raw, normalized, hook-ingress, controller, action-correlation, pending-operation, continuity, checkpoint, evidence-manifest, and projection-receipt relations.
- Reconcile provisional pre/post hook events with committed rollout records.
- Add restart, replay, duplicate, partial-line, conflict, claim-without-receipt, and source-discontinuity tests.

### Stage 3 — native System B conclusions and parent composition

- Construct closed System B evidence manifests.
- Implement native CUE readiness, continuity, conformance, and effect-attribution relations.
- Compose System A eligibility, tactical conclusion, System B conclusion, exact order identity, epochs, and parent authorization.
- Remove positive authorization meaning from provisional Python anti-churn approval paths.

### Stage 4 — operation and transition qualification

- Implement request, proposal, qualification decision, capability, receipt, and settlement contracts.
- Add official OSCAL validation and CUE semantic closure.
- Add compatibility-ledger recording.

### Stage 5 — constrained mutation adapter

- Implement object construction and authorized reference update as separate phases.
- Prove fail-closed behavior under stale source, moved references, invalid postconditions, capability violations, and System B continuity gaps.

### Stage 6 — generated adapters

- Generate Go and Python types.
- Add Pydantic and Hypothesis surfaces.
- Add CLI/MCP adapters only after contract parity is tested.

### Stage 7 — reactive execution and playbooks

- Add the bounded Marimo source/DAG adapter.
- Add closed graph-mutation vocabulary and initial playbook families.
- Bind candidate/prior-settled/operation-base comparisons to System B checkpoint projections.

### Stage 8 — bounded model integration

- Add provider-native structured output or constrained decoding.
- Add PydanticAI/Instructor boundaries as appropriate.
- Add DSPy only after deterministic eligibility, System B evidence, and acceptance metrics exist.

### Stage 9 — evidence, supply chain, and continuous reconciliation

- Add Assessment Results binding, SBOM, attestations, GUAC, telemetry publication, event triggers, collaboration state, pull-request publication, and bounded remediation.
- Prove every projection is rebuildable from canonical state and raw runtime sources.
- Keep effect execution explicitly gated; do not map generic reactivity directly to mutation.

## 29. Required conformance properties

The implementation SHOULD make the following properties executable:

1. **No unauthorized mutation** — every failed or rejected trace leaves protected graph state unchanged.
2. **Snapshot freshness** — a proposal qualified against stale source cannot execute.
3. **Capability confinement** — attempted effects outside the grant are rejected and recorded.
4. **Adapter non-widening** — generated Go/Python/JSON surfaces admit no value rejected by the canonical contract for the same operation boundary.
5. **Identity preservation** — all published artifacts remain traceable to OSCAL UUIDs, contract IDs, Git OIDs, raw source coordinates, operation identities, receipt identities, and digests.
6. **Evidence non-forgery** — unavailable or provisional evidence cannot be converted into a positive qualified observation.
7. **Complete-line ingestion** — a partial trailing JSONL record never enters the normalized event set or a control conclusion.
8. **Cursor monotonicity** — the committed prefix cursor advances only after a complete durable projection transaction.
9. **Ingestion idempotence** — replaying an identical prefix produces no duplicate semantic events and the same projection digest.
10. **Source discontinuity safety** — unexplained truncation, replacement, or generation change closes continuity and prevents automatic continuation.
11. **Hook reconciliation** — a provisional hook event cannot become committed evidence without an identity-consistent rollout counterpart or an explicit qualified gap disposition.
12. **Dispatch/receipt correlation** — post-hook success without dispatch/start and controller-receipt evidence cannot establish effect attribution.
13. **Conflict preservation** — mismatched request identities or terminal records remain conflicts and are never resolved by arrival order.
14. **Restart recovery** — after process restart, the rollout controller reconstructs the same pending, continuity, checkpoint, and evidence-manifest projections from raw sources.
15. **SQL non-authority** — DuckDB relations and queries cannot encode or publish final semantic admission, readiness, continuity, conformance, attribution, or settlement conclusions.
16. **Native conclusion binding** — every System B technical conclusion binds an exact evidence-manifest digest, native engine identity, and projection receipt.
17. **Settlement monotonicity** — `priorSettled` advances only after complete joint settlement.
18. **Projection rebuildability** — GUAC, DuckDB, reports, and generated artifacts can be reconstructed from canonical inputs and identified raw runtime sources.
19. **Deterministic projection** — pinned generators and normalizers produce byte-stable outputs or explicit nondeterminism evidence.
20. **Negative-witness permanence** — discovered counterexamples remain rejected by subsequent revisions unless an explicit contract change reclassifies them.
21. **Material-replan boundary** — changes outside delegated topology or authority require a new operation.
22. **Publication isolation** — candidate object construction and authoritative reference movement remain separate privileges.

## 30. Review decisions required

The architecture is coherent only after the following choices are made explicit.

### 30.1 Component Definition operation encoding

Select the exact OSCAL-native encoding convention for:

- operation identity;
- input/output schema references;
- read/write selectors;
- effects;
- evidence requirements;
- transition metadata;
- generated transport hints.

The selected convention SHOULD use official extension points and remain valid under official OSCAL validators.

### 30.2 Canonical state artifact layout

Define where the repository stores:

- desired OSCAL state;
- candidate proposals;
- qualification decisions;
- execution receipts;
- Assessment Results;
- POA&M transitions;
- projection receipts;
- compatibility-ledger entries.

The layout MUST distinguish canonical lifecycle state from disposable generated output.

### 30.3 Capability representation

Choose whether the narrowed execution capability is represented as:

- a signed CUE/JSON value;
- a content-addressed Git blob;
- an in-process opaque capability referencing an immutable grant;
- an attested short-lived token.

The authoritative grant content MUST remain inspectable and replayable.

### 30.4 Marimo mutation boundary

Define the exact allowed Marimo source transformations and how generated edits are proven to correspond to an admitted playbook instance.

### 30.5 Runtime persistence

Define which runtime events must be committed immediately, batched into decision/settlement receipts, or retained only as raw external artifacts.

### 30.6 Technology profile status

Decide which adapter recommendations are:

- required for the initial implementation;
- optional reference integrations;
- explicitly deferred.

The architecture should not couple canonical contracts to a rapidly changing LLM framework.

### 30.7 Rollout source and committed-prefix identity

Define the exact Codex rollout discovery mechanism, source-generation identity, byte-cursor persistence, complete-line boundary, prefix-digest chain, rotation/truncation response, retention policy, and replay contract.

### 30.8 Hook coverage and reconciliation

Define which controlled operations require `PreToolUse`, `PostToolUse`, dispatch/start, terminal, and controller-receipt coverage; the matching keys and semantic-equality rules; timeout and abandonment behavior; and which gaps force `indeterminate` versus `continuity-lost`.

### 30.9 DuckDB schema and lifecycle

Freeze the initial relation schemas, migration policy, raw-payload retention or externalization, database location, concurrency model, transaction boundary, corruption recovery, projection-receipt format, and rebuild procedure.

### 30.10 System B conclusion interface

Define the exact closed manifest consumed by native CUE and the disjoint result domains for readiness, continuity, conformance, and effect attribution. Define how the parent binds those result digests with System A, tactical, order, and authorization identities.

## 31. Source normalization map

| Source document | Retained concepts | Normalized disposition |
|---|---|---|
| `Cuestrap-Unified-Architecture.md` | OSCAL/CUE/Git authority chain; System A/B; operation and transition contracts; evidence, Git adapter, GUAC, SBOM, attestations, generation, vertical slice | Used as the principal integration spine; tightened around official OSCAL structure and runtime-plane distinctions |
| `OSCAL-Native-API-Centric-GitOps-Architecture.md` | Component Definition API thesis; OSCAL lifecycle mapping; authorization tuple; GitOps loop; Minder/GUAC/SBOM roles | Merged into the canonical domain, authorization, and service-adapter sections; overlapping text removed |
| `agentic-pipeline-architecture.md` | Marimo DAG authority; rollout/JSONL observation plane; operation base/prior settled/candidate anchors; two-phase decisions; settlement; playbooks; graph mutation algebra; DSPy ranking; DuckDB streaming projections | Integrated as the System B runtime telemetry and subordinate reactive execution protocol inside the OSCAL/CUE/Git authority model; committed-prefix, hook-reconciliation, DuckDB, continuity, and evidence-manifest contracts made explicit; unexplained “AOT” term replaced by Transition Qualification Decision |
| `awesome-llm-json.md` | Schema/runtime taxonomy; Pydantic, PydanticAI, Instructor, DSPy, constrained decoding, provider runtimes, generated-client references | Converted from ecosystem review into a replaceable adapter profile; no listed framework is canonical authority |

## 32. Compact normative formulation

```text
Every governed capability is identified in OSCAL.
Every callable operation is defined by the Cuestrap Component Definition profile.
Every authoritative constraint and relation is executable through CUE.
Every request begins from an immutable Git snapshot.
Every System B runtime conclusion begins from an identified committed-complete rollout prefix.
Every PreToolUse and PostToolUse observation remains provisional until reconciled or explicitly qualified as a gap.
Every operation correlation preserves proposed, effective, dispatch, terminal, and receipt identities.
Every DuckDB and Marimo projection is receipt-bound, rebuildable, and semantically subordinate.
Every System B readiness, continuity, conformance, and attribution conclusion is evaluated by native CUE over a closed evidence manifest.
Every proposal is frozen and digested before qualification.
Every model sees only a pre-admitted alternative space.
Every effect is bound to a narrowed capability.
Every raw observation is provenance-bound before becoming evidence.
Every accepted result satisfies official OSCAL structure, CUE semantics,
postconditions, invariants, evidence closure, and publication policy.
Every authoritative mutation passes through the constrained Git adapter.
Every settled state is committed and content-addressed.
Every analytical, graph, model, and transport surface is rebuildable and subordinate.
No derived component becomes a parallel authority.
```

## 33. Proposed decision

Adopt this document as the architecture-review baseline, then split implementation contracts from it in the following order:

1. repository snapshot, rollout source-generation, committed-prefix, raw-record, and controller-record identity contracts;
2. rollout/JSONL normalization, provisional hook reconciliation, DuckDB relation, cursor, and projection-receipt contracts;
3. System B evidence-manifest and native CUE readiness/continuity/conformance/attribution contracts;
4. exact parent composition contract across System A, System B, tactical conclusion, order revision, bundle identity, and authorization;
5. Component Definition operation profile;
6. transition request/proposal/decision/capability/receipt contract;
7. constrained Git mutation contract;
8. evidence and joint-settlement contract;
9. reactive playbook and Marimo mutation contract;
10. generated adapter and model-runtime profiles.

This ordering closes the missing runtime observation and continuity plane before the architecture claims governed execution, settlement, or continuous reconciliation.
