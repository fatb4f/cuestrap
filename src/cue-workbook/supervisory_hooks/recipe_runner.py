#!/usr/bin/env python3
"""Execute one digest-bound Just recipe request without a shell."""
from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

WORKBOOK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBOOK_ROOT))

from supervisory_hooks.policy import classify_tool  # noqa: E402
from supervisory_hooks.routing import (  # noqa: E402
    RECIPE_BY_TARGET,
    WORKBOOK_TARGETS,
    RecipeRequest,
    decode_recipe_request,
)


def _bounded_cwd(repository_root: Path, relative: str) -> Path:
    root = repository_root.resolve(strict=True)
    candidate = (root / relative).resolve(strict=True)
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("recipe working directory escaped repository") from error
    return candidate


def _validate(request: RecipeRequest, repository_root: Path) -> None:
    if request.proposed_tool_name.casefold() == "bash":
        assert request.argv is not None
        tool_name = "Bash"
        tool_input: object = {"command": shlex.join(request.argv)}
    else:
        tool_name = request.proposed_tool_name
        tool_input = request.tool_input
    classification = classify_tool(tool_name, tool_input, repository_root=repository_root)
    if not classification.recognized or classification.operation is None:
        raise ValueError("recipe request no longer matches the closed operation vocabulary")
    operation = classification.operation
    if operation.target_id in WORKBOOK_TARGETS:
        raise ValueError("workbook-centric actions must not execute through a general recipe")
    if RECIPE_BY_TARGET.get(operation.target_id) != request.recipe_id:
        raise ValueError("recipe identity mismatch")
    if operation.target_id != request.target_id:
        raise ValueError("recipe target identity mismatch")
    if operation.request_digest != request.request_digest:
        raise ValueError("recipe request digest mismatch")


def execute(request: RecipeRequest, repository_root: Path) -> int:
    _validate(request, repository_root)
    cwd = _bounded_cwd(repository_root, request.working_directory)
    if request.proposed_tool_name.casefold() == "bash":
        assert request.argv is not None
        if request.argv[:2] == ("command", "-v") and len(request.argv) == 3:
            resolved = shutil.which(request.argv[2])
            if resolved is None:
                return 1
            print(resolved)
            return 0
        return subprocess.run(list(request.argv), cwd=cwd, check=False).returncode

    assert request.proposed_tool_name == "apply_patch"
    assert isinstance(request.tool_input, dict)
    executable = shutil.which("apply_patch")
    if executable is None:
        raise RuntimeError("apply_patch executable is unavailable to the recipe runner")
    patch = request.tool_input["command"]
    return subprocess.run(
        [executable],
        cwd=cwd,
        input=patch,
        text=True,
        check=False,
    ).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("payload")
    args = parser.parse_args(argv)
    request = decode_recipe_request(args.payload)
    return execute(request, args.repository_root)


if __name__ == "__main__":
    raise SystemExit(main())
