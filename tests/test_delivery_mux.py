"""Exercise delivery trimming and real FFmpeg muxing without model inference."""
import os
from pathlib import Path
import sys

import numpy as np
import pytest

from h3_apple.media import validate
from h3_apple.runtime import engine, ref2va_pipeline


@pytest.mark.parametrize("count", [120, 157, 158, 243])
def test_delivery_keeps_every_frame_at_fractional_audio_sample_boundary(tmp_path, monkeypatch, count):
    model_count = ((count - 5 + 16) // 17) * 17 + 5
    request = dict(prompt="synthetic media fixture", seed=1, num_steps=4,
        model_height=64, model_width=64, model_num_frames=model_count,
        height=64, width=64, num_frames=count, fps=24,
        audio_sample_rate=32000, audio_channels=2)

    class DecodedFixture:
        mux = engine.upstream.MiniMaxH3MLXPipeline.mux

        def __init__(self, **kwargs):
            pass

        def decode_video(self, *_args, **_kwargs):
            values = np.arange(model_count, dtype=np.uint8)
            return np.broadcast_to(values[:, None, None, None], (model_count, 64, 64, 3)).copy()

        def decode_audio(self, *_args, **_kwargs):
            samples = (model_count * 32000 + 23) // 24
            wave = .1 * np.sin(np.arange(samples, dtype=np.float32) * (2 * np.pi * 440 / 32000))
            return np.stack([wave, wave])

    monkeypatch.setattr(engine, "Pipeline", DecodedFixture)
    monkeypatch.setattr(ref2va_pipeline, "condition_and_denoise", lambda *_args:
        (np.zeros(1), np.zeros(1), {"task": "ref2va", "attention": "vsa"}, None))
    for name in ("set_memory_limit", "set_cache_limit", "set_wired_limit", "reset_peak_memory"):
        monkeypatch.setattr(engine.mx, name, lambda *_args: None)
    monkeypatch.setattr(engine.mx, "device_info", lambda: {"max_recommended_working_set_size": 1024**3})
    monkeypatch.setattr(engine.mx, "get_peak_memory", lambda: 0)
    monkeypatch.setenv("PATH", str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"])
    output = tmp_path / "output.mp4"
    engine.run(request, {"components": str(tmp_path), "checkpoint": str(tmp_path)},
        output, lambda _event: None, ref2va={"task": "ref2va"})
    validate(output, request)
