"""Direct, exploratory access to the generated gopy CUE binding."""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

CUE_REVISION = "806821e40fae070318600a264d311517e596353b"
CUE_MODULE_VERSION = "v0.18.0"
GOPY_REVISION = "72557f647208599c726c14dc9721a6c850d2e6d9"
NATIVE_SUFFIXES = frozenset({".so", ".dylib", ".dll", ".pyd"})
NATIVE_PYTHON_SERIES = (3, 13)


class NativeBindingUnavailable(RuntimeError):
    """Raised when the generated extension is absent or incompatible."""


def import_bindings() -> ModuleType:
    errors: list[BaseException] = []
    for name in ("cue_native.bindings", "bindings"):
        try:
            return importlib.import_module(name)
        except (ImportError, OSError) as error:
            errors.append(error)
    detail = "; ".join(str(error) for error in errors)
    raise NativeBindingUnavailable(
        "native CUE extension unavailable; run "
        "`python src/cue-workbook/bootstrap_native.py`: " + detail
    )


def binding_identity(bindings: ModuleType | None = None) -> dict[str, Any]:
    bindings = bindings or import_bindings()
    value = json.loads(bindings.IdentityJSON())
    if value.get("cue_revision") != CUE_REVISION:
        raise NativeBindingUnavailable(f"unexpected CUE revision: {value}")
    if value.get("cue_module_version") != CUE_MODULE_VERSION:
        raise NativeBindingUnavailable(f"unexpected CUE module target: {value}")
    if value.get("observed_cue_module_version") != CUE_MODULE_VERSION:
        raise NativeBindingUnavailable(f"unexpected compiled CUE module: {value}")
    return value


def _digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _digest_file(path: Path) -> str:
    if not path.is_file():
        raise NativeBindingUnavailable(f"native artifact is missing: {path}")
    return _digest_bytes(path.read_bytes())


def _artifact_set_digest(files: list[dict[str, str]]) -> str:
    normalized = sorted(files, key=lambda item: item["relativePath"])
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
    return _digest_bytes(encoded)


def _manifest_path(root: Path | None = None) -> Path:
    root = root or Path(__file__).resolve().parents[2]
    return root / ".deps" / "manifest.json"


def build_manifest(root: Path | None = None) -> dict[str, Any] | None:
    path = _manifest_path(root)
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise NativeBindingUnavailable(f"invalid native build manifest: {error}") from error
    if not isinstance(value, dict):
        raise NativeBindingUnavailable("native build manifest is not an object")
    cue = value.get("cue")
    if not isinstance(cue, dict):
        raise NativeBindingUnavailable("native build manifest has no CUE identity")
    if cue.get("revision") != CUE_REVISION or cue.get("moduleVersion") != CUE_MODULE_VERSION:
        raise NativeBindingUnavailable(f"native build manifest CUE identity mismatch: {cue}")
    return value


def build_manifest_digest(root: Path | None = None) -> str:
    manifest = build_manifest(root)
    if manifest is None:
        raise NativeBindingUnavailable("native build manifest is missing")
    return _digest_file(_manifest_path(root))


def _python_identity(executable: Path) -> dict[str, Any]:
    source = (
        "import json,sys; "
        "print(json.dumps({"
        "'executable': sys.executable, "
        "'abi': getattr(sys.implementation, 'cache_tag', None), "
        "'version': sys.version, "
        "'versionInfo': list(sys.version_info[:3])"
        "}, sort_keys=True))"
    )
    try:
        raw = subprocess.check_output((str(executable), "-c", source), text=True).strip()
        value = json.loads(raw)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        raise NativeBindingUnavailable(f"native worker Python identity unavailable: {error}") from error
    if not isinstance(value, dict):
        raise NativeBindingUnavailable("native worker Python identity is not an object")
    return value


