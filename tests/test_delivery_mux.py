"""Exercise delivery trimming and real FFmpeg muxing without model inference."""
import os
from pathlib import Path
import sys

import numpy as np
import pytest

from h3_apple.media import validate
from h3_apple.runtime import engine, ref2va_pipeline


@pytest.mark.parametrize("count", [120, 157, 158, 243])
@pytest.mark.parametrize("canvas", [(64, 64, 64, 64), (96, 64, 106, 64), (64, 96, 64, 106)])
def test_delivery_keeps_every_frame_at_fractional_audio_sample_boundary(tmp_path, monkeypatch, count, canvas):
    model_count = ((count - 5 + 16) // 17) * 17 + 5
    width, height, model_width, model_height = canvas
    request = dict(prompt="synthetic media fixture", task="ref2va", seed=1, num_steps=4,
        model_height=model_height, model_width=model_width, model_num_frames=model_count,
        height=height, width=width, num_frames=count, fps=24,
        audio_sample_rate=32000, audio_channels=2)
    values = (np.arange(model_count)[:, None, None, None]
              + np.arange(model_height)[None, :, None, None]
              + np.arange(model_width)[None, None, :, None]) % 256
    decoded = np.broadcast_to(values, (model_count, model_height, model_width, 3)).astype(np.uint8)
    received = []

    class DecodedFixture:
        def mux(self, frames, waveform, path):
            received.append(frames.copy())
            return engine.upstream.MiniMaxH3MLXPipeline.mux(self, frames, waveform, path)

        def __init__(self, **kwargs):
            pass

        def decode_video(self, *_args, **_kwargs):
            return decoded

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
    top, left = (model_height-height)//2, (model_width-width)//2
    np.testing.assert_array_equal(received[0], decoded[:count, top:top+height, left:left+width])
