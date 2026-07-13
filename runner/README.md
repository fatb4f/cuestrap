# Thin runner bootstrap surface

This directory is reserved for a thin Go runner when the workbook-native cue-py/libcue backend or CUE CLI reference backend cannot provide the required isolation, diagnostic fidelity, or semantic operation.

The runner must consume a closed probe request and emit raw facts, diagnostics, identities, and process states. It must not own expected outcomes or admission verdicts, and it must be invoked through the Marimo workbook.
