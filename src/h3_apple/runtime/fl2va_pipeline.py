# SPDX-License-Identifier: Apache-2.0
# Keyframe preparation follows the MiniMax and Hugging Face reference.
"""Experimental first/last-frame conditioning with dedicated LightX2V weights.

Dense attention deliberately avoids depending on cross-task VSA gate quality.
The immutable anchors participate in every forward and are excluded from decode.
"""
from dataclasses import asdict
import gc
import json
from pathlib import Path

import mlx.core as mx
import numpy as np
from PIL import Image, ImageOps

from .._vendor.fastvideo_mlx.minimax_h3 import build_packed_layout, audio_latent_num_frames, load_mlx_h3_checkpoint
from .._vendor.fastvideo_mlx.minimax_h3_pipeline import MiniMaxH3MLXPipeline
from .._vendor.fastvideo_mlx.minimax_h3_vsa import MiniMaxH3VSAConfig
from .ref2va import Ref2VALayout
from .ref2va_multimodal import encode_references, checksum
from .ref2va_sampling import image_noise, sample_image
from .sparse import sparse_calls


def prepare_keyframe(image, width, height, *, stretch):
    image = ImageOps.exif_transpose(image).convert("RGB")
    if image.size == (width, height):
        return image
    if stretch:
        return image.resize((width, height), Image.Resampling.LANCZOS)
    scale = max(width / image.width, height / image.height)
    size = (max(width, round(image.width * scale)), max(height, round(image.height * scale)))
    left, top = max(0, (size[0] - width) // 2), max(0, (size[1] - height) // 2)
    return image.resize(size, Image.Resampling.LANCZOS).crop((left, top, left + width, top + height))


def keyframe_layout(tags, geometry, model_frames, anchors):
    if tuple(anchors) not in (("first",), ("last",), ("first", "last")):
        raise ValueError("Keyframe anchors must be first, last, or first then last.")
    base = build_packed_layout(len(tags), geometry["latent_frame_count"], geometry["latent_height"],
        geometry["latent_width"], audio_latent_num_frames(model_frames),
        keyframe_anchors=tuple(anchors), text_token_tags=tags)
    frame_rows = base.num_condition_video_rows // len(anchors)
    segments = (len(tags), *([frame_rows] * len(anchors)), len(base.audio_indices))
    return Ref2VALayout(**asdict(base), reference_prefix_segments=segments)


def condition_and_denoise(request, options, checkpoint, observer, phase):
    if request["task"] != "fl2va" or request["num_steps"] != 4 or options["attention"] != "dense":
        raise ValueError("The first/last-frame admission path uses four steps and dense attention.")
    recipe = json.loads((Path(checkpoint) / "fl2va_recipe.json").read_text())
    expected = dict(schema="h3-apple-fl2va/v1", task="fl2va", lora_tensors=624,
        lora_rank=128, lora_alpha=8, fasth3_t2va_deltas_applied=False)
    if any(recipe.get(key) != value for key, value in expected.items()):
        raise ValueError("Expected the dedicated FL2VA + LightX2V four-step checkpoint.")
    references = []
    if len(options["image_paths"]) != len(options["anchors"]):
        raise ValueError("Keyframe paths and anchors disagree.")
    for index, path in enumerate(options["image_paths"]):
        with Image.open(path) as image:
            prepared = prepare_keyframe(image, request["model_width"], request["model_height"], stretch=index == 0)
        references.append(dict(kind="image", image=prepared))
    text, tags, rows, audio_rows, _, segments = phase("conditioning", lambda: encode_references(
        Path(options["native_root"]), None, references, request["prompt"], observer))
    if len(audio_rows):
        raise ValueError("Keyframe conditioning cannot contain source audio.")
    geometry = MiniMaxH3MLXPipeline.resolve_geometry(request["model_height"], request["model_width"], request["model_num_frames"])
    layout = keyframe_layout(tags, geometry, request["model_num_frames"], options["anchors"])
    condition, initial_video, initial_audio = image_noise(rows, layout, request["seed"])
    metadata = dict(task="fl2va", attention="dense", experimental=True, anchors=options["anchors"],
        reference_segments=segments, condition_rows=len(condition), condition_sha256=checksum(condition),
        text_sha256=checksum(text), prefix_segments=list(layout.reference_prefix_segments),
        canvas=[request["model_width"], request["model_height"]],
        image_policy="First supplied keyframe stretches to the model canvas; the follower is cover-cropped.",
        noise_convention="NumPy SeedSequence(seed).spawn(3): reference, video, audio; PCG64 FP32",
        vsa_gates_used=False, video_shift=12, audio_shift=3)
    del references, rows, audio_rows
    gc.collect(); mx.clear_cache()

    def denoise():
        dit = load_mlx_h3_checkpoint(checkpoint)
        dit.configure_vsa(MiniMaxH3VSAConfig(enabled=False))
        before = sparse_calls()
        video, audio = sample_image(dit, text, condition, layout, initial_video, initial_audio, observer=observer)
        if (observer.nfe, observer.blocks, sparse_calls() - before) != (4, 200, 0):
            raise ValueError("Expected four complete dense FL2VA forwards.")
        stats = asdict(dit.last_vsa_stats) if dit.last_vsa_stats is not None else None
        return video, audio, stats
    video, audio, stats = phase("denoise", denoise)
    return video, audio, metadata, stats
