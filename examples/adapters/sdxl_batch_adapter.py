"""Batch SDXL adapter for GUI_Diffusion Slurm outputs.

Loads SDXL once, then generates every item in a GUI_Diffusion Slurm items.json.
This is the preferred demo path for full-trajectory SDXL generation because a
small trajectory should not reload the model for every GUI step.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import torch
from diffusers import StableDiffusionXLImg2ImgPipeline, StableDiffusionXLPipeline
from PIL import Image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--items", required=True, type=Path)
    parser.add_argument("--model", default=os.environ.get("GUI_DIFFUSION_SDXL_MODEL", "stabilityai/stable-diffusion-xl-base-1.0"))
    parser.add_argument("--height", type=int, default=512)
    parser.add_argument("--width", type=int, default=512)
    parser.add_argument("--steps", type=int, default=6)
    parser.add_argument("--guidance", type=float, default=3.0)
    parser.add_argument("--strength", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--mode", choices=["img2img", "txt2img"], default="img2img")
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available; run this adapter on a GPU Slurm allocation.")

    data = json.loads(args.items.read_text(encoding="utf-8"))
    items = data["items"]
    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    pipeline_cls = StableDiffusionXLImg2ImgPipeline if args.mode == "img2img" else StableDiffusionXLPipeline
    pipe = pipeline_cls.from_pretrained(args.model, torch_dtype=dtype, use_safetensors=True)
    pipe.to("cuda")
    if hasattr(pipe, "enable_attention_slicing"):
        pipe.enable_attention_slicing()

    negative_prompt = (
        "blurred text, misspelled text, unreadable UI labels, distorted buttons, "
        "warped layout, broken interface, watermark"
    )
    for index, item in enumerate(items):
        prompt = Path(item["prompt_file"]).read_text(encoding="utf-8").strip()
        generator = torch.Generator(device="cuda").manual_seed(args.seed + index)
        kwargs = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "height": args.height,
            "width": args.width,
            "num_inference_steps": args.steps,
            "guidance_scale": args.guidance,
            "generator": generator,
        }
        if args.mode == "img2img":
            init_image = Image.open(item["input"]).convert("RGB").resize((args.width, args.height))
            kwargs["image"] = init_image
            kwargs["strength"] = args.strength
        image = pipe(**kwargs).images[0]
        output = Path(item["output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        image.save(output)
        print(f"saved step={item['step']} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
