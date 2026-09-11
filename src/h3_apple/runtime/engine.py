"""The single Ours generation chain, with explicit owned runtime components."""

from importlib.resources import files
from pathlib import Path
import time

import mlx.core as mx
import numpy as np

from h3_apple._vendor.fastvideo_mlx import minimax_h3_pipeline as upstream
from h3_apple._vendor.fastvideo_mlx.minimax_h3_video_vae import mlx_h3_video_vae_from_dir
from h3_apple._vendor.fastvideo_mlx.minimax_h3_vsa import MiniMaxH3VSAConfig
from .observer import Observer
from .sparse import sparse_calls
from .vae import OptimizedVideoVAE


class Pipeline(upstream.MiniMaxH3MLXPipeline):
    def _load_video_vae(self):
        base = mlx_h3_video_vae_from_dir(self.model_root / "vae", include_encoder=False,
                                        storage_dtype="fp32")
        asset = files("h3_apple").joinpath("data/vae-calibration.npz")
        with asset.open("rb") as stream, np.load(stream) as data:
            calibration = {key: data[key].copy() for key in data.files}
        return OptimizedVideoVAE(base, calibration, self.observer)


def run(request, assets, output_path, emit, diagnostics_dir=None):
    observer = Observer(emit, diagnostics_dir)
    timings = {}
    peaks = {}
    mx.set_memory_limit(80 * 1024**3)
    mx.set_cache_limit(0)
    mx.set_wired_limit(min(48 * 1024**3, mx.device_info()["max_recommended_working_set_size"]))
    pipeline = Pipeline(model_root=assets["components"], mlx_dit_checkpoint=assets["checkpoint"],
                        vae_dtype="fp32", metal_wired_limit_gib=80,
                        prompt_cache_dir=None, observer=observer)

    def phase(name, function):
        emit({"phase": name})
        mx.reset_peak_memory()
        start = time.monotonic()
        value = function()
        timings[name] = time.monotonic() - start
        peaks[name] = mx.get_peak_memory() / 1024**3
        return value

    text, tags = phase("conditioning", lambda: pipeline.encode_prompt(request["prompt"]))
    if not np.isfinite(text).all():
        raise ValueError("Nonfinite conditioning.")
    observer.capture("conditioning", lambda: {"text": text, "tags": tags})
    geometry = dict(height=request["model_height"], width=request["model_width"],
                    num_frames=request["model_num_frames"])
    video, audio = phase("denoise", lambda: pipeline.denoise(
        text, tags, **geometry, seed=request["seed"], num_steps=request["num_steps"],
        vsa_config=MiniMaxH3VSAConfig(enabled=True, impl="simd")))
    if not np.isfinite(video).all() or not np.isfinite(audio).all():
        raise ValueError("Nonfinite final latents.")
    observer.capture("latents", lambda: {"video": video, "audio": audio})
    stats = pipeline.last_vsa_stats
    if (observer.nfe != 4 or observer.blocks != 200 or sparse_calls() != 200
            or stats is None or stats["fallback_reasons"] or stats["sparse_calls"] != 200):
        raise ValueError("Expected four complete VSA forwards without fallback.")
    frames = phase("video_decode", lambda: pipeline.decode_video(video, **geometry))
    waveform = phase("audio_decode", lambda: pipeline.decode_audio(
        audio, num_frames=request["model_num_frames"]))
    if not np.isfinite(waveform).all() or waveform.shape[0] != 2:
        raise ValueError("Audio must be finite and stereo.")
    if frames.shape != (request["model_num_frames"], request["model_height"],
                        request["model_width"], 3):
        raise ValueError("Unexpected decoded video geometry.")
    observer.capture("audio", lambda: {"waveform": waveform})
    left = (request["model_width"] - request["width"]) // 2
    frames = frames[:request["num_frames"], :, left:left + request["width"]]
    samples = request["num_frames"] * request["audio_sample_rate"] // request["fps"]
    if waveform.shape[-1] < samples:
        raise ValueError("Generated audio does not cover the delivery duration.")
    waveform = waveform[:, :samples]
    audio_rms = float(np.sqrt(np.mean(waveform.astype(np.float64) ** 2)))
    video_std = float(frames.std())
    if audio_rms <= 1e-6 or video_std <= 0:
        raise ValueError("Generated audio is silent or video is constant.")
    phase("mux", lambda: pipeline.mux(frames, waveform, Path(output_path)))
    return dict(timings_seconds=timings, peak_memory_gib=peaks, actual_nfe=observer.nfe,
                video_tiles=observer.tiles, vsa=stats, sparse_implementation="direct_nax",
                diagnostic_export_seconds=observer.export_seconds,
                diagnostics_enabled=diagnostics_dir is not None,
                audio_rms=audio_rms, video_std=video_std)
