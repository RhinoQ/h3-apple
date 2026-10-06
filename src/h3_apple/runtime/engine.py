"""VSA generation: original LightX2V, W8A8 projections and INT8 QK."""

from importlib.resources import files
from pathlib import Path
import time

import mlx.core as mx
import numpy as np

from h3_apple._vendor.fastvideo_mlx import minimax_h3_pipeline as upstream
from h3_apple._vendor.fastvideo_mlx.minimax_h3_video_vae import mlx_h3_video_vae_from_dir
from .observer import Observer
from .vae import OptimizedVideoVAE


class Pipeline(upstream.MiniMaxH3MLXPipeline):
    def _load_video_vae(self):
        if getattr(self, "x2_checkpoint", None) is not None:
            from .x2_vae import load_x2
            return load_x2(self.x2_checkpoint, observer=self.observer)
        base = mlx_h3_video_vae_from_dir(self.model_root / "vae", include_encoder=False,
                                        storage_dtype="fp32")
        asset = files("h3_apple").joinpath("data/vae-calibration.npz")
        with asset.open("rb") as stream, np.load(stream) as data:
            calibration = {key: data[key].copy() for key in data.files}
        return OptimizedVideoVAE(base, calibration, self.observer)


def delivery_frames(frames, request):
    """Trim time and alignment padding; X2 pixels are never resized."""
    scale = 2 if request.get("x2", False) else 1
    height, width = request["model_height"] * scale, request["model_width"] * scale
    if frames.shape != (request["model_num_frames"], height, width, 3):
        raise ValueError("Unexpected decoded video geometry.")
    left = (width - request["width"]) // 2
    top = (height - request["height"]) // 2
    if min(left, top) < 0:
        raise ValueError("Delivery cannot exceed the decoded canvas.")
    return frames[:request["num_frames"], top:top + request["height"], left:left + request["width"]]


def run(request, assets, output_path, emit, diagnostics_dir=None, *, ref2va=None):
    observer = Observer(emit, diagnostics_dir)
    timings = {}
    peaks = {}
    mx.set_memory_limit(80 * 1024**3)
    mx.set_cache_limit(4 * 1024**3)
    mx.set_wired_limit(min(48 * 1024**3, mx.device_info()["max_recommended_working_set_size"]))
    pipeline = Pipeline(model_root=assets["components"], mlx_dit_checkpoint=assets["checkpoint"],
                        vae_dtype="fp32", metal_wired_limit_gib=80,
                        prompt_cache_dir=None, observer=observer)
    pipeline.x2_checkpoint = assets["x2"]["checkpoint"] if request.get("x2", False) else None

    def phase(name, function):
        emit({"phase": name})
        mx.reset_peak_memory()
        start = time.monotonic()
        value = function()
        timings[name] = time.monotonic() - start
        peaks[name] = mx.get_peak_memory() / 1024**3
        return value

    geometry = dict(height=request["model_height"], width=request["model_width"],
                    num_frames=request["model_num_frames"])
    from .ref2va_pipeline import condition_and_denoise
    video, audio, reference_metadata, stats = condition_and_denoise(
        request, ref2va, assets["checkpoint"], observer, phase)
    if not np.isfinite(video).all() or not np.isfinite(audio).all():
        raise ValueError("Nonfinite final latents.")
    observer.capture("latents", lambda: {"video": video, "audio": audio})
    frames = phase("video_decode", lambda: pipeline.decode_video(video, **geometry))
    waveform = phase("audio_decode", lambda: pipeline.decode_audio(
        audio, num_frames=request["model_num_frames"]))
    if not np.isfinite(waveform).all() or waveform.shape[0] != 2:
        raise ValueError("Audio must be finite and stereo.")
    observer.capture("audio", lambda: {"waveform": waveform})
    frames = delivery_frames(frames, request)
    samples = (request["num_frames"] * request["audio_sample_rate"] + request["fps"] - 1) // request["fps"]
    if waveform.shape[-1] < samples:
        raise ValueError("Generated audio does not cover the delivery duration.")
    waveform = waveform[:, :samples]
    audio_rms = float(np.sqrt(np.mean(waveform.astype(np.float64) ** 2)))
    video_std = float(frames.std())
    if audio_rms <= 1e-6 or video_std <= 0:
        raise ValueError("Generated audio is silent or video is constant.")
    phase("mux", lambda: pipeline.mux(frames, waveform, Path(output_path)))
    result = dict(timings_seconds=timings, peak_memory_gib=peaks, actual_nfe=observer.nfe,
                video_tiles=observer.tiles, vsa=stats, sparse_implementation="direct_nax",
                diagnostic_export_seconds=observer.export_seconds,
                diagnostics_enabled=diagnostics_dir is not None,
                audio_rms=audio_rms, video_std=video_std)
    if reference_metadata is not None:
        result["ref2va"] = reference_metadata
        if reference_metadata["attention"] == "dense":
            result["sparse_implementation"] = None
    return result
