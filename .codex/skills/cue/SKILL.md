---
name: cue
description: Author, refactor, diagnose, and validate nontrivial CUE schemas, evaluators, workflows, evidence ingress, and publication projections. Use when Codex modifies CUE, encounters scope, conjunction, closure, totality, cardinality, or proof-construction failures, or needs concrete positive and negative CUE probes.
---

# CUE Authoring

Valid CUE is not necessarily a valid proof.
```

### 1. CUE LSP: authoring feedback

Use the CUE language server for syntax and parse diagnostics, name resolution,
navigation and references, module and package awareness, hover information,
formatting feedback, and rapid local feedback while editing.

Treat the LSP as a development sensor, not an admission gate. A clean LSP state
does not imply semantic correctness. It may not fully evaluate every conditional
branch or comprehension under concrete inputs, cardinality assumptions,
evidence completeness, observed-versus-expected equivalence, duplicate evidence,
workflow ordering, reference distinctions, or application-specific proof
obligations.

### 2. Package gates: structural evaluation

Run these gates even when the LSP reports no diagnostics:

```bash
cue fmt --check --files <changed-files>
cue vet <package>
cue vet -c <package>
```

Passing them means the package formats, unifies, and exposes the requested
concrete surface. It does not prove that incorrect evidence is rejected.
