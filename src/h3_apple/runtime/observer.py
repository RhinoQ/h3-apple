"""Cheap progress and optional, lazy numerical exports for research."""

from pathlib import Path
import time


class Observer:
    def __init__(self, emit, directory=None):
        self.emit = emit
        self.directory = Path(directory) if directory is not None else None
        if self.directory is not None:
            self.directory.mkdir(parents=True, exist_ok=False)
        self.nfe = 0
        self.blocks = 0
        self.tiles = 0
        self.export_seconds = 0.0

    def capture(self, name, build_arrays):
        if self.directory is None:
            return
        import numpy as np
        started = time.monotonic()
        with (self.directory / f"{name}.npz").open("xb") as stream:
            np.savez(stream, **build_arrays())
        self.export_seconds += time.monotonic() - started

    def block(self, step, index, total):
        import mlx.core as mx
        self.blocks += 1
        if mx.get_peak_memory() > 80 * 1024**3:
            raise RuntimeError("MLX peak memory exceeded 80 GiB.")
        if index % 10 == 0 or index == total:
            self.emit({"phase": "denoise", "step": step + 1, "steps": 4,
                       "block": index, "blocks": total})

    def step(self, index, video, audio, video_velocity, audio_velocity):
        import mlx.core as mx
        import numpy as np
        if index != self.nfe:
            raise ValueError("Unexpected denoising step order.")
        if not all(bool(mx.all(mx.isfinite(x)).item()) for x in (video_velocity, audio_velocity)):
            raise ValueError(f"Nonfinite DiT output at step {index}.")
        self.capture(f"step-{index}", lambda: {
            "video_state": np.asarray(video.astype(mx.float32)),
            "audio_state": np.asarray(audio.astype(mx.float32)),
            "video_velocity": np.asarray(video_velocity.astype(mx.float32)),
            "audio_velocity": np.asarray(audio_velocity.astype(mx.float32)),
        })
        self.nfe += 1

    def tile(self):
        self.tiles += 1
        if self.tiles % 20 == 0 or self.tiles == 1:
            self.emit({"phase": "video_decode", "tiles_completed": self.tiles})
