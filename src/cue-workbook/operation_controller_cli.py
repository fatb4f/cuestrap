#!/usr/bin/env python3
"""Run one general action through a fresh disposable Marimo controller workbook."""
from __future__ import annotations

import argparse
import json
import os
import runpy
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

WORKBOOK_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(WORKBOOK_ROOT))

from supervisory_hooks.routing import decode_controller_request  # noqa: E402


def _git_private_directory(repository_root: Path) -> Path:
    configured = os.environ.get("CUESTRAP_CONTROLLER_DATA_DIR")
    if configured:
        return Path(configured).resolve()
    result = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=repository_root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    directory = Path(result.stdout.strip())
    if not directory.is_absolute():
        directory = repository_root / directory
    return directory.resolve() / "cuestrap-operation-controller"


def _run_workbook(app: Any, defs: Mapping[str, Any]) -> dict[str, Any]:
    _outputs, definitions = app.run(defs=dict(defs))
    result = definitions.get("execution_result")
    if not isinstance(result, dict):
        raise RuntimeError("controller workbook did not produce execution_result")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--payload", required=True)
    args = parser.parse_args(argv)

    root = args.repository_root.resolve(strict=True)
    request = decode_controller_request(args.payload)
    workbook = WORKBOOK_ROOT / "operation-controller.py"
    namespace = runpy.run_path(str(workbook))
    result = _run_workbook(
        namespace["app"],
        {
            "execution_mode": "execute",
            "repository_root": str(root),
            "controller_state_root": str(_git_private_directory(root)),
            "controller_request": request.model_dump(
                by_alias=True,
                mode="json",
                exclude_none=True,
            ),
        },
    )

    if result.get("status") == "error":
        print(json.dumps(result, sort_keys=True), file=sys.stderr)
        return 70

    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")
    if isinstance(stdout, str):
        sys.stdout.write(stdout)
    if isinstance(stderr, str):
        sys.stderr.write(stderr)

    return_code = result.get("returnCode")
    if isinstance(return_code, int):
        return return_code
    print(json.dumps(result, sort_keys=True), file=sys.stderr)
    return 75


if __name__ == "__main__":
    raise SystemExit(main())
