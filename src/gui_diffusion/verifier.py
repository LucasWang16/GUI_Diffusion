from __future__ import annotations

from .models import AppSpec, StateGraph, Trajectory


def verify_spec(spec: AppSpec) -> list[str]:
    errors: list[str] = []
    screen_ids = {screen.id for screen in spec.screens}
    if not spec.screens:
        errors.append("spec has no screens")
    for task in spec.tasks:
        if task.start_screen not in screen_ids:
            errors.append(f"task {task.id} has missing start screen {task.start_screen}")
        if task.success_screen not in screen_ids:
            errors.append(f"task {task.id} has missing success screen {task.success_screen}")
    for screen in spec.screens:
        component_ids = set()
        for component in screen.components:
            if component.id in component_ids:
                errors.append(f"screen {screen.id} has duplicate component {component.id}")
            component_ids.add(component.id)
            x1, y1, x2, y2 = component.bbox
            if x2 <= x1 or y2 <= y1:
                errors.append(f"component {component.id} has invalid bbox")
            if component.target_screen and component.target_screen not in screen_ids:
                errors.append(f"component {component.id} targets missing screen {component.target_screen}")
    return errors


def verify_graph(graph: StateGraph) -> list[str]:
    errors: list[str] = []
    screen_ids = {screen.id for screen in graph.screens}
    components = {
        (screen.id, component.id)
        for screen in graph.screens
        for component in screen.components
    }
    if graph.initial_screen not in screen_ids:
        errors.append(f"initial screen {graph.initial_screen} is missing")
    for edge in graph.edges:
        if edge.source not in screen_ids:
            errors.append(f"edge source {edge.source} is missing")
        if edge.target not in screen_ids:
            errors.append(f"edge target {edge.target} is missing")
        if (edge.source, edge.component_id) not in components:
            errors.append(f"edge component {edge.component_id} is missing on {edge.source}")
    return errors


def verify_trajectories(graph: StateGraph, trajectories: list[Trajectory]) -> list[str]:
    errors: list[str] = []
    screen_ids = {screen.id for screen in graph.screens}
    components = {
        (screen.id, component.id)
        for screen in graph.screens
        for component in screen.components
    }
    for trajectory in trajectories:
        if not trajectory.steps:
            errors.append(f"trajectory {trajectory.task_id} has no steps")
        for step in trajectory.steps:
            if step.screen not in screen_ids:
                errors.append(f"trajectory {trajectory.task_id} step {step.step} missing screen {step.screen}")
            if step.target_id != "__screen__" and (step.screen, step.target_id) not in components:
                errors.append(
                    f"trajectory {trajectory.task_id} step {step.step} missing target {step.target_id}"
                )
            if step.expected_screen and step.expected_screen not in screen_ids:
                errors.append(
                    f"trajectory {trajectory.task_id} step {step.step} expects missing screen {step.expected_screen}"
                )
    return errors
