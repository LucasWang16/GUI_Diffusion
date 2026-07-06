from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Literal
import json


Role = Literal["button", "textbox", "listitem", "tab", "heading", "status", "card"]
Operation = Literal["click", "fill", "assert_screen"]


@dataclass(frozen=True)
class Component:
    id: str
    role: Role
    label: str
    bbox: tuple[int, int, int, int]
    value: str = ""
    target_screen: str | None = None


@dataclass(frozen=True)
class Screen:
    id: str
    title: str
    purpose: str
    components: list[Component]


@dataclass(frozen=True)
class Task:
    id: str
    instruction: str
    start_screen: str
    success_screen: str
    success_message: str


@dataclass(frozen=True)
class AppSpec:
    app_name: str
    domain: str
    description: str
    entities: list[str]
    screens: list[Screen]
    tasks: list[Task]


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    component_id: str
    operation: Operation
    value: str = ""


@dataclass(frozen=True)
class StateGraph:
    app_name: str
    initial_screen: str
    screens: list[Screen]
    edges: list[Edge]


@dataclass(frozen=True)
class TrajectoryStep:
    step: int
    screen: str
    operation: Operation
    target_id: str
    value: str = ""
    expected_screen: str | None = None


@dataclass(frozen=True)
class Trajectory:
    task_id: str
    instruction: str
    success_message: str
    steps: list[TrajectoryStep] = field(default_factory=list)


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(value), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
