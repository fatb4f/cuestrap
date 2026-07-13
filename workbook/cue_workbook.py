"""CUEstrap's reusable Marimo bootstrap laboratory.

The workbook is both the interactive iteration record and the browserless
validation/transport entrypoint. Backends emit observations, never admission
verdicts.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import Any

import marimo

app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo

    from cuestrap.backends import execute_cue_cli, execute_cue_py
    from cuestrap.models import BackendComparison, ProbeRequest
    from cuestrap.process import environment_identity
    from cuestrap.protocol import run_deterministic_properties

    return (
        BackendComparison,
        ProbeRequest,
        environment_identity,
        execute_cue_cli,
        execute_cue_py,
        mo,
        run_deterministic_properties,
    )


@app.cell
def _():
    workbook_request = {
        "schema": "cuestrap.probe-request.v0",
        "probeID": "harness.basic.valid",
        "moduleRoot": ".",
        "files": ["tests/fixtures/basic.cue"],
        "operation": "lookup",
        "expression": "valid",
        "operand": None,
        "backend": "both",
    }
    return (workbook_request,)


@app.cell
def _(ProbeRequest, workbook_request):
    probe_request = ProbeRequest.model_validate(workbook_request)
    return (probe_request,)


@app.cell
def _(environment_identity):
    repo_root = Path.cwd().resolve()
    environment = environment_identity(repo_root, verify_lock=True)
    return environment, repo_root


@app.cell
def _(execute_cue_cli, execute_cue_py, probe_request, repo_root):
    cue_cli_observation = None
    cue_py_observation = None
    if probe_request.backend in {"cue-cli", "both"}:
        cue_cli_observation = execute_cue_cli(repo_root, probe_request)
    if probe_request.backend in {"cue-py", "both"}:
        cue_py_observation = execute_cue_py(repo_root, probe_request)
    return cue_cli_observation, cue_py_observation


@app.cell
def _(BackendComparison, cue_cli_observation, cue_py_observation, probe_request):
    equivalent_subject = bool(
        cue_cli_observation
        and cue_py_observation
        and cue_cli_observation.subject.digest == cue_py_observation.subject.digest
    )
    agrees = None
    if equivalent_subject and cue_cli_observation and cue_py_observation:
        if cue_py_observation.state != "unavailable":
            agrees = (
                cue_cli_observation.state == cue_py_observation.state
                and cue_cli_observation.semantic_bottom == cue_py_observation.semantic_bottom
            )
    comparison = BackendComparison.model_validate(
        {
            "schema": "cuestrap.backend-comparison.v0",
            "probeID": probe_request.probe_id,
            "equivalentSubject": equivalent_subject,
            "agrees": agrees,
            "cueCLI": cue_cli_observation.model_dump(by_alias=True) if cue_cli_observation else None,
            "cuePy": cue_py_observation.model_dump(by_alias=True) if cue_py_observation else None,
        }
    )
    return (comparison,)


@app.cell
def _(comparison, environment, mo):
    workbook_result = {
        "schema": "cuestrap.workbook-result.v0",
        "environment": environment.model_dump(by_alias=True),
        "comparison": comparison.model_dump(by_alias=True),
    }
    mo.vstack(
        [
            mo.md("# CUEstrap single-pattern bootstrap"),
            mo.md(
                "This workbook records one bounded semantic subject and compares "
                "the CUE CLI reference backend with cue-py/libcue when available."
            ),
            mo.json(workbook_result),
        ]
    )
    return (workbook_result,)


def _validate_config(repo_root: Path) -> dict[str, Any]:
    config_path = repo_root / ".codex/config.toml"
    pyproject_path = repo_root / "pyproject.toml"
    problems: list[str] = []
    try:
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        servers = config.get("mcp_servers")
        if not isinstance(servers, dict) or set(servers) != {"cue_lsp", "gopls"}:
            problems.append("config must declare exactly cue_lsp and gopls MCP servers")
        for name in ("cue_lsp", "gopls"):
            args = list((servers or {}).get(name, {}).get("args") or [])
            required = {"run", "--project", ".", "--locked", "--exact", "workbook/cue_workbook.py"}
            if not required.issubset(args):
                problems.append(f"{name} does not use the locked workbook environment")
    except Exception as error:
        problems.append(f"config: {type(error).__name__}: {error}")
    try:
        project = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        workbook = project["tool"]["cuestrap"]["project"]["workbook"]
        if workbook != "workbook/cue_workbook.py" or not (repo_root / workbook).is_file():
            problems.append("pyproject workbook coordinate is invalid")
    except Exception as error:
        problems.append(f"pyproject: {type(error).__name__}: {error}")
    return {"status": "pass" if not problems else "fail", "problems": problems}


def run_validation(repo_root: Path) -> dict[str, Any]:
    from cuestrap.backends import execute_cue_cli
    from cuestrap.models import ProbeRequest
    from cuestrap.process import environment_identity
    from cuestrap.protocol import run_deterministic_properties

    repo_root = repo_root.resolve(strict=True)
    environment = environment_identity(repo_root, verify_lock=True)
    properties = run_deterministic_properties(repo_root)
    configuration = _validate_config(repo_root)
    request = ProbeRequest.model_validate(
        {
            "schema": "cuestrap.probe-request.v0",
            "probeID": "harness.basic.valid",
            "moduleRoot": ".",
            "files": ["tests/fixtures/basic.cue"],
            "operation": "lookup",
            "expression": "valid",
            "operand": None,
            "backend": "cue-cli",
        }
    )
    observation = execute_cue_cli(repo_root, request)
    checks = {
        "configuration": configuration,
        "properties": properties,
        "environmentLocked": environment.locked,
        "cueSmoke": observation.model_dump(by_alias=True),
    }
    if configuration["status"] == "fail" or properties["status"] != "pass":
        status = "fail"
    elif not environment.locked or observation.state in {"unavailable", "infrastructure-failure"}:
        status = "blocked"
    elif observation.state == "rejected":
        status = "fail"
    else:
        status = "pass"
    return {
        "schema": "cuestrap.validation-result.v0",
        "status": status,
        "environment": environment.model_dump(by_alias=True),
        "checks": checks,
    }


def run_probe(repo_root: Path, request_path: Path) -> dict[str, Any]:
    from cuestrap.models import ProbeRequest
    from cuestrap.protocol import bounded_path, reject_claimant_fields

    path = bounded_path(repo_root, request_path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    reject_claimant_fields(raw, path.name)
    ProbeRequest.model_validate(raw)
    _outputs, definitions = app.run(defs={"workbook_request": raw})
    result = definitions.get("workbook_result")
    if not isinstance(result, dict):
        raise RuntimeError("workbook did not produce workbook_result")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--probe-request", type=Path)
    parser.add_argument("--serve-mcp", choices=("cue-lsp", "gopls"))
    args, marimo_args = parser.parse_known_args()
    repo_root = args.repo_root.resolve()
    if args.validate:
        result = run_validation(repo_root)
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0 if result["status"] == "pass" else 1
    if args.probe_request:
        print(json.dumps(run_probe(repo_root, args.probe_request), sort_keys=True, separators=(",", ":")))
        return 0
    if args.serve_mcp:
        from cuestrap.mcp import serve_mcp

        return serve_mcp(args.serve_mcp, repo_root)
    sys.argv = [sys.argv[0], *marimo_args]
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
