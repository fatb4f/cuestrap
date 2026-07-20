"""Minimal isolated entrypoint for the generated gopy extension."""
from __future__ import annotations

from native_backend import gopy_worker_main


if __name__ == "__main__":
    raise SystemExit(gopy_worker_main())
