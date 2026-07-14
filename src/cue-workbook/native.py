"""Direct, exploratory access to the generated gopy CUE binding."""
from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

CUE_REVISION = "806821e40fae070318600a264d311517e596353b"
CUE_MODULE_VERSION = "v0.18.0"
GOPY_REVISION = "72557f647208599c726c14dc9721a6c850d2e6d9"


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
    return value


def build_manifest(root: Path | None = None) -> dict[str, Any] | None:
    root = root or Path(__file__).resolve().parents[2]
    path = root / ".deps" / "manifest.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


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
