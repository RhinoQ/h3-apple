# SPDX-License-Identifier: Apache-2.0
"""Video and image reference encoding on the H3 Apple execution chain.

Packing follows the pinned MiniMax/Diffusers reference. Media resampling uses
the Conda FFmpeg build and is recorded explicitly; it is not a claim of exact
Torchaudio resampler parity. Standalone audio precedes video soundtracks, so
an explicitly supplied Audio 1 keeps that label in the presentation.
"""
from dataclasses import asdict
import gc
import hashlib
import json
from pathlib import Path
import subprocess

import mlx.core as mx
import numpy as np
from PIL import Image

from ..media import VIDEO_REFERENCE_CANVAS, probe_reference, reference_video_size, tool
from .._vendor.fastvideo_mlx.minimax_h3 import (
    MiniMaxH3SchedulerState, audio_latent_num_frames, load_mlx_h3_checkpoint,
    patchify_video_latents,
)
from .._vendor.fastvideo_mlx.minimax_h3_conditioner import StreamedMiniMaxH3TextConditioner
from .._vendor.fastvideo_mlx.minimax_h3_pipeline import MiniMaxH3MLXPipeline
from .._vendor.fastvideo_mlx.minimax_h3_audio_vae import mlx_h3_audio_vae_from_dir
from .._vendor.fastvideo_mlx.minimax_h3_vsa import MiniMaxH3VSAConfig
from .ref2va import (ReferenceGeometry, build_ref2va_layout, build_ref2va_timesteps,
                    generated_rows, prepare_reference_image)
from .ref2va_conditioning import ImagePresentation, qwen_vision_features, load_native_image_vae, encode_image_latents
from .sparse import sparse_calls


