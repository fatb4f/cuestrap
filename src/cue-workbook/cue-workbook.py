"""Marimo entrypoint and browserless command surface for CUEstrap."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from harness import (
    DEFAULT_WORKBOOK_REQUEST,
    HarnessError,
    _cue_py_worker,
    _reject_claimant_fields,
    execute_probe,
    run_architecture_validation,
)
from lsp_mcp import McpServer


def create_app():
    try:
        import marimo
    except ImportError:
        return None

    app = marimo.App(width="full")

    @app.cell
    def _():
        import marimo as mo
        return (mo,)

    @app.cell
    def _():
        workbook_request = DEFAULT_WORKBOOK_REQUEST
        return (workbook_request,)

    @app.cell
    def _(mo):
        run_environment = mo.ui.run_button(label="Validate locked environment")
        run_probe = mo.ui.run_button(label="Run registered probe")
        mo.vstack(
            [
                mo.md("# CUE bootstrap workbook"),
                mo.md("One pattern, one kernel projection, one probe, and controlled backend observations."),
                mo.hstack([run_environment, run_probe]),
            ]
        )
        return run_environment, run_probe

    @app.cell
    def _(run_environment):
        if run_environment.value:
            environment_result = run_architecture_validation(Path.cwd())
        else:
            environment_result = {"status": "pending"}
        return (environment_result,)

    @app.cell
    def _(run_probe, workbook_request):
        if run_probe.value:
            try:
                probe_result = execute_probe(Path.cwd(), workbook_request)
            except Exception as error:
                probe_result = {"status": "error", "error": f"{type(error).__name__}: {error}"}
        else:
            probe_result = {"status": "pending"}
        return (probe_result,)

    @app.cell
    def _(environment_result, mo, probe_result, workbook_request):
        mo.vstack(
            [
                mo.md("## Iteration request"),
                mo.json(workbook_request),
                mo.md("## Environment"),
                mo.json(environment_result),
                mo.md("## Probe observations"),
                mo.json(probe_result),
            ]
        )
        return

    return app


app = create_app()


def _load_json(path: Path) -> object:
    value = json.loads(path.read_text(encoding="utf-8"))
    _reject_claimant_fields(value, path.name)
    return value


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--probe-request", type=Path)
    parser.add_argument("--cue-py-worker", action="store_true")
    parser.add_argument("--serve-mcp", choices=("cue-lsp", "gopls"))
    args, marimo_args = parser.parse_known_args()

    if args.cue_py_worker:
        return _cue_py_worker()
    root = args.repo_root.resolve(strict=True)
    if args.serve_mcp:
        return McpServer(args.serve_mcp, root).serve()
    if args.validate:
        print(json.dumps(run_architecture_validation(root), sort_keys=True, indent=2))
        return 0
    if args.probe_request:
        print(json.dumps(execute_probe(root, _load_json(args.probe_request)), sort_keys=True, indent=2))
        return 0
    if app is None:
        raise RuntimeError("marimo is unavailable; run through the locked uv project")
    sys.argv = [sys.argv[0], *marimo_args]
    app.run()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(_main())
    except HarnessError as error:
        print(json.dumps({"error": error.encode()}, sort_keys=True), file=sys.stderr)
        raise SystemExit(2) from error
