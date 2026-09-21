# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The MiniMax and HuggingFace Teams.
# H3 Apple still-image preparation.
"""Prepare still RGB inputs without importing a model runtime."""

import math
from PIL import Image, ImageOps


def reference_image_size(width: int, height: int, pixel_budget: int) -> tuple[int, int]:
    """Return H,W with Sol's per-image area budget and nearest-32 alignment."""
    if any(type(value) is not int or value <= 0 for value in (width, height, pixel_budget)):
        raise ValueError("Image dimensions and pixel budget must be positive integers.")
    if not 0.25 <= width / height <= 4:
        raise ValueError("Reference image aspect ratio must be between 1:4 and 4:1.")
    scale = min(1.0, math.sqrt(pixel_budget / (width * height)))
    return max(32, round(height * scale / 32) * 32), max(32, round(width * scale / 32) * 32)


def prepare_reference_image(image: Image.Image, pixel_budget: int) -> Image.Image:
    """Produce the one RGB image both the Qwen and H3 VAE encoders must see."""
    image = ImageOps.exif_transpose(image).convert("RGB")
    height, width = reference_image_size(*image.size, pixel_budget)
    return image.resize((width, height), Image.Resampling.LANCZOS)