def checksum(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def sample_vision_frames(frames):
    indices = list(range(0, len(frames), 12))
    times = [index / 2 for index in range(len(indices))]
    if len(times) % 2:
        times.append(times[-1])
    return frames[indices], [(times[i] + times[i + 1]) / 2 for i in range(0, len(times), 2)]


def presentation(tokenizer, prompt, references):
    """Build labels, visual blocks, and Qwen MRoPE in packed reference order."""
    control = {name: tokenizer.convert_tokens_to_ids(f"<|{name}|>") for name in
               ("vision_start", "vision_end", "image_pad", "video_pad")}
    if any(v is None for v in control.values()) or len(set(control.values())) != 4:
        raise ValueError("Missing distinct Qwen image/video control tokens.")
    ids, tags, masks, positions = [], [], [], []
    offset = 0

    def tokens(values, tag=1):
        nonlocal offset
        ids.extend(values); tags.extend([tag] * len(values)); masks.extend([False] * len(values))
        positions.append(np.tile(np.arange(len(values), dtype=np.int64) + offset, (3, 1)))
        offset += len(values)

    def text(value):
        values = list(tokenizer(value, add_special_tokens=False)["input_ids"])
        if any(v in control.values() for v in values):
            raise ValueError("Literal vision control tokens cannot occur in prompt text.")
        tokens(values)

    def vision(kind, grid):
        nonlocal offset
        _, height, width = map(int, grid)
        if height <= 0 or width <= 0 or height % 2 or width % 2:
            raise ValueError("Vision grid must be positive and divisible by merge size 2.")
        height //= 2; width //= 2
        tokens([control["vision_start"]], 0)
        coords = np.indices((1, height, width), dtype=np.int64).reshape(3, -1)
        count = height * width
        ids.extend([control[f"{kind}_pad"]] * count)
        tags.extend([0] * count); masks.extend([True] * count)
        positions.append(coords + offset)
        offset += max(height, width)
        tokens([control["vision_end"]], 0)

    counts = dict(image=0, video=0, audio=0)
    for ref in references:
        kind = ref["kind"]
        if ref.get("waveform") is not None:
            counts["audio"] += 1
            text(f'<Audio {counts["audio"]}>: ')
        if kind == "image":
            counts["image"] += 1
            text(f'<Picture {counts["image"]}>: ')
            vision("image", ref["grid"])
        elif kind == "video":
            counts["video"] += 1
            text(f'<Video {counts["video"]}>: ')
            if int(ref["grid"][0]) != len(ref["timestamps"]):
                raise ValueError("Video grid and timestamp block counts disagree.")
            for timestamp in ref["timestamps"]:
                text(f"<{timestamp:.1f} seconds>")
                vision("video", ref["grid"])
    text(prompt)
    return ImagePresentation(np.asarray(ids, dtype=np.int64), np.asarray(tags, dtype=np.int64),
                             np.concatenate(positions, axis=1), np.asarray(masks, dtype=np.bool_))


def decode_waveform(path, duration):
    result = subprocess.run([tool("ffmpeg"), "-v", "error", "-i", str(path), "-t", str(duration),
                             "-map", "0:a:0", "-ac", "2", "-ar", "32000", "-f", "f32le", "-"],
                            capture_output=True, check=True, timeout=60)
    samples = np.frombuffer(result.stdout, dtype="<f4")
    if not samples.size or samples.size % 2 or not np.isfinite(samples).all():
        raise ValueError("Reference audio must decode to finite, nonempty stereo samples.")
    return samples.reshape(-1, 2).T.copy()


def prepare_references(options, model_frames):
    references = []
    for path in options.get("image_paths", []):
        with Image.open(path) as image:
            references.append(dict(kind="image", image=prepare_reference_image(image, options["pixel_budget"])))
    duration = model_frames / 24
    # Keep explicitly numbered Audio inputs ahead of implicit video soundtracks.
    for path in options.get("audio_paths", []):
        probe_reference(path, "audio")
        references.append(dict(kind="audio", waveform=decode_waveform(path, duration)))
    for path in options.get("video_paths", []):
        probe = probe_reference(path, "videos")
        video = next(s for s in probe["streams"] if s["codec_type"] == "video")
        source_width, source_height = video["width"], video["height"]
        # FFmpeg applies the display-matrix rotation before the scale filter.
        rotations = [s["rotation"] for s in video.get("side_data_list", []) if "rotation" in s]
        if rotations and int(rotations[0]) % 180:
            source_width, source_height = source_height, source_width
        height, width = reference_video_size(source_width, source_height)
        result = subprocess.run([tool("ffmpeg"), "-v", "error", "-i", str(path), "-t", str(duration),
            "-map", "0:v:0", "-vf", f"fps=24,scale={width}:{height}:flags=lanczos", "-frames:v", str(model_frames),
            "-pix_fmt", "rgb24", "-f", "rawvideo", "-"], capture_output=True, check=True, timeout=120)
        frames = np.frombuffer(result.stdout, dtype=np.uint8).reshape(-1, height, width, 3)
        if len(frames) < 5:
            raise ValueError("A video reference needs at least five decoded frames.")
        ref = dict(kind="video", frames=frames)
        if options.get("video_audio", True) and any(s["codec_type"] == "audio" for s in probe["streams"]):
            ref["waveform"] = decode_waveform(path, duration)
        references.append(ref)
    if not references or len(references) > 12:
        raise ValueError("Mixed reference generation needs 1–12 references.")
    return references


def encode_video(vae, frames):
    """Native 17/5 temporal chunking with the native 256/64 spatial tiling."""
    import torch
    count = (len(frames) - 5) // 17 * 17 + 5
    frames = frames[:count]
    padding = (-count) % 17
    if padding:
        frames = np.concatenate([frames, np.repeat(frames[-1:], padding, axis=0)])
    height, width = frames.shape[1:3]
    ys, heights, yo = vae._split_tiles(height, 256, 64)
    xs, widths, xo = vae._split_tiles(width, 256, 64)
    moments = []
    for start in range(0, len(frames), 17):
        pixels = frames[start:start + 17].astype(np.float32).transpose(3, 0, 1, 2)[None] / 255
        pixels = vae.normalize_pixels(mx.array(pixels))
        rows = []
        for y, h in zip(ys, heights, strict=True):
            row = []
            for x, w in zip(xs, widths, strict=True):
                encoded = vae._encode_clip(pixels[..., y:y+h, x:x+w])
                mx.eval(encoded)
                row.append(encoded)
            rows.append(row)
        encoded = vae._stitch_tiles(rows, [v // 16 for v in yo], [v // 16 for v in xo])
        mx.eval(encoded)
        moments.append(np.asarray(encoded))
        del rows, row, encoded, pixels
        mx.clear_cache()
    moments = np.concatenate(moments, axis=2)[:, :, :-vae.config.token_drop]
    mean, logvar = np.split(moments, 2, axis=1)
    noise = torch.randn(tuple(mean.shape), generator=torch.Generator("cpu").manual_seed(42), dtype=torch.float32).numpy()
    sampled = vae.sample_posterior(mx.array(mean), mx.array(np.clip(logvar, -30, 20)), mx.array(noise))
    latents = vae.normalize_latents(sampled.astype(mx.float16).astype(mx.float32))
    mx.eval(latents)
    expected = (count - 5) // 17 * 5 + 2
    if latents.shape[2] != expected:
        raise ValueError("Reference video encoder violated native temporal geometry.")
    return np.asarray(latents)


def encode_references(native, audio_vae_dir, references, prompt, observer):
    import torch
    from transformers import AutoProcessor
    processor = AutoProcessor.from_pretrained(str(native / "processor"), local_files_only=True)
    pixels, grids = [], []
    for ref in references:
        if ref["kind"] == "image":
            vision = processor.image_processor(images=[ref["image"]], return_tensors="pt")
            pixel, grid = vision["pixel_values"], vision["image_grid_thw"]
            expected = ref["image"].size
        elif ref["kind"] == "video":
            sampled, ref["timestamps"] = sample_vision_frames(ref["frames"])
            vision = processor.video_processor(videos=[sampled], do_sample_frames=False, return_tensors="pt")
            pixel, grid = vision["pixel_values_videos"], vision["video_grid_thw"]
            expected = (ref["frames"].shape[2], ref["frames"].shape[1])
        else:
            continue
        ref["grid"] = grid[0].numpy()
        if tuple((grid[0, [2, 1]] * 16).tolist()) != expected:
            raise ValueError("Qwen resized prepared reference pixels a second time.")
        pixels.append(pixel); grids.append(grid)
    features, deepstack = qwen_vision_features(native / "text_encoder", torch.cat(pixels), torch.cat(grids))
    conditioner = StreamedMiniMaxH3TextConditioner(native / "text_encoder", native / "tokenizer")
    try:
        encoded_prompt = presentation(conditioner.tokenizer, prompt, references)
        if int(encoded_prompt.visual_mask.sum()) != len(features):
            raise ValueError("Visual features and prompt pad tokens disagree.")
        text, tags = conditioner.encode_presentation(encoded_prompt.token_ids, encoded_prompt.tags,
            encoded_prompt.positions, visual_features=features, visual_mask=encoded_prompt.visual_mask,
            deepstack_features=deepstack)
    finally:
        conditioner.close()
    del conditioner, features, deepstack, pixels, grids, processor
    gc.collect(); mx.clear_cache()
    vae = load_native_image_vae(native / "video_vae")
    visual_rows, audio_rows, metadata = [], [], []
    audio_index = 0
    for ref in references:
        item = dict(kind=ref["kind"])
        if ref.get("waveform") is not None:
            audio_index += 1
            item.update(audio_index=audio_index, audio_samples=ref["waveform"].shape[1],
                        audio_sample_rate=32000, audio_source="video_soundtrack" if ref["kind"] == "video" else "standalone")
        if ref["kind"] == "image":
            item["prepared_width_height"] = list(ref["image"].size)
        elif ref["kind"] == "video":
            count, height, width, _ = ref["frames"].shape
            item.update(prepared_width_height=[width, height], decoded_frames=count,
                qwen_frame_indices=list(range(0, count, 12)),
                vae_retained_frames=(count - 5) // 17 * 17 + 5)
        if ref["kind"] != "audio":
            latents = encode_image_latents(vae, ref["image"]) if ref["kind"] == "image" else encode_video(vae, ref["frames"])
            ref["latent_geometry"] = tuple(latents.shape[2:])
            rows = patchify_video_latents(latents, (1, 2, 2))
            visual_rows.append(rows)
            item.update(visual_rows=len(rows), visual_latents_sha256=checksum(rows),
                prepared_pixels_sha256=checksum(np.asarray(ref["image"]) if ref["kind"] == "image" else ref["frames"]))
        metadata.append(item)
    del vae
    gc.collect(); mx.clear_cache()
    if any(r.get("waveform") is not None for r in references):
        audio_vae = mlx_h3_audio_vae_from_dir(audio_vae_dir, include_encoder=True)
        for ref, item in zip(references, metadata, strict=True):
            if ref.get("waveform") is None:
                continue
            mean, _ = audio_vae.encode(mx.array(ref["waveform"][:, None]))
            normalized = audio_vae.normalize_latents(mean)
            mx.eval(normalized)
            ref["audio_latents"] = normalized.shape[-1]
            rows = np.asarray(normalized).transpose(0, 2, 1).reshape(-1, 32).copy()
            audio_rows.append(rows)
            item.update(audio_rows=len(rows), audio_latents_sha256=checksum(rows),
                        waveform_sha256=checksum(ref["waveform"]))
        del audio_vae
    visual = np.concatenate(visual_rows) if visual_rows else np.empty((0, 96), np.float32)
    audio = np.concatenate(audio_rows) if audio_rows else np.empty((0, 32), np.float32)
    geometries = [ReferenceGeometry(r["kind"], *r.get("latent_geometry", (0, 0, 0)),
                    has_audio=r.get("waveform") is not None, num_audio_latents=r.get("audio_latents", 0)) for r in references]
    observer.capture("reference-inputs", lambda: dict(text=text, tags=tags, reference_video=visual,
        reference_audio=audio, token_ids=encoded_prompt.token_ids, positions=encoded_prompt.positions))
    return text, tags, visual, audio, geometries, metadata


def mixed_noise(reference_video, layout, seed):
    streams = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(3)]
    noise = streams[0].standard_normal(reference_video.shape, dtype=np.float32)
    fixed = np.float32(.999) * reference_video + np.float32(.001) * noise
    video = streams[1].standard_normal((len(layout.video_indices) - layout.num_condition_video_rows, 96), dtype=np.float32)
    audio = streams[2].standard_normal((len(layout.audio_indices) - layout.num_condition_audio_rows, 32), dtype=np.float32)
    return fixed, video, audio


def sample_mixed(dit, text, fixed_video, fixed_audio, layout, video, audio, observer):
    generated_rows(np.concatenate([fixed_video, video]), np.concatenate([fixed_audio, audio]), layout)
    if (text.shape != (len(layout.text_indices), 5120)
            or fixed_video.shape != (layout.num_condition_video_rows, 96)
            or fixed_audio.shape != (layout.num_condition_audio_rows, 32)
            or not all(np.isfinite(x).all() for x in (text, fixed_video, fixed_audio, video, audio))):
        raise ValueError("Mixed-reference sampling inputs do not match their finite packed layout.")
    video_solver, audio_solver = MiniMaxH3SchedulerState.create(12, 4), MiniMaxH3SchedulerState.create(3, 4)
    schedule = [build_ref2va_timesteps(layout, float(v), float(a)) for v, a in
                zip(video_solver.timesteps, audio_solver.timesteps, strict=True)]
    union = np.unique(np.concatenate([t for t, _ in schedule]))
    cache = getattr(dit, "_adaln_cache", None)
    if cache is None:
        dit.precompute_adaln(union)
    elif not all(np.any(np.isclose(t, cache.timesteps, rtol=0, atol=1e-6)) for t in union):
        raise ValueError("Checkpoint lacks mixed-reference timestep embeddings.")
    dit.on_block = observer.block
    x_v, x_a, fixed_v, fixed_a, text = map(mx.array, (video, audio, fixed_video, fixed_audio, text))
    for index, (times, inverse) in enumerate(schedule):
        packed_v, packed_a = mx.concatenate([fixed_v, x_v]), mx.concatenate([fixed_a, x_a])
        velocity_v, velocity_a = dit.forward_with_cache(packed_v, packed_a, text, layout=layout,
            step_timesteps=times, row_timestep_inverse=inverse, step_index=index)
        mx.eval(velocity_v, velocity_a)
        if not all(bool(mx.all(mx.isfinite(x))) for x in (velocity_v, velocity_a)):
            raise ValueError("Nonfinite mixed-reference velocity.")
        observer.step(index, packed_v, packed_a, velocity_v, velocity_a)
        velocity_v, velocity_a = generated_rows(velocity_v, velocity_a, layout)
        x_v, x_a = video_solver.step(velocity_v, index, x_v), audio_solver.step(velocity_a, index, x_a)
        mx.eval(x_v, x_a)
        if not all(bool(mx.all(mx.isfinite(x))) for x in (x_v, x_a)):
            raise ValueError("Nonfinite mixed-reference solver state.")
    return np.asarray(x_v), np.asarray(x_a)


def prepare_conditioning(request, options, observer):
    """Create the exact condition and initial state shared by a paired run."""
    references = prepare_references(options, request["model_num_frames"])
    encoded = encode_references(Path(options["native_root"]),
        options["audio_vae"], references, request["prompt"], observer)
    text, tags, visual, fixed_audio, geometries, ref_metadata = encoded
    geometry = MiniMaxH3MLXPipeline.resolve_geometry(request["model_height"], request["model_width"], request["model_num_frames"])
    layout = build_ref2va_layout(tags, geometries, geometry["latent_frame_count"], geometry["latent_height"],
        geometry["latent_width"], audio_latent_num_frames(request["model_num_frames"]))
    fixed_video, video, audio = mixed_noise(visual, layout, request["seed"])
    metadata = dict(task="ref2va", reference_segments=ref_metadata,
        reference_resize=options.get("reference_resize", "legacy"), pixel_budget=options["pixel_budget"],
        video_reference_canvas=dict(VIDEO_REFERENCE_CANVAS),
        reference_geometries=[asdict(g) for g in geometries],
        sequence_length=layout.sequence_length, prefix_segments=list(layout.reference_prefix_segments),
        reference_video_rows=layout.num_condition_video_rows, reference_audio_rows=layout.num_condition_audio_rows,
        text_sha256=checksum(text), reference_video_sha256=checksum(visual), reference_audio_sha256=checksum(fixed_audio),
        fixed_video_sha256=checksum(fixed_video), initial_video_sha256=checksum(video),
        initial_audio_sha256=checksum(audio),
        reference_video_audio=options.get("video_audio", True),
        audio_numbering="Standalone audio before video soundtracks; each list preserves its supplied order.",
        resampling="FFmpeg: 24 fps RGB with Lanczos scaling; 32 kHz stereo audio")
    del references, encoded, visual
    gc.collect(); mx.clear_cache()
    return dict(text=text, tags=tags, fixed_video=fixed_video, fixed_audio=fixed_audio,
                initial_video=video, initial_audio=audio), metadata


def condition_and_denoise(request, options, checkpoint, observer, phase):
    attention = options.get("attention")
    if request["num_steps"] != 4 or attention not in ("dense", "vsa"):
        raise ValueError("Audio/video references require four-step Ref2VA dense or vsa attention.")
    recipe = json.loads((Path(checkpoint) / "ref2va_recipe.json").read_text())
    expected = dict(schema="h3-apple-ref2va/v1", task="ref2va", lora_tensors=624,
                    lora_rank=128, lora_alpha=8, gate_tensors=50, fasth3_t2va_deltas_applied=False)
    if any(recipe.get(k) != v for k, v in expected.items()):
        raise ValueError("Expected the dedicated Ref2VA checkpoint with gate-only transplant.")

    def condition():
        if options.get("conditioning_cache") is None:
            return prepare_conditioning(request, options, observer)
        from .reference_cache import cache_contract, load_or_build
        return load_or_build(options["conditioning_cache"], cache_contract(request, options),
                             lambda: prepare_conditioning(request, options, observer))

    arrays, metadata = phase("conditioning", condition)
    if set(arrays) != {"text", "tags", "fixed_video", "fixed_audio", "initial_video", "initial_audio"}:
        raise ValueError("Incomplete mixed-reference conditioning snapshot.")
    metadata["attention"] = attention
    geometry = MiniMaxH3MLXPipeline.resolve_geometry(request["model_height"], request["model_width"], request["model_num_frames"])
    layout = build_ref2va_layout(arrays["tags"],
        [ReferenceGeometry(**g) for g in metadata["reference_geometries"]],
        geometry["latent_frame_count"], geometry["latent_height"], geometry["latent_width"],
        audio_latent_num_frames(request["model_num_frames"]))
    if (list(layout.reference_prefix_segments) != metadata["prefix_segments"]
            or layout.sequence_length != metadata["sequence_length"]):
        raise ValueError("Conditioning cache geometry mismatch.")

    def denoise():
        dit = load_mlx_h3_checkpoint(checkpoint)
        if not dit.vsa_capable or len(dit.blocks) != 50:
            raise ValueError("Expected the dedicated Ref2VA checkpoint with all 50 transplanted gates.")
        dit.configure_vsa(MiniMaxH3VSAConfig(enabled=attention == "vsa", sparsity=.75,
            prefix_mode="exempt", impl="simd", routing_mode="kablex"))
        before = sparse_calls()
        result = sample_mixed(dit, arrays["text"], arrays["fixed_video"], arrays["fixed_audio"],
            layout, arrays["initial_video"], arrays["initial_audio"], observer)
        stats = asdict(dit.last_vsa_stats) if dit.last_vsa_stats is not None else None
        calls = sparse_calls() - before
        if (observer.nfe, observer.blocks) != (4, 200):
            raise ValueError("Expected exactly four complete mixed-reference forwards.")
        if attention == "vsa":
            if calls != 200 or stats is None or stats["fallback_reasons"] or stats["sparse_calls"] != 200:
                raise ValueError("Mixed reference generation did not use exactly 200 native VSA blocks.")
        elif calls or stats is not None or dit.vsa_config.enabled:
            raise ValueError("Dense mixed-reference generation unexpectedly used VSA.")
        return *result, stats

    video, audio, stats = phase("denoise", denoise)
    return video, audio, metadata, stats
