
# OSCAL-Native API-Centric GitOps Architecture

## Core Thesis

Promote **OSCAL as the authoritative data model**, not merely as a document interchange format.

The system collapses into:

```text
One model       = OSCAL
One API         = OSCAL Component Definition
One lattice     = CUE
One state log   = Git
One controller  = GitOps reconciler
One adapter set = generated Go, Pydantic and Hypothesis surfaces
```

The OSCAL Component Definition is not linked to a separate API specification.

> The OSCAL Component Definition **is the API specification**, authored and constrained in CUE, stored as immutable Git content, and executed through generated or constrained adapters.

```cue
#Authority:
    #OfficialOSCALComponentDefinition &
    #CuestrapAPIProfile
```

CUE supplies the executable grammar and semantic lattice. OSCAL supplies the authoritative objects, identities, relationships and lifecycle artifacts.

---

## Authority Model

```text
OSCAL
  authoritative domain model
  authoritative lifecycle identity
  authoritative API representation

CUE
  structural constraints
  semantic constraints
  composition lattice
  authorization
  transition admission
  adapter generation

Git
  immutable content storage
  desired-state publication
  revision history
  provenance and evidence ledger

GitOps controller
  resolution
  validation
  authorization
  reconciliation
  bounded execution
  publication of resulting OSCAL state
```

Generated adapters are subordinate projections:

```text
OSCAL + CUE
    ├── Go types and interfaces
    ├── Pydantic models
    ├── Hypothesis strategies
    ├── JSON Schema
    ├── CLI commands
    ├── HTTP endpoints
    ├── MCP tools
    └── workflow bindings
```

There is no independently authored API schema, graph schema, FSM schema, Python model or controller resource model.

---

## API Meaning

“API” is not limited to HTTP.

An operation may represent:

* a Go interface;
* a CLI command;
* an MCP tool;
* a Git mutation;
* a policy evaluation;
* a workflow action;
* an event handler;
* an evidence collector;
* a remediation procedure;
* a human-governed operation with typed inputs and outputs.

Every operation is an OSCAL-identified component or capability with:

```text
identity
input
output
read scope
write scope
preconditions
postconditions
authorization constraints
evidence requirements
state transition
bounded effects
```

Conceptually:

```cue
#Operation: {
    operationID: string
    mode: "query" | "command" | "transition"

    input:  _
    output: _

    reads:  [...#OscalSelector]
    writes: [...#MutationClass]

    requires: [...#Assertion]
    ensures:  [...#Assertion]

    transition?: {
        from: string
        event: string
        to:   string
    }

    evidence?: {
        required: [...#EvidenceRequirement]
        produces: [...#EvidenceType]
    }
}
```

The ergonomic operation map is a computed projection from the Component Definition. It is not a second source of authority.

---

## Git Object Model

Git provides the missing immutable substrate for OSCAL-linked semantic components.

```text
OSCAL UUID
  = stable semantic identity

Git blob OID
  = exact atomic content identity

Git tree OID
  = exact package or component closure

Git commit OID
  = coherent versioned state

Git branch
  = mutable desired-state discovery pointer
```

A single self-contained API may be one blob. A realistic CUE API is usually a tree containing multiple packages and modules at a pinned commit.

```text
repository + commit OID + path + tree/blob OID
```

Branches such as `main` are never authoritative by themselves.

---

## Addressing OSCAL Constraint Boundaries

OSCAL can express objects, identifiers, imports, links, properties, assessment artifacts and lifecycle records. Ordinary serialization validation cannot always enforce:

* cross-document referential integrity;
* semantic target typing;
* graph-wide cardinality;
* import closure correctness;
* evidence lineage;
* temporal ordering;
* state-transition legality;
* authorization-dependent mutations;
* postconditions over multiple OSCAL resources.

Git-addressed CUE components express these additional constraints while remaining anchored to OSCAL identities.

```text
admitted OSCAL closure
    =
root OSCAL resource
+ imported OSCAL resources
+ linked Git component closure
+ official OSCAL constraints
+ Cuestrap semantic constraints
+ lifecycle invariants
```

Git does not itself validate semantics. The controller resolves the closure and CUE evaluates it.

---

## OSCAL Layers as One API Lifecycle

### Catalog

The Catalog becomes the governance type system.

```text
control
  = required capability

statement
  = behavioral guarantee

parameter
  = configurable contract input

assessment objective
  = evaluable predicate
```

### Profile

The Profile specializes the API requirements.

It performs:

* requirement selection;
* interface refinement;
* parameter binding;
* constraint narrowing;
* organizational specialization.

```text
resolved profile
  = resolved API requirements
```

### Component Definition

The Component Definition publishes the reusable governed API.

It defines:

* components;
* capabilities;
* operations;
* protocols;
* behavioral guarantees;
* required evidence;
* allowable effects;
* supported transitions.

