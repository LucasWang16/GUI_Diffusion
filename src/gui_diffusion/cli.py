from __future__ import annotations

import argparse
from pathlib import Path

from .capture import capture_trajectory
from .exporter import export_hf_dataset
from .graph import build_state_graph
from .models import write_json
from .renderer import render_html
from .slurm import generate_slurm_visual_assets
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
        choices=["none", "mock", "external", "slurm"],
        default="none",
        help="generate visual refinement assets",
    )
    gen.add_argument(
        "--visual-command",
        default=None,
        help="command template for --visual external; placeholders: {input}, {mask}, {prompt_file}, {output}, {style}",
    )
    gen.add_argument("--slurm-partition", default="scavenge_gpu")
    gen.add_argument("--slurm-gpu", choices=["b200", "h200"], default="b200")
    gen.add_argument("--slurm-gpus", type=int, default=1)
    gen.add_argument("--slurm-time", default="00:10:00")
    gen.add_argument("--slurm-cpus", type=int, default=4)
    gen.add_argument("--slurm-mem", default="16G")
    gen.add_argument("--slurm-wait", action="store_true", help="wait for Slurm visual jobs to finish")
    gen.add_argument("--slurm-dry-run", action="store_true", help="write Slurm scripts without submitting jobs")
    gen.add_argument("--slurm-timeout", type=int, default=3600)
    gen.add_argument(
        "--slurm-single-task",
        action="store_true",
        help="run one Slurm task over all visual items; command template must contain {items}",
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
            {
                "partition": args.slurm_partition,
                "gpu_type": args.slurm_gpu,
                "gpus": args.slurm_gpus,
                "time_limit": args.slurm_time,
                "cpus": args.slurm_cpus,
                "mem": args.slurm_mem,
                "wait": args.slurm_wait,
                "dry_run": args.slurm_dry_run,
                "timeout_seconds": args.slurm_timeout,
                "single_task": args.slurm_single_task,
            },
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
    slurm_options: dict[str, object],
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
            if visual == "slurm":
                if not visual_command:
                    print("ERROR: --visual-command is required when --visual slurm is used")
                    return 2
                capture_result["visual"] = generate_slurm_visual_assets(
                    Path(capture_result["capture_dir"]),
                    command_template=visual_command,
                    partition=str(slurm_options["partition"]),
                    gpu_type=str(slurm_options["gpu_type"]),
                    gpus=int(slurm_options["gpus"]),
                    time_limit=str(slurm_options["time_limit"]),
                    cpus=int(slurm_options["cpus"]),
                    mem=str(slurm_options["mem"]),
                    wait=bool(slurm_options["wait"]),
                    dry_run=bool(slurm_options["dry_run"]),
                    timeout_seconds=int(slurm_options["timeout_seconds"]),
                    single_task=bool(slurm_options["single_task"]),
                )
            elif visual != "none":
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
            "visual_command": visual_command if visual in {"external", "slurm"} else None,
            "slurm_options": slurm_options if visual == "slurm" else None,
            "export_format": export,
            "export_result": export_result,
        },
    )
    print(f"generated dataset at {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
