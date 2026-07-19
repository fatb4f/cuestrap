
# Cuestrap: Single Architecture Digest

## 1. Core thesis

**Cuestrap is an OSCAL-native, CUE-executable, Git-backed, proof-carrying controller for governed repository state.**

```text
One semantic model    = OSCAL
One API               = OSCAL Component Definition
One constraint lattice = CUE
One authoritative log = Git and content-addressed blobs
One control loop      = GitOps reconciliation
One evidence graph    = GUAC projection
One adapter family    = generated Go, Python, CLI, MCP and transport surfaces
```

The OSCAL Component Definition is not documentation linked to a separately authored API specification.

> The OSCAL Component Definition is the governed API specification: authored as OSCAL-native values, constrained and made executable through CUE, stored as immutable Git content, and exposed through generated or bounded adapters.

```cue
#AuthoritativeAPI:
	#OfficialOSCALComponentDefinition &
	#CuestrapAPIProfile
```

OSCAL defines the governed semantic universe.

CUE defines which values, relationships, states, operations, transitions, authorizations, and publications are admissible.

Git records every authoritative revision.

---

## 2. Controlled system

Cuestrap does not primarily control an application runtime. Its controlled plant is the repository and governance graph:

```text
RepositoryState
├── Git object graph
│   ├── commits
│   ├── trees
│   ├── blobs
│   └── tags
├── reference graph
│   ├── branches
│   ├── remotes
│   └── symbolic references
├── workspace state
│   ├── index
│   ├── worktree
│   └── untracked content
├── proposal graph
│   ├── candidate commits
│   ├── virtual branches
│   └── conflict topology
├── collaboration graph
│   ├── pull requests
│   ├── reviews
│   ├── checks
│   └── publication state
├── governance graph
│   ├── controls
│   ├── capabilities
│   ├── implementations
│   ├── assessments
│   ├── findings
│   ├── risks
│   └── remediation state
└── authority context
    ├── actors
    ├── roles
    ├── protected resources
    ├── trust epochs
    └── publication policy
```

The controller observes this graph, proposes or receives a candidate transition, qualifies it, performs only the admitted mutation, and records the resulting state and evidence.

---

## 3. Authority hierarchy

```text
Level 0 — Immutable identity
    Git commit OID
    Git tree OID
    Git blob OID
    artifact digest

Level 1 — Canonical semantic authority
    OSCAL objects and UUIDs
    OSCAL Component Definition API
    CUE semantic and relational constraints
    Cuestrap profiles

Level 2 — Operational evidence
    observations
    execution receipts
    Assessment Results
    SBOMs
    provenance
    attestations
    VEX statements
    test results
    counterexamples

Level 3 — Derived graph materialization
    GUAC

Level 4 — Generated projections
    Go
    Pydantic
    Hypothesis
    JSON Schema
    OpenAPI
    GraphQL adapters
    CLI
    MCP
    reports
    dashboards
```

Higher levels may derive from lower levels but may not redefine their meaning.

GUAC node IDs, generated Python classes, OpenAPI schemas, and transport-specific resources are not canonical identities.

---

## 4. Identity model

```text
OSCAL UUID
    = stable semantic identity

CUE-qualified identifier
    = stable contract identity

Git blob OID
    = exact atomic content identity

Git tree OID
    = exact package or component closure

Git commit OID
    = coherent repository-state identity

pURL or VCS identity
    = software-package identity

attestation subject digest
    = exact claim subject identity

GUAC node ID
    = local derived index identity
```

A branch such as `main` is a mutable discovery pointer, not an authoritative version identifier.

A complete contract reference is therefore:

```text
repository
+ commit OID
+ path
+ tree or blob OID
+ OSCAL UUID
+ CUE-qualified identifier
```

Cross-domain bindings are explicit:

```cue
#IdentityBinding: {
	cueID:     string
	oscalUUID: string

	git: {
		repository: string
		commit?:    #Digest
		tree?:      #Digest
		blob?:      #Digest
	}

	purl?:               string
	sbomRef?:            string
	attestationSubject?: #Digest
}
```

Identity equivalence is admitted by CUE policy. It is not inferred authoritatively by GUAC or another adapter.

---

## 5. The OSCAL Component Definition as API

“API” includes any governed callable capability, not only HTTP endpoints.

An operation may be:

