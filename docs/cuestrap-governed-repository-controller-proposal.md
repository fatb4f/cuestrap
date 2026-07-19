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
- [16. Settlement](#16-settlement)
- [17. Reactive playbook model](#17-reactive-playbook-model)
- [18. Failure, correction, extraction, and continuity](#18-failure-correction-extraction-and-continuity)
- [19. Constrained Git mutation and publication boundary](#19-constrained-git-mutation-and-publication-boundary)

### Services, projections, and adapters

- [20. Supply-chain and evidence services](#20-supply-chain-and-evidence-services)
- [21. Generation and adapter architecture](#21-generation-and-adapter-architecture)
- [22. Python and LLM adapter profile](#22-python-and-llm-adapter-profile)
- [23. Structural validation and compatibility](#23-structural-validation-and-compatibility)
- [24. Query and graph materialization](#24-query-and-graph-materialization)

### Delivery and review

- [25. End-to-end reconciliation loop](#25-end-to-end-reconciliation-loop)
- [26. Minimal vertical slice](#26-minimal-vertical-slice)
- [27. Proposed implementation stages](#27-proposed-implementation-stages)
- [28. Required conformance properties](#28-required-conformance-properties)
- [29. Review decisions required](#29-review-decisions-required)
- [30. Source normalization map](#30-source-normalization-map)
- [31. Compact normative formulation](#31-compact-normative-formulation)
- [32. Proposed decision](#32-proposed-decision)

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

### 9.2 System B — proposal, observation, evaluation, and bounded execution plane

System B owns:

- candidate proposals;
- bounded playbook instantiations;
- test and assessment execution;
- evidence collection;
- remediation execution under granted capability;
- counterexamples and diagnostics;
- execution receipts;
- candidate resulting state.

System B MUST NOT:

- redefine policy or contract meaning;
- widen its capability;
- repair or manufacture evidence to satisfy closure;
- mutate protected state outside the grant;
- publish authoritative state;
- treat raw output as qualified evidence.

### 9.3 Marimo — live reactive execution plane

Marimo is authoritative for the actual live Python dependency graph it constructs:

- cell dependency analysis;
- invalidation;
- scheduling;
- reactive execution;
- stale-state propagation;
- graph settlement.

Marimo is not authoritative for:

- governance semantics;
- operation admission;
- actor authorization;
- evidence qualification;
- Git publication.

A CUE-admitted playbook MAY compile to a bounded Marimo source mutation. Marimo then reconstructs and executes the resulting DAG.

### 9.4 DuckDB — analytical projection plane

DuckDB MAY maintain streaming and historical projections of:

- runtime observations;
- state deltas;
- evidence prefixes;
- budgets;
- evaluation corpora;
- transition histories;
- settlement metrics.

DuckDB MUST remain reconstructible from authoritative records and MUST NOT become the sole store of lifecycle state.

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

## 16. Settlement

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
∧ Marimo graph is settled when Marimo is involved
∧ no relevant stale descendants remain
∧ effect evidence is qualified
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

## 17. Reactive playbook model

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

### 17.1 Mutation meanings

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

### 17.2 Eligibility before ranking

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

### 17.3 Bounded replacement versus material replan

A predefined alternative inside the existing authority envelope MAY be selected as a bounded replacement.

A change to objective, authority, topology, accepted risk, external resources, or execution contract is a material replan and MUST create a new operation boundary.

## 18. Failure, correction, extraction, and continuity

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

### 18.1 Reference failure scenario: incomplete upstream coverage

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

## 19. Constrained Git mutation and publication boundary

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

## 20. Supply-chain and evidence services

### 20.1 SBOM

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

### 20.2 Attestations

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

### 20.3 GUAC

GUAC MAY materialize a repository-scoped software and evidence graph for:

- software identity correlation;
- dependency traversal;
- provenance and vulnerability queries;
- attestation discovery;
- evidence correlation;
- supply-chain lineage.

GUAC MUST NOT become the semantic, authorization, lifecycle, API, or transition authority.

### 20.4 Minder and policy engines

Minder MAY act as an evaluator and bounded remediation adapter. Its rules and profiles are derived execution configuration. Its results become candidate observations or findings.

Minder MUST NOT independently select authoritative policy, widen scope, establish final OSCAL state, or publish remediation success as verified control effectiveness.

### 20.5 Legacy Apercue disposition

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

## 21. Generation and adapter architecture

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

## 22. Python and LLM adapter profile

The technology inventory in `awesome-llm-json.md` is normalized into replaceable layers rather than one flat dependency list.

### 22.1 Contract and runtime boundary

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

### 22.2 Recommended roles

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

### 22.3 External standards and transport profile

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

## 23. Structural validation and compatibility

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

## 24. Query and graph materialization

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

## 25. End-to-end reconciliation loop

```text
1. Observe repository, collaboration, governance, and evidence state.
2. Resolve an immutable Git snapshot and OSCAL closure.
3. Load the pinned Component Definition API profile and CUE contract.
4. Derive current lifecycle and continuity state.
5. Compare current state with Catalog/Profile requirements and desired OSCAL state.
6. Receive or construct a candidate request.
7. Derive the permitted operation or eligible playbook subset.
8. Permit deterministic, human, or model proposal generation inside that subset.
9. Normalize, freeze, and digest the proposal.
10. Construct a candidate checkpoint.
11. Perform structural, semantic, authority, evidence, continuity, and effect qualification.
12. Deny, suspend, or issue a narrowed capability.
13. Execute through System B and the relevant bounded adapter.
14. Collect raw outputs, artifacts, traces, and receipts.
15. Bind candidate observations to provenance.
16. Validate postconditions, invariants, and resulting OSCAL closure.
17. Evaluate settlement.
18. Construct and verify Git objects through the constrained adapter.
19. Move only the authorized reference and publish only qualified state.
20. Advance the settled anchor.
21. Update disposable GUAC, DuckDB, report, and transport projections.
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

## 26. Minimal vertical slice

The first implementation SHOULD prove the complete authority chain with one narrow scenario.

1. Pin one official OSCAL model, Metaschema revision, and validation toolchain.
2. Import or generate its structural CUE representation reproducibly.
3. Define one Cuestrap Component Definition capability and one operation.
4. Add one cross-resource identity or reference constraint.
5. Add one lifecycle or publication constraint.
6. Observe one immutable repository snapshot.
7. Construct one bounded transition request and proposal.
8. Freeze and digest the proposal and candidate checkpoint.
9. Qualify it through official OSCAL validation and CUE closure.
10. Generate one Go or Python adapter, one Pydantic model, and one Hypothesis strategy.
11. Introduce one deliberate invalid mutant and preserve it as a negative fixture.
12. Issue one narrowed execution capability.
13. Execute one bounded operation through System B.
14. Emit one execution receipt and one attestation.
15. Bind one observation into Assessment Results.
16. Apply one admitted mutation through the constrained Git adapter.
17. Generate or update one SBOM.
18. Ingest derived evidence into a repository-scoped GUAC projection.
19. Replay the complete slice and verify equivalent identities, digests, decisions, and resulting state.

## 27. Proposed implementation stages

### Stage 0 — vocabulary and contract kernel

- Freeze identifiers, digests, references, actors, resource selectors, effects, assertions, evidence references, epochs, and dispositions.
- Establish closed CUE definitions and negative fixtures.
- Define which OSCAL extension points carry Cuestrap operation-profile data.

### Stage 1 — immutable observation

- Implement Git object and repository snapshot observation.
- Resolve mutable references to commits.
- Produce deterministic snapshot digests and dirty-state handling.

### Stage 2 — operation and transition qualification

- Implement request, proposal, qualification decision, capability, receipt, and settlement contracts.
- Add official OSCAL validation and CUE semantic closure.
- Add compatibility-ledger recording.

### Stage 3 — constrained mutation adapter

- Implement object construction and authorized reference update as separate phases.
- Prove fail-closed behavior under stale source, moved references, invalid postconditions, and capability violations.

### Stage 4 — generated adapters

- Generate Go and Python types.
- Add Pydantic and Hypothesis surfaces.
- Add CLI/MCP adapters only after contract parity is tested.

### Stage 5 — reactive execution and playbooks

- Add Marimo source/DAG adapter.
- Add closed graph-mutation vocabulary and initial playbook families.
- Add candidate/prior-settled/operation-base checkpoint comparison.

### Stage 6 — bounded model integration

- Add provider-native structured output or constrained decoding.
- Add PydanticAI/Instructor boundaries as appropriate.
- Add DSPy only after deterministic eligibility and acceptance metrics exist.

### Stage 7 — evidence and projections

- Add Assessment Results binding, SBOM, attestations, GUAC, DuckDB, and telemetry projections.
- Prove every projection is rebuildable from canonical state.

### Stage 8 — continuous reconciliation

- Add event triggers, reconciliation scheduling, collaboration state, pull-request publication, and bounded remediation.
- Keep effect execution explicitly gated; do not map generic reactivity directly to mutation.

## 28. Required conformance properties

The implementation SHOULD make the following properties executable:

1. **No unauthorized mutation** — every failed or rejected trace leaves protected graph state unchanged.
2. **Snapshot freshness** — a proposal qualified against stale source cannot execute.
3. **Capability confinement** — attempted effects outside the grant are rejected and recorded.
4. **Adapter non-widening** — generated Go/Python/JSON surfaces admit no value rejected by the canonical contract for the same operation boundary.
5. **Identity preservation** — all published artifacts remain traceable to OSCAL UUIDs, contract IDs, Git OIDs, and digests.
6. **Evidence non-forgery** — unavailable evidence cannot be converted into a positive observation.
7. **Settlement monotonicity** — `priorSettled` advances only after complete settlement.
8. **Projection rebuildability** — GUAC, DuckDB, reports, and generated artifacts can be reconstructed from canonical inputs.
9. **Deterministic projection** — pinned generators produce byte-stable outputs or explicit nondeterminism evidence.
10. **Negative-witness permanence** — discovered counterexamples remain rejected by subsequent revisions unless an explicit contract change reclassifies them.
11. **Material-replan boundary** — changes outside delegated topology or authority require a new operation.
12. **Publication isolation** — candidate object construction and authoritative reference movement remain separate privileges.

## 29. Review decisions required

The architecture is coherent only after the following choices are made explicit.

### 29.1 Component Definition operation encoding

Select the exact OSCAL-native encoding convention for:

- operation identity;
- input/output schema references;
- read/write selectors;
- effects;
- evidence requirements;
- transition metadata;
- generated transport hints.

The selected convention SHOULD use official extension points and remain valid under official OSCAL validators.

### 29.2 Canonical state artifact layout

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

### 29.3 Capability representation

Choose whether the narrowed execution capability is represented as:

- a signed CUE/JSON value;
- a content-addressed Git blob;
- an in-process opaque capability referencing an immutable grant;
- an attested short-lived token.

The authoritative grant content MUST remain inspectable and replayable.

### 29.4 Marimo mutation boundary

Define the exact allowed Marimo source transformations and how generated edits are proven to correspond to an admitted playbook instance.

### 29.5 Runtime persistence

Define which runtime events must be committed immediately, batched into decision/settlement receipts, or retained only as raw external artifacts.

### 29.6 Technology profile status

Decide which adapter recommendations are:

- required for the initial implementation;
- optional reference integrations;
- explicitly deferred.

The architecture should not couple canonical contracts to a rapidly changing LLM framework.

## 30. Source normalization map

| Source document | Retained concepts | Normalized disposition |
|---|---|---|
| `Cuestrap-Unified-Architecture.md` | OSCAL/CUE/Git authority chain; System A/B; operation and transition contracts; evidence, Git adapter, GUAC, SBOM, attestations, generation, vertical slice | Used as the principal integration spine; tightened around official OSCAL structure and runtime-plane distinctions |
| `OSCAL-Native-API-Centric-GitOps-Architecture.md` | Component Definition API thesis; OSCAL lifecycle mapping; authorization tuple; GitOps loop; Minder/GUAC/SBOM roles | Merged into the canonical domain, authorization, and service-adapter sections; overlapping text removed |
| `agentic-pipeline-architecture.md` | Marimo DAG authority; operation base/prior settled/candidate anchors; two-phase decisions; settlement; playbooks; graph mutation algebra; DSPy ranking; DuckDB projections | Integrated as a subordinate reactive execution protocol inside the OSCAL/CUE/Git authority model; unexplained “AOT” term replaced by Transition Qualification Decision |
| `awesome-llm-json.md` | Schema/runtime taxonomy; Pydantic, PydanticAI, Instructor, DSPy, constrained decoding, provider runtimes, generated-client references | Converted from ecosystem review into a replaceable adapter profile; no listed framework is canonical authority |

## 31. Compact normative formulation

```text
Every governed capability is identified in OSCAL.
Every callable operation is defined by the Cuestrap Component Definition profile.
Every authoritative constraint and relation is executable through CUE.
Every request begins from an immutable Git snapshot.
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

## 32. Proposed decision

Adopt this document as the architecture-review baseline, then split implementation contracts from it in the following order:

1. identity and repository snapshot contract;
2. Component Definition operation profile;
3. transition request/proposal/decision/capability/receipt contract;
4. constrained Git mutation contract;
5. evidence and settlement contract;
6. reactive playbook and Marimo mutation contract;
7. generated adapter and model-runtime profiles.

This ordering establishes authority and effect boundaries before adding reactive or probabilistic execution.
