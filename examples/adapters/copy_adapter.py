"""Minimal external visual adapter example.

This is not a diffusion model. It copies the input screenshot to the requested
output path so the external-adapter contract can be tested end to end.
"""

import sys

from PIL import Image


Image.open(sys.argv[1]).save(sys.argv[2])
