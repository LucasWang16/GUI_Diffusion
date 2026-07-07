# GUI Diffusion

MVP framework for generating GUI-agent training data from an application description.

The current version creates a structured app spec, GUI state graph, executable HTML prototype, trajectory JSON, optional Playwright screenshots/video, deterministic mock visual-refinement assets, external visual-adapter outputs, and a JSONL export table. The `mock` visual adapter is intentionally not a real diffusion model; it defines the contract for a later SDXL/FLUX/ControlNet adapter while keeping labels exact.

## Quick Start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install chromium
gui-diffusion generate \
  --description "A personal expense tracker with add expense, category picker, budget alert, and monthly statistics." \
  --out examples/out/expense_tracker \
  --capture \
  --visual mock \
  --export hf
pytest
```

If Chromium is unavailable, omit `--capture`, `--visual`, and `--export`; the structured dataset is still generated.

## Output

- `app_spec.json`
- `state_graph.json`
- `trajectory.json`
- `index.html`
- `manifest.json`
- `capture/` with screenshots, DOM snapshots, bounding boxes, and video when capture is enabled
- `capture/*/layout_masks/` and `capture/*/visual/` when `--visual mock` is enabled
- `dataset/gui_agent_steps.jsonl` when `--export hf` is enabled

## Visual Adapter Contract

`--visual mock` generates:

- a layout mask per captured step
- a text-preserving mock visual image per step
- `visual_prompts.json` with the prompt and preservation constraints

A real diffusion adapter should consume the same screenshot/mask/prompt inputs and produce the same output fields without changing component ids or bounding boxes.

## External Visual Adapter

Use `--visual external --visual-command "<command>"` to connect a local diffusion script or service wrapper. The command template receives:

- `{input}` screenshot path
- `{mask}` layout mask path
- `{prompt_file}` text prompt path
- `{output}` required output image path
- `{style}` style slug

Example shape:

```bash
gui-diffusion generate \
  --description "A shop app with product detail, cart, and checkout" \
  --out examples/out/shop_external \
  --visual external \
  --visual-command "python run_diffusion.py --input {input} --mask {mask} --prompt-file {prompt_file} --output {output}" \
  --export hf \
  --no-video
```

## Slurm B200/H200 Visual Adapter

Use `--visual slurm` to run the visual adapter as a Slurm array job. This is the intended path for real diffusion generation on B200/H200 nodes.

```bash
gui-diffusion generate \
  --description "A shop app with product detail, cart, and checkout" \
  --out examples/out/shop_slurm_b200 \
  --visual slurm \
  --visual-command "python run_diffusion.py --input {input} --mask {mask} --prompt-file {prompt_file} --output {output}" \
  --slurm-partition scavenge_gpu \
  --slurm-gpu b200 \
  --slurm-gpus 1 \
  --slurm-time 00:10:00 \
  --slurm-wait \
  --export hf \
  --no-video
```

For H200, switch to `--slurm-gpu h200` and a partition that exposes H200, such as `gpu_h200` when available.

Use `--slurm-dry-run` to write the Slurm job script and item manifest without submitting.

## Batched SDXL On Slurm

For full-trajectory SDXL generation, prefer one Slurm task that loads SDXL once and processes every captured GUI step:

```bash
gui-diffusion generate \
  --description "A shop app with product detail, cart, order, and checkout." \
  --out examples/out/shop_sdxl_b200 \
  --visual slurm \
  --visual-command "GUI_Diffusion/.venv/bin/python GUI_Diffusion/examples/adapters/sdxl_batch_adapter.py --items {items} --height 512 --width 512 --steps 6 --guidance 3.0 --strength 0.25 --mode img2img" \
  --slurm-single-task \
  --slurm-partition scavenge_gpu \
  --slurm-gpu b200 \
  --slurm-gpus 1 \
  --slurm-time 00:45:00 \
  --slurm-wait \
  --export hf \
  --no-video
```

The batch adapter writes one `step_*_slurm_diffusion.png` image per trajectory step.
