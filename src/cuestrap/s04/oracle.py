"""Subprocess facade that treats the pinned CUE package as the semantic oracle."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CueEvaluation:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def published(self) -> bool:
        return self.returncode == 0

    def json_value(self) -> Any:
        if not self.published:
            raise RuntimeError(self.stderr)
        return json.loads(self.stdout)


class CueOracle:
    def __init__(self, repo_root: Path, cue_binary: str | Path | None = None) -> None:
        self.repo_root = repo_root.resolve(strict=True)
        self.pattern_root = self.repo_root / "pattern/s04"
        candidate = str(cue_binary or os.environ.get("CUESTRAP_CUE") or shutil.which("cue") or "")
        if not candidate:
            raise RuntimeError("CUE v0.18 is unavailable; set CUESTRAP_CUE")
        self.cue_binary = Path(candidate).resolve(strict=True)

    def evaluate(self, relation: str, payload: dict[str, Any], selector: str) -> CueEvaluation:
        package_files = sorted(self.pattern_root.glob("*.cue"))
        witness = (
            "package s04\n\n"
            f"propertySubject: {relation} & "
            + json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            + "\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".cue",
            prefix="zz_property_",
            dir=self.pattern_root,
            delete=False,
        ) as stream:
            stream.write(witness)
            witness_path = Path(stream.name)
        try:
            argv = (
                str(self.cue_binary),
                "eval",
                "-c",
                *(str(path) for path in package_files),
                str(witness_path),
                "-e",
                f"propertySubject.{selector}",
                "--out",
                "json",
            )
            process = subprocess.run(
                argv,
                cwd=self.repo_root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )
            return CueEvaluation(argv=argv, returncode=process.returncode, stdout=process.stdout, stderr=process.stderr)
        finally:
            witness_path.unlink(missing_ok=True)

    def assert_package_is_formatted_and_valid(self) -> None:
        files = tuple(str(path) for path in sorted(self.pattern_root.glob("*.cue")))
        for argv in (
            (str(self.cue_binary), "fmt", "--check", *files),
            (str(self.cue_binary), "vet", "-c=false", *files),
        ):
            subprocess.run(argv, cwd=self.repo_root, check=True, timeout=30)
