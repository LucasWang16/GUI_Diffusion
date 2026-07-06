from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import os
import re
import subprocess
import sys
import time

from .models import write_json
from .visual import prepare_visual_items


def generate_slurm_visual_assets(
    capture_dir: Path,
    command_template: str,
    style: str = "clean_product_ui",
    partition: str = "scavenge_gpu",
    gpu_type: str = "b200",
    gpus: int = 1,
    time_limit: str = "00:10:00",
    cpus: int = 4,
    mem: str = "16G",
    wait: bool = False,
    poll_seconds: float = 10.0,
    timeout_seconds: int = 3600,
    dry_run: bool = False,
) -> dict[str, Any]:
    items = prepare_visual_items(capture_dir, style)
    visual_dir = capture_dir / "visual"
    slurm_dir = capture_dir / "slurm"
    visual_dir.mkdir(exist_ok=True)
    slurm_dir.mkdir(exist_ok=True)

    prompt_records = []
    worker_items = []
    for item in items:
        output_name = f"step_{item['step']:03d}_slurm_diffusion.png"
        output_path = visual_dir / output_name
        prompt_records.append(
            {
                "step": item["step"],
                "adapter": "slurm",
                "style": item["style"],
                "input_screenshot": item["input_screenshot"],
                "layout_mask": item["layout_mask"],
                "prompt_file": item["prompt_file"],
                "output_image": f"visual/{output_name}",
                "prompt": item["prompt"],
                "preserve": item["preserve"],
            }
        )
        worker_items.append(
            {
                "step": item["step"],
                "input": item["input_screenshot_path"],
                "mask": item["layout_mask_path"],
                "prompt_file": item["prompt_file_path"],
                "output": str(output_path),
                "style": item["style"],
            }
        )

    items_path = slurm_dir / "items.json"
    job_path = slurm_dir / "run_visual_array.sbatch"
    log_path = slurm_dir / "slurm-%A_%a.out"
    items_path.write_text(
        json.dumps({"command_template": command_template, "items": worker_items}, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_job_script(
        job_path=job_path,
        items_path=items_path,
        log_path=log_path,
        partition=partition,
        gpu_type=gpu_type,
        gpus=gpus,
        time_limit=time_limit,
        cpus=cpus,
        mem=mem,
        array_max=max(len(worker_items) - 1, 0),
    )

    write_json(capture_dir / "visual_prompts.json", {"adapter": "slurm", "style": style, "items": prompt_records})
    result: dict[str, Any] = {
        "adapter": "slurm",
        "style": style,
        "prompt_file": str(capture_dir / "visual_prompts.json"),
        "items": len(prompt_records),
        "partition": partition,
        "gpu_type": gpu_type,
        "gpus": gpus,
        "job_script": str(job_path),
        "items_file": str(items_path),
        "dry_run": dry_run,
        "job_id": None,
        "completed": False,
    }
    if dry_run:
        return result

    submit = subprocess.run(["sbatch", str(job_path)], text=True, capture_output=True, check=False)
    if submit.returncode != 0:
        raise RuntimeError(f"sbatch failed: {submit.stderr.strip() or submit.stdout.strip()}")
    job_id = _parse_job_id(submit.stdout)
    result["job_id"] = job_id
    result["sbatch_output"] = submit.stdout.strip()
    if wait:
        result["completed"] = _wait_for_job(job_id, poll_seconds, timeout_seconds)
        missing = [record["output_image"] for record in prompt_records if not (capture_dir / record["output_image"]).exists()]
        if missing:
            raise RuntimeError(f"slurm visual job completed but outputs are missing: {missing[:5]}")
    return result


def _write_job_script(
    job_path: Path,
    items_path: Path,
    log_path: Path,
    partition: str,
    gpu_type: str,
    gpus: int,
    time_limit: str,
    cpus: int,
    mem: str,
    array_max: int,
) -> None:
    cwd = Path.cwd()
    python = sys.executable
    script = f"""#!/bin/bash
#SBATCH --job-name=gui-diffusion-visual
#SBATCH --partition={partition}
#SBATCH --gres=gpu:{gpu_type}:{gpus}
#SBATCH --cpus-per-task={cpus}
#SBATCH --mem={mem}
#SBATCH --time={time_limit}
#SBATCH --array=0-{array_max}
#SBATCH --output={log_path}

set -euo pipefail
cd {cwd}
echo "node=$(hostname)"
echo "cuda_visible_devices=${{CUDA_VISIBLE_DEVICES:-unset}}"
{python} -m gui_diffusion.slurm_worker --items {items_path}
"""
    job_path.write_text(script, encoding="utf-8")


def _parse_job_id(output: str) -> str:
    match = re.search(r"Submitted batch job (\d+)", output)
    if not match:
        raise RuntimeError(f"could not parse sbatch job id from: {output!r}")
    return match.group(1)


def _wait_for_job(job_id: str, poll_seconds: float, timeout_seconds: int) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        queue = subprocess.run(["squeue", "-h", "-j", job_id], text=True, capture_output=True, check=False)
        if queue.returncode == 0 and not queue.stdout.strip():
            return True
        time.sleep(poll_seconds)
    raise TimeoutError(f"slurm job {job_id} did not finish within {timeout_seconds} seconds")
