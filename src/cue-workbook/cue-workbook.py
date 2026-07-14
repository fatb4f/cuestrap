"""Marimo entrypoint and browserless command surface for CUEstrap."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

from harness import (
    DEFAULT_WORKBOOK_REQUEST,
    DirectSession,
    HarnessError,
    NativeBindingUnavailable,
    _reject_claimant_fields,
    gopy_worker_main,
    summarize_value,
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
        from pathlib import Path

        import marimo as mo

        from harness import (
            DEFAULT_WORKBOOK_REQUEST,
            DirectSession,
            NativeBindingUnavailable,
            execute_native_probe,
            run_architecture_validation,
            summarize_value,
        )

        return (
            DEFAULT_WORKBOOK_REQUEST,
            DirectSession,
            NativeBindingUnavailable,
            Path,
            execute_native_probe,
            mo,
            run_architecture_validation,
            summarize_value,
        )

    @app.cell
    def _(DEFAULT_WORKBOOK_REQUEST, Path):
        execution_mode = "interactive"
        repo_root = str(Path.cwd())
        workbook_request = DEFAULT_WORKBOOK_REQUEST
        return execution_mode, repo_root, workbook_request

    @app.cell
    def _(mo):
        run_environment = mo.ui.run_button(label="Validate locked environment")
        run_probe = mo.ui.run_button(label="Run qualified native probe")
        direct_source = mo.ui.text_area(
            label="Interactive CUE source",
            value="x: int & >=0\nx: 2",
            rows=5,
        )
        run_direct = mo.ui.run_button(label="Compile live native value")
        mo.vstack(
            [
                mo.md("# CUE bootstrap workbook"),
                mo.md(
                    "Qualified mode compares an isolated gopy worker with the independent "
                    "`cueprobe` process. Direct mode retains live Go-backed values and is exploratory only."
                ),
                mo.hstack([run_environment, run_probe]),
                mo.md("## Interactive native surface"),
                direct_source,
                run_direct,
            ]
        )
        return direct_source, run_direct, run_environment, run_probe

    @app.cell
    def _(Path, execution_mode, repo_root, run_architecture_validation, run_environment):
        if run_environment.value or execution_mode == "validate":
            environment_result = run_architecture_validation(Path(repo_root))
        else:
            environment_result = {"status": "pending"}
        return (environment_result,)

    @app.cell
    def _(Path, execute_native_probe, execution_mode, repo_root, run_probe, workbook_request):
        if run_probe.value or execution_mode == "probe":
            try:
                probe_result = execute_native_probe(Path(repo_root), workbook_request)
            except Exception as error:
                probe_result = {"status": "error", "error": f"{type(error).__name__}: {error}"}
        else:
            probe_result = {"status": "pending"}
        return (probe_result,)

    @app.cell
    def _(
        DirectSession,
        NativeBindingUnavailable,
        direct_source,
        run_direct,
        summarize_value,
    ):
        direct_result = {"status": "pending"}
        direct_value = None
        if run_direct.value:
            try:
                direct_session = DirectSession.open()
                direct_value = direct_session.compile(direct_source.value, "interactive.cue")
                direct_result = {
                    "status": "exploratory",
                    "identity": direct_session.identity,
                    "summary": summarize_value(direct_value),
                    "proxyType": type(direct_value).__name__,
                }
            except NativeBindingUnavailable as error:
                direct_result = {"status": "unavailable", "error": str(error)}
            except Exception as error:
                direct_result = {"status": "error", "error": f"{type(error).__name__}: {error}"}
        return direct_result, direct_value

    @app.cell
    def _(direct_result, environment_result, execution_mode, mo, probe_result, workbook_request):
        mo.vstack(
            [
                mo.md(f"**Execution mode:** `{execution_mode}`"),
                mo.md("## Iteration request"),
                mo.json(workbook_request),
                mo.md("## Environment"),
                mo.json(environment_result),
                mo.md("## Qualified observations"),
                mo.json(probe_result),
                mo.md("## Direct exploratory observation"),
                mo.json(direct_result),
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
    parser.add_argument("--gopy-worker", action="store_true")
    parser.add_argument("--serve-mcp", choices=("cue-lsp", "gopls"))
    args, marimo_args = parser.parse_known_args()

    if args.gopy_worker:
        return gopy_worker_main()
    root = args.repo_root.resolve(strict=True)
    if args.serve_mcp:
        return McpServer(args.serve_mcp, root).serve()
    if args.validate:
        result = _run_workbook(
            {
                "execution_mode": "validate",
                "repo_root": str(root),
                "workbook_request": DEFAULT_WORKBOOK_REQUEST,
            },
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
