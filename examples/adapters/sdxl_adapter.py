"""SDXL visual adapter for GUI_Diffusion.

This adapter is designed for Slurm GPU execution. It reads the text prompt
created by GUI_Diffusion and writes one SDXL-generated image to the requested
output path.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import torch
from diffusers import StableDiffusionXLImg2ImgPipeline, StableDiffusionXLPipeline
from PIL import Image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Source screenshot path; kept for adapter contract compatibility.")
    parser.add_argument("--mask", required=True, help="Layout mask path; kept for adapter contract compatibility.")
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default=os.environ.get("GUI_DIFFUSION_SDXL_MODEL", "stabilityai/stable-diffusion-xl-base-1.0"))
    parser.add_argument("--height", type=int, default=512)
    parser.add_argument("--width", type=int, default=512)
    parser.add_argument("--steps", type=int, default=8)
    parser.add_argument("--guidance", type=float, default=4.5)
    parser.add_argument("--strength", type=float, default=0.35)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--mode", choices=["img2img", "txt2img"], default="img2img")
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available; run this adapter on a GPU Slurm allocation.")

    prompt = Path(args.prompt_file).read_text(encoding="utf-8").strip()
    negative_prompt = (
        "blurred text, misspelled text, unreadable UI labels, distorted buttons, "
        "warped layout, broken interface, watermark"
    )

    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    pipeline_cls = StableDiffusionXLImg2ImgPipeline if args.mode == "img2img" else StableDiffusionXLPipeline
    pipe = pipeline_cls.from_pretrained(
        args.model,
        torch_dtype=dtype,
        use_safetensors=True,
    )
    pipe.to("cuda")
    if hasattr(pipe, "enable_attention_slicing"):
        pipe.enable_attention_slicing()

    generator = torch.Generator(device="cuda").manual_seed(args.seed)
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
        init_image = Image.open(args.input).convert("RGB").resize((args.width, args.height))
        kwargs["image"] = init_image
        kwargs["strength"] = args.strength
    image = pipe(**kwargs).images[0]

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    print(f"saved {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
