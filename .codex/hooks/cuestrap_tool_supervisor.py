#!/usr/bin/env python3
"""Repository-stable entrypoint for CUEstrap Codex lifecycle hooks."""
from __future__ import annotations

import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
WORKBOOK_ROOT = REPOSITORY_ROOT / "src/cue-workbook"
sys.path.insert(0, str(WORKBOOK_ROOT))

from supervisory_hooks.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main(wire_safe=True))
