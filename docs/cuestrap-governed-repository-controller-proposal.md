# Proposal migrated to Kernel Spec

The former **Cuestrap Governed Repository Controller** proposal has been extracted from CUEstrap.

CUEstrap retains its original scope as a narrow laboratory for aligning and qualifying idiomatic CUE patterns against pinned upstream `cue-lang/cue` authority.

The proposal was found to conflate five downstream concerns:

```text
Model A machine-readable semantic specification
+ Model B transport-neutral API model
+ semantic compiler-kernel contracts
+ OSCAL governed-repository project profile
+ OSCAL agentic GitOps controller and binding profile
```

Those concerns now belong to [`fatb4f/kernel-spec`](https://github.com/fatb4f/kernel-spec), initially proposed in [kernel-spec PR #1](https://github.com/fatb4f/kernel-spec/pull/1).

## Destination

- `docs/kernel-spec-proposal.md` — base semantic compiler specification;
- `docs/oscal-agentic-gitops-controller-proposal.md` — downstream governed-project/controller profile;
- `docs/migration-manifest.md` — source-to-destination mapping;
- `spec/` — Model A, Model B, compiler, conformance, behavior, project/controller, and extension seeds;
- `profiles/` — JSON Structure import and OSCAL agentic GitOps seeds.

## Source preservation

The complete original proposal remains available through Git history at blob:

```text
9fe2cb6708d0c2a8a98f2d03cdaae2754c139f36
```

This file remains as a discovery and provenance pointer; it is no longer a CUEstrap architecture proposal.
