from __future__ import annotations

from pathlib import Path

import pytest

from gui_diffusion.capture import capture_trajectory
from gui_diffusion.cli import main
from gui_diffusion.graph import build_state_graph
from gui_diffusion.models import read_json
from gui_diffusion.renderer import render_html
from gui_diffusion.spec_parser import parse_app_description
from gui_diffusion.trajectory import synthesize_trajectories
from gui_diffusion.verifier import verify_graph, verify_spec, verify_trajectories


def test_finance_parser_builds_expected_core_screens() -> None:
    spec = parse_app_description("A personal expense tracker with budget alerts and monthly statistics.")
    assert spec.domain == "finance"
    assert {screen.id for screen in spec.screens} >= {"home", "add_expense", "category", "stats", "confirmation"}
    assert spec.tasks[0].success_screen == "confirmation"


def test_graph_and_trajectory_are_verifiable() -> None:
    spec = parse_app_description("A personal expense tracker with add expense and categories.")
    graph = build_state_graph(spec)
    trajectories = synthesize_trajectories(spec, graph)
    assert verify_spec(spec) == []
    assert verify_graph(graph) == []
    assert verify_trajectories(graph, trajectories) == []
    first = trajectories[0]
    assert [step.target_id for step in first.steps] == [
        "add_expense",
        "amount_input",
        "merchant_input",
        "category_picker",
        "food_category",
        "save_expense",
        "__screen__",
    ]


def test_renderer_writes_executable_html(tmp_path: Path) -> None:
    spec = parse_app_description("A todo app for task planning.")
    graph = build_state_graph(spec)
    html = tmp_path / "index.html"
    render_html(graph, html)
    text = html.read_text(encoding="utf-8")
    assert "data-gui-id" in text
    assert "window.__guiDiffusion" in text
    assert "Add task" in text


def test_cli_generates_manifest_and_json(tmp_path: Path) -> None:
    out = tmp_path / "dataset"
    code = main([
        "generate",
        "--description",
        "A personal expense tracker with add expense and monthly statistics.",
        "--out",
        str(out),
    ])
    assert code == 0
    assert (out / "index.html").exists()
    assert (out / "app_spec.json").exists()
    assert (out / "state_graph.json").exists()
    assert (out / "trajectory.json").exists()
    manifest = read_json(out / "manifest.json")
    assert manifest["trajectory_count"] == 2
    assert manifest["capture_enabled"] is False
    assert manifest["visual_adapter"] == "none"


def test_capture_records_screenshots_dom_and_video(tmp_path: Path) -> None:
    spec = parse_app_description("A personal expense tracker with add expense and categories.")
    graph = build_state_graph(spec)
    trajectories = synthesize_trajectories(spec, graph)
    html = tmp_path / "index.html"
    render_html(graph, html)

    try:
        result = capture_trajectory(html, trajectories[0], tmp_path / "capture")
    except Exception as exc:
        message = str(exc).lower()
        if "executable doesn't exist" in message or "browser" in message:
            pytest.skip(f"playwright browser unavailable: {exc}")
        raise

    assert result["steps"] == len(trajectories[0].steps)
    assert (tmp_path / "capture" / "capture.json").exists()
    assert (tmp_path / "capture" / "step_001.png").exists()
    assert result["video"] is not None
    assert Path(result["video"]).exists()


def test_cli_generates_visual_assets_and_export(tmp_path: Path) -> None:
    out = tmp_path / "dataset_v2"
    try:
        code = main([
            "generate",
            "--description",
            "A personal expense tracker with add expense and monthly statistics.",
            "--out",
            str(out),
            "--visual",
            "mock",
            "--export",
            "hf",
            "--no-video",
        ])
    except Exception as exc:
        message = str(exc).lower()
        if "executable doesn't exist" in message or "browser" in message:
            pytest.skip(f"playwright browser unavailable: {exc}")
        raise

    assert code == 0
    manifest = read_json(out / "manifest.json")
    assert manifest["capture_enabled"] is True
    assert manifest["record_video"] is False
    assert manifest["visual_adapter"] == "mock"
    assert manifest["export_result"]["rows"] > 0
    rows = (out / "dataset" / "gui_agent_steps.jsonl").read_text(encoding="utf-8").splitlines()
    assert rows
    assert (out / "capture" / "add_food_expense" / "layout_masks" / "step_001_mask.png").exists()
    assert (out / "capture" / "add_food_expense" / "visual" / "step_001_mock_diffusion.png").exists()
