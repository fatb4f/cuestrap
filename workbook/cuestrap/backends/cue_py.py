from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from ..models import ProbeObservation, ProbeRequest
from ..protocol import bounded_files, bounded_path, digest_json
from .cue_cli import build_subject


def _unavailable(request: ProbeRequest, subject, diagnostic: str) -> ProbeObservation:
    return ProbeObservation.model_validate(
        {
            "schema": "cuestrap.probe-observation.v0",
            "probeID": request.probe_id,
            "backend": "cue-py/libcue",
            "stage": "load",
            "state": "unavailable",
            "semanticBottom": None,
            "subject": subject.model_dump(by_alias=True),
            "facts": {},
            "diagnostic": diagnostic,
            "process": None,
        }
    )


def _binding() -> tuple[Any, str | None]:
    cue_py_root = os.environ.get("CUE_PY_ROOT")
    library = os.environ.get("LIBCUE_LIBRARY")
    if not cue_py_root or not library:
        return None, "CUE_PY_ROOT and LIBCUE_LIBRARY are required"
    root = Path(cue_py_root).resolve()
    shared = Path(library).resolve()
    if not root.is_dir() or not shared.is_file():
        return None, "cue-py or libcue coordinate does not exist"
    sys.path.insert(0, str(root))
    library_var = "PATH" if sys.platform == "win32" else ("DYLD_LIBRARY_PATH" if sys.platform == "darwin" else "LD_LIBRARY_PATH")
    os.environ[library_var] = str(shared.parent) + os.pathsep + os.environ.get(library_var, "")
    try:
        module = importlib.import_module("cue")
        context = importlib.import_module("cue.context")
        return (module, context), None
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"


def _source(module_root: Path, files: list[str]) -> str:
    paths = bounded_files(module_root, files)
    return "\n\n".join(path.read_text(encoding="utf-8") for path in paths)


def _operand_source(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True)


def execute_cue_py(repo_root: Path, request: ProbeRequest) -> ProbeObservation:
    subject = build_subject(repo_root, request)
    binding, error = _binding()
    if binding is None:
        return _unavailable(request, subject, error or "binding unavailable")
    _, context_module = binding
    module_root = bounded_path(repo_root, request.module_root)
    try:
        ctx = context_module.Context()
        root = ctx.compile(_source(module_root, request.files))
        value = root.lookup(request.expression)
        stage = "lookup"
        facts: dict[str, Any] = {}
        if request.operation == "unify":
            value = value.unify(ctx.compile(_operand_source(request.operand)))
            stage = "unify"
        elif request.operation == "subsume":
            candidate = ctx.compile(_operand_source(request.operand))
            candidate.check_schema(value)
            stage = "subsume"
            facts["subsumes"] = True
        elif request.operation == "validate":
            value.validate()
            stage = "validate"
        result = value.error()
        if result.__class__.__name__.lower().startswith("err"):
            diagnostic = str(result)
            state, bottom = "rejected", True
        else:
            diagnostic = ""
            state, bottom = "completed", False
            try:
                facts["valueDigest"] = digest_json(json.loads(value.to_json()))
            except Exception:
                facts["valueDigest"] = None
        return ProbeObservation.model_validate(
            {
                "schema": "cuestrap.probe-observation.v0",
                "probeID": request.probe_id,
                "backend": "cue-py/libcue",
                "stage": stage,
                "state": state,
                "semanticBottom": bottom,
                "subject": subject.model_dump(by_alias=True),
                "facts": facts,
                "diagnostic": diagnostic[:4000],
                "process": None,
            }
        )
    except Exception as exc:
        return ProbeObservation.model_validate(
            {
                "schema": "cuestrap.probe-observation.v0",
                "probeID": request.probe_id,
                "backend": "cue-py/libcue",
                "stage": request.operation,
                "state": "rejected",
                "semanticBottom": True,
                "subject": subject.model_dump(by_alias=True),
                "facts": {},
                "diagnostic": f"{type(exc).__name__}: {exc}"[:4000],
                "process": None,
            }
        )
