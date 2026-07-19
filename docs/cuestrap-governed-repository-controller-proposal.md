# Cuestrap Governed Repository Controller

## Architecture and Contract Proposal

| Field | Value |
|---|---|
| Status | Draft for architecture review |
| Scope | Normalized architecture for continuous OSCAL ATO, governed repository transitions, streaming assessment, and bounded agent execution |
| Intended audience | Architecture, contract, implementation, security, compliance, and agent-control reviewers |
| Normative language | `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT`, and `MAY` are requirement terms |
| Semantic center | One continuously revised OSCAL-centered typed semantic graph |
| Executable semantic authority | Pinned CUE relations through a narrow qualified Go facade |
| Causal authority | Immutable graph checkpoints and ordered event segments bound to Git and cryptographic digests |
| Analytical runtime | DuckDB materializations orchestrated by a qualified Marimo reactive DAG |
| Effect boundary | Exact parent authorization plus narrowed one-use capabilities |

## Overview

Cuestrap is a proof-carrying, event-sourced controller for a continuously evaluated authorization system. Its architectural center is **one shared typed semantic graph** containing normative controls, implementation state, assessment procedures, evidence, System A target facts, System B execution facts, findings, risks, remediation obligations, authorization decisions, and the currently derived authorization posture.

The graph changes only through ordered, content-addressed transition events evaluated by a pinned CUE/Go transition kernel. Each accepted event advances an immutable graph revision. DuckDB materializes revision-bound semantic and temporal relations. Marimo owns the live reactive dependency graph that determines which materializations, metrics, assessment procedures, findings, risks, authorization-posture conclusions, and OSCAL projections must be recomputed after each change.

```text
immutable graph checkpoint
        +
ordered transition event
        +
pinned policy, procedure, and kernel revisions
        ↓
deterministic CUE/Go graph fold
        ↓
next semantic graph revision
        ├── control and implementation state
        ├── evidence currency and assessment state
        ├── findings, risks, and POA&M obligations
        ├── System A and System B conclusions
        ├── continuously derived authorization posture
        ├── permitted capability envelope
        └── OSCAL lifecycle projections
                 ↓
        DuckDB materializations
                 ↓
        qualified Marimo reactive DAG
                 ↓
        next bounded evaluation cycle
```

Continuous ATO in this proposal does **not** mean that software accepts organizational risk or autonomously grants formal authorization. The accountable authorizing authority retains formal authorization and risk-acceptance responsibility. Cuestrap continuously derives and enforces the technical posture and delegated operating envelope that follow from the current authorization decision, current evidence, current policy, current graph revision, and current findings and risks.

### Implementation status boundary

The repository currently implements only part of the runtime foundation.

| Implemented on `main` | Still required for the architecture in this proposal |
|---|---|
| Main target workbook and typed workbook adapter | One shared typed semantic graph and immutable graph-revision contract |
| One-operation Marimo controller with identity-bound request, binding, claim, release, and receipt records | Canonical immutable event segments and deterministic graph fold |
| `PreToolUse` and `PostToolUse` hook ingress with local correlation for recognized calls | Session-scoped rollout controller and reconciliation into canonical semantic events |
| Hook-local `state.json` and diagnostic `events.jsonl` | DuckDB semantic, temporal, metric, finding, risk, posture, and OSCAL-projection materializations |
| Provisional Python anti-churn predicates | Qualified CUE assessment procedures and authoritative technical conclusions |
| Bounded operation execution through workbook capabilities | Continuously derived authorization posture and delegated capability envelope |
| System A/System B terminology and partial evidence contracts | Independent evidence partitions inside one graph, composed without creating separate semantic universes |

The hook-local ledger MUST remain provisional diagnostic evidence. It MUST NOT be described as the canonical event ledger, the semantic graph, the continuous streaming analytics plane, or the complete System B implementation.

## Table of contents

### Foundation

