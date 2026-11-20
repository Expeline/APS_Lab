"""HTTP-интерфейс событийной модели."""

from collections import OrderedDict
from dataclasses import dataclass, field
from threading import Lock
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .model.model import Config, SimulationEngine, demonstration
from .model.report import compare, history, run, select_sample, summary

app = FastAPI(title="APS — модель системы массового обслуживания")
Time = Annotated[float, Field(ge=0.001, le=1e6)]
MAX_JOBS = 50_000


class Settings(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    n: int = Field(ge=1, le=20)
    intervals: list[Annotated[list[Time], Field(min_length=2, max_length=2)]] = Field(
        min_length=1, max_length=20
    )
    workers: int = Field(ge=1, le=50)
    capacity: int = Field(ge=1, le=200)
    meanService: Time
    limit: int = Field(ge=1, le=MAX_JOBS)
    seed: int = Field(ge=0, le=2**31 - 1)

    @model_validator(mode="after")
    def check_intervals(self):
        if self.n != len(self.intervals):
            raise ValueError("Число интервалов должно совпадать с числом источников.")
        if any(a > b for a, b in self.intervals):
            raise ValueError("Для каждого источника нужно 0 < a ≤ b.")
        return self

    def config(self) -> Config:
        return Config(
            tuple((a, b) for a, b in self.intervals),
            self.workers,
            self.capacity,
            self.meanService,
            self.limit,
            self.seed,
        )


class Start(BaseModel):
    configuration: Settings
    demo: bool = False

    def engine(self) -> SimulationEngine:
        return (
            demonstration()
            if self.demo
            else SimulationEngine(self.configuration.config())
        )


class Step(BaseModel):
    count: int = Field(1, ge=1, le=10, strict=True)


class Auto(Start):
    adaptive: bool = False
    cap: int = Field(10_000, ge=100, le=MAX_JOBS, strict=True)


class Experiment(BaseModel):
    configuration: Settings
    configurations: list[Settings] | None = Field(None, min_length=4, max_length=8)
    price: float = Field(ge=0, le=1e9)
    workerHour: float = Field(ge=0, le=1e9)
    slotHour: float = Field(ge=0, le=1e9)
    secondsPerUnit: Time


@dataclass
class Session:
    engine: SimulationEngine
    lock: Lock = field(default_factory=Lock)


_sessions: OrderedDict[str, Session] = OrderedDict()
_registry_lock = Lock()


def session(simulation_id: str) -> Session:
    with _registry_lock:
        current = _sessions.get(simulation_id)
        if current is None:
            raise HTTPException(404, "Прогон не найден. Начните новый прогон.")
        _sessions.move_to_end(simulation_id)
        return current


def snapshot(engine: SimulationEngine, start: int | None = None) -> dict:
    state = engine.snapshot(len(engine.log) if start is None else start)
    state["modelTime"] = state.pop("time")
    state["workerPointer"] = state.pop("worker_pointer")
    if "slot_pointer" in state:
        state["slotPointer"] = state.pop("slot_pointer")
    state["actions"] = state["actions"][-500:]
    state["history"] = history(engine, limit=500)
    state["lastEviction"] = next(
        (row for row in reversed(engine.log) if row["Действие"] == "EVICT"), None
    )
    state["finished"] = engine.done
    return state


def result(
    engine: SimulationEngine, attempts: list | None = None, message: str = ""
) -> dict:
    return {
        "summary": summary(engine),
        "journal": engine.log,
        "attempts": attempts or [],
        "message": message,
    }


@app.exception_handler(RequestValidationError)
async def validation_message(_request: Request, error: RequestValidationError):
    details = []
    for item in error.errors():
        field_name = ".".join(map(str, item["loc"][1:]))
        message = str(item["msg"]).removeprefix("Value error, ")
        if item["type"] != "value_error":
            message = "проверьте тип и допустимый диапазон значения."
        details.append(f"{field_name or 'Параметры'} — {message}")
    return JSONResponse(status_code=422, content={"detail": " ".join(details)})


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/simulations", status_code=201)
def create(request: Start):
    engine = request.engine()
    simulation_id = uuid4().hex
    with _registry_lock:
        _sessions[simulation_id] = Session(engine)
        if len(_sessions) > 12:
            _sessions.popitem(last=False)
    return {"id": simulation_id, "snapshot": snapshot(engine)}


@app.get("/api/simulations/{simulation_id}")
def get(simulation_id: str):
    current = session(simulation_id)
    with current.lock:
        return {"id": simulation_id, "snapshot": snapshot(current.engine)}


@app.post("/api/simulations/{simulation_id}/step")
def step(simulation_id: str, request: Step | None = None):
    current = session(simulation_id)
    with current.lock:
        engine = current.engine
        start = len(engine.log)
        for _ in range(request.count if request else 1):
            if engine.done:
                break
            engine.advance()
        state = snapshot(engine, start)
        response = {"id": simulation_id, "snapshot": state, "finished": engine.done}
        if engine.done:
            response["result"] = result(engine)
        return response


@app.post("/api/simulations/{simulation_id}/run")
def finish(simulation_id: str):
    current = session(simulation_id)
    with current.lock:
        engine = current.engine
        start = len(engine.log)
        # На заявку приходится одно поступление и не более одного завершения.
        for _ in range(2 * engine.config.limit):
            if engine.done:
                break
            engine.advance()
        if not engine.done:
            raise HTTPException(409, "Достигнут предел числа событий.")
        return {
            "id": simulation_id,
            "snapshot": snapshot(engine, start),
            "finished": True,
            "result": result(engine),
        }


@app.post("/api/auto")
def automatic(request: Auto):
    config = request.configuration.config()
    if request.demo:
        engine = request.engine()
        engine.run_to_end()
    elif request.adaptive:
        engine, attempts, message = select_sample(config, request.cap)
        return result(engine, attempts, message)
    else:
        engine = run(config)
    return result(engine)


@app.post("/api/experiments")
def experiments(request: Experiment):
    custom = (
        [item.config() for item in request.configurations]
        if request.configurations
        else None
    )
    rows = compare(
        request.configuration.config(),
        request.price,
        request.workerHour,
        request.slotHour,
        request.secondsPerUnit,
        custom=custom,
    )
    candidates = [
        row
        for row in rows
        if row["Pотк"] <= 0.1 and row["Отклонение K от 0,90"] <= 0.05
    ]
    best = min(candidates, key=lambda row: (-row["Эффект"], row["Tсист"]), default=None)
    message = (
        "Среди проверенных конфигураций нет сочетания Pотк ≤ 10% и загрузки 85–95%."
        if best is None
        else f"Предпочтительна «{best['Конфигурация']}» с эффектом {best['Эффект']:.2f}. "
        "При равном эффекте выбирается меньшее время в системе."
    )
    return {"rows": rows, "best": best, "message": message}