### System Security Plan

The SSP becomes the concrete API binding manifest.

It specifies:

* which Component Definition APIs are instantiated;
* their deployment scope;
* configuration;
* dependencies;
* responsible parties;
* inherited guarantees;
* system-specific implementation narratives.

The “system” becomes a composition and deployment boundary, not the exclusive semantic center.

### Assessment Plan

The Assessment Plan becomes the API evaluation contract.

It defines:

* operations to exercise;
* subjects to assess;
* evaluator roles;
* test inputs;
* expected outputs;
* expected predicates;
* evidence requirements.

It can project into Go tests, CUE fixtures, policy evaluations, workflows and continuous-monitoring jobs.

### Assessment Results

Assessment Results become authoritative API execution records.

```text
activity
  = operation invocation

observation
  = emitted or collected evidence

finding
  = observed behavior compared with required behavior

risk
  = consequence derived from failed or uncertain guarantees
```

### POA&M

The POA&M becomes the remediation API lifecycle.

```text
undesired state
+ target state
+ remediation operation
+ milestones
+ required evidence
+ reassessment requirement
```

Remediation execution does not itself prove closure.

```text
remediation succeeded
    ≠
control effectiveness verified
```

A typical transition chain is:

```text
risk-open
  → remediation-planned
  → remediation-executed
  → reassessment-pending
  → verified
  → closed
```

---

## One Semantic Graph

The graph is a projection of OSCAL, not a competing model.

```text
Control
  ──requires────────────▶ Capability

Profile
  ──specializes─────────▶ Capability

Component
  ──provides────────────▶ Operation

Operation
  ──claims──────────────▶ Implemented Requirement

SSP implementation
  ──binds───────────────▶ Operation

Assessment task
  ──invokes─────────────▶ Operation

Observation
  ──result-of───────────▶ Invocation

Finding
  ──evaluates───────────▶ Guarantee

Risk
  ──derived-from────────▶ Finding

POA&M item
  ──selects─────────────▶ Remediation Operation
```

Graph nodes remain addressable through OSCAL UUIDs. Derived edges may be materialized for efficient querying, but OSCAL remains the identity and lifecycle authority.

---

## One State Machine

FSM state is not independently authored.

```text
current state
  = deterministic fold over OSCAL lifecycle artifacts and events
```

A transition is admitted only when:

```text
valid prior state
∧ authorized actor
∧ valid operation
∧ valid resource scope
∧ required evidence present
∧ transition guards satisfied
∧ effects remain bounded
∧ resulting OSCAL state satisfies postconditions
```

Each accepted transition produces an OSCAL mutation, observation, finding, risk, response, POA&M update or equivalent lifecycle artifact.

---

## One Authorization Model

The architecture transforms authorization from endpoint-centric ACLs into model-native operation admission.

The authorization tuple is:

```text
actor
operation
OSCAL resource
current lifecycle state
contract revision
input
requested effects
execution context
```

```cue
#AdmittedInvocation:
    #Invocation &
    #ActorPermissions &
    #OperationPolicy &
    #ResourcePolicy &
    #TransitionGuards &
    #EffectBounds &
    #TrustedRevision
```

Authorization can answer:

> May actor A invoke operation O against OSCAL subject S, under contract revision C, from lifecycle state L, using input I, producing only effects E?

This permits:

* domain-specific permission vocabulary;
* exact resource scoping;
* lifecycle-aware permission;
* effect-level authorization;
* revision-bound authorization;
* generated least-privilege capabilities;
* reproducible audit decisions.

An actor may be generally permitted to invoke an operation while the invocation remains invalid in the current state.

```text
role permission
    is necessary

transition validity
    is also necessary
```

Adapters receive a narrowed execution capability rather than ambient repository or provider access.

---

## GUAC

GUAC becomes the materialized software and evidence graph adapter for the same API.

Its roles are:

* software identity correlation;
* dependency graph resolution;
* claim indexing;
* provenance correlation;
* vulnerability exposure queries;
* graph materialization.

It does not become a second governance model or authorization authority.

```text
OSCAL UUID
  = governance identity

pURL / VCS URI / artifact digest
  = software identity

Git OID
  = immutable content identity

GUAC node ID
  = local graph index
```

GUAC operations are declared by the Component Definition API, for example:

```text
supplychain.graph.ingest
supplychain.graph.resolve
supplychain.graph.query-exposure
supplychain.graph.query-provenance
```

GUAC GraphQL, CLI or service endpoints become transport adapters behind those operations.

---

## SBOM

SBOMs become first-class typed API values and assessment evidence.

They describe the composition and provenance of an OSCAL component implementation.

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

An SBOM remains an SPDX or CycloneDX artifact, but its lifecycle is governed through the OSCAL API:

