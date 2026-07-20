"""Build the exact CUE v0.18 gopy extension and cueprobe binary."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

CUE_REPOSITORY = "https://github.com/cue-lang/cue"
CUE_REVISION = "806821e40fae070318600a264d311517e596353b"
CUE_MODULE_VERSION = "v0.18.0"
GOPY_REPOSITORY = "https://github.com/go-python/gopy"
GOPY_REVISION = "72557f647208599c726c14dc9721a6c850d2e6d9"
GOIMPORTS_VERSION = "v0.38.0"
BINDING_PACKAGE = "github.com/fatb4f/cuestrap/runner/bindings"
NATIVE_PYTHON_SERIES = (3, 13)


def run(*args: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    subprocess.run(args, cwd=cwd, env=merged, check=True)


def output(*args: str, cwd: Path | None = None) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def checkout(target: Path, repository: str, revision: str) -> None:
    if not target.exists():
        run("git", "clone", "--filter=blob:none", "--no-checkout", repository, str(target))
    run("git", "fetch", "--depth", "1", "origin", revision, cwd=target)
    run("git", "checkout", "--detach", revision, cwd=target)
    observed = output("git", "rev-parse", "HEAD", cwd=target)
    if observed != revision:
        raise RuntimeError(f"checkout mismatch: {observed} != {revision}")


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_set_digest(files: list[dict[str, str]]) -> str:
    normalized = sorted(files, key=lambda item: item["relativePath"])
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def python_identity(executable: Path) -> dict[str, Any]:
    source = (
        "import json,sys; "
        "print(json.dumps({"
        "'executable': sys.executable, "
        "'abi': getattr(sys.implementation, 'cache_tag', None), "
        "'version': sys.version, "
        "'versionInfo': list(sys.version_info[:3])"
        "}, sort_keys=True))"
    )
    value = json.loads(output(str(executable), "-c", source))
    if not isinstance(value, dict):
        raise RuntimeError("Python identity is not an object")
    return value


def resolve_native_python() -> tuple[Path, dict[str, Any]]:
    configured = os.environ.get("CUESTRAP_NATIVE_PYTHON", sys.executable)
    executable = Path(configured).expanduser().resolve(strict=True)
    identity = python_identity(executable)
    version_info = identity.get("versionInfo")
    if not isinstance(version_info, list) or tuple(version_info[:2]) != NATIVE_PYTHON_SERIES:
        required = ".".join(str(value) for value in NATIVE_PYTHON_SERIES)
        raise RuntimeError(
            f"gopy native worker requires Python {required}.x; "
            f"set CUESTRAP_NATIVE_PYTHON to the pinned worker interpreter: {identity}"
        )
    return executable, identity


def require_pybindgen(executable: Path) -> None:
    process = subprocess.run(
        (str(executable), "-c", "import pybindgen"),
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode:
        raise RuntimeError(
            "pybindgen is required by gopy in the native worker interpreter; "
            "install pybindgen==0.22.1 into CUESTRAP_NATIVE_PYTHON: "
            + (process.stderr.strip() or process.stdout.strip())
        )


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


def install_tools(gopy_source: Path, tools: Path) -> Path:
    tools.mkdir(parents=True, exist_ok=True)
    env = {"GOBIN": str(tools)}
    run("go", "install", ".", cwd=gopy_source, env=env)
    run("go", "install", f"golang.org/x/tools/cmd/goimports@{GOIMPORTS_VERSION}", env=env)
    binary = tools / ("gopy.exe" if os.name == "nt" else "gopy")
    if not binary.is_file():
        raise RuntimeError(f"gopy binary not produced: {binary}")
    return binary


def build_extension(
    gopy: Path,
    runner: Path,
    tools: Path,
    extension: Path,
    native_python: Path,
) -> None:
    staged_extension = runner / "bin" / extension.name
    if staged_extension.exists():
        shutil.rmtree(staged_extension)
    environment = {"PATH": str(tools) + os.pathsep + os.environ.get("PATH", "")}
    run(
        str(gopy),
        "build",
        f"-vm={native_python}",
        f"-name={extension.name}",
        f"-output={staged_extension}",
        BINDING_PACKAGE,
        cwd=runner,
        env=environment,
    )
    if extension.exists():
        shutil.rmtree(extension)
    shutil.move(staged_extension, extension)
    run("go", "mod", "tidy", cwd=runner)


def main() -> int:
    workbook = Path(__file__).resolve().parent
    root = workbook.parents[1]
    runner = root / "runner"
    deps = root / ".deps"
    cue_source = deps / "cue"
    gopy_source = deps / "gopy"
    tools = deps / "bin"
    extension = workbook / "cue_native"
    cueprobe = runner / "bin" / ("cueprobe.exe" if os.name == "nt" else "cueprobe")

    native_python, native_python_identity = resolve_native_python()
    require_pybindgen(native_python)
    checkout(cue_source, CUE_REPOSITORY, CUE_REVISION)
    checkout(gopy_source, GOPY_REPOSITORY, GOPY_REVISION)
    require_target_checkout(runner, cue_source)
    run("go", "mod", "tidy", cwd=runner)
    gopy = install_tools(gopy_source, tools)

    build_extension(gopy, runner, tools, extension, native_python)

    cueprobe.parent.mkdir(parents=True, exist_ok=True)
    run("go", "build", "-o", str(cueprobe), "./cmd/cueprobe", cwd=runner)

    identity_raw = output(
        str(native_python),
        "-c",
        "from cue_native import bindings; print(bindings.IdentityJSON())",
        cwd=workbook,
    )
    identity = json.loads(identity_raw)
    if identity.get("cue_revision") != CUE_REVISION:
        raise RuntimeError(f"extension revision mismatch: {identity}")
    if identity.get("cue_module_version") != CUE_MODULE_VERSION:
        raise RuntimeError(f"extension module mismatch: {identity}")
    if identity.get("observed_cue_module_version") != CUE_MODULE_VERSION:
        raise RuntimeError(f"extension observed module mismatch: {identity}")

    native_files = [
        path
        for path in extension.rglob("*")
        if path.is_file() and path.suffix in {".so", ".dylib", ".dll", ".pyd"}
    ]
    if not native_files:
        raise RuntimeError("gopy produced no native extension")

    extension_files = [
        {"relativePath": path.relative_to(extension).as_posix(), "digest": digest(path)}
        for path in native_files
    ]
    manifest = {
        "cue": {
            "repository": CUE_REPOSITORY,
            "revision": CUE_REVISION,
            "moduleVersion": CUE_MODULE_VERSION,
        },
        "gopy": {"repository": GOPY_REPOSITORY, "revision": GOPY_REVISION},
        "python": native_python_identity,
        "controllerPython": python_identity(Path(sys.executable).resolve(strict=True)),
        "go": {"version": output("go", "version")},
        "extension": {
            "identity": identity,
            "digest": artifact_set_digest(extension_files),
            "files": extension_files,
        },
        "cueprobe": {
            "path": cueprobe.relative_to(root).as_posix(),
            "digest": digest(cueprobe),
        },
    }
    deps.mkdir(exist_ok=True)
    (deps / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
