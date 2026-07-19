
# Reactive Agentic Pipeline Architecture — Normalized Digest

## 1. Architectural premise

The target is not a general-purpose autonomous agent framework.

It is a **bounded reactive execution system** in which:

* **marimo owns the reactive DAG**;
* **Git owns immutable transition history and checkpoints**;
* **CUE owns semantic validity, playbook applicability, and graph-mutation admission**;
* **DuckDB owns streaming analytical projections of runtime and historical state**;
* **DSPy evaluates and ranks a pre-authorized subset of playbooks**;
* **agents propose or select within constrained alternatives rather than inferring arbitrary next actions**;
* **external authority remains responsible for discretionary authorization beyond delegated playbook scope**.

The core control principle is:

> The model does not decide what to do from an unconstrained action space. It evaluates which admitted playbook best fits the current transition state.

---

## 2. Relevant ecosystem positioning

The broader ecosystem contains several governance and specification layers:

```text
NIST / OSCAL
    governance, controls, components, assessment artifacts

OASIS Open
    interoperable security, workflow, command, and linked-resource standards

Linux Foundation ecosystems
    implementation, delivery, security, runtime, data, and infrastructure projects
```

Relevant OASIS standards include:

* **CACAO** — cybersecurity playbooks and workflow structure;
* **OpenC2** — commands to cyber-defense actuators;
* **STIX/TAXII** — threat intelligence representation and exchange;
* **CSAF/VEX** — vulnerability advisory and applicability state;
* **SARIF** — normalized analyzer findings;
* **OSLC** — linked lifecycle resources and relationships;
* **TOSCA** — topology and lifecycle orchestration;
* **XACML** — policy decision semantics.

OpenC2 is not a universal command language. It remains centered on cyber-defense functions such as network, endpoint, firewall, process, artifact, and threat-hunting actuators.

CACAO is a more useful architectural precedent because it demonstrates a portable, versioned playbook graph with:

* declared participants;
* typed workflow steps;
* branching;
* loops;
* exceptions;
* variables;
* commands;
* signatures;
* lifecycle transitions.

The proposed system borrows the **playbook pattern**, not CACAO’s cybersecurity-specific ontology.

---

## 3. Reactive agent playbooks

The missing semantic layer is a contract for **bounded reactive agency**.

Existing technologies provide adjacent capabilities:

```text
CloudEvents / CDEvents
    event transport and event vocabularies

MCP
    tool, resource, and prompt exposure

A2A
    remote-agent task and artifact exchange

workflow runtimes
    durable execution

marimo
    reactive Python DAG execution
```

What remains missing is a portable contract that defines:

* which agent capabilities may participate;
* which observations activate which playbook classes;
* what discretion an agent is permitted;
* which graph mutations are legal;
* which evidence is required;
* when authority or human approval is needed;
* how plan revisions become admitted state transitions;
* how execution settles or fails closed.

The central transition pattern is:

```text
observation
    ↓
state projection
    ↓
eligible playbook subset
    ↓
DSPy evaluation
    ↓
CUE admission
    ↓
marimo source/DAG mutation
    ↓
reactive execution
    ↓
evidence and settlement evaluation
```

---

## 4. Streaming analytics and AOT validation

DuckDB-backed streaming analytics continuously projects the current operational state.

AOT validation evaluates authority-bearing transition boundaries.

An AOT conclusion is not merely a label. It implies a legal revision of the reactive continuation graph:

```text
approve
    → admit continuation or bounded expansion

deny
    → invalidate the proposed continuation
    → expose corrective, extraction, replacement, or termination playbooks

indeterminate
    → suspend effectful continuation
    → expose evidence-acquisition, requalification, or termination playbooks

continuity lost
    → suspend
    → requalify or rebase
    → no automatic continuation
```

Every AOT conclusion capable of changing authority or graph topology must be bound to an immutable checkpoint.

Streaming observations may update in memory continuously, but an authoritative evaluation epoch closes only when a material boundary occurs, such as:

* relevant program or state change;
* evidence-prefix change;
* objective revision;
* budget change;
* continuity-epoch change;
* playbook-set revision;
* verdict-boundary crossing;
* proposed DAG mutation.

---

## 5. Git checkpoint and anchor model

There are three distinct state anchors.

### Operation base

