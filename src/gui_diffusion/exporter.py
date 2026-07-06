from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import os

from .models import AppSpec, Trajectory, read_json, to_jsonable


def export_hf_dataset(
    out_dir: Path,
    spec: AppSpec,
    trajectories: list[Trajectory],
    capture_results: list[dict[str, Any]],
    visual_enabled: bool,
) -> dict[str, Any]:
    dataset_dir = out_dir / "dataset"
    dataset_dir.mkdir(exist_ok=True)
    rows_path = dataset_dir / "gui_agent_steps.jsonl"
    trajectories_by_id = {trajectory.task_id: trajectory for trajectory in trajectories}
    row_count = 0

    with rows_path.open("w", encoding="utf-8") as handle:
        for capture_result in capture_results:
            capture_dir = Path(capture_result["capture_dir"])
            capture = read_json(capture_dir / "capture.json")
            visual_items = _load_visual_items(capture_dir) if visual_enabled else {}
            trajectory = trajectories_by_id[capture["trajectory"]]
            for item in capture["steps"]:
                step = item["step"]
                visual = visual_items.get(step["step"], {})
                row = {
                    "app_name": spec.app_name,
                    "domain": spec.domain,
                    "task_id": trajectory.task_id,
                    "instruction": trajectory.instruction,
                    "step": step["step"],
                    "screen": step["screen"],
                    "screen_after": item["current_screen"],
                    "operation": step["operation"],
                    "target_id": step["target_id"],
                    "value": step["value"],
                    "expected_screen": step["expected_screen"],
                    "screenshot": _rel(out_dir, capture_dir / item["screenshot"]),
                    "dom": item["dom"],
                    "layout_mask": _rel(out_dir, Path(visual["layout_mask"])) if visual.get("layout_mask") else None,
                    "visual_image": _rel(out_dir, Path(visual["output_image"])) if visual.get("output_image") else None,
                    "visual_prompt": visual.get("prompt"),
                }
                handle.write(json.dumps(to_jsonable(row), ensure_ascii=False) + "\n")
                row_count += 1

    readme = dataset_dir / "README.md"
    readme.write_text(
        "# GUI Agent Steps Dataset\n\n"
        "Each JSONL row is one GUI-agent step with screenshot, DOM-like nodes, "
        "action target, and optional mock diffusion visual artifacts.\n",
        encoding="utf-8",
    )
    return {"format": "hf-jsonl", "path": str(rows_path), "rows": row_count}


def _load_visual_items(capture_dir: Path) -> dict[int, dict[str, Any]]:
    visual_path = capture_dir / "visual_prompts.json"
    if not visual_path.exists():
        return {}
    data = read_json(visual_path)
    items: dict[int, dict[str, Any]] = {}
    for item in data["items"]:
        step = int(item["step"])
        item = dict(item)
        item["layout_mask"] = str(capture_dir / item["layout_mask"])
        item["output_image"] = str(capture_dir / item["output_image"])
        items[step] = item
    return items


def _rel(root: Path, path: Path) -> str:
    return os.path.relpath(path, root)