* a Go interface method;
* a CLI command;
* an MCP tool;
* a Git mutation;
* a query;
* a policy evaluation;
* an assessment procedure;
* an evidence collector;
* a workflow action;
* a remediation procedure;
* a human-governed transition.

Every operation has:

```text
identity
mode
input
output
errors
read scope
write scope
preconditions
postconditions
authorization
required evidence
produced evidence
bounded effects
state transition
control bindings
```

Conceptually:

```cue
#Operation: {
	operationID: string
	mode:        "query" | "command" | "transition"

	input:  _
	output: _
	errors: [string]: _

	reads:  [...#OscalSelector]
	writes: [...#MutationClass]

	requires: [...#Assertion]
	ensures:  [...#Assertion]

	authorization: #Authorization
	controlRefs:   [...#ControlRef]

	transition?: {
		from:       #StateConstraint
		event:      string
		to:         #StateConstraint
		invariants: [...#Assertion]
	}

	evidence: {
		required: [...#EvidenceRequirement]
		produces: [...#EvidenceType]
	}
}
```

The ergonomic operation map, generated interfaces, and transport definitions are projections of the Component Definition. They are not parallel API authorities.

---

## 6. OSCAL lifecycle as one governed API

### Catalog

The Catalog defines the governance type system:

```text
control
    = required capability or guarantee

statement
    = required behavior

parameter
    = configurable contract input

assessment objective
    = evaluable predicate
```

### Profile

The Profile specializes the API requirements through:

* control selection;
* parameter binding;
* constraint narrowing;
* organizational specialization;
* interface refinement.

```text
resolved profile
    = resolved governed API requirements
```

### Component Definition

The Component Definition publishes reusable governed capabilities and operations.

It defines:

* components;
* capabilities;
* operations;
* protocols;
* supported guarantees;
* control implementations;
* allowable effects;
* evidence requirements;
* supported transitions.

### System Security Plan

The SSP binds APIs into a concrete system context:

* selected components;
* implementation identities;
* deployment scope;
* configuration;
* dependencies;
* responsible parties;
* inherited guarantees;
* system-specific implementation claims.

### Assessment Plan

The Assessment Plan defines an evaluation contract:

* operations to exercise;
* subjects to assess;
* evaluator identities;
* test inputs;
* expected outputs;
* predicates;
* evidence requirements;
* execution conditions.

### Assessment Results

Assessment Results record qualified execution and evaluation:

```text
activity
    = operation invocation

observation
    = bound evidence

finding
    = observed behavior compared with required behavior

risk
    = consequence derived from failed or uncertain guarantees
```

### POA&M

The POA&M defines the corrective lifecycle:

```text
undesired state
+ target state
+ remediation operation
+ milestones
+ evidence requirements
+ reassessment requirement
```

Remediation execution alone does not establish closure:

```text
remediation executed
    ≠ control effectiveness verified
```

A valid lifecycle may be:

```text
risk-open
→ remediation-planned
→ remediation-authorized
→ remediation-executed
→ reassessment-pending
→ verified
→ closed
```

---

## 7. One semantic graph

The semantic graph is derived from OSCAL relationships rather than independently authored.

```text
Control
    ──requires────────────▶ Capability

Profile
    ──specializes─────────▶ Requirement

Component
    ──provides────────────▶ Operation

Operation
    ──implements──────────▶ Requirement

SSP binding
    ──instantiates────────▶ Component

Assessment task
    ──invokes─────────────▶ Operation

Observation
    ──result-of───────────▶ Invocation

Finding
    ──evaluates───────────▶ Requirement

Risk
    ──derived-from────────▶ Finding

POA&M item
    ──selects─────────────▶ Remediation Operation

SBOM
    ──describes───────────▶ Component Implementation

Attestation
    ──asserts-about───────▶ Artifact or Transition
```

Derived edges may be materialized for querying, but OSCAL UUIDs and Git identities remain authoritative.

---

## 8. One state machine

State is not maintained in an independent workflow database.

```text
current lifecycle state
    =
deterministic fold over:
    Git history
    + OSCAL lifecycle artifacts
    + qualified events
```

A desired state does not itself authorize a transition.

```text
desired-state projection
    ≠ authorized transition

reactive dependency edge
    ≠ permitted mutation edge

generated output
    ≠ admitted execution plan
```

A transition is admitted only when:

