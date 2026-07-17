# Exact validation protocol

The qualification surface for this contract bundle is the upstream CUE source
revision pinned by the repository:

```text
cue-lang/cue@806821e40fae070318600a264d311517e596353b
language/module target v0.18.0
Go 1.25.5
```

The validator builds the CLI from that exact revision:

```sh
GOBIN="$RUNNER_TEMP/bin" \
  go install cuelang.org/go/cmd/cue@806821e40fae070318600a264d311517e596353b
cue version
```

It then evaluates the committed generic contract witness:

```sh
cue fmt --check pattern/s04/*.cue
cue vet -c=false pattern/s04/*.cue
cue eval pattern/s04/*.cue \
  -e validation.positive.judgement.outcome --out text
cue eval pattern/s04/*.cue \
  -e validation.indeterminate.judgement.outcome --out text
cue eval pattern/s04/*.cue -e sliceOutput --out json
```

Expected outputs are `satisfied` and `indeterminate`. The package contains
incomplete reusable definitions, so structural vetting deliberately uses
`-c=false`; concrete witness expressions are separately evaluated.

Each `.cue.txt` negative input is copied to a temporary `.cue` filename and must
bottom under `cue vet -c=false pattern/s04/*.cue`:

- a validate operation carrying a right operand;
- a realization containing foreign semantic references;
- a projection containing a foreign realization case.

The committed witness is generic qualification evidence, not an LT-01 package
fixture and not a second semantic authority.
