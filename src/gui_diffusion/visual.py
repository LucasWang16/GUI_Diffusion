from __future__ import annotations

from pathlib import Path
from typing import Any
import subprocess

from PIL import Image, ImageDraw, ImageEnhance

from .models import read_json, write_json


ROLE_COLORS = {
    "button": (47, 111, 115),
    "textbox": (225, 138, 61),
    "listitem": (103, 91, 183),
    "heading": (54, 67, 78),
    "status": (68, 145, 94),
    "card": (82, 129, 190),
}


def generate_visual_assets(
    capture_dir: Path,
    style: str = "clean_product_ui",
    adapter: str = "mock",
    command_template: str | None = None,
) -> dict[str, Any]:
    """Generate visual assets from captured screenshots.

    `mock` is deterministic and local. `external` calls a user supplied command
    template and validates that it produced the expected output file.
    """
    if adapter not in {"mock", "external"}:
        raise ValueError(f"unsupported visual adapter {adapter!r}")
    if adapter == "external" and not command_template:
        raise ValueError("--visual-command is required when --visual external is used")

    capture = read_json(capture_dir / "capture.json")
    masks_dir = capture_dir / "layout_masks"
    visual_dir = capture_dir / "visual"
    prompt_dir = capture_dir / "visual_prompt_text"
    masks_dir.mkdir(exist_ok=True)
    visual_dir.mkdir(exist_ok=True)
    prompt_dir.mkdir(exist_ok=True)

    prompts = []
    for item in capture["steps"]:
        screenshot = capture_dir / item["screenshot"]
        step_no = item["step"]["step"]
        mask_name = f"step_{step_no:03d}_mask.png"
        visual_name = f"step_{step_no:03d}_{adapter}_diffusion.png"
        prompt_name = f"step_{step_no:03d}_prompt.txt"

        mask_path = masks_dir / mask_name
        visual_path = visual_dir / visual_name
        prompt = _prompt_for_step(item, style)
        prompt_path = prompt_dir / prompt_name

        _write_layout_mask(item["dom"], mask_path)
        prompt_path.write_text(prompt + "\n", encoding="utf-8")
        if adapter == "mock":
            _write_mock_refinement(screenshot, visual_path)
        else:
            _run_external_adapter(
                command_template=command_template or "",
                screenshot=screenshot,
                mask=mask_path,
                prompt_file=prompt_path,
                output=visual_path,
                style=style,
            )
        prompts.append(
            {
                "step": step_no,
                "adapter": adapter,
                "style": style,
                "input_screenshot": item["screenshot"],
                "layout_mask": f"layout_masks/{mask_name}",
                "prompt_file": f"visual_prompt_text/{prompt_name}",
                "output_image": f"visual/{visual_name}",
                "prompt": prompt,
                "preserve": ["text", "component bounding boxes", "click targets"],
            }
        )

    write_json(capture_dir / "visual_prompts.json", {"adapter": adapter, "style": style, "items": prompts})
    return {
        "adapter": adapter,
        "style": style,
        "prompt_file": str(capture_dir / "visual_prompts.json"),
        "items": len(prompts),
    }


def _write_layout_mask(dom: list[dict[str, Any]], out_path: Path) -> None:
    image = Image.new("RGB", (390, 720), (10, 12, 16))
    draw = ImageDraw.Draw(image, "RGBA")
    for node in dom:
        color = ROLE_COLORS.get(node["role"], (180, 180, 180))
        x1, y1, x2, y2 = node["bbox"]
        draw.rectangle((x1, y1, x2, y2), fill=(*color, 170), outline=(*color, 255), width=2)
    image.save(out_path)


def _write_mock_refinement(screenshot_path: Path, out_path: Path) -> None:
    base = Image.open(screenshot_path).convert("RGB")
    overlay = Image.new("RGB", base.size, (238, 244, 241))
    blended = Image.blend(base, overlay, 0.08)
    blended = ImageEnhance.Contrast(blended).enhance(1.06)
    blended = ImageEnhance.Color(blended).enhance(1.08)
    draw = ImageDraw.Draw(blended, "RGBA")
    draw.rectangle((0, 0, base.width - 1, base.height - 1), outline=(47, 111, 115, 90), width=2)
    blended.save(out_path)


def _run_external_adapter(
    command_template: str,
    screenshot: Path,
    mask: Path,
    prompt_file: Path,
    output: Path,
    style: str,
) -> None:
    command = command_template.format(
        input=str(screenshot),
        mask=str(mask),
        prompt_file=str(prompt_file),
        output=str(output),
        style=style,
    )
    result = subprocess.run(command, shell=True, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            "external visual adapter failed with exit code "
            f"{result.returncode}: {result.stderr.strip() or result.stdout.strip()}"
        )
    if not output.exists():
        raise RuntimeError(f"external visual adapter did not create output image: {output}")


def _prompt_for_step(item: dict[str, Any], style: str) -> str:
    labels = [node["text"] for node in item["dom"] if node.get("text")]
    label_text = "; ".join(labels[:8])
    return (
        "Refine this GUI screenshot into a polished but text-preserving "
        f"{style} interface. Preserve exact layout, readable labels, and "
        f"clickable target boxes. Visible UI text: {label_text}"
    )
