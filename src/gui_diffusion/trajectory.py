from __future__ import annotations

from collections import deque

from .models import AppSpec, Edge, StateGraph, Trajectory, TrajectoryStep


TASK_VALUES = {
    "amount_input": "12",
    "merchant_input": "Coffee",
    "task_input": "Submit report",
    "name_input": "Demo",
}


def synthesize_trajectories(spec: AppSpec, graph: StateGraph) -> list[Trajectory]:
    trajectories: list[Trajectory] = []
    for task in spec.tasks:
        path = _task_path(graph, task.id, task.start_screen, task.success_screen)
        steps: list[TrajectoryStep] = []
        step_no = 1

        for edge in _inject_required_form_steps(graph, path):
            value = TASK_VALUES.get(edge.component_id, edge.value)
            steps.append(
                TrajectoryStep(
                    step=step_no,
                    screen=edge.source,
                    operation=edge.operation,
                    target_id=edge.component_id,
                    value=value,
                    expected_screen=edge.target,
                )
            )
            step_no += 1

        steps.append(
            TrajectoryStep(
                step=step_no,
                screen=task.success_screen,
                operation="assert_screen",
                target_id="__screen__",
                value=task.success_message,
                expected_screen=task.success_screen,
            )
        )
        trajectories.append(Trajectory(task.id, task.instruction, task.success_message, steps))
    return trajectories


def _task_path(graph: StateGraph, task_id: str, start: str, target: str) -> list[Edge]:
    if task_id == "add_food_expense":
        return [
            Edge("home", "add_expense", "add_expense", "click"),
            Edge("add_expense", "category", "category_picker", "click"),
        ]
    return _shortest_path(graph.edges, start, target)


def _shortest_path(edges: list[Edge], start: str, target: str) -> list[Edge]:
    by_source: dict[str, list[Edge]] = {}
    for edge in edges:
        by_source.setdefault(edge.source, []).append(edge)

    queue = deque([(start, [])])
    seen = {start}
    while queue:
        screen, path = queue.popleft()
        if screen == target:
            return path
        for edge in by_source.get(screen, []):
            if edge.target not in seen:
                seen.add(edge.target)
                queue.append((edge.target, path + [edge]))
    raise ValueError(f"no path from {start!r} to {target!r}")


def _inject_required_form_steps(graph: StateGraph, path: list[Edge]) -> list[Edge]:
    enriched: list[Edge] = []
    for edge in path:
        if edge.source == "add_expense" and edge.component_id == "category_picker":
            enriched.append(Edge("add_expense", "add_expense", "amount_input", "fill"))
            enriched.append(Edge("add_expense", "add_expense", "merchant_input", "fill"))
        if edge.source == "add_task" and edge.component_id == "save_task":
            enriched.append(Edge("add_task", "add_task", "task_input", "fill"))
        if edge.source == "create" and edge.component_id == "save_item":
            enriched.append(Edge("create", "create", "name_input", "fill"))
        enriched.append(edge)

        if edge.component_id == "category_picker":
            enriched.append(Edge("category", "add_expense", "food_category", "click"))
            enriched.append(Edge("add_expense", "confirmation", "save_expense", "click"))
            break
    return enriched