```text
operationBase
    = pre-transition last known good
    = admitted repository HEAD at bounded-operation start
```

This is normally the original `HEAD`, pinned to an immutable operation reference.

If relevant initial state is dirty or external runtime state is required, an explicit operation-base checkpoint must be created or operation startup must be rejected.

### Prior settled checkpoint

```text
priorSettled
    = pre-settlement last known good
    = most recent transition checkpoint that completed settlement
```

This moves forward only when execution and postconditions settle successfully.

### Candidate checkpoint

```text
candidateCheckpoint
    = exact marimo program and relevant state currently being evaluated
```

A candidate is not yet known good.

A denied or indeterminate candidate remains durable evidence and may serve as:

* a corrective starting point;
* an extraction source;
* a failure witness;
* a provenance anchor.

It does not advance the settled reference.

---

## 6. Two-phase checkpointing

Each authority-bearing evaluation uses two immutable records.

### Candidate commit

The candidate commit captures:

* marimo program source;
* candidate tree;
* relevant state projections;
* operation base;
* prior settled anchor;
* current DAG revision;
* objective revision;
* evidence-prefix identity;
* evaluator identity.

### Decision receipt

A decision receipt binds:

* the candidate commit;
* operation base;
* prior settled checkpoint;
* AOT disposition;
* matched reasons;
* eligible playbook-set digest;
* selected playbook, when applicable;
* resulting DAG revision;
* settlement status.

The decision receipt may be represented as:

* a same-tree metadata commit;
* a content-addressed blob referenced by a commit;
* another immutable Git-addressable record.

The verdict must not be retroactively written into the candidate commit.

---

## 7. Required state comparisons

Every evaluation receives three deltas:

```text
localTransitionDelta
    = candidate − priorSettled

cumulativeOperationDelta
    = candidate − operationBase

priorSettledCumulativeDelta
    = priorSettled − operationBase
```

These answer separate questions:

| Delta                               | Meaning                                                    |
| ----------------------------------- | ---------------------------------------------------------- |
| Candidate versus prior settled      | What did the current transition change?                    |
| Candidate versus operation base     | Where has the complete bounded operation moved the system? |
| Prior settled versus operation base | What cumulative change had already been accepted?          |

DSPy evaluation therefore consumes:

```text
candidate state
+ prior settled state
+ operation base
+ local transition delta
+ cumulative operation delta
+ current objective
+ current DAG revision
+ qualified evidence
+ remaining budgets
+ eligible playbook subset
```

---

## 8. Settlement

AOT approval is not settlement.

The lifecycle is:

```text
candidate checkpoint
    ↓
AOT approval
    ↓
playbook and DAG continuation admitted
    ↓
marimo execution
    ↓
terminal observations
    ↓
post-transition evaluation
    ↓
settlement
```

A checkpoint becomes the new settled LKG only when:

```text
marimo graph is settled
∧ required cells completed
∧ no relevant stale descendants remain
∧ effect evidence is qualified
∧ postconditions are satisfied
∧ continuity remains trusted
```

Possible states include:

* running;
* stale;
* blocked;
* failed;
* indeterminate;
* settled.

On denial, failure, indeterminacy, or continuity loss, the prior settled anchor remains unchanged.

---

## 9. Marimo’s authoritative role

Marimo is not merely an analytical adapter.

It owns the reactive DAG through:

* Python variable dependency analysis;
* cell dependency construction;
* invalidation;
* scheduling;
* reactive execution;
* stale-state propagation;
* graph settlement.

There is no separate authoritative operational DAG that marimo merely displays.

The actual loop is:

```text
CUE-authorized playbook
    ↓
bounded marimo source mutation
    ↓
marimo reconstructs reactive DAG
    ↓
marimo executes revised graph
    ↓
DuckDB projects runtime state
    ↓
AOT evaluates
    ↓
next playbook selection
```

Marimo’s computational graph and the operational control semantics remain distinguishable:

```text
marimo
    owns actual dependency topology and execution

CUE
    owns whether a proposed mutation is admissible

playbook
    owns the authorized graph-rewrite template
```

---

## 10. Graph mutation algebra

The playbook system should cover a closed set of main graph-mutation categories:

```cue
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
```

### Meanings