```text
valid source state
∧ pinned contract revision
∧ current source snapshot
∧ valid actor
∧ permitted operation
∧ valid input
∧ valid resource scope
∧ required evidence present
∧ transition guards satisfied
∧ effects remain bounded
∧ protected invariants hold
∧ resulting OSCAL closure satisfies postconditions
```

---

## 9. Transition contract

A transition begins from an immutable snapshot.

```cue
#TransitionRequest: {
	from: #RepositorySnapshot

	operation: #OperationRef
	input:     _
	targets:   [...#GraphIdentity]

	actor:     #ActorRef
	authority: #AuthorityContext
	evidence:  [...#EvidenceReference]
}
```

A proposal describes a candidate transition without applying it:

```cue
#TransitionProposal: {
	requestDigest: string

	preconditions:  [...#Assertion]
	operations:     [...#GraphOperation]
	postconditions: [...#Assertion]

	expected: #RepositoryProjection

	producer: {
		kind:     "dspy" | "human" | "deterministic"
		identity: string
	}

	frozen: true
}
```

Admission is conjunctive:

```text
AdmissibleTransition
    =
      source snapshot remains current
    ∧ identities resolve
    ∧ operation vocabulary is permitted
    ∧ authority closure holds
    ∧ projected state is concrete
    ∧ evidence requirements are satisfied
    ∧ protected graph invariants hold
    ∧ negative witnesses remain rejected
    ∧ publication requirements hold
```

No weighted score may compensate for an authority, safety, identity, or evidence failure.

---

## 10. System A and System B

System A and System B are API-centric components whose composition forms the GitOps controller capability.

### System A: authority and ledger plane

System A owns:

* authoritative Git and blob state;
* desired OSCAL state;
* contract revisions;
* authority artifacts;
* frozen proposals;
* transition admission;
* result validation;
* publication;
* accepted revisions.

System A:

1. resolves the current ledger state;
2. loads the pinned OSCAL/CUE contract;
3. validates the request;
4. admits or rejects the proposed transition;
5. grants a narrowed execution capability;
6. validates returned results and evidence;
7. commits accepted state.

### System B: proposal, observation, and bounded execution plane

System B owns:

* candidate proposals;
* evaluations;
* test execution;
* evidence collection;
* remediation execution;
* counterexamples;
* execution receipts;
* proposed resulting state.

System B may:

* propose;
* inspect;
* evaluate;
* execute an admitted operation;
* produce evidence;
* return a candidate result.

System B may not independently:

* redefine policy;
* widen its authority;
* mutate protected state outside its capability;
* publish authoritative state;
* treat raw output as qualified evidence.

System B output becomes authoritative only after evidence binding, CUE qualification, System A validation, and Git publication.

---

## 11. GitOps reconciliation loop

```text
Observe
    ↓
resolve pinned Git commit and OSCAL closure
    ↓
load Component Definition API
    ↓
evaluate CUE constraints and relations
    ↓
derive current lifecycle state
    ↓
compare with desired OSCAL state
    ↓
select or receive a candidate operation
    ↓
freeze and digest the proposal
    ↓
qualify transition and authorization
    ↓
grant bounded execution capability
    ↓
invoke System B or a specialized adapter
    ↓
collect outputs, evidence and receipts
    ↓
validate postconditions and invariants
    ↓
commit resulting OSCAL state and artifacts
    ↓
update derived GUAC projection
```

Control-theoretically:

```text
reference signal
    = Catalog/Profile requirements
      + desired OSCAL state

controller law
    = Component Definition operations
      + CUE admission rules

plant
    = governed repository graph

observation
    = Git state
      + Assessment Results
      + SBOM and GUAC evidence

error signal
    = findings
      + risks
      + failed constraints

control input
    = admitted API operation

corrective lifecycle
    = POA&M

next authoritative state
    = validated Git commit
```

---

## 12. Probabilistic proposal generation

DSPy is a proposal compiler, not an authority.

It may propose:

* semantic mappings;
* operation sequences;
* candidate transitions;
* assessment procedures;
* remediation plans;
* evidence requests;
* repair strategies.

Its output is normalized, frozen, and digested before qualification:

```text
OSCAL goal
+ current repository state
+ authority context
+ evidence
        ↓
DSPy proposal
        ↓
normalization
        ↓
frozen proposal snapshot
        ↓
CUE and OSCAL qualification
```

DSPy may not:

* relax hard constraints;
* redefine authority;
* invent evidence;
* authorize mutation;
* directly move Git references;
* publish findings or conclusions.

