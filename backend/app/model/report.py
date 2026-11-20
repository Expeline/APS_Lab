"""Статистика выполненных заявок и сравнение конфигураций."""

from dataclasses import replace
from math import ceil, sqrt
from statistics import mean, pvariance

from .model import Config, SimulationEngine, Status


def average(values: list[float]) -> float:
    return mean(values) if values else 0.0


def divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def history(engine: SimulationEngine, limit: int = 500) -> list[dict]:
    return [
        {
            "Заявка": job.id,
            "Пакет": job.batch,
            "Источник": job.source,
            "Приход": job.arrived,
            "В буфер": job.buffered,
            "Ячейка": job.slot,
            "Начало": job.started,
            "Конец": job.finished,
            "Отказ": job.rejected,
            "Прибор": job.worker,
            "Состояние": job.status.value,
        }
        for job in engine.recent_jobs(limit)
    ]


def summary(engine: SimulationEngine) -> dict:
    jobs_by_source = [[] for _ in engine.config.intervals]
    for job in engine.jobs:
        jobs_by_source[job.source - 1].append(job)

    sources, system_times = [], []
    completed_total = rejected_total = 0
    for source, jobs in enumerate(jobs_by_source, 1):
        rejected = sum(job.status == Status.REJECTED for job in jobs)
        waits, services, residence = [], [], []
        for job in jobs:
            if job.finished is not None:
                assert job.started is not None
                waits.append(job.started - job.arrived)
                services.append(job.finished - job.started)
                residence.append(job.finished - job.arrived)
        system_times.extend(residence)
        completed_total += len(residence)
        rejected_total += rejected
        sources.append(
            {
                "Источник": source,
                "Создано": len(jobs),
                "Отказано": rejected,
                "Обслужено": len(residence),
                "Pотк": divide(rejected, len(jobs)),
                "Tож": average(waits),
                "Tобсл": average(services),
                "Tсист": average(residence),
                "Dож": pvariance(waits) if waits else 0.0,
                "Dобсл": pvariance(services) if services else 0.0,
            }
        )

    workers = []
    for worker in engine.workers:
        busy = worker.busy
        if worker.job is not None:
            assert worker.job.started is not None
            busy += engine.time - worker.job.started
        workers.append(
            {
                "Прибор": worker.number,
                "Время занятости": busy,
                "Kисп": min(1.0, divide(busy, engine.time)),
            }
        )
    return {
        "Общие": {
            "Создано": sum(map(len, jobs_by_source)),
            "Обслужено": completed_total,
            "Отказано": rejected_total,
            "Pотк": divide(rejected_total, sum(map(len, jobs_by_source))),
            "Tсист": average(system_times),
            "Kисп": average([worker["Kисп"] for worker in workers]),
            "Пропускная способность": divide(completed_total, engine.time),
            "Длительность": engine.time,
        },
        "Источники": sources,
        "Приборы": workers,
    }


def run(config: Config, *, keep_log: bool = True) -> SimulationEngine:
    engine = SimulationEngine(config, keep_log=keep_log)
    engine.run_to_end()
    return engine


def select_sample(config: Config, cap: int) -> tuple[SimulationEngine, list[dict], str]:
    size, attempts = 100, []
    while True:
        engine = run(replace(config, limit=size), keep_log=False)
        p = summary(engine)["Общие"]["Pотк"]
        needed = ceil(1.643**2 * (1 - p) / (p * 0.1**2)) if p else None
        error = 1.643 * sqrt((1 - p) / (p * size)) if p else None
        attempts.append(
            {
                "N": size,
                "Pотк": p,
                "Расчётный N": needed,
                "Оценка относительной погрешности": error,
            }
        )
        if needed is not None and size >= needed:
            message = (
                "Оценка по формуле не превышает 10%. Заявки одной очереди зависимы."
            )
            break
        if size == cap:
            message = (
                "Точность по вероятности отказа не подтверждена, нулевые отказы в выборке."
                if p == 0
                else "Достигнут предел N, требуемая точность по формуле не подтверждена."
            )
            break
        size = min(cap, max(size * 2, needed or 0))
    return run(replace(config, limit=size)), attempts, message


def compare(
    config: Config,
    price: float,
    worker_hour: float,
    slot_hour: float,
    seconds_per_unit: float,
    *,
    custom: list[Config] | None = None,
) -> list[dict]:
    changed_workers = config.workers + (1 if config.workers < 50 else -1)
    changed_capacity = config.capacity + (2 if config.capacity <= 198 else -2)
    options = [
        ("Базовая", config),
        ("Другое число приборов", replace(config, workers=changed_workers)),
        ("Другой размер буфера", replace(config, capacity=changed_capacity)),
        (
            "Изменены приборы и буфер",
            replace(config, workers=changed_workers, capacity=changed_capacity),
        ),
    ]
    if custom is not None:
        options = [
            (f"Конфигурация {index}", item) for index, item in enumerate(custom, 1)
        ]
    rows = []
    for name, option in options:
        totals = summary(run(option, keep_log=False))["Общие"]
        hours = totals["Длительность"] * seconds_per_unit / 3600
        expense = hours * (option.workers * worker_hour + option.capacity * slot_hour)
        revenue = price * totals["Обслужено"]
        rows.append(
            {
                "Конфигурация": name,
                "n": len(option.intervals),
                "B": option.capacity,
                "M": option.workers,
                "a, b": str(option.intervals),
                "Среднее обслуживание": option.mean_service,
                "N": option.limit,
                **totals,
                "Отклонение K от 0,90": abs(totals["Kисп"] - 0.9),
                "Расходы": expense,
                "Выручка": revenue,
                "Эффект": revenue - expense,
            }
        )
    return rows
