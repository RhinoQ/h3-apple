"""Original LightX2V reference conditioning and VSA sampling."""

import gc
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import mlx.core as mx
import numpy as np
from PIL import Image

from .._vendor.fastvideo_mlx.minimax_h3 import (
    audio_latent_num_frames, load_mlx_h3_checkpoint,
)
from .._vendor.fastvideo_mlx.minimax_h3_pipeline import MiniMaxH3MLXPipeline
from .._vendor.fastvideo_mlx.minimax_h3_vsa import MiniMaxH3VSAConfig
from ..image_inputs import prepare_reference_image
from .ref2va import ReferenceGeometry, build_ref2va_layout
from .ref2va_conditioning import encode_images
from .. import pika_recipe
from .ref2va_sampling import image_noise, sample_image
from .sparse import sparse_calls


def prepare_images(options):
    """Load the worker's ordered list of 1–9 images."""
    paths = options.get("image_paths")
    if (not isinstance(paths, (list, tuple)) or not 1 <= len(paths) <= 9
            or any(not isinstance(path, (str, Path)) or not str(path) for path in paths)):
        raise ValueError("Reference images must be an ordered list of 1–9 file paths.")
    images = []
    for path in paths:
        with Image.open(path) as original:
            images.append(prepare_reference_image(original, options["pixel_budget"]))
    return images


def condition_and_denoise(request, options, checkpoint, observer, phase):
    """Encode shared reference pixels, sample four times, return generated rows only.

    This uses the Ours INT8/BF16 representation. It does not reproduce ComfyUI's
    ConvRot quantization, NVFP4 text encoder, or CUDA random-number streams.
    """
    pika = request.get("recipe") == pika_recipe.RECIPE
    steps = 6 if pika else 4
    if request["num_steps"] != steps:
        raise ValueError("Ref2VA step count differs from its generation recipe.")
    attention = options.get("attention", "vsa")
    if attention not in ("vsa", "dense"):
        raise ValueError("The Ref2VA runtime requires vsa or dense attention.")
    recipe = json.loads((Path(checkpoint) / "ref2va_recipe.json").read_text())
    if (recipe.get("schema") != "h3-apple-ref2va/v1" or recipe.get("task") != "ref2va"
            or recipe.get("lora_tensors") != 624 or recipe.get("gate_tensors") != 50
            or recipe.get("fasth3_t2va_deltas_applied") is not False):
        raise ValueError("Expected a dedicated Ref2VA + LightX2V checkpoint with gate-only transplant.")
    if pika != (recipe.get("sampling_recipe") == pika_recipe.RECIPE):
        raise ValueError("Selected generator and checkpoint recipe differ.")
    if pika and (attention != "dense" or recipe.get("lora_alpha") != 128
                 or recipe.get("manifest_sha256") != pika_recipe.MANIFEST):
        raise ValueError("Pika High requires its pinned Ref2VA weights and Dense attention.")
    native = Path(options["native_root"])
    prepared = prepare_images(options)
    metadata = dict(task="ref2va", precision="int8_group64_bf16", attention=attention,
        reference_resize="match", pixel_budget=options["pixel_budget"],
        reference_images=[dict(index=index + 1, width_height=list(image.size),
            pixels_sha256=hashlib.sha256(np.asarray(image).tobytes()).hexdigest())
            for index, image in enumerate(prepared)],
        noise_convention="NumPy SeedSequence(seed).spawn(3): reference, video, audio; PCG64 FP32")
    if len(prepared) == 1:
        metadata.update(image_width_height=list(prepared[0].size),
            image_pixels_sha256=metadata["reference_images"][0]["pixels_sha256"])

    text, tags, reference, condition_metadata = phase("conditioning", lambda: encode_images(
        native, prepared, request["prompt"], observer))
    metadata.update(condition_metadata)
    if pika:
        if reference.dtype != np.float32:
            raise ValueError("Pika reference latents require FP32 conditioning.")
        metadata.update(sampling_recipe=pika_recipe.RECIPE, renoise_seed=request["seed"] + 1,
                        renoise_order="PCG64 FP32, video then audio, five pairs", knots=pika_recipe.KNOTS,
                        reference_latent_dtype=str(reference.dtype))
    gc.collect(); mx.clear_cache()
    geometry = MiniMaxH3MLXPipeline.resolve_geometry(
        request["model_height"], request["model_width"], request["model_num_frames"])
    layout = build_ref2va_layout(tags,
        [ReferenceGeometry("image", 1, image.height // 16, image.width // 16) for image in prepared],
        geometry["latent_frame_count"], geometry["latent_height"], geometry["latent_width"],
        audio_latent_num_frames(request["model_num_frames"]))
    condition_rows, initial_video, initial_audio = image_noise(reference, layout, request["seed"])
    metadata.update(sequence_length=layout.sequence_length,
        prefix_segments=list(layout.reference_prefix_segments),
        condition_sha256=hashlib.sha256(condition_rows.tobytes()).hexdigest(),
        initial_video_sha256=hashlib.sha256(initial_video.tobytes()).hexdigest(),
        initial_audio_sha256=hashlib.sha256(initial_audio.tobytes()).hexdigest(),
        target_video_rows=len(initial_video), target_audio_rows=len(initial_audio))

    def denoise():
        dit = load_mlx_h3_checkpoint(checkpoint)
        if not dit.vsa_capable or len(dit.blocks) != 50:
            raise ValueError("Expected the dedicated Ref2VA checkpoint with all 50 transplanted gates.")
        dit.configure_vsa(MiniMaxH3VSAConfig(enabled=attention == "vsa", sparsity=.75,
                                            prefix_mode="exempt", impl="simd", routing_mode="kablex"))
        before = sparse_calls()
        from .dispatch import Dispatch
        with Dispatch(dit, attention=attention) as intervention:
            video, audio = sample_image(dit, text, condition_rows, layout, initial_video,
                                       initial_audio, observer=observer,
                                       renoise_seed=request["seed"] + 1 if pika else None)
        summary = metadata["acceleration"] = intervention.summary()
        expected = dict(projection_calls=300*steps, int8_fine_calls=50*steps if attention == "vsa" else 0,
                        dense_self_attention_calls=50*steps if attention == "dense" else 0,
                        activation_pack_calls=200*steps, qkv_pack_reuses=100*steps)
        if any(summary[key] != count for key, count in expected.items()):
            raise ValueError("Incomplete Ref2VA projection / attention dispatch.")
        stats = asdict(dit.last_vsa_stats) if dit.last_vsa_stats is not None else None
        calls = sparse_calls() - before
        if (observer.nfe, observer.blocks) != (steps, 50*steps):
            raise ValueError("Incomplete Ref2VA forwards for the selected recipe.")
        if attention == "vsa":
            if calls != 200 or stats is None or stats["fallback_reasons"] or stats["sparse_calls"] != 200:
                raise ValueError("Expected 200 native VSA block calls without fallback.")
        elif calls != 0 or stats is not None:
            raise ValueError("Dense attention must execute zero sparse blocks and no VSA branch.")
        return video, audio, stats

    video, audio, stats = phase("denoise", denoise)
    gc.collect(); mx.clear_cache()
    return video, audio, metadata, stats
