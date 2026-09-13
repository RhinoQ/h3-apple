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
    encode_image_latents,
)
from .ref2va_sampling import image_noise, sample_image
from .sparse import sparse_calls


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
    with Image.open(options["image_path"]) as original:
        prepared = prepare_reference_image(original, options["pixel_budget"])
    metadata = dict(task="ref2va", precision="int8_group64_bf16", attention=attention,
        image_width_height=list(prepared.size),
        image_pixels_sha256=hashlib.sha256(np.asarray(prepared).tobytes()).hexdigest(),
        noise_convention="NumPy SeedSequence(seed).spawn(3): reference, video, audio; PCG64 FP32")

    def condition():
        inputs = qwen_image_inputs(native / "processor", [prepared])
        features, deepstack = qwen_vision_features(native / "text_encoder",
            inputs["pixel_values"], inputs["image_grid_thw"])
        conditioner = StreamedMiniMaxH3TextConditioner(native / "text_encoder", native / "tokenizer")
        try:
            presentation = image_presentation(conditioner.tokenizer, request["prompt"],
                                               inputs["image_grid_thw"].numpy())
            text, tags = conditioner.encode_presentation(
                presentation.token_ids, presentation.tags, presentation.positions,
                visual_features=features, visual_mask=presentation.visual_mask,
                deepstack_features=deepstack)
        finally:
            conditioner.close()
        del conditioner, features, deepstack, inputs
        gc.collect(); mx.clear_cache()
        vae = load_native_image_vae(native / "video_vae")
        reference = patchify_video_latents(encode_image_latents(vae, prepared), (1, 2, 2))
        metadata.update(prompt_tokens=len(tags), reference_rows=len(reference),
            text_sha256=hashlib.sha256(text.tobytes()).hexdigest(),
            reference_sha256=hashlib.sha256(reference.tobytes()).hexdigest())
        observer.capture("reference-inputs", lambda: dict(
            pixels=np.asarray(prepared), text=text, tags=tags, reference=reference))
        return text, tags, reference

    text, tags, reference = phase("conditioning", condition)
    gc.collect(); mx.clear_cache()
    geometry = MiniMaxH3MLXPipeline.resolve_geometry(
        request["model_height"], request["model_width"], request["model_num_frames"])
    layout = build_ref2va_layout(tags,
        [ReferenceGeometry("image", 1, prepared.height // 16, prepared.width // 16)],
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