| Mutation     | Meaning                                                           |
| ------------ | ----------------------------------------------------------------- |
| `advance`    | Consume a completed transition and activate an admitted successor |
| `insert`     | Add evidence, correction, approval, or validation nodes           |
| `replace`    | Supersede an invalid future subgraph with an admitted alternative |
| `prune`      | Remove invalid, unauthorized, or unreachable continuation         |
| `fork`       | Create bounded parallel branches                                  |
| `join`       | Reconcile branches under an explicit completion rule              |
| `suspend`    | Freeze effectful continuation while preserving graph state        |
| `resume`     | Reactivate a suspended graph after qualification                  |
| `rebase`     | Establish a fresh qualified state anchor and rebuild continuation |
| `compensate` | Apply corrective effects for a previously settled transition      |
| `extract`    | Preserve admissible outputs from a failed or incomplete branch    |
| `terminate`  | Close the bounded operation with a typed disposition              |

These are semantic graph operations. Their concrete implementation is a bounded marimo source transformation followed by marimo graph reconstruction.

---

## 11. Operational playbook families

Playbooks are admitted compositions of graph-mutation primitives.

Initial families include:

| Family                      | Typical mutations                  |
| --------------------------- | ---------------------------------- |
| Continue                    | `advance`                          |
| Acquire evidence            | `suspend`, `insert`, `resume`      |
| Retry bounded action        | `insert`, `advance`                |
| Correct candidate           | `prune`, `insert`, `replace`       |
| Compensate settled state    | `insert`, `compensate`, `rebase`   |
| Requalify continuity        | `suspend`, `rebase`, `resume`      |
| Revise bounded continuation | `prune`, `replace`                 |
| Extract partial value       | `extract`, `prune`                 |
| Parallel investigation      | `fork`, `join`                     |
| Escalate                    | `suspend`, `terminate`             |
| Abort and restore           | `prune`, `compensate`, `terminate` |

Playbooks operate from an explicit base:

```cue
#MutationBase:
    "operation-base" |
    "prior-settled" |
    "candidate"
```

Examples:

```text
repair failed work
    → base = candidate

discard failed transition and try an alternative
    → base = prior-settled

abandon all operation progress
    → base = operation-base
```

---

## 12. Playbook selection

CUE derives the eligible playbook subset before DSPy sees any candidates.

Eligibility includes:

```text
trigger compatibility
∧ failure-class compatibility
∧ objective-state compatibility
∧ continuity requirements
∧ authority envelope
∧ available evidence
∧ epoch compatibility
∧ budget availability
∧ permitted graph mutation classes
```

DSPy then ranks only that subset.

The DSPy output is advisory evidence, not authority.

It may produce:

* candidate scores;
* matched signals;
* conflicting evidence;
* uncertainty classification;
* recommendation or abstention.

DSPy may not:

* synthesize a new playbook;
* enlarge authority;
* remove a precondition;
* reinterpret unavailable evidence as approval;
* change the objective;
* create unbounded source edits;
* directly mutate the graph.

CUE revalidates the exact selected playbook instance against the latest checkpoint before mutation occurs.

This transforms latent model bias into an explicit, measurable optimization problem without granting the model control authority.

---

## 13. Graph rewrite contracts

A playbook is a versioned graph-rewrite contract.

It declares:

* applicability;
* mutation base;
* nodes retained;
* nodes invalidated;
* nodes inserted;
* nodes activated;
* nodes suspended;
* authority envelope;
* required budgets;
* preconditions;
* postconditions;
* expected settlement state.

The agent may bind constrained parameters such as:

* target resource;
* evidence source;
* admitted actuator;
* retry count within budget;
* extraction selectors.

It does not author the topology.

The adapter/code generator compiles the admitted playbook instance into a bounded marimo source edit.

---

## 14. Replacement versus material replanning

A bounded replacement remains inside the current operation when it selects a predefined alternative already covered by the operation’s authority.

```text
failed acquisition path
    → replace with qualified alternate acquisition path
```

A material replan changes:

* the objective;
* authority scope;
* operation topology;
* accepted risk;
* external resources;
* execution contract.

That must terminate or suspend the current bounded operation and produce a handoff into a new operation.

```text
bounded predefined replacement
    ≠ material replan
```

The playbook system provides controlled alternatives without granting general replanning authority.

---

## 15. Major failure, correction, and extraction

When the original objective becomes infeasible, the system should not ask the model to improvise a new objective.

It enters a typed sequence:

