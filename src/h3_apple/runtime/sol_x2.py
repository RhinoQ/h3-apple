"""SOL normalized latent and lossless audio handoff to the shared X2 decoder."""

import hashlib
from pathlib import Path
import re
import subprocess
import time

import numpy as np

from ..io import digest
from ..media import probe, tool
from .._vendor.fastvideo_mlx.minimax_h3 import video_latent_num_frames


def read_latent(path, request, native_log):
    shape = (24, video_latent_num_frames(request["model_num_frames"]),
             request["model_height"] // 16, request["model_width"] // 16)
    matches = re.findall(r"dumped latent \[(\d+), (\d+), (\d+), (\d+)\] to ([^\r\n]+)", native_log)
    if len(matches) != 1 or tuple(map(int, matches[0][:4])) != shape or matches[0][4] != str(path):
        raise ValueError("SOL did not confirm the expected final latent export.")
    if Path(path).stat().st_size != int(np.prod(shape)) * 4:
        raise ValueError("SOL latent file size differs from the expected geometry.")
    value = np.fromfile(path, dtype="<f4").reshape(1, *shape)
    if not np.isfinite(value).all():
        raise ValueError("Nonfinite SOL video latent.")
    return value


def read_audio(path, request):
    data = probe(path)
    streams = data["streams"]
    if (len(streams) != 1 or streams[0]["codec_type"] != "audio"
            or streams[0]["codec_name"] != "pcm_f32le"
            or int(streams[0]["sample_rate"]) != request["audio_sample_rate"]
            or streams[0]["channels"] != 2):
        raise ValueError("SOL audio handoff must be lossless float32 stereo PCM.")
    raw = subprocess.check_output([tool("ffmpeg"), "-v", "error", "-xerror", "-nostdin",
        "-i", str(path), "-map", "0:a:0", "-f", "f32le", "-acodec", "pcm_f32le", "-"], timeout=120)
    if len(raw) % 8:
        raise ValueError("Truncated SOL stereo PCM.")
    waveform = np.frombuffer(raw, dtype="<f4").reshape(-1, 2).T.copy()
    samples = (request["num_frames"] * request["audio_sample_rate"] + request["fps"] - 1) // request["fps"]
    if waveform.shape[-1] < samples or not np.isfinite(waveform).all():
        raise ValueError("Invalid or insufficient SOL audio samples.")
    return waveform[:, :samples]


def finish(request, assets, workspace, native_log, emit, *, diagnostics=False):
    import mlx.core as mx
    from .backend import backend_identity
    from .engine import delivery_frames
    from .observer import Observer
    from .x2_vae import decode_latents
    from .._vendor.fastvideo_mlx.minimax_h3_pipeline import MiniMaxH3MLXPipeline

    mx.set_memory_limit(80 * 1024**3)
    mx.set_cache_limit(4 * 1024**3)
    mx.set_wired_limit(min(48 * 1024**3, mx.device_info()["max_recommended_working_set_size"]))
    decoder_backend = backend_identity()
    observer = Observer(emit, workspace / "diagnostics" if diagnostics else None)
    timings = {}

    def phase(name, function):
        emit(dict(phase=name)); start=time.monotonic()
        value=function(); timings[name]=time.monotonic()-start
        return value

    path=workspace / "video-latent.f32"
    latent=phase("latent_handoff", lambda: read_latent(path, request, native_log))
    frames=phase("video_decode", lambda: decode_latents(latent, assets["x2"]["checkpoint"],
        height=request["model_height"], width=request["model_width"],
        num_frames=request["model_num_frames"], observer=observer))
    frames=delivery_frames(frames, request)
    waveform=phase("audio_handoff", lambda: read_audio(workspace / "native.wav", request))
    rms=float(np.sqrt(np.mean(waveform.astype(np.float64)**2)))
    std=float(frames.std())
    if rms <= 1e-6 or std <= 0:
        raise ValueError("Generated audio is silent or video is constant.")
    phase("mux", lambda: MiniMaxH3MLXPipeline.mux(frames, waveform, workspace / "output.mp4",
        fps=request["fps"], sample_rate=request["audio_sample_rate"]))
    return dict(timings_seconds=timings, x2_backend=decoder_backend, video_tiles=observer.tiles,
        audio_rms=rms, video_std=std,
        sol_x2=dict(normalized_latent_shape=list(latent.shape), dtype="little-endian-float32",
            layout="NCTHW", video_latent_sha256=digest(path),
            delivered_pcm_sha256=hashlib.sha256(waveform.tobytes()).hexdigest(),
            native_video_decode_skipped=True, native_audio_codec="pcm_f32le"))
