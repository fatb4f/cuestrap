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
    normalizes semantic facts, applies comparison rules, and derives
    satisfied / rejected / indeterminate
```

Candidate `accepted` and `rejected` values in the package profile are declared
expectations. They are not runner verdicts and do not establish an S04 semantic
outcome.

## Files

- `semantic_ir.cue` defines the backend-neutral S04 v0 vocabulary and the
  CUE-owned normalization/judgement relation.
- `integrity.cue` proves graph references and authority roles.
- `ppf_profile.cue` defines the minimal Kattis-shaped package profile.
- `projection_relation.cue` derives the total identity-bound projection.
- `slice_output.cue` publishes the exact contract-bundle handoff.
- `validation_witness.cue` and `qualification.cue` prove positive and
  indeterminate semantic derivations.
- `negative_validate.cue.txt`, `invalid_reference.cue.txt`,
  `invalid_projection.cue.txt`, `invalid_claim_value.cue.txt`,
  `invalid_materialization.cue.txt`, and
  `invalid_outcome_constraint.cue.txt` are expected-bottom qualification inputs.
- `VALIDATION.md` records the pinned CUE qualification protocol.

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

From a repository environment with the pinned CUE toolchain:

```sh
cue fmt --check pattern/s04/*.cue
cue vet -c=false pattern/s04/*.cue
cue eval pattern/s04/*.cue -e validation.positive.judgement.outcome --out text
cue eval pattern/s04/*.cue -e validation.indeterminate.judgement.outcome --out text
```

The negative inputs must each bottom when copied to a `.cue` filename and vetted
with the same package. The exact build and evidence protocol is recorded in
`VALIDATION.md`.

The corrected source manifest remains `indeterminate` until those checks are
rerun against the exact source-set digest recorded by `sliceOutput`.
