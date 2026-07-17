# Launch the loopback-only Marimo code-mode MCP listener for the target workbook.
marimo-listener:
    direnv exec . uv run --project . --locked --exact -- \
        marimo edit --headless --no-token --host 127.0.0.1 --port 2718 --mcp code-mode \
        src/cue-workbook/cue-workbook.py

# Open the disposable controller workbook template for operator inspection.
operation-controller:
    direnv exec . uv run --project . --locked --exact -- \
        marimo edit src/cue-workbook/operation-controller.py
