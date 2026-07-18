# S04 object and property model

The S04 contract is tested as a model, not as a growing list of hand-written
counterexamples.

## Authority split

| Layer | Owns | Does not own |
|---|---|---|
| Pydantic | closed transport objects, discriminated unions, map-key identity, local envelope rules, deterministic JSON | semantic admissibility or final outcomes |
| Hypothesis | valid graph generation, controlled mutations, shrinking, metamorphic tests | semantic decisions |
| CUE | reference integrity, case-local coherence, authority roles, projection totality, outcome derivation, publication | fixture generation or process orchestration |

A property succeeds only when the Pydantic object can be serialized, Hypothesis
can mutate it into the target state, and CUE gives the expected publication
result.

## Object assertions

| Object | Structural assertions | Relational assertions |
|---|---|---|
| `AuthorityBinding` | closed role/source envelope | referenced authority has the role required by the relation |
| `SubjectSpec` | closed CUE subject source | selected subjects exist in the realization and selecting case |
| `MaterializedSubjectIdentity` | digest-bound file map | materialization exists, belongs to the realization, and matches the referenced subject |
| `SubjectRef` | subject plus optional materialization | both identities resolve and agree |
| `PrimitiveOperation` | kind-discriminated arity/direction | operands belong to the selecting case; produced facts are case-local inputs |
| `OperationPlan` | non-empty operation sequence | selected plan operands and outputs are coherent with the selecting case |
| `SemanticClaim` | authority, predicate, operands, value | semantic authority exists; operands belong to the selecting case |
| `ExpectedFact` | claim/authority/predicate/value envelope | referenced claim exists and preserves authority, predicate, and value |
| `NormalizationRule` | raw-to-normalized identity | raw fact is produced by the selecting plan |
| `ComparisonRule` | expected/normalized/operator envelope | both facts are selected by the same case |
| `BackendCapabilityRequirement` | required operation-kind set | every selected operation kind is covered by a selected capability |
| `RealizationCase` | unique non-empty ID lists | all selected graph members form one coherent subgraph |
| `ObservationRecord` | state-specific fact/diagnostic envelope | case, observer role, fact identity, and source digest match ingress |
| `JudgementIngress` | no claimant-authored result fields | case and rule lists exactly match the selected realization case |
| `JudgementDerivation` | internal derived judgement | public `judgement` exists only after every sibling proof is concrete |
| `MinimalPPFPackage` | closed profile-only package envelope | validator/path and package-case identities are coherent |
| `S04PPFProjectionRequest` | authority and case-map request | mapping is total, source/target members exist, and roles match |
| `S04PPFProjectionDerivation` | internal derived projection | public `projection` exists only after the complete proof payload is concrete |
| `S04ConsumerProfileContract` | realization/package/projection envelope | all embedded identities agree |
| `QualifiedS04ConsumerProfileContract` | candidate contract input | public `contract` exists only after realization equality and projection qualification |

## Property families

1. **Construction properties** — generated valid objects round-trip through
   Pydantic and serialize deterministically.
2. **Mutation properties** — one controlled invariant violation prevents CUE
   publication.
3. **Locality properties** — a case may not borrow subjects, facts, rules, or
   plan outputs from unrelated graph regions.
4. **Publication properties** — selecting `judgement`, `projection`, or
   `contract` forces every proof that qualifies that output.
5. **Metamorphic properties** — unrelated valid graph extensions do not change
   the selected case outcome.
6. **Shrink properties** — Hypothesis reduces a failing graph to the smallest
   object and edge set that still violates the relation.

The executable catalog is in `src/cuestrap/s04/properties.py`; generated tests
are in `tests/test_s04_properties.py`.