```text
major qualified failure
    ↓
original continuation invalidated
    ↓
corrective playbook selection
    ↓
restore invariants or establish safe degraded state
    ↓
extraction playbook selection
    ↓
preserve admissible evidence and partial products
    ↓
terminate or hand off to a fresh operation
```

The operation outcome separately records:

* objective outcome;
* correction outcome;
* extraction outcome;
* continuation disposition.

This allows:

```text
objective not met
+ correction completed
+ extraction completed
+ fresh operation required
```

without misclassifying the operation as simple success or failure.

---

## 16. Application to Issues #7–9

### Issue #7

Issue #7 owns tactical anti-churn evaluation over:

* effective semantic action;
* relevant state;
* qualified terminal evidence;
* continuity;
* correction and uncertainty budgets.

It does not own:

* material replanning;
* phase control;
* operation authorization;
* session-wide command;
* final execution authorization.

Its conclusions constrain playbook eligibility but do not independently mutate the overall operation.

### Issue #8

Issue #8 establishes independent target and execution planes:

```text
System A
    target state and target assessment

System B
    execution state, readiness, continuity, and conformance
```

Neither plane may manufacture or repair the other’s evidence.

The combined playbook evaluator must inspect both planes against:

* operation base;
* prior settled checkpoint;
* candidate checkpoint.

### Issue #9

The upstream-monitor coverage-gap scenario demonstrates:

```text
objective:
    classify both required upstream channels

failure:
    exact independent alpha-channel head cannot be established

invalid continuation:
    semantic classification and canonical publication

corrective playbook:
    acquire exact ref evidence through another admitted source

extraction playbook:
    retain qualified partial observations and diagnostics

forbidden:
    infer the missing ref
    publish a successful canonical bundle
    advance the latest pointer
```

This is the archetypal case for bounded playbook evaluation rather than agent improvisation.

---

## 17. Final authority allocation

| Component            | Responsibility                                                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **Marimo**           | Reactive DAG derivation, invalidation, scheduling, execution, stale-state propagation, settlement                              |
| **Git**              | Program versions, candidate checkpoints, decision receipts, settled anchors, operation base                                    |
| **CUE**              | Closed semantic validity, playbook eligibility, graph-mutation admission, exact instantiation constraints                      |
| **DuckDB**           | Streaming analytics, state projections, deltas, historical evaluation corpus                                                   |
| **DSPy**             | Optimize and rank CUE-eligible playbooks                                                                                       |
| **Agent/model**      | Evaluate controlled hypotheses and produce structured recommendations                                                          |
| **Adapter/codegen**  | Translate an admitted playbook instance into a bounded marimo source mutation                                                  |
| **Parent authority** | Authorize discretionary changes outside delegated playbook scope                                                               |
| **OSCAL**            | Portable representation of components, controls, activities, observations, findings, risks, and assessment lifecycle artifacts |

---

## 18. Consolidated control law

```text
1. Begin a bounded operation from an admitted Git HEAD.

2. Pin that HEAD as the immutable operation base.

3. Execute the marimo reactive DAG on a transition branch/worktree.

4. Project streaming observations and state through DuckDB.

5. Close an authority-bearing evaluation epoch on material transition boundaries.

6. Commit the exact candidate program and state.

7. Evaluate the candidate against:
      operation base
    + prior settled checkpoint
    + local transition delta
    + cumulative operation delta
    + objective
    + continuity
    + budgets
    + evidence.

8. Produce an AOT conclusion.

9. Derive the CUE-eligible playbook subset.

10. Let DSPy rank that subset or abstain.

11. Revalidate the selected playbook instance through CUE.

12. Compile the admitted graph rewrite into a bounded marimo source mutation.

13. Let marimo reconstruct and execute the revised reactive DAG.

14. Collect terminal evidence and evaluate settlement.

15. Advance the settled checkpoint only when all settlement conditions hold.

16. Otherwise preserve the candidate, retain the prior settled anchor, and select correction, acquisition, extraction, rebase, escalation, or termination playbooks.
```

## Final invariant

> Marimo owns the live reactive graph. Git makes every evaluated graph state immutable. CUE constrains which graph rewrites are legal. DuckDB projects the state required to judge transitions. DSPy selects among pre-authorized playbooks. The model evaluates bounded alternatives rather than inventing operational policy.