```text
Component Definition
  declares SBOM capability

SSP
  binds an implementation

Assessment Plan
  requires SBOM evidence

Assessment Results
  records observed SBOM state and findings

POA&M
  tracks dependency remediation
```

The SBOM is content-addressed through Git and linked to the OSCAL subject, source revision, builder and generating operation.

---

## Minder

Minder becomes the policy evaluator and bounded remediation adapter for the same API.

Its concepts map directly:

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
  = authorized transition operation

Minder reevaluation
  = verification assessment
```

Minder is not a second controller.

```text
GitOps controller
  resolves the authority
  selects the operation
  performs CUE admission
  issues a bounded capability
  invokes Minder
  validates the result
  commits OSCAL evidence and state
```

Minder may evaluate declared rules, query provider state and perform explicitly authorized effects. It may not independently choose policy, widen scope or determine authoritative OSCAL state.

---

## One GitOps Controller

The reconciler performs the unified control loop:

```text
Observe
  ↓
resolve Git commit and OSCAL closure
  ↓
load OSCAL Component Definition API
  ↓
evaluate the CUE lattice
  ↓
derive current state
  ↓
compare with desired OSCAL state
  ↓
select an admissible operation
  ↓
authorize bounded effects
  ↓
invoke GUAC, SBOM, Minder or another adapter
  ↓
validate the resulting OSCAL closure
  ↓
commit state, evidence and provenance
```

Control-theoretically:

```text
desired state
  = Catalog/Profile requirements and Git-published OSCAL state

controller surface
  = Component Definition API

plant configuration
  = SSP bindings

observed state
  = Assessment Results, GUAC graph and SBOM evidence

error signal
  = findings, risks and failed constraints

control input
  = authorized API operation

corrective lifecycle
  = POA&M

next state
  = validated OSCAL mutation committed to Git
```

---

## Pydantic Adapter

Pydantic is a generated Python boundary, not an authority.

Its uses include:

* typed Python requests and responses;
* marimo and data-analysis integration;
* agent-facing construction;
* serialization;
* editor support;
* adapter validation.

```text
Pydantic-valid
  = valid at the Python boundary

CUE-admitted
  = valid for authoritative execution
```

Pydantic cannot fully preserve all CUE semantics, especially cross-instance constraints, disjunctions, subsumption, graph reachability, lifecycle guards and postconditions.

---

## Hypothesis Adapter

Hypothesis is the generated adversarial verification layer.

It validates:

* positive structural conformance;
* boundary values;
* negative fixtures;
* CUE/Pydantic agreement;
* round-trip preservation;
* transition invariants;
* unreachable illegal states;
* Go/Python adapter equivalence;
* preservation of effect boundaries.

```text
CUE contract
  → generated Pydantic surface
  → generated Hypothesis strategies
  → differential and property-based validation
```

Generated adapters must prove they do not widen the canonical lattice.

---

## Direction of Generation

The direction is one-way:

```text
OSCAL + CUE
    ├── Go
    ├── Pydantic
    ├── Hypothesis
    ├── JSON Schema
    ├── OpenAPI
    ├── CLI
    ├── MCP
    └── workflow projections
```

Never:

```text
Pydantic or OpenAPI
  → canonical OSCAL/CUE semantics
```

Transport projections may be lossy. The authoritative contract remains the CUE-constrained OSCAL Component Definition.

---

## Compact Invariant

```text
Cuestrap
    =
one OSCAL data model
∧ one OSCAL Component Definition API
∧ one CUE semantic lattice
∧ one Git state and provenance graph
∧ one GitOps reconciler
∧ GUAC as graph projection
∧ SBOMs as typed supply-chain evidence
∧ Minder as evaluator and bounded actuator
∧ generated Pydantic and Hypothesis verification adapters
```

Operationally:

```text
Every command is an OSCAL API operation.

Every operation is admitted through CUE.

Every authorization decision is revision-, state- and effect-bound.

Every desired and resulting state is committed through Git.

Every graph, SBOM, policy evaluation and remediation passes through
the same Component Definition API.

Every implementation adapter is generated and tested against the
same lattice.

Every observation, finding, risk, remediation and transition returns
to OSCAL.
```

## Final Formulation

> **Cuestrap is an OSCAL-native, CUE-executable, Git-backed governance control system in which the OSCAL Component Definition is the universal API contract. Catalogs and Profiles define required behavior; Component Definitions publish callable governed capabilities; SSPs bind them; Assessment Plans exercise them; Assessment Results record their behavior; POA&Ms drive corrective transitions; GUAC materializes the software and evidence graph; SBOMs provide typed composition evidence; Minder evaluates and executes bounded remediation; and one GitOps controller authorizes, reconciles, validates and commits every lifecycle mutation through one semantic lattice.**
