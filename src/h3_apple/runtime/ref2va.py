# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The MiniMax and HuggingFace Teams.
# Adapted for NumPy by H3 Apple; pinned source recorded in docs/sources.json.
"""Ref2VA input geometry and generated-only handoff.

This module describes packed rows. Its support for a reference geometry is not
an assertion that the media encoder or end-to-end runtime supports that mode.
"""

from dataclasses import dataclass
import math

import numpy as np
from PIL import Image, ImageOps

from .._vendor.fastvideo_mlx.minimax_h3 import (
    MiniMaxH3PackedLayout,
    MINIMAX_H3_ROPE_FRAME_RESCALE,
    MINIMAX_H3_ROPE_FRAMES_PER_LATENT,
    spatial_position_grid,
    temporal_position_grid,
)


@dataclass(frozen=True)
class ReferenceGeometry:
    media_type: str
    num_latent_frames: int = 0
    latent_height: int = 0
    latent_width: int = 0
    has_audio: bool = False
    num_audio_latents: int = 0


@dataclass(frozen=True)
class Ref2VALayout(MiniMaxH3PackedLayout):
    """Keep every ordered reference segment separate for sparse attention."""

    reference_prefix_segments: tuple[int, ...] = ()


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


def _frame_grid(height, width):
    area = np.sqrt(height * width)
    y = spatial_position_grid(height, 2, area)
    x = spatial_position_grid(width, 2, area)
    return np.stack([grid.reshape(-1) for grid in np.meshgrid(y, x, indexing="ij")], axis=-1), x


def _audio_positions(positions, rows, frames, origin, width_grid):
    positions[rows, 0] = np.tile(origin + np.arange(frames, dtype=np.float64), 2)
    positions[rows, 2] = np.concatenate([
        np.full(frames, width_grid[0], dtype=np.float64),
        np.full(frames, width_grid[-1], dtype=np.float64),
    ])


