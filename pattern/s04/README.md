# S04 semantic realization and minimal PPF profile

This directory implements child issue #13 under #12. It is the pattern-only
contract slice that produces `S04ConsumerProfileContract.v0` for the next
fixture-design slice.

## Authority boundary

```text
problem package
    declares cases, candidate expectations, limits, evidence paths,
    capability requirements, and the independent judge entrypoint

runner / transport
    emits raw observation records, diagnostics, identities, and process states

S04 CUE authority
    validates concrete semantic inputs and graph integrity
    normalizes semantic facts
    applies comparison rules
    derives satisfied / rejected / indeterminate
```

Candidate `accepted` and `rejected` values in the package profile are declared
expectations. They are not runner verdicts and do not establish an S04 semantic
outcome.

## Concrete judgement publication

`#JudgementDerivation` first constructs an internal judgement. The public
`judgement` field exists only after `encoding/json.Marshal` succeeds over:

- the complete realization and judgement ingress;
- realization and observation integrity results;
- outcome-permission and required-outcome checks;
- the complete derived judgement.

The marshal is a CUE-owned concreteness gate. It rejects unresolved types and
disjunctions rather than silently narrowing them to a value that permits a
semantic outcome. Concrete invalid references still bottom through the
integrity relations.

## Files

- `semantic_ir.cue` defines the backend-neutral S04 v0 vocabulary, materialized
  subject registry, concrete publication gate, normalization, and judgement.
- `integrity.cue` proves graph references, authority roles, claim/fact value
  preservation, and materialization coherence.
- `ppf_profile.cue` defines the minimal Kattis-shaped package profile.
- `projection_relation.cue` derives the total identity-bound projection.
- `slice_output.cue` publishes the exact contract-bundle handoff.
- `validation_witness.cue` and `qualification.cue` prove concrete positive and
  indeterminate derivations.
- `.cue.txt` inputs prove concrete structural bottoms and prevent incomplete or
  disjunctive values from exposing `judgement.outcome`.
- `qualification_receipt.json` records the exact offline bundle and command
  results used to qualify the source set.
- `VALIDATION.md` records the reproducible qualification protocol.

No LT-01 package instance or candidate fixture is included in this slice.

## Contract handoff

The next slice consumes the concrete `sliceOutput` artifact and instantiates a
value satisfying:

```cue
#QualifiedS04ConsumerProfileContract
```

It then supplies the concrete LT-01 family:

```text
directional success
reverse-direction rejection
adversarial structural case
```

The concrete slice must preserve the source-set identity recorded by
`sliceOutput` and may not add backend-specific semantic fields to the S04 IR.

## PPF source profile

The projection is intentionally `profile-only` and pins the `2025-09` Problem
Package Format surface. It selects only the package elements required by #12:

- `problem.yaml` metadata;
- a problem statement path;
- `data/secret` case identity and grouping;
- `submissions` candidate identity and package expectations;
- `input_validators` and an explicit independent judge entrypoint;
- execution limits;
- deterministic raw-observation, normalized-fact, comparison, and judgement
  evidence paths.

Normative source:

- <https://icpc.io/problem-package-format/>
- <https://www.kattis.com/problem-package-format/spec/2025-09.html>

This profile does not claim complete PPF conformance and does not import Kattis
verdict vocabulary as S04 authority.

## Narrow qualification

Install the project-source bundle, prepend its `bin` directory to `PATH`, and
run the protocol in `VALIDATION.md`. The structural witnesses must bottom under
`cue vet -c=false`; the incomplete/disjunctive witnesses must fail when their
public judgement outcome is selected.
