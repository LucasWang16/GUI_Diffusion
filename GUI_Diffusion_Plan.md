# GUI Diffusion Training Data Framework Plan

## Goal

Build a framework that turns an application feature description into GUI-agent training data:

- main application screens
- structured GUI state graph
- executable UI prototype
- interaction trajectories for core tasks
- screenshots, DOM/accessibility-like snapshots, bounding boxes, and optional videos

The first version should prioritize controllability and verifiability over visual realism. Diffusion models should be added after the deterministic data loop is reliable.

## Core Principle

Use a structured GUI representation as ground truth. Diffusion should only be a visual diversity layer, not the source of interaction truth.

Pure image/video generation is weak for GUI-agent data because it cannot reliably guarantee readable text, clickable elements, valid state transitions, or exact target coordinates. A structured renderer can guarantee those properties, while diffusion can later stylize screenshots under layout constraints.

## Architecture

1. App Spec Parser
   - Input: short app description.
   - Output: app name, domain, screens, tasks, entities, and user goals.
   - MVP: deterministic keyword/rule parser with sensible defaults.
   - Later: LLM parser with schema validation.

2. GUI State Graph Generator
   - Output: screens as nodes and actions as edges.
   - Each action includes source screen, target screen, control id, operation, and expected result.

3. UI Intermediate Representation
   - A JSON-friendly model of each screen.
   - Includes component ids, roles, labels, values, and stable bounding-box slots.
   - This is the source of truth for labels and training targets.

4. Deterministic Renderer
   - MVP: static HTML/JavaScript app rendered from the intermediate representation.
   - Every component has a `data-gui-id`.
   - Playwright can query these ids to click, type, snapshot, and record video.

5. Trajectory Synthesizer
   - Generates task instructions and action sequences from the state graph.
   - Records step-level action metadata:
     - screen before action
     - target component id
     - operation
     - value
     - expected next screen
   - Playwright execution enriches trajectories with screenshots, DOM snapshots, bounding boxes, and optional video.

6. Verifier
   - Confirms every target exists.
   - Confirms required screens exist.
   - Confirms trajectory transitions are valid.
   - Confirms generated output files are internally consistent.

7. Diffusion Visual Layer
   - Add only after the deterministic loop works.
   - Recommended uses:
     - wireframe-to-styled screenshot
     - component-mask-to-realistic UI
     - icon/background/avatar generation
     - theme/style variation
   - Keep text rendering deterministic to avoid OCR noise and hallucinated labels.

## MVP Deliverables

- Python package under `GUI_Diffusion/src/gui_diffusion`.
- CLI command:
  - generate spec, graph, HTML, manifest, and base trajectory.
  - optionally run Playwright capture for screenshots and video.
- Tests covering parser, graph generation, renderer output, trajectory validity, verifier behavior, and CLI smoke path.
- Example output under `GUI_Diffusion/examples/out`.

## Installed Base Skills

Installed curated Codex skills:

- `playwright`
- `screenshot`
- `jupyter-notebook`

Optional later skills:

- `figma`
- `figma-generate-design`
- `pdf`

Restart Codex to pick up newly installed skills in future turns.

## Near-Term Roadmap

1. Version 0.1
   - Deterministic web/mobile-web prototype generation.
   - JSON trajectory generation.
   - Verifier and tests.
   - Optional Playwright screenshot/video capture.

2. Version 0.2
   - Mock visual adapter contract for later diffusion integration.
   - Layout masks and prompt metadata per captured step.
   - Text-preserving visual mock output per step.
   - Dataset export format compatible with HuggingFace-style JSONL.

3. Version 0.3
   - More app domains and screen templates.
   - External diffusion adapter hook for SDXL/FLUX/ControlNet.
   - Command-template adapter with screenshot, mask, prompt file, and output placeholders.

4. Version 0.4
   - Slurm visual adapter for B200/H200 execution.
   - Slurm array jobs over captured GUI steps.
   - Dry-run mode for job script validation.
   - Wait mode for synchronous small demos.

5. Version 0.5
   - Batched SDXL img2img adapter for full trajectories.
   - Single Slurm task mode to load SDXL once per trajectory.
   - B200 smoke/demo path for SDXL outputs.

6. Version 0.6
   - Randomized but valid layout/theme variation.
   - LLM-based app spec parser.
   - VLM/OCR quality critic.
   - Automatic task expansion and negative examples.

7. Version 0.7
   - Real diffusion/ControlNet visual refinement.
   - LoRA training dataset builder from generated screen IR and screenshots.
   - Verifier that compares refined screenshot OCR and target bounding boxes against the original IR.
