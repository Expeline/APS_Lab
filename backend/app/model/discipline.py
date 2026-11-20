"""Правила размещения и извлечения заявок."""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from itertools import count


@dataclass
class Job:
    id: str
    source: int
    serial: int
    arrived: float
    status: StrEnum
    buffered: float | None = None
    slot: int | None = None
    insertion: int = 0
    started: float | None = None
    finished: float | None = None
    rejected: float | None = None
    worker: int | None = None
    batch: int | None = None


class Buffer:
    def __init__(self, size: int):
        self._slots: list[Job | None] = [None] * size
        self._sequence = count(1)

    @property
    def slots(self) -> tuple[Job | None, ...]:
        return tuple(self._slots)

    def place(self, job: Job) -> tuple[int, Job | None]:
        if None in self._slots:
            index = self._slots.index(None)
        else:
            index = self._victim_index()
        victim = self._slots[index]
        job.insertion = next(self._sequence)
        self._slots[index] = job
        return index, victim

    def take(self, index: int) -> Job:
        job = self._slots[index]
        assert job is not None
        self._slots[index] = None
        return job

    def _victim_index(self) -> int:
        occupied = [
            (index, job) for index, job in enumerate(self._slots) if job is not None
        ]
        return max(occupied, key=lambda pair: (pair[1].source, pair[1].insertion))[0]


@dataclass(frozen=True)
class JobBatch:
    number: int
    source: int
    created: float
    ids: tuple[str, ...]
    waiting: set[str]
    running: set[str] = field(default_factory=set)
    completed: set[str] = field(default_factory=set)
    rejected: set[str] = field(default_factory=set)


class DispatchRule:
    def __init__(self, buffer: Buffer):
        self._buffer = buffer
        self._sequence = count(1)
        self._active: JobBatch | None = None
        self._last: JobBatch | None = None

    def take(self, now: float, log: Callable) -> Job | None:
        slots = self._buffer.slots
        if self._active is None:
            source = min((job.source for job in slots if job is not None), default=None)
            if source is None:
                return None
            members = tuple(
                job for job in slots if job is not None and job.source == source
            )
            ids = tuple(job.id for job in members)
            self._active = JobBatch(next(self._sequence), source, now, ids, set(ids))
            for job in members:
                job.batch = self._active.number
            log(
                "BATCH_OPEN",
                None,
                f"Пакет {self._active.number}, И{source}: {', '.join(ids)}",
            )
        batch = self._active
        for index, job in enumerate(slots):
            if job is not None and job.id in batch.waiting:
                batch.waiting.remove(job.id)
                batch.running.add(job.id)
                return self._buffer.take(index)
        return None

    def completed(self, job: Job):
        batch = self._active
        assert batch is not None
        batch.running.remove(job.id)
        batch.completed.add(job.id)

    def rejected(self, job: Job):
        batch = self._active
        if batch is not None and job.id in batch.waiting:
            batch.waiting.remove(job.id)
            batch.rejected.add(job.id)

    def close_if_finished(self, log: Callable):
        batch = self._active
        if batch and not (batch.waiting or batch.running):
            log("BATCH_CLOSE", None, f"Пакет {batch.number} завершён")
            self._last, self._active = batch, None

    def snapshot(self) -> dict:
        return {
            "batch": self._batch_info(self._active),
            "last_batch": self._batch_info(self._last),
        }

    @staticmethod
    def _batch_info(batch: JobBatch | None) -> dict | None:
        if batch is None:
            return None
        return {
            "Пакет": batch.number,
            "Источник": batch.source,
            "Создан": batch.created,
            "Фиксированный состав": ", ".join(batch.ids),
            "Ожидают": ", ".join(sorted(batch.waiting)),
            "В работе": ", ".join(sorted(batch.running)),
            "Обслужены": ", ".join(sorted(batch.completed)),
            "Вытеснены": ", ".join(sorted(batch.rejected)),
        }
