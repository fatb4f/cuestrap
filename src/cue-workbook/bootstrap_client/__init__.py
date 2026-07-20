"""Checked structural boundary for Marimo code-mode bootstrap operations."""

from .client import BootstrapCodeModeClient, QuarantinedObservation
from .generated.models import (
    ApplyCellTransaction,
    BootstrapRunBinding,
    CaptureState,
    RawCodeModeObservation,
    ResolveSession,
    RunFocusedProbe,
    SessionBinding,
)
from .lt01_execution import execute_intent as execute_lt01_intent
from .lt01_execution import qualify_matrix as qualify_lt01_matrix
from .lt01_protocol import ExecutionIntent as LT01ExecutionIntent
from .lt01_protocol import resolve_execution as resolve_lt01_execution
from .mcp_adapter import MCPAdapter
from .recorder import MemoryObservationRecorder

__all__ = [
    "ApplyCellTransaction",
    "BootstrapCodeModeClient",
    "BootstrapRunBinding",
    "CaptureState",
    "LT01ExecutionIntent",
    "MCPAdapter",
    "MemoryObservationRecorder",
    "QuarantinedObservation",
    "RawCodeModeObservation",
    "ResolveSession",
    "RunFocusedProbe",
    "SessionBinding",
    "execute_lt01_intent",
    "qualify_lt01_matrix",
    "resolve_lt01_execution",
]
