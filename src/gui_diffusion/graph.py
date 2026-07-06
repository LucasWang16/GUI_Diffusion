from __future__ import annotations

from .models import AppSpec, Edge, StateGraph


def build_state_graph(spec: AppSpec) -> StateGraph:
    edges: list[Edge] = []
    for screen in spec.screens:
        for component in screen.components:
            if component.target_screen:
                operation = "fill" if component.role == "textbox" else "click"
                edges.append(Edge(screen.id, component.target_screen, component.id, operation))
    return StateGraph(
        app_name=spec.app_name,
        initial_screen=spec.tasks[0].start_screen if spec.tasks else spec.screens[0].id,
        screens=spec.screens,
        edges=edges,
    )