Optimization occurs only among admitted candidates.

---

## 13. Controller and qualification surface

Marimo may provide the inspectable controller interface.

It exposes:

* repository snapshots;
* OSCAL objects;
* authority relations;
* candidate proposals;
* candidate graph deltas;
* qualification failures;
* counterexamples;
* receipts;
* admitted operations;
* resulting state.

Two surfaces remain distinct:

### Controller surface

Contains durable operational state:

* frozen proposals;
* authority snapshots;
* qualification results;
* evidence bindings;
* transition receipts;
* publication decisions.

### Scratchpad surface

Contains exploratory state:

* schema probes;
* temporary DSPy programs;
* candidate mappings;
* experimental code;
* counterexample investigation.

Promotion is explicit:

```text
scratchpad result
    ↓ normalize
frozen proposal
    ↓ qualify
admitted controller operation
```

A successful scratchpad execution has no authority by itself.

---

## 14. Effect classification

```cue
#ExecutionClass:
	"pure" |
	"proposal" |
	"qualification" |
	"observation" |
	"effect" |
	"publication"
```

Rules:

```text
pure
    reactive and cacheable

proposal
    reactive but non-authoritative

qualification
    evaluated against frozen inputs

observation
    bound to an explicit execution epoch

effect
    requires exact authorization and bounded capability

publication
    requires complete publication qualification
```

An effectful operation must never execute merely because an upstream value changed.

---

## 15. Evidence boundary

Raw execution output is not automatically evidence.

A candidate observation must be bound to:

* proposal digest;
* operation identity;
* evaluator identity;
* actor identity;
* authority context;
* source revision;
* contract revision;
* toolchain identity;
* trust epoch;
* execution epoch;
* artifact digest;
* trace or receipt.

```text
raw output
    ↓ provenance binding
candidate OSCAL observation
    ↓ semantic qualification
qualified evidence
    ↓ result construction
Assessment Results
```

No component may manufacture an observation to satisfy closure.

---

## 16. Git mutation adapter

Only a constrained Git adapter may mutate repository state.

Its operation vocabulary is explicit:

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

Execution flow:

```text
inspect pinned snapshot
    ↓
resolve exact identities
    ↓
read affected objects
    ↓
construct candidate objects
    ↓
evaluate CUE invariants
    ↓
run qualification probes
    ↓
create candidate commit
    ↓
verify resulting graph
    ↓
move only the authorized reference
    ↓
publish only after publication qualification
```

DSPy, Marimo, Minder, GUAC, and generated clients cannot bypass this adapter.

---

## 17. SBOM and supply-chain evidence

SBOMs are first-class API values and assessment evidence.

They describe the implementation of an OSCAL component, including:

* packages;
* files;
* dependencies;
* generated binaries;
* source identities;
* checksums;
* licenses;
* build relationships.

Governed operations may include:

```text
component.generate-sbom
component.validate-sbom
component.publish-sbom
component.ingest-sbom
component.compare-sbom
component.resolve-dependencies
component.evaluate-vulnerabilities
component.attest-sbom
```

The lifecycle is OSCAL-native:

```text
Component Definition
    declares SBOM capabilities

SSP
    binds the implementation

Assessment Plan
    requires SBOM evidence

Assessment Results
    records observed state and findings

POA&M
    governs dependency remediation
```

An SBOM does not define transition guards, authorization, lifecycle state, or controller semantics. Those remain OSCAL/CUE concerns.

---

## 18. Attestations

Attestations bind claims to immutable subjects.

They may describe:

* source provenance;
* build provenance;
* generated artifacts;
* assessment execution;
* policy evaluation;
* remediation execution;
* Git transition results;
* SBOM production;
* deployment or publication.

```text
attestation
    =
typed predicate
+ subject digest
+ producer identity
+ operation identity
+ source revision
+ execution context
+ signature or verification material
```

Attestations supplement Git history but do not replace semantic qualification.

---

## 19. GUAC

GUAC is the repository-scoped materialized software and evidence graph.

It provides:

* software identity correlation;
* dependency traversal;
* provenance queries;
* vulnerability exposure queries;
* attestation discovery;
* evidence correlation;
* supply-chain lineage.

```text
OSCAL UUID
    = governance identity

Git OID
    = immutable content identity

pURL / VCS URI
    = software identity

attestation digest
    = claim identity

GUAC node ID
    = derived local index
```

