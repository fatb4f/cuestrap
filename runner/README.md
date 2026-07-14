# Native runner surface

`bindings/` exposes the narrow gopy facade used by the isolated Python worker.
`cmd/cueprobe/` is an independent process backend. Both compile against the exact
CUE checkout selected by `src/cue-workbook/bootstrap_native.py`.

The backends consume the same closed probe request, including its package
selector, and emit raw facts, diagnostics, identities, and process states. They
do not own expected outcomes or admission verdicts; the workbook compares their
digest-bound observations.
