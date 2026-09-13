"""Four-step image-conditioned sampling with immutable reference prefixes."""

import mlx.core as mx
import numpy as np

from .._vendor.fastvideo_mlx.minimax_h3 import MiniMaxH3SchedulerState
from .ref2va import build_ref2va_timesteps, generated_rows


def image_noise(reference_rows, layout, seed):
    """Independent PCG64 streams keep reference/audio noise fixed across canvases.

    These are reproducible local seeds, not a claim of Torch/CUDA RNG identity.
    """
    if type(seed) is not int or seed < 0:
        raise ValueError("Seed must be a nonnegative integer.")
    streams = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(3)]
    reference_rows = np.asarray(reference_rows, dtype=np.float32)
    noise = streams[0].standard_normal(reference_rows.shape, dtype=np.float32)
    condition = np.float32(.999) * reference_rows + np.float32(.001) * noise
    video = streams[1].standard_normal((len(layout.video_indices) - layout.num_condition_video_rows, 96), dtype=np.float32)
    audio = streams[2].standard_normal((len(layout.audio_indices), 32), dtype=np.float32)
    return condition, video, audio


def sample_image(dit, text_rows, condition_rows, layout, initial_video, initial_audio, *, observer=None):
    """Return only generated rows. The reference prefix never enters the solver."""
    if layout.num_condition_audio_rows or not layout.num_condition_video_rows:
        raise ValueError("This sampler supports image references only.")
    text = np.asarray(text_rows, dtype=np.float32)
    condition = np.asarray(condition_rows, dtype=np.float32)
    video, audio = np.asarray(initial_video, dtype=np.float32), np.asarray(initial_audio, dtype=np.float32)
    if condition.shape != (layout.num_condition_video_rows, 96) or text.shape != (len(layout.text_indices), 5120):
        raise ValueError("Conditioning does not match the packed layout.")
    generated_rows(np.concatenate([condition, video]), audio, layout)
    if not all(np.isfinite(x).all() for x in (text, condition, video, audio)):
        raise ValueError("Sampling inputs must be finite.")
    if dit.vsa_config.enabled and (not getattr(dit, "vsa_capable", False)
            or not getattr(dit.vsa_config, "exempt", False)
            or not getattr(layout, "reference_prefix_segments", ())):
        raise ValueError("Ref2VA VSA requires trained gates and explicit dense-exempt reference segments.")
    video_solver = MiniMaxH3SchedulerState.create(12, 4)
    audio_solver = MiniMaxH3SchedulerState.create(3, 4)
    schedule = [build_ref2va_timesteps(layout, float(v), float(a))
                for v, a in zip(video_solver.timesteps, audio_solver.timesteps, strict=True)]
    union = np.unique(np.concatenate([times for times, _ in schedule]))
    cache = getattr(dit, "_adaln_cache", None)
    if cache is None:
        dit.precompute_adaln(union)
    elif not all(np.any(np.isclose(t, cache.timesteps, rtol=0, atol=1e-6)) for t in union):
        raise ValueError("Prepared Ref2VA checkpoint is missing required cached timesteps.")
    if observer is not None:
        dit.on_block = observer.block
        observer.capture("initial-inputs", lambda: dict(video=video, audio=audio, condition=condition, text=text))
    x_v, x_a, fixed, text = [mx.array(x) for x in (video, audio, condition, text)]
    for index, (times, inverse) in enumerate(schedule):
        packed_video = mx.concatenate([fixed, x_v])
        velocity_v, velocity_a = dit.forward_with_cache(packed_video, x_a, text, layout=layout,
            step_timesteps=times, row_timestep_inverse=inverse, step_index=index)
        mx.eval(velocity_v, velocity_a)
        if not all(bool(mx.all(mx.isfinite(x))) for x in (velocity_v, velocity_a)):
            raise ValueError(f"Nonfinite Ref2VA velocity at step {index}.")
        if observer is not None:
            observer.step(index, packed_video, x_a, velocity_v, velocity_a)
        velocity_v, velocity_a = generated_rows(velocity_v, velocity_a, layout)
        x_v = video_solver.step(velocity_v, index, x_v)
        x_a = audio_solver.step(velocity_a, index, x_a)
        mx.eval(x_v, x_a)
        if not all(bool(mx.all(mx.isfinite(x))) for x in (x_v, x_a)):
            raise ValueError(f"Nonfinite Ref2VA state at step {index}.")
    return np.array(x_v), np.array(x_a)
