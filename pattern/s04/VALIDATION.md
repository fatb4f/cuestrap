# Exact validation protocol

The qualification surface for this contract bundle is the upstream CUE source
revision pinned by the repository:

```text
cue-lang/cue@806821e40fae070318600a264d311517e596353b
language/module target v0.18.0
```

The validation branch builds the CLI from that revision with Go 1.25 and runs:

```sh
go install cuelang.org/go/cmd/cue@806821e40fae070318600a264d311517e596353b
cue version
cue fmt --check pattern/s04/*.cue
cue vet ./pattern/s04
cue eval ./pattern/s04 -e validation.positive.judgement.outcome
cue eval ./pattern/s04 -e validation.indeterminate.judgement.outcome
```

The witness is generated only inside the validation job. It is not a durable
fixture and does not become a second source of truth for the contract.
