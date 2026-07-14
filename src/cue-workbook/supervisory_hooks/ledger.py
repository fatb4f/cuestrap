"""Locked, append-only supervisory ledger and atomic state snapshot."""
from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import fcntl

from .models import LedgerRecord, SupervisorState


class LedgerTransaction:
    def __init__(self, state: SupervisorState) -> None:
        self.state = state
        self.records: list[LedgerRecord] = []

    def next_sequence(self) -> int:
        sequence = self.state.sequence + 1
        self.state = self.state.model_copy(update={"sequence": sequence})
        return sequence

    def append(self, record: LedgerRecord) -> None:
        if record.sequence != self.state.sequence:
            raise ValueError("record sequence does not match supervisory state")
        self.records.append(record)


class DurableLedger:
    def __init__(self, directory: Path, *, initial_phase: str = "inspect") -> None:
        self.directory = directory.resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.state_path = self.directory / "state.json"
        self.ledger_path = self.directory / "events.jsonl"
        self.lock_path = self.directory / "lock"
        self.initial_phase = initial_phase

    def _load_state(self) -> SupervisorState:
        if not self.state_path.exists():
            return SupervisorState(phase=self.initial_phase)
        return SupervisorState.model_validate_json(self.state_path.read_text(encoding="utf-8"))

    def _write_state(self, state: SupervisorState) -> None:
        encoded = state.model_dump_json(by_alias=True, indent=2) + "\n"
        descriptor, temporary = tempfile.mkstemp(prefix="state-", suffix=".json", dir=self.directory)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.state_path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _append_records(self, records: list[LedgerRecord]) -> None:
        if not records:
            return
        with self.ledger_path.open("a", encoding="utf-8") as stream:
            for record in records:
                stream.write(record.model_dump_json(by_alias=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    @contextmanager
    def transaction(self) -> Iterator[LedgerTransaction]:
        with self.lock_path.open("a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            transaction = LedgerTransaction(self._load_state())
            try:
                yield transaction
                self._append_records(transaction.records)
                self._write_state(transaction.state)
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def read_state(self) -> SupervisorState:
        with self.transaction() as transaction:
            return transaction.state

    def read_records(self) -> list[dict[str, object]]:
        if not self.ledger_path.exists():
            return []
        return [json.loads(line) for line in self.ledger_path.read_text(encoding="utf-8").splitlines()]
