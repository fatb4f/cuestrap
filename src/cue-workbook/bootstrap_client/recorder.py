"""Raw observation recording without semantic classification."""
from __future__ import annotations

from pathlib import Path

from .generated.models import RawCodeModeObservation, digest_json


class MemoryObservationRecorder:
    def __init__(self) -> None:
        self.observations: list[RawCodeModeObservation] = []

    @property
    def next_sequence(self) -> int:
        return len(self.observations)

    def record(self, observation: RawCodeModeObservation) -> str:
        self.observations.append(observation)
        return digest_json(observation.model_dump(by_alias=True, mode="json"))


class JsonLinesObservationRecorder(MemoryObservationRecorder):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path

    def record(self, observation: RawCodeModeObservation) -> str:
        observation_id = super().record(observation)
        encoded = observation.model_dump_json(by_alias=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(encoded + "\n")
        return observation_id
