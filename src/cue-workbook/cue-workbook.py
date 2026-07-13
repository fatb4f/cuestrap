"""Marimo entrypoint and browserless command surface for CUEstrap."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

from harness import HarnessError, _cue_py_worker, _reject_claimant_fields
from lsp_mcp import McpServer


def create_app():
    try:
        import marimo
    except ImportError:
        return None

    app = marimo.App(width="full")

    @app.cell
    def _():
        from pathlib import Path

        import marimo as mo

        from harness import DEFAULT_WORKBOOK_REQUEST, execute_probe, run_architecture_validation

        return DEFAULT_WORKBOOK_REQUEST, Path, execute_probe, mo, run_architecture_validation

    @app.cell
    def _(DEFAULT_WORKBOOK_REQUEST, Path):
        execution_mode = "interactive"
        repo_root = str(Path.cwd())
        workbook_request = DEFAULT_WORKBOOK_REQUEST
        return execution_mode, repo_root, workbook_request

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
    def _(Path, execution_mode, repo_root, run_architecture_validation, run_environment):
        if run_environment.value or execution_mode == "validate":
            environment_result = run_architecture_validation(Path(repo_root))
        else:
            environment_result = {"status": "pending"}
        return (environment_result,)

    @app.cell
    def _(Path, execute_probe, execution_mode, repo_root, run_probe, workbook_request):
        if run_probe.value or execution_mode == "probe":
            try:
                probe_result = execute_probe(Path(repo_root), workbook_request)
            except Exception as error:
                probe_result = {"status": "error", "error": f"{type(error).__name__}: {error}"}
        else:
            probe_result = {"status": "pending"}
        return (probe_result,)

    @app.cell
    def _(environment_result, execution_mode, mo, probe_result, workbook_request):
        mo.vstack(
            [
                mo.md(f"**Execution mode:** `{execution_mode}`"),
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


def _run_workbook(defs: Mapping[str, Any], result_name: str) -> dict[str, Any]:
    if app is None:
        raise RuntimeError("marimo is unavailable; run through the locked uv project")
    _outputs, definitions = app.run(defs=dict(defs))
    result = definitions.get(result_name)
    if not isinstance(result, dict):
        raise RuntimeError(f"workbook did not produce {result_name}")
    if result.get("status") == "error":
        raise RuntimeError(str(result.get("error", "workbook execution failed")))
    return result


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
        result = _run_workbook(
            {"execution_mode": "validate", "repo_root": str(root)},
            "environment_result",
        )
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0 if result.get("status") == "pass" else 1
    if args.probe_request:
        result = _run_workbook(
            {
                "execution_mode": "probe",
                "repo_root": str(root),
                "workbook_request": _load_json(args.probe_request),
            },
            "probe_result",
        )
        print(json.dumps(result, sort_keys=True, indent=2))
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