GUAC is not:

* a canonical semantic store;
* an authorization engine;
* a lifecycle authority;
* an API authority;
* a state-transition authority.

GUAC GraphQL, CLI, and service operations are transport adapters behind Component Definition operations such as:

```text
supplychain.graph.ingest
supplychain.graph.resolve
supplychain.graph.query-exposure
supplychain.graph.query-provenance
```

---

## 20. Minder

Minder is an optional evaluator and bounded remediation adapter.

```text
Minder rule type
    = evaluator implementation

Minder profile
    = derived execution configuration

Minder entity
    = OSCAL subject binding

Minder evaluation
    = assessment activity

Minder result
    = observation or finding

Minder remediation
    = admitted transition operation

Minder reevaluation
    = verification assessment
```

Minder does not become a second controller.

The GitOps controller selects the operation, performs CUE admission, grants narrowed authority, invokes Minder, validates the result, and commits accepted OSCAL state.

---

## 21. Apercue disposition

Apercue is no longer required as an independent architectural authority.

Its responsibilities are absorbed by:

| Former responsibility           | Normalized authority       |
| ------------------------------- | -------------------------- |
| Semantic object model           | OSCAL                      |
| Constraint system               | CUE                        |
| API contract                    | OSCAL Component Definition |
| State history                   | Git                        |
| Artifact identity               | Git OIDs and digests       |
| Dependency inventory            | SBOM                       |
| Provenance and execution claims | Attestations               |
| Supply-chain graph              | GUAC                       |
| Query and reporting projections | Generated adapters         |
| Optional semantic-web output    | Deterministic projections  |

The replacement is not GUAC alone:

```text
Apercue responsibilities
    =
      OSCAL semantic authority
    + CUE executable constraints
    + Git state authority
    + SBOM implementation evidence
    + attestation evidence
    + GUAC graph materialization
```

Reusable Apercue projection patterns may survive as non-authoritative generators.

---

## 22. Generated adapters

Generation flows in one direction:

```text
OSCAL + CUE
    ├── Go types and interfaces
    ├── constrained Git clients
    ├── Pydantic models
    ├── Hypothesis strategies
    ├── JSON Schema
    ├── OpenAPI
    ├── GraphQL adapters
    ├── CLI
    ├── MCP tools
    ├── workflow bindings
    ├── test fixtures
    ├── assertion packages
    └── documentation
```

Never:

```text
OpenAPI
Pydantic
GraphQL
or generated Go types
    → canonical OSCAL/CUE meaning
```

Generated surfaces may be lossy. They must not widen the canonical lattice.

---

## 23. Pydantic and Hypothesis

### Pydantic

Pydantic is a generated Python boundary for:

* request and response construction;
* Marimo integration;
* agent interaction;
* serialization;
* editor support;
* data analysis.

```text
Pydantic-valid
    = valid at the Python boundary

CUE-admitted
    = valid for authoritative execution
```

### Hypothesis

Hypothesis is the adversarial verification layer.

It generates:

* malformed OSCAL structures;
* invalid identity relations;
* boundary values;
* branch divergence;
* stale snapshots;
* concurrent reference movement;
* conflicting edits;
* partial history;
* protected-reference attacks;
* illegal state transitions;
* effect-boundary violations;
* premature publication attempts.

The central property is:

```text
Every admitted operation trace
either reaches its projected qualified state
or fails without unauthorized graph mutation.
```

Review findings and counterexamples become permanent fixtures and regression properties.

---

## 24. OSCAL structural authority

Official OSCAL validation remains an independent gate.

The authority chain is:

```text
pinned NIST Metaschema revision
        ↓
official generated schema and validator
        ↓
pinned CUE import
        ↓
generated structural CUE package
        ↓
hand-authored Cuestrap semantic overlays
```

Admission is:

```text
Cuestrap-admissible OSCAL
    =
      official OSCAL structural validity
    ∧ generated CUE structural validity
    ∧ Cuestrap profile constraints
    ∧ semantic relation closure
    ∧ lifecycle invariants
    ∧ publication qualification
```

Disagreements between validators are recorded in a compatibility ledger rather than silently patched.

Generated schema packages are never hand-edited.

---

## 25. Deterministic projection

Accepted models may be projected into external artifacts through pinned deterministic projectors.

```text
accepted OSCAL/CUE model
        ↓
pinned projector
        ↓
generated artifact tree
        +
projection receipt
```

