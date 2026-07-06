from __future__ import annotations

from pathlib import Path
from typing import Any
from dataclasses import asdict
import shutil

from .models import Trajectory, write_json


def capture_trajectory(
    html_path: Path,
    trajectory: Trajectory,
    out_dir: Path,
    record_video: bool = True,
) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("playwright is not installed; run `pip install -e .`") from exc

    out_dir.mkdir(parents=True, exist_ok=True)
    video_dir = out_dir / "video"
    if record_video:
        video_dir.mkdir(exist_ok=True)
    snapshots: list[dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context_options: dict[str, Any] = {"viewport": {"width": 390, "height": 720}}
        if record_video:
            context_options.update(
                {
                    "record_video_dir": str(video_dir),
                    "record_video_size": {"width": 390, "height": 720},
                }
            )
        context = browser.new_context(**context_options)
        page = context.new_page()
        page.goto(html_path.resolve().as_uri(), wait_until="domcontentloaded", timeout=10000)
        page.locator("#app").wait_for(state="visible", timeout=3000)

        for step in trajectory.steps:
            if step.operation == "assert_screen":
                current = page.locator("#app").get_attribute("data-current-screen")
                if current != step.expected_screen:
                    raise RuntimeError(f"expected screen {step.expected_screen}, got {current}")
            else:
                locator = page.locator(f'[data-gui-id="{step.target_id}"]')
                locator.wait_for(state="visible", timeout=3000)
                if step.operation == "fill":
                    locator.fill(step.value)
                elif step.operation == "click":
                    locator.click()
                else:
                    raise RuntimeError(f"unsupported operation {step.operation}")

            screenshot_path = out_dir / f"step_{step.step:03d}.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            snapshots.append(
                {
                    "step": asdict(step),
                    "current_screen": page.locator("#app").get_attribute("data-current-screen"),
                    "screenshot": screenshot_path.name,
                    "dom": page.locator("#app").evaluate(
                        """app => Array.from(app.querySelectorAll('[data-gui-id]')).map(el => ({
                          id: el.dataset.guiId,
                          role: el.dataset.role,
                          text: el.innerText || el.getAttribute('placeholder') || el.value || '',
                          bbox: (() => {
                            const r = el.getBoundingClientRect();
                            return [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)];
                          })()
                        }))"""
                    ),
                }
            )

        video = page.video if record_video else None
        context.close()
        video_path = None
        if video is not None:
            video_path = out_dir / f"{trajectory.task_id}.webm"
            video.save_as(str(video_path))
        browser.close()

    if record_video:
        shutil.rmtree(video_dir, ignore_errors=True)
    write_json(out_dir / "capture.json", {"trajectory": trajectory.task_id, "steps": snapshots, "video": video_path.name if video_path else None})
    return {"capture_dir": str(out_dir), "video": str(video_path) if video_path else None, "steps": len(snapshots)}