def _visual_rows(frames, height, width):
    if any(type(value) is not int or value <= 0 for value in (frames, height, width)):
        raise ValueError("Visual latent geometry must contain positive integers.")
    if height % 2 or width % 2:
        raise ValueError("Visual latent geometry must be divisible by the (1,2,2) patch.")
    return frames * (height // 2) * (width // 2)


def build_ref2va_layout(text_token_tags, references, num_latent_frames, latent_height,
                       latent_width, num_audio_latents, patch_size=(1, 2, 2)):
    """Build [text | ordered references | generated audio | generated video]."""
    if patch_size != (1, 2, 2):
        raise ValueError("Ref2VA requires patch_size=(1,2,2).")
    tags = np.asarray(text_token_tags)
    if tags.ndim != 1 or not np.isin(tags, (0, 1)).all():
        raise ValueError("Text token tags must be a one-dimensional array of text/vision tags.")
    if not references or len(references) > 12:
        raise ValueError("Ref2VA needs between one and twelve reference geometries.")
    target_video = _visual_rows(num_latent_frames, latent_height, latent_width)
    if type(num_audio_latents) is not int or num_audio_latents <= 0:
        raise ValueError("Target audio geometry must be a positive integer.")
    visual_counts, audio_counts = [], []
    for reference in references:
        if reference.media_type not in ("image", "video", "audio"):
            raise ValueError("Unsupported reference type.")
        if reference.media_type == "image" and (reference.has_audio or reference.num_latent_frames != 1):
            raise ValueError("An image must have one latent frame and no soundtrack.")
        if reference.media_type == "audio" and not reference.has_audio:
            raise ValueError("An audio reference must have audio latents.")
        if reference.has_audio and (type(reference.num_audio_latents) is not int or reference.num_audio_latents <= 0):
            raise ValueError("Audio-bearing references need positive audio geometry.")
        visual_counts.append(0 if reference.media_type == "audio" else _visual_rows(
            reference.num_latent_frames, reference.latent_height, reference.latent_width))
        audio_counts.append(reference.num_audio_latents * 2 if reference.has_audio else 0)
    count_text = len(tags)
    count_video, count_audio = sum(visual_counts), sum(audio_counts)
    length = count_text + count_video + count_audio + target_video + num_audio_latents * 2
    positions = np.zeros((length, 3), dtype=np.float64)
    positions[:count_text, 0] = np.arange(count_text, dtype=np.float64)
    target_grid, target_width_grid = _frame_grid(latent_height, latent_width)
    video_indices, audio_indices = [], []
    cursor, clock = count_text, float(count_text)
    segments = [count_text]
    for ref, visual_count, audio_count in zip(references, visual_counts, audio_counts, strict=True):
        if ref.media_type == "audio":
            grid, width_grid = None, target_width_grid
        else:
            grid, width_grid = _frame_grid(ref.latent_height, ref.latent_width)
        if audio_count:
            segments.append(audio_count)
            rows = slice(cursor, cursor + audio_count)
            audio_indices.append(np.arange(rows.start, rows.stop))
            _audio_positions(positions, rows, ref.num_audio_latents, clock, width_grid)
            cursor = rows.stop
        if visual_count:
            segments.append(visual_count)
            rows = slice(cursor, cursor + visual_count)
            video_indices.append(np.arange(rows.start, rows.stop))
            times = temporal_position_grid(ref.num_latent_frames, clock)
            positions[rows, 0] = np.repeat(times, grid.shape[0])
            positions[rows, 1:] = np.tile(grid, (ref.num_latent_frames, 1))
            cursor = rows.stop
        if ref.media_type == "image":
            clock += 1.0
        elif ref.media_type == "audio":
            clock += float(ref.num_audio_latents)
        else:
            # The pinned Python 3.12 reference uses compensated float summation.
            # fsum preserves that clock on the product's Python 3.11 runtime;
            # its ordinary sum diverges by one ulp for 17-frame references.
            span = math.fsum(MINIMAX_H3_ROPE_FRAME_RESCALE * MINIMAX_H3_ROPE_FRAMES_PER_LATENT[
                index % len(MINIMAX_H3_ROPE_FRAMES_PER_LATENT)] for index in range(ref.num_latent_frames))
            clock += max(float(ref.num_audio_latents if ref.has_audio else 0), span)
    audio_start, video_start = cursor, cursor + num_audio_latents * 2
    _audio_positions(positions, slice(audio_start, video_start), num_audio_latents, clock, target_width_grid)
    positions[video_start:, 0] = np.repeat(temporal_position_grid(num_latent_frames, clock), target_grid.shape[0])
    positions[video_start:, 1:] = np.tile(target_grid, (num_latent_frames, 1))
    video = np.concatenate(video_indices + [np.arange(video_start, length)])
    audio = np.concatenate(audio_indices + [np.arange(audio_start, video_start)])
    text = np.arange(count_text)
    packed_tags = np.empty(length, dtype=np.int64)
    packed_tags[text], packed_tags[video], packed_tags[audio] = tags, 0, 2
    segments.append(num_audio_latents * 2)
    return Ref2VALayout(length, positions, packed_tags, video, audio, text,
        count_video, count_audio, num_latent_frames, latent_height, latent_width,
        num_audio_latents, tuple(value for value in segments if value > 0))


def build_ref2va_timesteps(layout, video_timestep, audio_timestep):
    """Match native FP32 row assignment before deduplicating timestep values."""
    rows = np.full(layout.sequence_length, video_timestep, dtype=np.float32)
    rows[layout.video_indices[:layout.num_condition_video_rows]] = max(video_timestep, 0.999)
    rows[layout.audio_indices[layout.num_condition_audio_rows:]] = audio_timestep
    rows[layout.audio_indices[:layout.num_condition_audio_rows]] = 1.0
    return np.unique(rows, return_inverse=True)


def generated_rows(video_rows, audio_rows, layout):
    """Remove all reference rows from modality arrays before decode or LTX transfer."""
    target_video = _visual_rows(layout.num_video_latent_frames, layout.latent_height, layout.latent_width)
    target_audio = layout.num_audio_latents * 2
    if (video_rows.shape != (layout.num_condition_video_rows + target_video, 96)
            or audio_rows.shape != (layout.num_condition_audio_rows + target_audio, 32)
            or len(layout.video_indices) != len(video_rows)
            or len(layout.audio_indices) != len(audio_rows)):
        raise ValueError("Packed modality rows do not match the complete reference and target geometry.")
    return video_rows[layout.num_condition_video_rows:], audio_rows[layout.num_condition_audio_rows:]
