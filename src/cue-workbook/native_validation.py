"""Workbook execution surface for the native CUE v0.18 model."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from backends import observe_cli
from models import parse_probe_request
from native_backend import compare_native_backends, observe_cueprobe, observe_gopy_worker


def execute_native_probe(root: Path, raw_request: object) -> dict[str, Any]:
    root = root.resolve(strict=True)
    request = parse_probe_request(raw_request)
    cli = observe_cli(root, request)
    gopy = observe_gopy_worker(root, request)
    cueprobe = observe_cueprobe(root, request)
    return {
        "schema": "cuestrap.workbook-result.v0",
        "request": request.model_dump(by_alias=True),
        "cli": cli.model_dump(by_alias=True),
        "gopyWorker": gopy.model_dump(by_alias=True),
        "cueprobe": cueprobe.model_dump(by_alias=True),
        "nativeComparison": compare_native_backends(gopy, cueprobe),
    }
