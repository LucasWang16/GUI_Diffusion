from __future__ import annotations

import argparse
from pathlib import Path

from .capture import capture_trajectory
from .exporter import export_hf_dataset
from .graph import build_state_graph
from .models import write_json
from .renderer import render_html
from .spec_parser import parse_app_description
from .trajectory import synthesize_trajectories
from .verifier import verify_graph, verify_spec, verify_trajectories
from .visual import generate_visual_assets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gui-diffusion")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="generate a deterministic GUI-agent dataset")
    gen.add_argument("--description", required=True)
    gen.add_argument("--out", required=True, type=Path)
    gen.add_argument("--capture", action="store_true", help="record screenshots and videos with Playwright")
    gen.add_argument("--no-video", action="store_true", help="capture screenshots and DOM without recording videos")
    gen.add_argument(
        "--visual",
        choices=["none", "mock", "external"],
        default="none",
        help="generate visual refinement assets",
    )
    gen.add_argument(
        "--visual-command",
        default=None,
        help="command template for --visual external; placeholders: {input}, {mask}, {prompt_file}, {output}, {style}",
    )
    gen.add_argument(
        "--export",
        choices=["none", "hf"],
        default="none",
        help="export a GUI-agent dataset table",
    )
    args = parser.parse_args(argv)

    if args.command == "generate":
        return _generate(
            args.description,
            args.out,
            args.capture,
            args.visual,
            args.export,
            not args.no_video,
            args.visual_command,
        )
    return 1


def _generate(
    description: str,
    out_dir: Path,
    capture: bool,
    visual: str,
    export: str,
    record_video: bool,
    visual_command: str | None,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    spec = parse_app_description(description)
    graph = build_state_graph(spec)
    trajectories = synthesize_trajectories(spec, graph)

    errors = verify_spec(spec) + verify_graph(graph) + verify_trajectories(graph, trajectories)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 2

    html_path = out_dir / "index.html"
    render_html(graph, html_path)

    write_json(out_dir / "app_spec.json", spec)
    write_json(out_dir / "state_graph.json", graph)
    write_json(out_dir / "trajectory.json", {"trajectories": trajectories})

    capture_results = []
    capture_enabled = capture or visual != "none" or export == "hf"
    if capture_enabled:
        for trajectory in trajectories:
            capture_result = capture_trajectory(
                html_path,
                trajectory,
                out_dir / "capture" / trajectory.task_id,
                record_video=record_video,
            )
            if visual != "none":
                capture_result["visual"] = generate_visual_assets(
                    Path(capture_result["capture_dir"]),
                    adapter=visual,
                    command_template=visual_command,
                )
            capture_results.append(capture_result)

    export_result = None
    if export == "hf":
        export_result = export_hf_dataset(out_dir, spec, trajectories, capture_results, visual_enabled=visual != "none")

    write_json(
        out_dir / "manifest.json",
        {
            "app_name": spec.app_name,
            "domain": spec.domain,
            "html": "index.html",
            "trajectory_count": len(trajectories),
            "capture_enabled": capture_enabled,
            "record_video": record_video if capture_enabled else False,
            "capture_results": capture_results,
            "visual_adapter": visual,
            "visual_command": visual_command if visual == "external" else None,
            "export_format": export,
            "export_result": export_result,
        },
    )
    print(f"generated dataset at {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
