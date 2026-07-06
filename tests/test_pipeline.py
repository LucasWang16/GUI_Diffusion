from __future__ import annotations

from pathlib import Path
import sys

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


def test_health_and_commerce_domains_have_valid_trajectories() -> None:
    for description, expected_domain in [
        ("A fitness health app for logging workout and activity progress.", "health"),
        ("A shop app with product detail, cart, order, and checkout.", "commerce"),
    ]:
        spec = parse_app_description(description)
        graph = build_state_graph(spec)
        trajectories = synthesize_trajectories(spec, graph)
        assert spec.domain == expected_domain
        assert verify_spec(spec) == []
        assert verify_graph(graph) == []
        assert verify_trajectories(graph, trajectories) == []


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


def test_cli_external_visual_adapter(tmp_path: Path) -> None:
    adapter = tmp_path / "copy_adapter.py"
    adapter.write_text(
        "from PIL import Image\n"
        "import sys\n"
        "Image.open(sys.argv[1]).save(sys.argv[2])\n",
        encoding="utf-8",
    )
    out = tmp_path / "external_dataset"

    try:
        code = main([
            "generate",
            "--description",
            "A shop app with product detail, cart, and checkout.",
            "--out",
            str(out),
            "--visual",
            "external",
            "--visual-command",
            f"{sys.executable} {adapter} {{input}} {{output}}",
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
    assert manifest["visual_adapter"] == "external"
    assert manifest["export_result"]["rows"] > 0
    visual_prompts = read_json(out / "capture" / "buy_featured_product" / "visual_prompts.json")
    assert visual_prompts["adapter"] == "external"
    assert (out / "capture" / "buy_featured_product" / "visual" / "step_001_external_diffusion.png").exists()


def test_cli_slurm_visual_adapter_dry_run(tmp_path: Path) -> None:
    out = tmp_path / "slurm_dataset"
    try:
        code = main([
            "generate",
            "--description",
            "A shop app with product detail, cart, and checkout.",
            "--out",
            str(out),
            "--visual",
            "slurm",
            "--visual-command",
            f"{sys.executable} examples/adapters/copy_adapter.py {{input}} {{output}}",
            "--slurm-partition",
            "gpu_devel",
            "--slurm-gpu",
            "b200",
            "--slurm-dry-run",
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
    assert manifest["visual_adapter"] == "slurm"
    visual = manifest["capture_results"][0]["visual"]
    assert visual["dry_run"] is True
    assert visual["job_id"] is None
    job_script = Path(visual["job_script"])
    assert job_script.exists()
    assert "--gres=gpu:b200:1" in job_script.read_text(encoding="utf-8")
    prompts = read_json(out / "capture" / "buy_featured_product" / "visual_prompts.json")
    assert prompts["adapter"] == "slurm"
