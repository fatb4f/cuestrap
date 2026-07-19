# Exact validation protocol

The qualification surface is the offline CUEstrap tool bundle supplied with the
project sources. Its outer archive identity is:

```text
cuestrap-tools-linux-amd64.tar.zst
sha256:bde8864f55193a712d5e0b55e89c4e7a7fb6de11f0667dd8235f8e21373cc5e3
```

The installed CUE executable reports:

```text
cue-lang/cue revision 806821e40fae070318600a264d311517e596353b
CUE language version v0.18.0
Go 1.26.5
```

## Positive package qualification

```sh
cue fmt --check pattern/s04/*.cue
cue vet -c=false pattern/s04/*.cue
cue eval -c pattern/s04/*.cue \
  -e validation.positive.judgement --out json
cue eval -c pattern/s04/*.cue \
  -e validation.indeterminate.judgement --out json
```

Expected outcomes are `satisfied` and `indeterminate`.

The package contains incomplete reusable definitions, so structural vetting uses
`-c=false`. The two admitted judgement values are separately evaluated with
`-c`, and judgement publication itself is guarded by the CUE-owned JSON
concreteness gate.

## Concrete expected-bottom witnesses

Copy each file to a temporary `.cue` filename and require
`cue vet -c=false pattern/s04/*.cue` to fail:

- `negative_validate.cue.txt` — validate cannot carry a right operand;
- `invalid_reference.cue.txt` — semantic references must exist;
- `invalid_projection.cue.txt` — projection cases must be total and valid;
- `invalid_claim_value.cue.txt` — expected facts preserve claim values;
- `invalid_materialization.cue.txt` — materialization references must exist;
- `invalid_outcome_constraint.cue.txt` — required outcome must match;
- `invalid_unpermitted_outcome.cue.txt` — derived outcome must be permitted;
- `invalid_required_not_permitted.cue.txt` — required must be in permitted.

## Incomplete/disjunctive publication witnesses

Copy each file to a temporary `.cue` filename and require selection of the named
public outcome to fail:

```text
invalid_incomplete_claim_value.cue.txt
    invalidIncompleteClaimValue.judgement.outcome

invalid_incomplete_materialization.cue.txt
    invalidIncompleteMaterialization.judgement.outcome

invalid_disjunctive_materialization.cue.txt
    invalidDisjunctiveMaterialization.judgement.outcome

invalid_disjunctive_required_outcome.cue.txt
    invalidDisjunctiveRequiredOutcome.judgement.outcome
```

These witnesses specifically prevent a concrete semantic outcome from escaping
through CUE narrowing of unresolved or disjunctive consumer input.

The durable command/result record is `qualification_receipt.json`. It is
evidence for the source set but is excluded from the source-set digest to avoid
self-reference.
