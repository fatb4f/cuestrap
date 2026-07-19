# LT-01 fixture-design handoff

Issue #18 instantiates the first concrete package governed by the qualified S04
consumer profile.

## Qualified input

- contract source-set digest: `sha256:0b756609d6b5f17be6c062b2ec7e15d1f22be0bece9702a2fea140f1d806e217`
- frozen handoff manifest head: `3ae2953936b8eee86068516d666b8faec1f5789b`
- merged contract commit: `0adfb2bae27f9bcd28c1c9feea84b97fbbda3451`

## Produced values

- `lt01Package` — `LT01MinimalPPFPackage.v0`
- `lt01QualifiedContract` — concrete `#QualifiedS04ConsumerProfileContract`
- `lt01FixtureDesignManifest` — `LT01FixtureDesignManifest.v0`
- package tree — `pattern/s04/fixtures/lt01`

The package contains directional success, reverse-direction rejection, and an
adversarial structural case, plus one accepted and one rejected candidate.

## Phase boundary

This slice publishes declarations and durable fixtures only. It intentionally
contains no raw observations, normalized facts, comparison results, runtime
capability assertions, or final semantic judgements.

The later execution/judgement slice consumes the package tree digest
`sha256:3a3556162a7b5bc4b740d26a8997961fb6e6533abb1d6dab0e5485ca85f4925b` and populates the reserved evidence roots.

## Validation

```sh
cue fmt --check pattern/s04/*.cue
cue vet -c=false pattern/s04/*.cue
python -m compileall -q src tests
python -m unittest -v tests.test_s04_properties tests.test_s04_lt01_fixtures
```

The package-tree digest is computed from sorted lines of the form:

```text
<sha256 hex><two spaces><package-relative path>\n
```

The manifest separately binds every file digest and the aggregate package-tree
digest.
