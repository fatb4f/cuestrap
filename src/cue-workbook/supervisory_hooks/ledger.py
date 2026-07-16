"""Atomic control state plus an independently append-only evidence ledger."""
from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import fcntl

from .models import (
    Activity,
    EvidenceRecord,
    SupervisorState,
    SupervisorStateV1,
    default_scope,
    digest_json,
)


def migrate_state_document(
    raw: object,
    *,
    initial_activity: Activity = "inspect",
) -> SupervisorState:
    """Validate and migrate v1 once; validating v2 is idempotent."""
    if not isinstance(raw, dict):
        raise ValueError("supervisory state must be a JSON object")
    schema_version = raw.get("schemaVersion", raw.get("schema_version"))
    if schema_version == "supervisory-state/v2":
        return SupervisorState.model_validate(raw)
    if schema_version != "supervisory-state/v1":
        raise ValueError(f"unsupported supervisory state schema: {schema_version!r}")

    legacy = SupervisorStateV1.model_validate(raw)
    migrated = SupervisorState(
        scope=default_scope(legacy.phase),
        session_id=legacy.session_id,
        run_id=legacy.run_id,
        attempt_id=legacy.attempt_id,
        pending={},
        legacy_state_digest=digest_json(raw),
    )
    # Validate the serialized v2 document before it is eligible for persistence.
    return SupervisorState.model_validate(migrated.model_dump(by_alias=True, mode="json"))


class LedgerTransaction:
    def __init__(
        self,
        state: SupervisorState,
        history: list[dict[str, object]],
        *,
        migration_pending: bool,
    ) -> None:
        self.initial_state = state
        self.state = state
        self.history = history
        self.records: list[EvidenceRecord] = []
        self.migration_pending = migration_pending
        self._sequence = max(
            (
                value
                for record in history
                if isinstance((value := record.get("sequence")), int)
            ),
            default=0,
        )

    def next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    def append(self, record: EvidenceRecord) -> None:
        if record.sequence != self._sequence:
            raise ValueError("record sequence does not match evidence ledger sequence")
        self.records.append(record)

    @property
    def state_changed(self) -> bool:
        return self.migration_pending or self.state != self.initial_state


class DurableLedger:
    def __init__(self, directory: Path, *, initial_activity: Activity = "inspect") -> None:
        self.directory = directory.resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.state_path = self.directory / "state.json"
        self.ledger_path = self.directory / "events.jsonl"
        self.lock_path = self.directory / "lock"
        self.initial_activity = initial_activity

    def _load_state(self) -> tuple[SupervisorState, bool]:
        if not self.state_path.exists():
            return SupervisorState(scope=default_scope(self.initial_activity)), False
        raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        migration_pending = isinstance(raw, dict) and raw.get("schemaVersion") != (
            "supervisory-state/v2"
        )
        return (
            migrate_state_document(raw, initial_activity=self.initial_activity),
            migration_pending,
        )

    def _load_records(self) -> list[dict[str, object]]:
        if not self.ledger_path.exists():
            return []
        records: list[dict[str, object]] = []
        for index, line in enumerate(self.ledger_path.read_text(encoding="utf-8").splitlines(), 1):
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"evidence record {index} is not a JSON object")
            records.append(value)
        return records

    def _write_state(self, state: SupervisorState) -> None:
        validated = SupervisorState.model_validate(state.model_dump(by_alias=True, mode="json"))
        encoded = validated.model_dump_json(by_alias=True, indent=2) + "\n"
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

    def _append_records(self, records: list[EvidenceRecord]) -> None:
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
            state, migration_pending = self._load_state()
            transaction = LedgerTransaction(
                state,
                self._load_records(),
                migration_pending=migration_pending,
            )
            try:
                yield transaction
                if transaction.state_changed:
                    self._write_state(transaction.state)
                self._append_records(transaction.records)
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def read_state(self) -> SupervisorState:
        with self.transaction() as transaction:
            return transaction.state

    def read_records(self) -> list[dict[str, object]]:
        with self.lock_path.open("a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_SH)
            try:
                return self._load_records()
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
