# Launch the loopback-only Marimo code-mode MCP listener.
marimo-listener:
    direnv exec . uv run --project . --locked --exact -- \
        marimo edit --headless --no-token --host 127.0.0.1 --port 2718 --mcp code-mode \
        src/cue-workbook/cue-workbook.py
