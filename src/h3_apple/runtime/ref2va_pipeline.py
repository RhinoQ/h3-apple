"""Experimental native H3 image-reference conditioning and dense/VSA sampling."""

import gc
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import mlx.core as mx
import numpy as np
from PIL import Image

from .._vendor.fastvideo_mlx.minimax_h3 import (
    patchify_video_latents, audio_latent_num_frames, load_mlx_h3_checkpoint,
)
from .._vendor.fastvideo_mlx.minimax_h3_conditioner import StreamedMiniMaxH3TextConditioner
from .._vendor.fastvideo_mlx.minimax_h3_pipeline import MiniMaxH3MLXPipeline
from .._vendor.fastvideo_mlx.minimax_h3_vsa import MiniMaxH3VSAConfig
from .ref2va import prepare_reference_image, ReferenceGeometry, build_ref2va_layout
from .ref2va_conditioning import (
    qwen_image_inputs, qwen_vision_features, image_presentation, load_native_image_vae,
    encode_image_latents, encode_images,
)
from .ref2va_sampling import image_noise, sample_image
from .sparse import sparse_calls


def prepare_images(options):
    """Load one legacy image or an explicitly ordered list of 1–9 images."""
    if ("image_path" in options) == ("image_paths" in options):
        raise ValueError("Provide exactly one of image_path and image_paths.")
    paths = [options["image_path"]] if "image_path" in options else options["image_paths"]
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
    if request["num_steps"] != 4:
        raise ValueError("The Ref2VA Turbo adapter requires four steps.")
    attention = options.get("attention", "vsa")
    if attention not in ("dense", "vsa"):
        raise ValueError("Reference attention must be dense or vsa.")
    recipe = json.loads((Path(checkpoint) / "ref2va_recipe.json").read_text())
    if (recipe.get("schema") != "h3-apple-ref2va/v1" or recipe.get("task") != "ref2va"
            or recipe.get("lora_tensors") != 624 or recipe.get("gate_tensors") != 50
            or recipe.get("fasth3_t2va_deltas_applied") is not False):
        raise ValueError("Expected a dedicated Ref2VA + LightX2V checkpoint with gate-only transplant.")
    native = Path(options["native_root"])
    prepared = prepare_images(options)
    metadata = dict(task="ref2va", precision="int8_group64_bf16", attention=attention,
        reference_resize=options.get("reference_resize", "legacy"), pixel_budget=options["pixel_budget"],
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
        video, audio = sample_image(dit, text, condition_rows, layout, initial_video,
                                   initial_audio, observer=observer)
        stats = asdict(dit.last_vsa_stats) if dit.last_vsa_stats is not None else None
        calls = sparse_calls() - before
        if (observer.nfe, observer.blocks) != (4, 200):
            raise ValueError("Expected exactly four complete Ref2VA forwards.")
        if attention == "vsa":
            if calls != 200 or stats is None or stats["fallback_reasons"] or stats["sparse_calls"] != 200:
                raise ValueError("Expected 200 native VSA block calls without fallback.")
        elif calls:
            raise ValueError("Dense Ref2VA unexpectedly called sparse attention.")
        return video, audio, stats

    video, audio, stats = phase("denoise", denoise)
    gc.collect(); mx.clear_cache()
    return video, audio, metadata, stats
