"""Дискретно-событийная модель СМО."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from heapq import heappop, heappush
from itertools import count
from math import inf, isfinite, nextafter
from random import Random

from .discipline import Buffer, DispatchRule, Job


@dataclass(frozen=True)
class Config:
    intervals: tuple[tuple[float, float], ...] = ((1.0, 3.0), (2.0, 4.0), (3.0, 5.0))
    workers: int = 3
    capacity: int = 5
    mean_service: float = 2.0
    limit: int = 100
    seed: int = 42

    def __post_init__(self):
        for value in (self.workers, self.capacity, self.limit):
            if type(value) is not int or value < 1:
                raise ValueError(
                    "Число приборов, ячеек и заявок должно быть целым положительным."
                )
        if not self.intervals or any(
            not (isfinite(a) and isfinite(b) and 0 < a <= b) for a, b in self.intervals
        ):
            raise ValueError("Для каждого источника нужно 0 < a ≤ b.")
        if not isfinite(self.mean_service) or self.mean_service <= 0:
            raise ValueError(
                "Среднее время обслуживания должно быть положительным и конечным."
            )


class Kind(IntEnum):
    SERVICE_COMPLETED = 0
    REQUEST_GENERATED = 1


class Status(StrEnum):
    CREATED = "Создана"
    WAITING = "В буфере"
    RUNNING = "Обрабатывается"
    COMPLETED = "Обслужена"
    REJECTED = "Отказ"


@dataclass(order=True, frozen=True)
class Event:
    time: float
    kind: Kind
    order: int
    source: int = field(compare=False)
    job: str = field(compare=False)
    worker: int | None = field(default=None, compare=False)


class EventCalendar:
    def __init__(self):
        self._events: list[Event] = []
        self._sequence = count()

    def add(
        self, time: float, kind: Kind, source: int, job: str, worker: int | None = None
    ):
        heappush(
            self._events, Event(time, kind, next(self._sequence), source, job, worker)
        )

    def pop(self) -> Event:
        return heappop(self._events)

    def snapshot(self) -> tuple[Event, ...]:
        return tuple(sorted(self._events))

    def stop_arrivals(self):
        # В календаре остаются только завершения уже начатого обслуживания.
        events = [
            event for event in self._events if event.kind == Kind.SERVICE_COMPLETED
        ]
        self._events.clear()
        for event in events:
            heappush(self._events, event)

    def __bool__(self) -> bool:
        return bool(self._events)


@dataclass
class Source:
    number: int
    bounds: tuple[float, float]
    random: Random
    generated: int = 0

    def schedule(self, now: float, calendar: EventCalendar):
        calendar.add(
            future(now, self.random.uniform(*self.bounds)),
            Kind.REQUEST_GENERATED,
            self.number,
            f"И{self.number}-{self.generated + 1}",
        )


@dataclass
class Worker:
    number: int
    job: Job | None = None
    end: float | None = None
    busy: float = 0.0

    def finish(self, now: float) -> Job:
        job = self.job
        assert job is not None and job.started is not None
        self.busy += now - job.started
        self.job = None
        self.end = None
        job.finished = now
        job.status = Status.COMPLETED
        return job


class WorkerPool:
    def __init__(self, size: int):
        self._workers = tuple(Worker(i + 1) for i in range(size))
        self._pointer = 0

    @property
    def workers(self) -> tuple[Worker, ...]:
        return self._workers

    @property
    def pointer(self) -> int:
        return self._pointer

    def find_free(self) -> Worker | None:
        for offset in range(len(self._workers)):
            worker = self._workers[(self._pointer + offset) % len(self._workers)]
            if worker.job is None:
                return worker
        return None

    def assign(self, worker: Worker, job: Job, now: float, end: float):
        worker.job, worker.end = job, end
        job.started, job.worker, job.status = now, worker.number, Status.RUNNING
        self._pointer = worker.number % len(self._workers)


def future(now: float, delay: float) -> float:
    time = max(now + delay, nextafter(now, inf))
    if not isfinite(time):
        raise ValueError("Модельное время вышло за допустимый диапазон.")
    return time


class Statistics:
    def __init__(self, sources: int):
        self.jobs: list[Job] = []
        self.refusals = [0] * sources
        self.completed = 0

    def reject(self, job: Job, now: float):
        job.rejected, job.status = now, Status.REJECTED
        self.refusals[job.source - 1] += 1


class PlacementDispatcher:
    def __init__(self, buffer: Buffer, statistics: Statistics):
        self._buffer, self._statistics = buffer, statistics

    def accept(self, job: Job, now: float, log: Callable) -> Job | None:
        index, victim = self._buffer.place(job)
        job.buffered, job.slot, job.status = now, index + 1, Status.WAITING
        if victim is not None:
            self._statistics.reject(victim, now)
            log("EVICT", victim, f"Ячейка {index + 1} освобождена для {job.id}")
        log("PUT", job, f"Ячейка {index + 1}")
        return victim


class SelectionDispatcher:
    def __init__(
        self,
        buffer: Buffer,
        pool: WorkerPool,
        calendar: EventCalendar,
        service: Callable[[], float],
    ):
        self._buffer, self._pool, self._calendar = buffer, pool, calendar
        self._service = service
        self.rule = DispatchRule(buffer)

    def dispatch(self, now: float, log: Callable):
        self.rule.close_if_finished(log)
        while (worker := self._pool.find_free()) is not None:
            job = self.rule.take(now, log)
            if job is None:
                break
            log("TAKE", job, f"Ячейка {job.slot}")
            end = future(now, self._service())
            self._pool.assign(worker, job, now, end)
            log("ASSIGN", job, f"Прибор {worker.number}")
            log("START", job, f"Завершение в {end:.6g}")
            self._calendar.add(
                end, Kind.SERVICE_COMPLETED, job.source, job.id, worker.number
            )


class SimulationEngine:
    def __init__(
        self,
        config: Config,
        *,
        arrivals: Iterable[tuple[float, int]] | None = None,
        service: Callable[[], float] | None = None,
        keep_log: bool = True,
    ):
        self.config = config
        self.time = 0.0
        self.last_event: Event | None = None
        self.log: list[dict] = []
        self._keep_log = keep_log
        self._sources = [
            Source(i, bounds, Random(f"{config.seed}:source:{i}"))
            for i, bounds in enumerate(config.intervals, 1)
        ]
        self._random = Random(config.seed)
        self._calendar = EventCalendar()
        self._buffer = Buffer(config.capacity)
        self._pool = WorkerPool(config.workers)
        self._stats = Statistics(len(self._sources))
        self._placement = PlacementDispatcher(self._buffer, self._stats)
        self._selection = SelectionDispatcher(
            self._buffer, self._pool, self._calendar, service or self._draw_service
        )
        self._scheduled = arrivals is not None
        if arrivals is None:
            for source in self._sources:
                source.schedule(self.time, self._calendar)
        else:
            serials = [0] * len(self._sources)
            for time, source in sorted(arrivals, key=lambda item: item[0]):
                if not isfinite(time) or time < 0 or not 1 <= source <= len(serials):
                    raise ValueError("Недопустимое событие фиксированной трассы.")
                serials[source - 1] += 1
                self._calendar.add(
                    time,
                    Kind.REQUEST_GENERATED,
                    source,
                    f"И{source}-{serials[source - 1]}",
                )

    def _draw_service(self) -> float:
        return max(
            self._random.expovariate(1 / self.config.mean_service), nextafter(0.0, inf)
        )

    def _record(self, action: str, job: Job | None, detail: str):
        if self._keep_log:
            self.log.append(
                {
                    "Время": self.time,
                    "Действие": action,
                    "Заявка": job.id if job else None,
                    "Подробности": detail,
                }
            )

    @property
    def done(self) -> bool:
        return not self._calendar

    @property
    def jobs(self) -> tuple[Job, ...]:
        return tuple(self._stats.jobs)

    def recent_jobs(self, limit: int) -> tuple[Job, ...]:
        return tuple(self._stats.jobs[-limit:])

    @property
    def workers(self) -> tuple[Worker, ...]:
        return self._pool.workers

    def _advance(self):
        event = self._calendar.pop()
        self.last_event, self.time = event, event.time
        if event.kind == Kind.REQUEST_GENERATED:
            source = self._sources[event.source - 1]
            source.generated += 1
            job = Job(
                event.job, event.source, source.generated, self.time, Status.CREATED
            )
            self._stats.jobs.append(job)
            self._record("GEN", job, f"Источник И{source.number}")
            if len(self._stats.jobs) == self.config.limit:
                self._calendar.stop_arrivals()
            elif not self._scheduled:
                source.schedule(self.time, self._calendar)
            victim = self._placement.accept(job, self.time, self._record)
            if victim is not None:
                self._selection.rule.rejected(victim)
        else:
            assert event.worker is not None
            job = self.workers[event.worker - 1].finish(self.time)
            self._stats.completed += 1
            self._record("COMPLETE", job, f"Прибор {event.worker}")
            self._selection.rule.completed(job)
        self._selection.dispatch(self.time, self._record)

    def advance(self):
        if not self.done:
            self._advance()

    def step(self) -> dict:
        start = len(self.log)
        self.advance()
        return self.snapshot(start)

    def run_to_end(self):
        while not self.done:
            self._advance()

    def snapshot(self, log_start: int = 0) -> dict:
        calendar = self._calendar.snapshot()
        next_arrivals = {}
        for event in calendar:
            if event.kind == Kind.REQUEST_GENERATED:
                next_arrivals.setdefault(event.source, event.time)
        slots = self._buffer.slots
        waiting = sum(job is not None for job in slots)
        running = sum(worker.job is not None for worker in self.workers)
        generated = len(self._stats.jobs)
        rejected = sum(self._stats.refusals)
        assert generated == rejected + self._stats.completed + waiting + running
        return {
            "time": self.time,
            "event": self.last_event.kind.name if self.last_event else "Инициализация",
            "calendar": [
                {
                    "Время": e.time,
                    "Событие": e.kind.name,
                    "Источник": e.source,
                    "Заявка": e.job,
                    "Прибор": e.worker,
                }
                for e in calendar
            ],
            "sources": [
                {
                    "Источник": s.number,
                    "Создано": s.generated,
                    "Следующий приход": next_arrivals.get(s.number),
                    "Отказано": self._stats.refusals[s.number - 1],
                    "Доля отказов": self._stats.refusals[s.number - 1] / s.generated
                    if s.generated
                    else 0.0,
                }
                for s in self._sources
            ],
            "slots": [
                {
                    "Ячейка": i,
                    "Заявка": j.id if j else "—",
                    "Источник": j.source if j else None,
                    "Возраст": self.time - j.arrived if j else None,
                }
                for i, j in enumerate(slots, 1)
            ],
            "workers": [
                {
                    "Прибор": w.number,
                    "Состояние": "BUSY" if w.job else "IDLE",
                    "Заявка": w.job.id if w.job else None,
                    "Начало": w.job.started if w.job else None,
                    "Конец": w.end,
                    "Указатель": w.number == self._pool.pointer + 1,
                }
                for w in self.workers
            ],
            "worker_pointer": self._pool.pointer + 1,
            "generated": generated,
            "waiting": waiting,
            "running": running,
            "completed": self._stats.completed,
            "rejected": rejected,
            "loss": rejected / generated if generated else 0.0,
            "actions": self.log[log_start:],
            **self._selection.rule.snapshot(),
        }


def demonstration() -> SimulationEngine:
    arrivals = [
        (1.0, 2),
        (2.0, 2),
        (3.0, 2),
        (4.0, 2),
        (5.0, 2),
        (10.5, 2),
        (11.0, 1),
        (12.0, 1),
        (13.0, 1),
    ]
    durations = iter((9.0, 7.0, 9.0))
    return SimulationEngine(
        Config(
            intervals=((1.0, 1.0), (1.0, 1.0)),
            workers=2,
            capacity=3,
            limit=len(arrivals),
        ),
        arrivals=arrivals,
        service=lambda: next(durations, 9.0),
    )