- [1. Proposal](#1-proposal)
- [2. Review objectives](#2-review-objectives)
- [3. Non-goals](#3-non-goals)
- [4. Core invariants](#4-core-invariants)
- [5. Authority hierarchy](#5-authority-hierarchy)
- [6. Identity model](#6-identity-model)
- [7. Shared typed semantic graph](#7-shared-typed-semantic-graph)
- [8. OSCAL lifecycle projections](#8-oscal-lifecycle-projections)
- [9. System decomposition](#9-system-decomposition)

### State, transition, and authority

- [10. Graph revisions, snapshots, and checkpoints](#10-graph-revisions-snapshots-and-checkpoints)
- [11. Event ledger and transition protocol](#11-event-ledger-and-transition-protocol)
- [12. Admission law](#12-admission-law)
- [13. Effect and capability model](#13-effect-and-capability-model)
- [14. Authorization decision and continuous posture](#14-authorization-decision-and-continuous-posture)
- [15. Evidence and provenance boundary](#15-evidence-and-provenance-boundary)

### Continuous evaluation and execution

- [16. Continuous OSCAL ATO semantic graph and reactive DAG](#16-continuous-oscal-ato-semantic-graph-and-reactive-dag)
- [17. System B runtime telemetry and hook reconciliation](#17-system-b-runtime-telemetry-and-hook-reconciliation)
- [18. Settlement](#18-settlement)
- [19. Reactive playbook model](#19-reactive-playbook-model)
- [20. Failure, correction, extraction, and continuity](#20-failure-correction-extraction-and-continuity)
- [21. Constrained Git mutation and publication boundary](#21-constrained-git-mutation-and-publication-boundary)

### Services, projections, and adapters

- [22. Supply-chain and evidence services](#22-supply-chain-and-evidence-services)
- [23. Generation and adapter architecture](#23-generation-and-adapter-architecture)
- [24. Python and LLM adapter profile](#24-python-and-llm-adapter-profile)
- [25. Structural validation and compatibility](#25-structural-validation-and-compatibility)
- [26. DuckDB query and materialization plane](#26-duckdb-query-and-materialization-plane)

### Delivery and review

- [27. End-to-end continuous reconciliation loop](#27-end-to-end-continuous-reconciliation-loop)
- [28. Minimal vertical slice](#28-minimal-vertical-slice)
- [29. Proposed implementation stages](#29-proposed-implementation-stages)
- [30. Required conformance properties](#30-required-conformance-properties)
- [31. Review decisions required](#31-review-decisions-required)
- [32. Source normalization map](#32-source-normalization-map)
- [33. Compact normative formulation](#33-compact-normative-formulation)
- [34. Proposed decision](#34-proposed-decision)

## 1. Proposal

Cuestrap SHOULD be implemented as a continuously evaluated governed-repository controller with this normalized contract:

```text
Cuestrap
    = one shared OSCAL-centered typed semantic graph
    + immutable graph checkpoints and ordered transition events
    + a pinned deterministic CUE/Go transition kernel
    + qualified executable assessment procedures
    + independently evidenced System A and System B partitions
    + DuckDB semantic and temporal materializations
    + a qualified Marimo continuous reactive DAG
    + continuously derived authorization posture
    + accountable parent authorization and risk acceptance
    + bounded one-use execution capabilities
    + continuously refreshed OSCAL lifecycle projections
    + constrained Git settlement and publication
```

The official OSCAL models remain the portable governance and lifecycle representation. CUE owns executable semantic closure, transition admissibility, assessment relations, posture derivation, and effect constraints. Git and cryptographic digests own exact source, graph-checkpoint, event-segment, artifact, receipt, and publication identity.

System A and System B are evidence partitions in the same graph. They MUST remain independently sourced and independently concluded, but they MUST NOT be modeled as unrelated semantic universes. Their conclusions compose through typed relations over shared subjects, operation identities, graph revisions, policy revisions, procedure revisions, and event cutoffs.

## 2. Review objectives

This proposal resolves the following recurring ambiguities:

1. **Bounded operation versus continuous ATO** — bounded operations are effect transactions inside a larger continuously evaluated semantic and authorization system.
2. **System A versus System B** — they are independently evidenced partitions and views of one graph, not competing authorities or isolated state stores.
3. **OSCAL versus CUE** — OSCAL owns lifecycle representation and stable governance identity; CUE owns executable semantic relations and admissibility.
4. **JSONL telemetry versus the canonical event ledger** — host rollout JSONL is an input source. Canonical semantic events are immutable, normalized, qualified records in the graph-transition ledger.
5. **DuckDB and Marimo authority** — DuckDB materializes; Marimo orchestrates reactive dependencies. Neither owns semantic conclusions.
6. **Procedure qualification versus live assessment** — proof that a procedure is trustworthy is distinct from evidence produced by one invocation of that procedure.
7. **Formal authorization versus derived posture** — accountable authority accepts risk; the controller continuously derives and enforces technical posture and delegated operating conditions.
8. **Reactive recomputation versus actuation** — graph recomputation may narrow authority immediately, but it cannot directly execute a mutation.
9. **Component Definition as API** — the official Component Definition plus the Cuestrap CUE profile is the canonical capability publication surface; generated transports are subordinate projections.

## 3. Non-goals

The architecture is not:

- an autonomous authorizing official;
- a replacement for organizational risk acceptance;
- a mutable notebook whose cells are the authoritative compliance record;
- a database-led governance model in which SQL rows redefine OSCAL or CUE meanings;
- a second workflow ledger that competes with Git and immutable event segments;
- a model-driven replanner with unrestricted action synthesis;
- an independently authored OpenAPI, GraphQL, Pydantic, or finite-state-machine authority;
- a universal interception layer for every host tool;
- a claim that successful execution retroactively authorizes initiation;
- a system in which a metric breach, stream event, or reactive invalidation directly performs an effect.

## 4. Core invariants

### 4.1 One semantic graph

All authority-bearing normative, implementation, qualification, assessment, execution, risk, remediation, and posture facts MUST be representable in one typed semantic graph. Partitions preserve authority and provenance; they do not create separate meanings for the same subject.

### 4.2 Event-sourced graph advancement

Every causal graph change MUST be represented by an immutable ordered transition event. The accepted graph revision MUST be reproducible from a qualified checkpoint, ordered events, and pinned policy, procedure, and kernel identities.

### 4.3 Frozen before qualified

Any proposal, event, procedure, evidence manifest, graph delta, posture conclusion, capability grant, or publication request that may influence authority MUST be normalized, frozen, and content-addressed before qualification.

### 4.4 No authority by successful execution

Successful model inference, SQL execution, notebook execution, tool invocation, test result, or shell exit status MUST NOT by itself establish admission, evidence, conformance, settlement, posture, or publication authority.

### 4.5 Reactive non-actuation

A new event MAY invalidate descendants, recompute metrics, create findings, narrow posture, suspend a delegated envelope, or construct a remediation proposal. It MUST NOT directly execute a mutation. Effects require a separate admitted capability.

### 4.6 Qualified procedures only

An assessment conclusion is authoritative only when produced by an exact currently qualified procedure, evaluator, policy revision, subject revision, and evidence cutoff. A stale or unavailable procedure produces an unavailable or indeterminate conclusion, never implicit satisfaction.

### 4.7 No derived parallel authority

DuckDB rows, Marimo values, GUAC identifiers, generated classes, dashboards, policy-engine output, model scores, and provider-native structured output are reconstructable projections or observations. They MUST NOT redefine graph, OSCAL, CUE, Git, event, or accountable-authority truth.

### 4.8 Provenance-preserving composition

System A and System B facts MAY compose only while their independent source references, graph revisions, policy revisions, procedure identities, event cutoffs, and evidence manifests remain visible and compatible.

## 5. Authority hierarchy

| Tier | Authority | Canonical responsibility |
|---|---|---|
| 0 | Git OIDs and cryptographic digests | Exact repository, graph checkpoint, event segment, artifact, receipt, and attestation identity |
| 1 | Accountable authorization records and official OSCAL resources | Organizational authorization, risk acceptance, governance objects, lifecycle identity, controls, implementations, assessments, risks, and remediation |
| 2 | CUE contracts through the qualified Go facade | Graph integrity, transition relations, procedure semantics, evidence qualification, posture derivation, effect bounds, and publication requirements |
| 3 | Qualified operational evidence | Observations, receipts, attestations, SBOMs, tests, counterexamples, assessment invocations, and System A/System B conclusions |
| 4 | Canonical graph checkpoints and event ledger | Reproducible causal history and current semantic state |
| 5 | Materialized projections | DuckDB, GUAC, indexes, caches, metrics, analytical views, and Marimo values |
| 6 | Generated transport surfaces | Go/Python types, Pydantic, Hypothesis, JSON Schema, OpenAPI, GraphQL, CLI, MCP, reports, and dashboards |

A higher-numbered tier MAY be regenerated or replaced. It MUST NOT redefine a lower-numbered tier.

## 6. Identity model

Cuestrap MUST preserve distinct identity domains.

| Identity | Meaning |
|---|---|
| OSCAL UUID | Stable lifecycle and governance identity |
| CUE identifier | Stable contract vocabulary and relation identity |
| Git blob/tree/commit OID | Exact content and coherent repository-state identity |
| Graph revision digest | Exact semantic graph closure after an accepted event cutoff |
| Policy revision digest | Exact transition, assessment, posture, and authorization-condition rules |
| Kernel revision digest | Exact CUE/Go evaluator implementation and build identity |
| Event segment digest and position | Exact causal ledger source and ordered cutoff |
| Procedure qualification receipt | Proof that one assessment procedure revision is trusted for a bounded domain |
| Assessment invocation receipt | Evidence and result for one concrete procedure execution |
| Projection receipt | Exact projector, input revision/cutoff, output artifact, and schema identity |
| Capability grant digest | Exact narrowed authority for one effect transaction |

```cue
#SemanticCoordinate: close({
    subjectRef:       #Reference
    graphRevision:    #Digest
    policyRevision:   #Digest
    kernelRevision:   #Digest
    eventCutoff:      #EventPosition
    repositoryCommit?: #Digest
})
```

Mutable names such as `main`, a workbook session name, a database filename, or a dashboard URL MAY aid discovery but MUST resolve to immutable coordinates before qualification.

## 7. Shared typed semantic graph

The graph SHOULD expose at least these authority-bounded partitions.

### 7.1 Normative partition

- OSCAL catalogs, profiles, controls, objectives, parameters, constraints, procedures, and required evidence;
- CUE relation and policy identities;
- authorization-condition vocabulary and transition classes.

### 7.2 Implementation partition

- components, capabilities, services, inventories, repositories, workbooks, dependencies, implementation statements, responsibility assignments, and inheritance relationships;
- target state and relevant-state projections.

### 7.3 Qualification partition

- assessment procedure specifications;
- generators, witnesses, mutation classes, negative fixtures, metamorphic properties, evaluator identities, qualification plans, and qualification receipts.

### 7.4 System A partition

- target subjects and snapshots;
- implementation observations;
- control-objective results;
- findings, risks, remediation state, and resulting target conclusions.

### 7.5 System B partition

- operation orders, proposals, parent decisions, capability grants, hook ingress, rollout records, dispatch/start/terminal records, controller claims and receipts, continuity epochs, conformance, and effect attribution.

### 7.6 Governance partition

- formal authorization records;
- authorization conditions and expiry;
- derived technical posture;
- delegated operating envelope;
- references to independent System A and System B conclusions;
- joint operation conclusions and settlement dispositions.

A graph node or relation MUST retain its authority owner, source references, revision coordinates, and evidence status. A derived correlation MUST NOT erase the independent provenance of its operands.

## 8. OSCAL lifecycle projections

OSCAL artifacts are continuously refreshed, governed projections of exact graph revisions and event cutoffs.

| OSCAL resource | Graph projection role |
|---|---|
| Catalog | Normative controls, objectives, properties, and assessment expectations |
| Profile | Selected, parameterized, tailored, and scoped requirements |
| Component Definition | Reusable capabilities, control implementations, operation publication, and supporting evidence references |
| System Security Plan | Concrete system, deployment, responsibility, inheritance, component, inventory, and implementation state |
| Assessment Plan | Qualified assessment procedures, subjects, tasks, evidence contracts, methods, and timing |
| Assessment Results | Concrete assessment invocations, observations, findings, risks, limitations, and System A/System B conclusions |
| POA&M | Open deficiencies, milestones, remediation obligations, owners, deadlines, and reassessment requirements |
| Authorization package records | Accountable authorization decision, accepted risks, conditions, expiry, and delegated operating envelope |

Every projection MUST bind:

```cue
#OSCALProjectionReceipt: close({
    model:             string & != ""
    graphRevision:     #Digest
    policyRevision:    #Digest
    eventCutoff:       #EventPosition
    projectorRevision: #Digest
    sourceSetDigest:   #Digest
    artifactDigest:    #Digest
    validationReceipt: #Digest
})
```

OSCAL artifacts MUST validate against official schemas outside the semantic kernel. CUE MUST evaluate the bounded semantic projection, not reproduce the entire official schema.

## 9. System decomposition

### 9.1 Semantic graph and transition kernel

The graph and pinned CUE/Go kernel own deterministic semantic state advancement. They do not execute effects or accept organizational risk.

### 9.2 System A evidence partition

System A observes and assesses the governed target: repository, worktree, workbook, component, OSCAL implementation, and resulting technical state. It produces target eligibility and outcome conclusions from independently qualified evidence.

### 9.3 System B evidence partition

System B observes and assesses the execution plane: proposal, admission, dispatch, continuity, tool behavior, controller receipts, terminal state, conformance, and effect attribution. Hook and rollout telemetry are source branches within this partition.

### 9.4 DuckDB analytical plane

DuckDB materializes revision-bound graph, event, temporal, metric, assessment, risk, posture, and projection relations. It is reconstructable and non-authoritative.

### 9.5 Marimo reactive plane

Marimo owns the actual live Python dependency DAG: source cursors, graph-fold invocation, materialization refresh, affected-subject selection, metric windows, procedure invocation, posture refresh, OSCAL previews, and review surfaces. It does not own semantic conclusions or mutation authority.

### 9.6 Parent and accountable authority

The parent qualifies one exact operation order and authorizes one exact bounded bundle. The accountable authorizing authority owns formal system authorization and risk acceptance. Neither may manufacture missing technical evidence.

## 10. Graph revisions, snapshots, and checkpoints

The controller MUST distinguish:

- **repository snapshot** — exact Git and relevant live-target state;
- **graph checkpoint** — complete content-addressed semantic graph closure at an event cutoff;
- **operation base** — target and graph state against which an operation was constructed;
- **prior settled checkpoint** — last fully settled graph, target, posture, OSCAL, and publication state;
- **candidate checkpoint** — proposed resulting state before settlement;
- **projection checkpoint** — rebuildable DuckDB or OSCAL projection bound to a graph revision.

```cue
#GraphCheckpoint: close({
    graphRevision:  #Digest
    policyRevision: #Digest
    kernelRevision: #Digest
    eventCutoff:    #EventPosition
    repository?:    #RepositorySnapshot
    rootSetDigest:  #Digest
    nodeSetDigest:  #Digest
    edgeSetDigest:  #Digest
    createdBy:      #QualifiedProcedureReference
})
```

A checkpoint MUST NOT advance merely because a job completed. It advances only after all required graph, evidence, posture, projection, and publication conditions settle.

## 11. Event ledger and transition protocol

### 11.1 Canonical transition events

The canonical event ledger is the causal memory of the semantic graph.

```cue
#TransitionEvent: close({
    eventID:  string & != ""
    sequence: uint64
    occurredAt?: string
    admittedAt:  string

    context: close({
        priorGraphRevision: #Digest
        policyRevision:     #Digest
        kernelRevision:     #Digest
    })

    sourceRefs: [#RawRecordReference, ...#RawRecordReference]
    transition: #Transition
    decision?:  #TransitionDecision
    result?:    #ObservedResult
    evidence:   [...#EvidenceReference]

    nextGraphRevision?: #Digest
})
```

Raw host events become canonical semantic events only after deterministic normalization, source binding, identity reconciliation, schema validation, and transition admission.

### 11.2 Immutable event segments

The durable ledger SHOULD use immutable checksummed segments rather than one indefinitely mutable file.

```text
events/
  000000000001-000000001000.jsonl
  000000001001-000000002000.jsonl
  000000002001-000000003000.jsonl
```

Each segment MUST bind sequence range, previous-segment digest, schema revision, record count, byte length, content digest, and sealing receipt. A trailing partial record is never admitted.

### 11.3 Deterministic graph fold

```text
checkpoint₀ + event₁ → revision₁
revision₁  + event₂ → revision₂
revision₂  + event₃ → revision₃
```

For identical checkpoint, ordered event set, policy revision, procedure set, and kernel revision, batch replay and incremental streaming MUST produce the same graph revision and conclusions.

### 11.4 Transition request and decision

A transition proposal MUST identify the actor, subjects, operation, prior graph, policy, event cutoff, repository snapshot, reads, effects, evidence requirements, and requested resulting state. Qualification MUST return an explicit admitted, denied, unavailable, or indeterminate result with a receipt.

## 12. Admission law

Governed admission for a bounded effect is:

```text
governed admission
= current graph and repository identities
∧ current policy and kernel identities
∧ current qualified assessment procedures
∧ System A technical eligibility
∧ System B readiness and trusted continuity
∧ qualified tactical conclusion
∧ authorization posture permits the operation
∧ exact accountable authorization conditions remain valid
∧ exact parent decision authorizes the bundle
∧ requested effects fit a narrowed capability
∧ no identity, evidence, event, or projection conflict remains
```

Admission is prospective. A later successful outcome cannot repair missing initiation authority. Restrictive evidence MAY narrow or suspend authority immediately when its provenance and applicability are qualified. Expansive authority requires complete qualification and accountable authority where required.

## 13. Effect and capability model

Effects MUST be expressed as a closed mutation vocabulary rather than ambient tool access.

```cue
#CapabilityGrant: close({
    grantID:            #Digest
    actorRef:           #Reference
    operationRef:       #Reference
    graphRevision:      #Digest
    policyRevision:     #Digest
    eventCutoff:        #EventPosition
    repositorySnapshot: #RepositorySnapshot
    authorizationRef:   #Reference
    parentDecisionRef:  #Reference
    allowedEffects:     [#Effect, ...#Effect]
    deniedEffects:      [...#Effect]
    executionEpoch:     #Digest
    expiresAt:          string
    maximumUses:        1
})
```

The executor MUST reject stale graph, policy, event, repository, authorization, or epoch coordinates. Attempts outside the grant MUST be rejected and recorded. Object construction and authoritative reference movement remain separate privileges.

## 14. Authorization decision and continuous posture

### 14.1 Formal authorization

Formal authorization and risk acceptance belong to an accountable organizational authority and are represented in governed authorization records. CUE may verify their structure, scope, identity, conditions, and applicability; it does not invent the decision.

### 14.2 Continuously derived posture

The controller continuously derives the technical posture under the current formal authorization.

```cue
#AuthorizationPostureState:
    "authorized" |
    "conditional" |
    "suspended" |
    "revoked" |
    "indeterminate"

#AuthorizationPosture: close({
    subjectRef:          #Reference
    graphRevision:       #Digest
    policyRevision:      #Digest
    kernelRevision:      #Digest
    eventCutoff:         #EventPosition
    authorizationRef:    #Reference

    state: #AuthorizationPostureState

    satisfiedControlRefs: [...#Reference]
    blockingFindingRefs:  [...#Reference]
    openRiskRefs:         [...#Reference]
    expiringEvidenceRefs: [...#Reference]
    activeConditionRefs:  [...#Reference]
    continuityGapRefs:    [...#Reference]

    delegatedEnvelope: #CapabilityEnvelope
    derivedBy:         #QualifiedProcedureReference
    receipt:           #AssessmentInvocationReceipt
})
```

A posture may transition continuously, for example:

```text
authorized  + forbidden mutation      → suspended
authorized  + evidence expiry         → conditional or indeterminate
conditional + qualified remediation   → authorized
any posture + unresolved continuity gap → indeterminate or suspended
formal revocation                     → revoked
```

The posture constrains the next operation and delegated envelope. It does not replace the formal authorization record.

## 15. Evidence and provenance boundary

Raw output becomes evidence only through explicit binding and qualification.

```text
raw source record
    → immutable source reference and digest
    → deterministic normalization
    → graph subject and claim binding
    → qualified assessment procedure
    → concrete assessment invocation receipt
    → observation, finding, risk, remediation, or posture fact
```

Every evidence item SHOULD bind producer, subject, claim, graph revision, policy revision, kernel revision, event cutoff, procedure qualification, concrete invocation, toolchain, source bytes, artifact digests, trust epoch, and retention status.

### 15.1 Procedure qualification

Second-order evidence answers: **Is this assessment procedure trustworthy for this bounded domain?**

```cue
#AssessmentProcedureQualification: close({
    procedureRevision: #Digest
    semanticRelation:  #Reference
    evaluatorIdentity: #Digest
    generatorRevision: #Digest
    propertySetDigest: #Digest
    witnessSetDigest:  #Digest
    mutationSetDigest: #Digest
    negativeSetDigest: #Digest
    outcome: "qualified" | "qualified-with-limitations" | "not-qualified"
    limitations: [...string]
    receiptDigest: #Digest
})
```

### 15.2 Concrete assessment invocation

First-order evidence answers: **What did the qualified procedure conclude for this subject, graph revision, and event window?**

A qualification receipt MUST NOT substitute for a concrete assessment receipt. A successful invocation MUST NOT qualify its own procedure.

## 16. Continuous OSCAL ATO semantic graph and reactive DAG

This section defines the architectural center omitted by a telemetry-only design.

### 16.1 Continuous evaluation loop

```text
new source record or scheduled time boundary
    → immutable raw-record capture
    → canonical semantic event proposal
    → event admission and deterministic graph fold
    → graph revision advances
    → DuckDB revision-bound relations update
    → Marimo invalidates affected descendants
    → affected metrics and windows recompute
    → qualified assessment procedures execute
    → observations, findings, risks, and POA&M obligations update
    → authorization posture and delegated envelope update
    → affected OSCAL lifecycle projections refresh
    → next bounded operation is evaluated against the new posture
```

This loop operates continuously even when no mutation is authorized. Observation, assessment, posture derivation, and projection are distinct from actuation.

### 16.2 Streaming evaluation classes

The continuous evaluator MUST support four classes without creating different semantic kernels.

#### Stateless evaluation

One admitted event contains sufficient facts for a conclusion, such as a forbidden mutation attempt or malformed authoritative record.

#### Keyed stateful evaluation

Evaluation accumulates state keyed by component, control, objective, evidence requirement, repository, actor, operation, finding, risk, POA&M item, authorization package, or other closed subject identity.

#### Windowed evaluation

Policies may operate over event time, processing time, or explicit graph/event ranges, including:

- evidence not supplied before a deadline;
- evidence nearing or passing expiry;
- vulnerability or finding not remediated within its allowed interval;
- repeated denied or failed transitions;
- excessive correction attempts;
- stale policy or procedure execution;
- unclosed tool requests or claims;
- recurring state oscillation;
- sustained metric threshold violation.

Window definitions, watermark policy, late-event policy, and correction semantics MUST be explicit and revisioned.

#### Lifecycle and sequence evaluation

The evaluator MUST verify valid state paths, for example:

```text
declared → implemented → evidenced → assessed → authorized
```

An event attempting to skip required states MUST be denied or produce an indeterminate conclusion. The lifecycle is a CUE relation over typed graph states, not an independently authored Python or SQL state machine.

### 16.3 Qualified dynamic DAG

The Marimo DAG itself is a qualified artifact. Every node MUST declare:

- closed input and output contracts;
- semantic or mechanical role;
- source and revision dependencies;
- preconditions and postconditions;
- deterministic identity;
- idempotency or compensation behavior;
- timeout, retry, failure, and partial-output semantics;
- whether it may publish a projection, propose an effect, or only observe.

Every edge MUST declare:

- producer/consumer compatibility;
- cardinality and ordering;
- stale, missing, duplicate, delayed, conflicting, and late-event behavior;
- revision and migration compatibility;
- invalidation propagation.

No node publishes merely because it ran. Authority-bearing output publishes only when input proofs, transformation properties, output assertions, procedure qualification, and execution receipt all qualify.

### 16.4 Marimo continuous DAG topology

The canonical workbook SHOULD expose this dependency topology:

```text
event segment and graph-checkpoint cursor
    → source integrity and complete-record validation
    → canonical event normalization and admission
    → deterministic graph-fold request
    → graph revision and changed-subject set
    → DuckDB incremental materialization
    → affected keyed state and temporal windows
    → due assessment-procedure invocations
    → CUE assessment conclusions and receipts
    → observations, findings, risks, and POA&M deltas
    → authorization-posture derivation
    → delegated-envelope derivation
    → OSCAL projection manifests and previews
    → settlement and review blockers
```

Representative live cells SHOULD expose:

- current graph, policy, kernel, procedure-set, repository, and event-cutoff identities;
- segment integrity and incomplete-tail status;
- changed and affected graph subjects;
- control applicability and implementation state;
- evidence freshness and missing evidence;
- current metric windows and violations;
- due, running, failed, stale, and completed assessment invocations;
- findings, risks, POA&M deadlines, and remediation candidates;
- System A and System B conclusions with separate provenance;
- current authorization posture and delegated envelope;
- OSCAL projection receipts and structural-validation status;
- unresolved conflicts, gaps, stale descendants, and settlement blockers.

Interactive and browserless execution MUST use the same DAG and produce equivalent revision-bound results.

### 16.5 Deterministic transition kernel

Marimo, DuckDB, or a production streaming runtime MAY schedule evaluation, retain keyed state, manage watermarks, and select affected procedures. The actual graph transition, procedure relation, posture derivation, and lifecycle conclusion MUST use the same pinned CUE/Go kernel.

A future Flink-, Spark-, Storm-, or equivalent runtime MAY replace scheduling mechanics only if batch, incremental, replay, and Marimo results remain equivalent over the qualified corpus.

### 16.6 Continuous metrics

A metric is a typed graph projection with an explicit subject, formula, source set, window, cutoff, policy revision, and receipt. A metric threshold breach is evidence for an assessment procedure; it is not itself an authorization decision unless the governing CUE relation explicitly derives the corresponding posture transition.

### 16.7 Continuous OSCAL projection

After each settled graph revision, only affected OSCAL projections need recomputation. The projector MUST preserve stable OSCAL UUIDs, source links, graph/event coordinates, and prior artifact lineage. A continuously updated Assessment Results or POA&M artifact is a lifecycle view of graph state, not the raw event journal.

### 16.8 Continuous ATO completion gate

The architecture MUST NOT be described as continuous ATO until the following are implemented and qualified:

```text
one shared semantic graph
∧ immutable event segments and graph checkpoints
∧ deterministic batch/incremental graph fold
∧ qualified assessment procedures
∧ stateless, keyed, windowed, and lifecycle evaluation
∧ revision-bound DuckDB materialization
∧ qualified Marimo dynamic DAG
∧ findings, risks, POA&M, and evidence-freshness advancement
∧ continuously derived authorization posture
∧ delegated-envelope enforcement
∧ continuous OSCAL projection receipts
∧ replay, restart, late-event, conflict, and stale-procedure tests
```

## 17. System B runtime telemetry and hook reconciliation

System B runtime telemetry is one source branch feeding the continuous graph. It is not the architecture's semantic center.

```text
Codex rollout JSONL ───────────────────────────────┐
PreToolUse/PostToolUse provisional ingress ───────┤
operation-controller request/claim/receipt ────────┤
target-workbook observations ──────────────────────┤
parent decisions and capability grants ────────────┘
                         ↓
          deterministic source normalization
                         ↓
          canonical System B event proposals
                         ↓
             graph-transition admission
```

### 17.1 Source precedence

1. The committed complete prefix of the host rollout is the primary host runtime record.
2. Operation-controller request, binding, claim, release, and receipt records are controller-side execution evidence.
3. Hook ingress is provisional low-latency evidence.
4. Canonical graph events exist only after reconciliation and admission.
5. DuckDB and Marimo views remain rebuildable projections.

### 17.2 Complete-prefix contract

The reader MUST stop at the final complete newline-delimited record, retain exact byte ranges and raw digests, detect replacement/truncation/rotation, advance its cursor only after durable ingestion, and close or suspend continuity on unexplained discontinuity.

```cue
#RolloutPrefix: close({
    sourceIdentity: string & != ""
    generation:     string & != ""
    byteStart:      uint
    byteEnd:        uint
    completeEnd:    uint
    recordCount:    uint
    prefixDigest:   #Digest
    previousDigest?: #Digest
    completeLinesOnly: true
})
```

### 17.3 Provisional reconciliation

```text
PreToolUse received              → provisional-pre
matching rollout proposal        → pre-reconciled
dispatch/start evidence          → dispatched
PostToolUse received             → provisional-terminal
matching rollout terminal        → terminal-reconciled
controller receipt bound         → effect-correlated
all identities and records agree → continuity-preserved
```

The following remain explicit: unmatched provisional events, coverage gaps, semantic identity conflict, dispatch missing, claim without receipt, terminal conflict, unsupported controlled event, source discontinuity, and late contradictory evidence.

Provisional ingress MAY impose fail-closed restrictions. It MUST NOT expand authority before canonical reconciliation and exact parent composition.

### 17.4 System B evidence manifest

The qualified manifest SHOULD bind rollout prefix, canonical-event set, hook overlay, controller records, continuity epoch, pending operations, conflicts, operation base, candidate, procedure identities, projection receipt, and exact graph/policy/event coordinates. Native CUE produces readiness, continuity, conformance, and attribution conclusions from that manifest.

## 18. Settlement

Admission to execute is not settlement. Settlement advances the prior-settled checkpoint only when the continuous graph and the bounded operation agree.

```text
candidate operation admitted
    → effect executed under one-use capability
    → runtime records reconciled into canonical events
    → graph revision advances
    → System A independently recaptured
    → System B conformance and attribution assessed
    → affected findings, risks, metrics, and posture recomputed
    → affected OSCAL projections validated
    → publication qualification succeeds
    → prior-settled checkpoint advances
```

Settlement requires:

- exact operation, graph, policy, event, repository, capability, and epoch identities;
- required runtime records and receipts;
- no unresolved identity, continuity, or terminal conflict;
- current qualified procedures;
- settled Marimo descendants and DuckDB projection receipt;
- independently qualified System A outcome and System B conformance;
- qualified effect attribution;
- recomputed findings, risks, POA&M, and posture;
- valid OSCAL projection receipts;
- successful constrained Git publication.

Possible states SHOULD include `proposed`, `qualified`, `running`, `stale`, `indeterminate`, `failed`, `assessed`, `held`, `settled`, and `published`.

## 19. Reactive playbook model

Playbooks are typed graph-mutation plans, not arbitrary scripts.

A playbook MUST declare:

- selected subjects and graph revision;
- required control, evidence, and posture predicates;
- exact nodes and edges to add, remove, or replace;
- allowed mutation classes;
- expected metric, finding, risk, or posture consequences;
- required assessment procedures;
- failure and compensation semantics;
- settlement criteria.

DSPy or another model MAY rank only pre-admitted playbooks. It MUST NOT create a new mutation vocabulary, bypass posture constraints, or convert an ineligible plan into an eligible one.

Reactive recomputation MAY construct or reprioritize remediation proposals. A proposal becomes effectful only through the normal transition, authorization, and capability path.

## 20. Failure, correction, extraction, and continuity

Failures are graph facts and event records, not exceptions to governance.

The system MUST distinguish:

- semantic denial;
- unavailable evaluator or procedure;
- transport failure;
- dispatch not observed;
- execution failure;
- result conflict;
- continuity gap;
- stale graph or projection;
- effect-attribution uncertainty;
- target regression;
- posture suspension or revocation.

A bounded correction MUST change at least one qualified dimension: request, relevant state, graph revision, evidence, procedure, policy, capability, or parent order. Repeating an identical failed operation without new evidence is not progress.

A material objective, topology, accepted-risk, authority, or scope change ends the current operation boundary and requires a fresh qualified order. Knowledge extraction MAY preserve observations, counterexamples, and remediation candidates without carrying forward stale authority.

## 21. Constrained Git mutation and publication boundary

Git performs two distinct roles:

1. immutable identity and storage for source, checkpoints, segments, artifacts, evidence, and receipts;
2. constrained mutation and publication through explicit capabilities.

The Git adapter MUST separate:

- object construction;
- index/worktree mutation;
- commit construction;
- reference movement;
- remote publication.

A capability to construct a commit MUST NOT imply authority to move `main`. A capability to update one authorized reference MUST NOT imply arbitrary repository write access.

Publication MUST verify expected current reference, exact new commit, allowed ancestry, authorized target, graph and event coordinates, settlement receipt, and no conflicting concurrent change.

## 22. Supply-chain and evidence services

SBOMs, attestations, provenance, vulnerability intelligence, GUAC, and policy services provide evidence and correlation.

- SBOMs identify components and dependencies.
- Attestations bind claims to exact subjects and producers.
- GUAC or equivalent services propose correlations and graph indexes.
- Vulnerability and policy services produce source-bound observations.
- Minder or similar engines MAY generate candidate findings or enforcement observations.

No service independently establishes canonical equivalence, control satisfaction, authorization posture, or publication authority. Its output enters the graph through qualified evidence and transition relations.

## 23. Generation and adapter architecture

Generation is one-way from canonical contracts.

```text
OSCAL identities and lifecycle resources
        +
CUE graph, transition, procedure, and operation contracts
        ↓
closed intermediate representation
        ├── Go types and facade bindings
        ├── Python/Pydantic transport models
        ├── Hypothesis strategies and mutations
        ├── JSON Schema/OpenAPI/GraphQL projections
        ├── CLI and MCP adapters
        ├── DuckDB DDL and projection bindings
        └── reports and dashboards
```

Generated artifacts MUST record source contract revision and generator revision. Hand-edited generated output MUST fail drift checks. Generated validators MAY reject structurally invalid input but MUST revalidate through CUE before an authority-bearing conclusion.

## 24. Python and LLM adapter profile

Python MAY own:

- bounded collection and framing;
- Pydantic ingress/egress closure;
- deterministic normalization;
- Marimo DAG orchestration;
- DuckDB transactions;
- source correlation;
- graph-fold and procedure facade invocation;
- rendering and diagnostics.

Python MUST NOT own canonical graph semantics, procedure conclusions, posture derivation, authorization, or publication authority.

LLM tooling MAY:

- extract candidate structured records;
- suggest identity matches;
- rank admitted playbooks;
- draft remediation descriptions;
- summarize evidence and diagnostics.

Every model output MUST be treated as untrusted candidate data, constrained to a closed schema, provenance-bound, and revalidated. Model confidence is not evidence quality.

## 25. Structural validation and compatibility

The system MUST pin and record:

- OSCAL schema and content revisions;
- CUE language, module, source, and binary revisions;
- Go facade and build identity;
- graph and event schema revisions;
- procedure and property-set revisions;
- DuckDB schema and projector revisions;
- Marimo workbook and runtime revisions;
- generated adapter revisions.

Full OSCAL documents validate through official schemas. Bounded semantic subjects validate through CUE. Compatibility MUST be explicit for graph migrations, event schemas, procedure revisions, projector revisions, and replay across kernel versions.

An incompatible migration MUST produce an explicit unavailable or migration-required state. It MUST NOT silently reinterpret prior evidence or events.

## 26. DuckDB query and materialization plane

DuckDB SHOULD materialize the entire continuous semantic and authorization context, not only tool telemetry.

### 26.1 Required relation families

| Family | Example relations |
|---|---|
| Revision and provenance | `graph_revisions`, `graph_checkpoints`, `event_segments`, `events`, `projection_receipts` |
| OSCAL normative | `catalogs`, `profiles`, `controls`, `control_objectives`, `parameters` |
| Implementation | `components`, `capabilities`, `subjects`, `resources`, `implementations`, `responsibilities` |
| Qualification | `procedure_specs`, `qualification_plans`, `qualification_receipts`, `procedure_properties` |
| Assessment | `assessment_invocations`, `observations`, `objective_results`, `assessment_receipts` |
| System B runtime | `raw_runtime_records`, `hook_ingress`, `rollout_prefixes`, `controller_records`, `action_correlations`, `continuity_epochs` |
| Risk and remediation | `findings`, `risks`, `poam_items`, `milestones`, `remediation_deadlines` |
| Continuous metrics | `metric_definitions`, `metric_samples`, `metric_windows`, `metric_violations` |
| Authorization | `authorization_decisions`, `authorization_conditions`, `authorization_postures`, `delegated_envelopes` |
| OSCAL projections | `projection_manifests`, `projection_artifacts`, `validation_receipts` |

Every authority-relevant row MUST be coordinateable to graph revision, policy revision, event cutoff, source identity, and projector revision.

### 26.2 Incremental transaction

```text
lock current projection cursor
    → verify checkpoint and segment chain
    → ingest new immutable records idempotently
    → request deterministic graph fold
    → persist new graph revision
    → compute changed and affected subjects
    → refresh semantic and temporal relations
    → refresh keyed and windowed metrics
    → enqueue due qualified procedures
    → persist procedure and posture results
    → persist OSCAL projection manifests
    → emit projection receipt
    → atomically advance cursor
```

A failure MUST leave the previous cursor and materialization valid. Full rebuild and incremental update MUST be equivalent for the same revision and cutoff. Corruption or incompatible schema requires rebuild or explicit unavailability.

SQL queries MAY select facts and construct closed CUE subjects. They MUST NOT directly manufacture `satisfied`, `eligible`, `conformant`, `authorized`, `settled`, or equivalent semantic conclusions.

## 27. End-to-end continuous reconciliation loop

```text
1. Resolve current repository, graph, policy, kernel, procedure, and authorization identities.
2. Capture new raw records and time boundaries.
3. Seal or extend the next immutable event segment.
4. Normalize and reconcile source records into canonical event proposals.
5. Evaluate event admission through CUE.
6. Fold accepted events into the next graph revision.
7. Persist the graph revision and changed-subject set.
8. Incrementally refresh DuckDB materializations.
9. Let Marimo invalidate and recompute affected descendants.
10. Run due qualified assessment procedures.
11. Advance observations, findings, risks, POA&M, metrics, and posture.
12. Refresh affected OSCAL lifecycle projections.
13. Construct eligible bounded transition proposals against the current posture.
14. Qualify System A, System B, tactical, accountable-condition, and parent inputs.
15. Issue one narrowed capability.
16. Execute and collect request, claim, dispatch, terminal, and receipt evidence.
17. Reconcile execution records into canonical events.
18. Independently recapture System A and assess System B.
19. Recompute graph, posture, and OSCAL projections.
20. Settle and publish only when all required descendants agree.
```

## 28. Minimal vertical slice

The first complete slice SHOULD prove one continuous graph advancement and one bounded effect.

1. Pin OSCAL, CUE, Go facade, graph, event, DuckDB, Marimo, and projector revisions.
2. Define one control objective, one component implementation, one evidence requirement, and one authorization condition.
3. Define one shared graph checkpoint and one repository snapshot.
4. Define and property-qualify one assessment procedure.
5. Seal one immutable event segment and fold it into a new graph revision.
6. Materialize the graph and one temporal metric in DuckDB.
7. Run the same Marimo DAG interactively and browserlessly.
8. Invoke the qualified procedure and create one assessment receipt.
9. Derive one finding or satisfied objective and one authorization-posture update.
10. Render and validate one Assessment Results update and one authorization projection receipt.
11. Reconcile one pre/post hook pair, rollout record, and controller receipt into one System B canonical event.
12. Construct and admit one bounded operation against the current posture.
13. Execute it through a one-use operation-controller capability.
14. Recapture System A, assess System B, recompute posture, and settle.
15. Publish through the constrained Git adapter.
16. Replay from the initial checkpoint and prove identical graph, DuckDB, assessment, posture, OSCAL, decision, and publication identities.
17. Preserve negative fixtures for malformed event, stale procedure, late conflict, continuity loss, and unauthorized effect.

## 29. Proposed implementation stages

### Stage 0 — Shared graph vocabulary and authority contracts

Freeze nodes, relations, partitions, revisions, procedures, posture states, capabilities, and accountable-authority boundaries.

### Stage 1 — Graph checkpoints and immutable event ledger

Implement checkpoint identity, event segments, ordering, chaining, correction events, replay cutoff, and source provenance.

### Stage 2 — Deterministic CUE/Go transition kernel

Implement graph folding, transition admission, changed-subject output, and batch/incremental/replay equivalence.

### Stage 3 — Qualified assessment procedures

Implement procedure specs, property schemes, generated witnesses and mutations, qualification plans, receipts, and concrete invocation contracts.

### Stage 4 — DuckDB semantic and temporal materialization

Implement revision-bound graph relations, keyed state, temporal windows, evidence freshness, findings, risks, POA&M, metrics, posture, and projection receipts.

### Stage 5 — Qualified continuous Marimo DAG

Implement source, graph-fold, materialization, affected-subject, metric, procedure, posture, and OSCAL-projection cells; qualify node, edge, stale-state, retry, timeout, restart, and browserless equivalence behavior.

### Stage 6 — OSCAL lifecycle and authorization-posture projections

Render Catalog/Profile/Component/SSP/AP/AR/POA&M/authorization projections and enforce the delegated operating envelope.

### Stage 7 — System B rollout and hook reconciliation

Implement complete-prefix tailing, provisional overlays, controller correlation, continuity epochs, canonical event admission, and qualified System B procedures.

### Stage 8 — Bounded transition and constrained mutation

Implement exact parent composition, capability grants, operation-controller execution, independent System A recapture, settlement, and constrained Git publication.

### Stage 9 — Generated adapters and model integration

Generate transport surfaces and introduce constrained decoding or DSPy only over admitted alternatives.

### Stage 10 — Supply chain and production stream runtime

Add SBOM, attestations, GUAC, optional production streaming runtime, collaboration state, migration tooling, retention, and operational hardening without changing kernel semantics.

## 30. Required conformance properties

The implementation SHOULD make these executable:

1. **Deterministic graph fold** — identical checkpoint, ordered events, policy, procedures, and kernel produce the same graph revision.
2. **Batch/stream equivalence** — batch replay and incremental streaming produce equivalent graph, metric, procedure, posture, and OSCAL results.
3. **Event integrity** — missing, duplicate, reordered, conflicting, partial, or unchained events cannot silently advance authority-bearing state.
4. **One-graph provenance** — System A and System B composition preserves independent source and evidence identity.
5. **Procedure currentness** — stale, incompatible, unavailable, or unqualified procedures cannot produce authoritative conclusions.
6. **Procedure/invocation separation** — qualification and concrete operation evidence cannot substitute for one another.
7. **Incremental/rebuild equivalence** — DuckDB incremental state equals full rebuild for the same revision and cutoff.
8. **Reactive non-actuation** — no Marimo invalidation, SQL update, metric breach, posture change, or stream event directly performs an effect.
9. **DAG qualification** — every authority-bearing node and edge satisfies its declared contract.
10. **DAG settlement** — publication waits for all relevant descendants to be current, qualified, and non-conflicting.
11. **Posture traceability** — every posture binds exact graph, policy, event, procedure, authorization, finding, risk, condition, and receipt identities.
12. **Restriction monotonicity** — current qualified restrictive evidence may narrow delegated authority immediately; expansion requires complete qualification.
13. **No unauthorized mutation** — denied, unavailable, or failed traces leave protected repository and graph state unchanged.
14. **Freshness enforcement** — stale graph, policy, procedure, event cutoff, posture, repository, or capability invalidates execution.
15. **Capability confinement** — attempted effects outside the grant are rejected and recorded.
16. **Evidence non-forgery** — missing, stale, conflicting, or unreconciled evidence cannot become a positive conclusion.
17. **Continuity safety** — source discontinuity, missing terminal evidence, or restart ambiguity produces a gap, not implicit success.
18. **OSCAL projection traceability** — every artifact binds graph, policy, event, projector, source-set, and validation receipts.
19. **Settlement monotonicity** — `priorSettled` advances only after graph, runtime, assessment, posture, projection, and publication settlement.
20. **Projection rebuildability** — DuckDB, GUAC, Marimo state, reports, and generated artifacts reconstruct from checkpoints and events.
21. **Negative-witness permanence** — discovered counterexamples remain rejected unless an explicit contract revision reclassifies them.
22. **Publication isolation** — constructing objects and moving an authoritative reference remain separate privileges.

## 31. Review decisions required

### 31.1 Shared graph vocabulary

Select exact node, relation, partition, extension, and revision conventions for normative, implementation, qualification, System A, System B, and governance facts.

### 31.2 Canonical event ledger

Decide segment size, sequence allocation, digest chaining, source normalization, late-event policy, correction events, checkpoints, compaction, and retention.

### 31.3 Transition-kernel and procedure ABI

Freeze narrow Go/CUE operations for graph fold, event admission, procedure qualification, assessment invocation, posture derivation, changed-subject reporting, and OSCAL projection manifests.

### 31.4 Continuous evaluation runtime

Decide whether Marimo plus DuckDB is sufficient initially or whether a dedicated stream runtime is required for watermarks, partitioned state, event time, windows, and recovery. Any runtime MUST use the same kernel.

### 31.5 DuckDB schema and receipts

Freeze required relations, keys, revision coordinates, transaction boundaries, rebuild rules, corruption recovery, and projection-receipt format.

### 31.6 Dynamic DAG qualification

Define node and edge contracts, invalidation rules, stale-state semantics, retries, timeouts, partial results, and how source changes are proven to match admitted playbooks.

### 31.7 Assessment procedure qualification

Define property corpora, generators, mutations, negative fixtures, evaluator identity, expiry, compatibility, and invalidation rules.

### 31.8 Authorization posture semantics

Define control-satisfaction, evidence-freshness, finding/risk severity, continuity, condition-expiry, and delegated-envelope rules for `authorized`, `conditional`, `suspended`, `revoked`, and `indeterminate`.

### 31.9 OSCAL projection layout

Define repository paths and extension conventions for continuously projected Catalog, Profile, Component, SSP, AP, AR, POA&M, authorization artifacts, and receipts.

### 31.10 Runtime reconciliation

Define which hook, rollout, controller, target, parent, metric, assessment, and posture events become canonical immediately, remain raw evidence, or are summarized in checkpoints.

### 31.11 Capability representation

Choose signed value, content-addressed grant, opaque reference, or attested token representation and freeze exact Git/workbook mutation vocabularies.

### 31.12 Technology profile status

Classify DuckDB, Marimo, optional stream runtimes, GUAC, model frameworks, and adapter libraries as required, reference, optional, or deferred without coupling canonical contracts to replaceable runtimes.

## 32. Source normalization map

| Source | Retained concepts | Normalized disposition |
|---|---|---|
| `Cuestrap-Unified-Architecture.md` | OSCAL/CUE/Git authority chain, operation contracts, evidence, Git adapter, generation, vertical slice | Retained as repository-governance spine and revised around one continuously evaluated graph |
| `OSCAL-Native-API-Centric-GitOps-Architecture.md` | Component Definition API profile, OSCAL lifecycle, authorization tuple, GitOps loop, GUAC/SBOM roles | Integrated into lifecycle projections and formal-authorization versus derived-posture distinction |
| `agentic-pipeline-architecture.md` | Marimo DAG, checkpoints, settlement, playbooks, mutation algebra, DuckDB, DSPy | Expanded from bounded execution into a qualified continuous reactive DAG over graph revisions and temporal materializations |
| `awesome-llm-json.md` | Schema/runtime taxonomy and replaceable model adapters | Kept subordinate; no framework becomes semantic or authorization authority |
| Archived continuous-ATO discussions | Shared graph, event-sourced revisions, segmented JSONL, streaming classes, qualified procedures, dynamic DAG, continuous OSCAL projections, authorization posture | Promoted to the architectural center and composed with the existing bounded-operation model |
| Existing hook/controller implementation | Provisional pre/post ingress, local ledger, one-use binding/claim/receipt | Classified as a partial System B source and execution branch, not the graph or complete continuous ATO plane |

## 33. Compact normative formulation

```text
There is one shared typed semantic graph.
Every authority-bearing state is identified by graph, policy, kernel, procedure, event, and source revisions.
Every causal change enters through an immutable ordered event.
Every graph transition is applied by the pinned deterministic CUE/Go kernel.
Every live assessment uses a currently qualified procedure.
Every System A and System B fact retains independent provenance.
Every DuckDB relation, Marimo value, metric, index, report, and transport is rebuildable.
Every reactive DAG node and edge has a qualified contract.
Every reactive recomputation is non-effectful by default.
Every finding, risk, POA&M obligation, control conclusion, and posture change is receipted.
Every OSCAL artifact is a validated projection of an exact graph and event cutoff.
Every continuously derived posture enforces, but does not replace, accountable authorization and risk acceptance.
Every model sees only a pre-admitted alternative space.
Every effect is bound to a narrowed one-use capability.
Every runtime action is reconciled across required rollout, hook, controller, parent, and target evidence.
Every settled state composes target outcome, execution conformance, effect attribution, posture, OSCAL projection, and publication qualification.
No derived component becomes a parallel authority.
```

## 34. Proposed decision

Adopt this document as the architecture-review baseline with **continuous OSCAL ATO as the organizing center**.

Implementation SHOULD proceed in this order:

1. shared semantic graph vocabulary and revision identity;
2. immutable event-segment and graph-fold contract;
3. qualified assessment-procedure and invocation contract;
4. DuckDB semantic/temporal materialization and projection receipts;
5. qualified Marimo continuous-DAG contract;
6. OSCAL lifecycle projection and authorization-posture contract;
7. System B rollout/hook/controller reconciliation contract;
8. bounded transition, parent composition, capability, receipt, settlement, and constrained Git mutation contract;
9. generated adapter, supply-chain, query, and model-runtime profiles.

This ordering establishes the continuously evaluated semantic and authorization system before treating runtime hooks, notebooks, databases, or probabilistic proposal machinery as complete governance.
