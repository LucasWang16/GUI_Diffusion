from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m gui_diffusion.slurm_worker")
    parser.add_argument("--items", required=True, type=Path)
    parser.add_argument("--array-index", default=None)
    args = parser.parse_args(argv)

    index_text = args.array_index or os.environ.get("SLURM_ARRAY_TASK_ID", "0")
    index = int(index_text)
    data = json.loads(args.items.read_text(encoding="utf-8"))
    item = data["items"][index]
    command = data["command_template"].format(
        input=item["input"],
        mask=item["mask"],
        prompt_file=item["prompt_file"],
        output=item["output"],
        style=item["style"],
    )
    result = subprocess.run(command, shell=True, text=True, capture_output=True, check=False)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=os.sys.stderr)
    if result.returncode != 0:
        return result.returncode
    if not Path(item["output"]).exists():
        print(f"expected output was not created: {item['output']}", file=os.sys.stderr)
        return 10
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
