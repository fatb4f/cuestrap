"""Build the pinned independent cueprobe runner without the exploratory gopy extension."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

CUE_REPOSITORY = "https://github.com/cue-lang/cue"
CUE_REVISION = "806821e40fae070318600a264d311517e596353b"
CUE_MODULE_VERSION = "v0.18.0"
MANIFEST_SCHEMA = "cuestrap.cueprobe-build-manifest.v0"


def run(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def output(*args: str, cwd: Path | None = None) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def checkout(target: Path, repository: str, revision: str) -> None:
    if not target.exists():
        run("git", "clone", "--filter=blob:none", "--no-checkout", repository, str(target))
    run("git", "fetch", "--depth", "1", "origin", revision, cwd=target)
    run("git", "checkout", "--detach", revision, cwd=target)
    observed = output("git", "rev-parse", "HEAD", cwd=target)
    if observed != revision:
        raise RuntimeError(f"checkout mismatch: {observed} != {revision}")


def require_target_checkout(runner: Path, cue_source: Path) -> None:
    document: dict[str, Any] = json.loads(output("go", "mod", "edit", "-json", cwd=runner))
    replacements = document.get("Replace", [])
    replacement = next(
        (
            item.get("New", {}).get("Path")
            for item in replacements
            if item.get("Old", {}).get("Path") == "cuelang.org/go"
        ),
        None,
    )
    if replacement is None or (runner / replacement).resolve() != cue_source.resolve():
        raise RuntimeError("runner/go.mod does not resolve cuelang.org/go to the pinned checkout")


def main() -> int:
    workbook = Path(__file__).resolve().parent
    root = workbook.parents[1]
    runner = root / "runner"
    deps = root / ".deps"
    cue_source = deps / "cue"
    cueprobe = runner / "bin" / ("cueprobe.exe" if os.name == "nt" else "cueprobe")

    checkout(cue_source, CUE_REPOSITORY, CUE_REVISION)
    require_target_checkout(runner, cue_source)
    run("go", "mod", "tidy", cwd=runner)
    cueprobe.parent.mkdir(parents=True, exist_ok=True)
    run("go", "build", "-o", str(cueprobe), "./cmd/cueprobe", cwd=runner)

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "cue": {
            "repository": CUE_REPOSITORY,
            "revision": CUE_REVISION,
            "moduleVersion": CUE_MODULE_VERSION,
        },
        "go": {"version": output("go", "version")},
        "cueprobe": {
            "path": cueprobe.relative_to(root).as_posix(),
            "digest": digest(cueprobe),
        },
    }
    deps.mkdir(exist_ok=True)
    (deps / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
