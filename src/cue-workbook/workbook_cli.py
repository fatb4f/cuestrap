"""Browserless command surface for the canonical CUEstrap workbook."""
from __future__ import annotations

import argparse
import json
import runpy
import sys
from pathlib import Path
from typing import Any, Mapping

from backends import _cue_py_worker
from harness import DEFAULT_WORKBOOK_REQUEST, HarnessError, _reject_claimant_fields, gopy_worker_main
from lsp_mcp import McpServer


def _load_json(path: Path) -> object:
    value = json.loads(path.read_text(encoding="utf-8"))
    _reject_claimant_fields(value, path.name)
    return value


def _run_workbook(app: Any, defs: Mapping[str, Any], result_name: str) -> dict[str, Any]:
    _outputs, definitions = app.run(defs=dict(defs))
    result = definitions.get(result_name)
    if not isinstance(result, dict):
        raise RuntimeError(f"workbook did not produce {result_name}")
    if result.get("status") == "error":
        raise RuntimeError(str(result.get("error", "workbook execution failed")))
    return result


def _dispatch(app: Any) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--probe-request", type=Path)
    parser.add_argument("--gopy-worker", action="store_true")
    parser.add_argument("--cue-py-worker", action="store_true")
    parser.add_argument("--serve-mcp", choices=("cue-lsp", "gopls"))
    args, marimo_args = parser.parse_known_args()

    if args.gopy_worker:
        return gopy_worker_main()
    if args.cue_py_worker:
        return _cue_py_worker()
    root = args.repo_root.resolve(strict=True)
    if args.serve_mcp:
        return McpServer(args.serve_mcp, root).serve()
    if args.validate:
        result = _run_workbook(
            app,
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
            app,
            {
                "execution_mode": "probe",
                "repo_root": str(root),
                "workbook_request": _load_json(args.probe_request),
            },
            "probe_result",
        )
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    sys.argv = [sys.argv[0], *marimo_args]
    app.run()
    return 0


def run(app: Any) -> int:
    try:
        return _dispatch(app)
    except HarnessError as error:
        print(json.dumps({"error": error.encode()}, sort_keys=True), file=sys.stderr)
        return 2


def main() -> int:
    workbook = Path(__file__).with_name("cue-workbook.py")
    namespace = runpy.run_path(str(workbook))
    return run(namespace["app"])


if __name__ == "__main__":
    raise SystemExit(main())