```cue
#ProjectionReceipt: {
	modelDigest:       string
	projectorIdentity: string
	projectorVersion:  string
	projectorDigest:   string
	outputTreeDigest:  string
	byteStable:        true
	concrete:          true
}
```

The projector is replaceable. The accepted model is authoritative.

---

## 26. Admission formulas

### OSCAL closure

```text
admitted OSCAL closure
    =
      root OSCAL resource
    + imported OSCAL resources
    + linked Git component closure
    + official structural constraints
    + Cuestrap semantic constraints
    + lifecycle invariants
```

### API invocation

```text
admitted invocation
    =
      actor permission
    ∧ trusted contract revision
    ∧ valid operation
    ∧ valid subject
    ∧ valid input
    ∧ valid lifecycle state
    ∧ transition guards
    ∧ effect bounds
    ∧ evidence requirements
```

### Implementation

```text
admitted implementation
    =
      API conformance
    ∧ SBOM policy
    ∧ provenance policy
    ∧ vulnerability policy
    ∧ repository policy
    ∧ control-evidence policy
```

### Transition

```text
accepted transition
    =
      admitted request
    ∧ authorized bounded execution
    ∧ valid execution receipt
    ∧ valid attestations
    ∧ matching artifact digests
    ∧ satisfied postconditions
    ∧ preserved invariants
    ∧ admitted resulting OSCAL state
    ∧ committed Git revision
```

---

## 27. Minimal vertical slice

The first implementation should test the complete authority chain without building the entire platform.

1. Pin one OSCAL Assessment Results schema and toolchain.
2. Import it reproducibly into CUE.
3. Add one cross-reference constraint.
4. Add one publication constraint.
5. Define one Component Definition operation.
6. Observe one pinned repository snapshot.
7. produce one bounded candidate transition.
8. Freeze and digest the proposal.
9. Qualify it through official OSCAL validation, CUE, and authority closure.
10. Generate one Pydantic model and one Hypothesis strategy.
11. Introduce one deliberate invalid mutant.
12. Apply the admitted transition through the constrained Git adapter.
13. Emit one receipt and one attestation.
14. Bind one observation into Assessment Results.
15. Generate or update one SBOM.
16. Ingest the resulting evidence into a repo-scoped GUAC graph.
17. Replay the complete slice and verify equivalent digests and state.

---

## 28. Compact invariant

```text
Cuestrap
    =
      one OSCAL semantic universe
    ∧ one OSCAL Component Definition API
    ∧ one CUE executable lattice
    ∧ one Git and blob authority ledger
    ∧ one composed System A/System B GitOps controller
    ∧ one constrained Git mutation boundary
    ∧ one evidence and attestation chain
    ∧ GUAC as derived graph materialization
    ∧ SBOMs as typed implementation evidence
    ∧ generated adapters that cannot widen authority
```

Operationally:

```text
Every governed capability is an OSCAL API operation.

Every operation is constrained and admitted through CUE.

Every proposal is frozen before qualification.

Every authorization decision is actor-, resource-, revision-,
state-, evidence-, and effect-bound.

Every mutation passes through the constrained Git adapter.

Every desired and resulting authoritative state is committed to Git.

Every observation is provenance-bound before becoming evidence.

Every graph, SBOM, assessment, remediation, and attestation returns
to the same OSCAL lifecycle.

Every external surface is a generated or bounded adapter.

No derived system becomes a parallel authority.
```

## Final formulation

> **Cuestrap is an OSCAL-native, CUE-executable, Git-backed, proof-carrying governance controller. The OSCAL Component Definition is its universal API contract. Catalogs and Profiles define required behavior; Component Definitions publish callable governed capabilities; SSPs bind implementations; Assessment Plans exercise them; Assessment Results record qualified behavior; POA&Ms govern corrective transitions. System A owns authority, admission, validation, and Git publication. System B proposes, observes, evaluates, and performs bounded admitted execution. DSPy may propose but never authorize. Marimo exposes the control and qualification process. Hypothesis attempts to falsify transition properties. A constrained Git adapter performs only exact authorized mutations. SBOMs describe implementation composition. Attestations bind claims and transitions to immutable identities. GUAC materializes the derived supply-chain and evidence graph. Every authoritative state, operation, finding, risk, remediation, and publication remains inside one OSCAL lifecycle governed by one CUE lattice.**