def native_worker_python(root: Path | None = None) -> Path:
    manifest = build_manifest(root)
    if manifest is None:
        raise NativeBindingUnavailable("native build manifest is missing")
    declared = manifest.get("python")
    if not isinstance(declared, dict):
        raise NativeBindingUnavailable("native build manifest has no worker Python identity")
    configured = os.environ.get("CUESTRAP_NATIVE_PYTHON")
    path_value = configured or declared.get("executable")
    if not isinstance(path_value, str) or not path_value:
        raise NativeBindingUnavailable("native worker Python executable is missing")
    try:
        executable = Path(path_value).expanduser().resolve(strict=True)
    except OSError as error:
        raise NativeBindingUnavailable(f"native worker Python is missing: {path_value}") from error
    observed = _python_identity(executable)
    version_info = observed.get("versionInfo")
    if not isinstance(version_info, list) or tuple(version_info[:2]) != NATIVE_PYTHON_SERIES:
        raise NativeBindingUnavailable(f"native worker Python must be 3.13.x: {observed}")
    for field in ("executable", "abi", "version", "versionInfo"):
        if observed.get(field) != declared.get(field):
            raise NativeBindingUnavailable(
                f"native worker Python identity mismatch for {field}: "
                f"declared {declared.get(field)!r}, observed {observed.get(field)!r}"
            )
    return executable


def verify_extension_artifact(root: Path, extension: Path) -> dict[str, Any]:
    manifest = build_manifest(root)
    if manifest is None:
        raise NativeBindingUnavailable("native build manifest is missing")
    section = manifest.get("extension")
    if not isinstance(section, dict) or not isinstance(section.get("files"), list):
        raise NativeBindingUnavailable("native build manifest has no extension artifacts")

    expected: dict[str, str] = {}
    for item in section["files"]:
        if not isinstance(item, dict) or not isinstance(item.get("digest"), str):
            raise NativeBindingUnavailable("native build manifest has an invalid extension artifact")
        relative = item.get("relativePath")
        if not isinstance(relative, str):
            legacy = item.get("path")
            if not isinstance(legacy, str):
                raise NativeBindingUnavailable("native build manifest extension path is missing")
            try:
                relative = Path(legacy).resolve().relative_to(extension.resolve()).as_posix()
            except ValueError as error:
                raise NativeBindingUnavailable("native build manifest extension path is inconsistent") from error
        expected[relative] = item["digest"]

    actual_paths = sorted(
        path for path in extension.rglob("*") if path.is_file() and path.suffix in NATIVE_SUFFIXES
    )
    actual = {
        path.relative_to(extension).as_posix(): _digest_file(path)
        for path in actual_paths
    }
    if not actual or actual != expected:
        raise NativeBindingUnavailable(
            f"generated extension does not match build manifest: expected {expected}, observed {actual}"
        )
    records = [
        {"relativePath": relative, "digest": digest}
        for relative, digest in actual.items()
    ]
    artifact_digest = _artifact_set_digest(records)
    declared_digest = section.get("digest", artifact_digest)
    if declared_digest != artifact_digest:
        raise NativeBindingUnavailable("generated extension aggregate digest does not match build manifest")
    return {
        "buildManifestDigest": build_manifest_digest(root),
        "artifactDigest": artifact_digest,
        "artifactManifestVerified": True,
    }


def verify_cueprobe_artifact(root: Path, binary: Path) -> dict[str, Any]:
    manifest = build_manifest(root)
    if manifest is None:
        raise NativeBindingUnavailable("native build manifest is missing")
    section = manifest.get("cueprobe")
    if not isinstance(section, dict) or not isinstance(section.get("digest"), str):
        raise NativeBindingUnavailable("native build manifest has no cueprobe artifact")
    artifact_digest = _digest_file(binary)
    if artifact_digest != section["digest"]:
        raise NativeBindingUnavailable("cueprobe digest does not match build manifest")
    return {
        "buildManifestDigest": build_manifest_digest(root),
        "artifactDigest": artifact_digest,
        "artifactManifestVerified": True,
    }


@dataclass
class DirectSession:
    """Live Go-backed values for interactive Marimo exploration only."""

    bindings: ModuleType
    context: Any

    @classmethod
    def open(cls) -> "DirectSession":
        bindings = import_bindings()
        binding_identity(bindings)
        return cls(bindings=bindings, context=bindings.NewContext())

    @property
    def identity(self) -> dict[str, Any]:
        return binding_identity(self.bindings)

    def compile(self, source: str, filename: str = "interactive.cue") -> Any:
        return self.context.CompileString(source, filename)

    def open_loader(self, root: str) -> Any:
        return self.context.OpenLoader(root)


def summarize_value(value: Any) -> dict[str, Any]:
    return {
        "exists": bool(value.Exists()),
        "semanticBottom": bool(value.IsBottom()),
        "error": value.Error() or None,
        "kind": value.Kind(),
        "incompleteKind": value.IncompleteKind(),
        "diagnostics": json.loads(value.DiagnosticsJSON()),
    }
