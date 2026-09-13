"""Synthetic solver-boundary tests; trained trajectory admission is separate."""
from types import SimpleNamespace

import mlx.core as mx
import numpy as np
import pytest

from h3_apple.runtime.ref2va import ReferenceGeometry, build_ref2va_layout
from h3_apple.runtime.ref2va_sampling import image_noise, sample_image


def layout(width=6):
    return build_ref2va_layout([1, 0, 1], [ReferenceGeometry("image", 1, 4, 6)], 2, 4, width, 4)


class ConstantVelocity:
    vsa_config = SimpleNamespace(enabled=False)
    _adaln_cache = None

    def __init__(self):
        self.seen = []

    def precompute_adaln(self, times):
        self._adaln_cache = SimpleNamespace(timesteps=times)

    def forward_with_cache(self, video, audio, text, **kwargs):
        self.seen.append((np.array(video), np.array(audio)))
        # Huge reference velocities deliberately differ from generated rows.
        count = kwargs["layout"].num_condition_video_rows
        return mx.concatenate([mx.full((count, 96), 1e6), mx.full((len(video)-count, 96), 2.)]), mx.full(audio.shape, -3.)


def test_reference_never_updates_and_never_leaves_sampler():
    geometry = layout()
    ref = np.full((6, 96), 7, np.float32)
    initial = np.zeros((12, 96), np.float32), np.zeros((8, 32), np.float32)
    model = ConstantVelocity()
    v, a = sample_image(model, np.ones((3, 5120), np.float32), ref, geometry, *initial)
    assert len(model.seen) == 4
    for video, audio in model.seen:
        np.testing.assert_array_equal(video[:6], ref)
        assert video.shape == (18, 96) and audio.shape == (8, 32)
    assert v.shape == (12, 96) and a.shape == (8, 32)
    np.testing.assert_allclose(v, 2., atol=1e-6)
    np.testing.assert_allclose(a, -3., atol=1e-6)
    assert np.float32(.999) in model._adaln_cache.timesteps


def test_reference_and_audio_noise_are_independent_of_output_canvas():
    reference = np.ones((6, 96), np.float32)
    small = image_noise(reference, layout(6), 42)
    large = image_noise(reference, layout(12), 42)
    np.testing.assert_array_equal(small[0], large[0])
    np.testing.assert_array_equal(small[2], large[2])
    np.testing.assert_array_equal(small[1], large[1][:len(small[1])])


def test_four_reference_segments_are_fixed_in_order_across_all_steps():
    refs = [ReferenceGeometry("image", 1, h, w) for h, w in ((4, 6), (6, 4), (2, 2), (4, 4))]
    geometry = build_ref2va_layout([1, 0, 1], refs, 2, 4, 6, 4)
    counts = [6, 6, 1, 4]
    condition = np.concatenate([np.full((n, 96), i + 1, np.float32) for i, n in enumerate(counts)])
    model = ConstantVelocity()
    v, a = sample_image(model, np.ones((3, 5120), np.float32), condition, geometry,
                        np.zeros((12, 96), np.float32), np.zeros((8, 32), np.float32))
    assert geometry.reference_prefix_segments == (3, 6, 6, 1, 4, 8)
    assert len(model.seen) == 4 and v.shape == (12, 96) and a.shape == (8, 32)
    for video, _ in model.seen:
        np.testing.assert_array_equal(video[:17], condition)
    np.testing.assert_allclose(v, 2., atol=1e-6)


def test_prepared_timestep_superset_is_reused_without_missing_adaln_weights():
    from h3_apple.runtime.ref2va import build_ref2va_timesteps
    from h3_apple._vendor.fastvideo_mlx.minimax_h3 import MiniMaxH3SchedulerState
    model = ConstantVelocity()
    geometry = layout()
    video = MiniMaxH3SchedulerState.create(12, 4).timesteps
    audio = MiniMaxH3SchedulerState.create(3, 4).timesteps
    union = np.unique(np.concatenate([build_ref2va_timesteps(geometry, v, a)[0]
                                      for v, a in zip(video, audio)] + [np.array([1.], np.float32)]))
    model._adaln_cache = SimpleNamespace(timesteps=union)
    def forbidden(_):
        raise AssertionError("Prepared cache must not reconstruct discarded AdaLN weights")
    model.precompute_adaln = forbidden
    condition, v, a = image_noise(np.ones((6, 96), np.float32), geometry, 42)
    sample_image(model, np.ones((3, 5120), np.float32), condition, geometry, v, a)
    assert len(model.seen) == 4


@pytest.mark.parametrize("problem", ["nonfinite", "wrong_prefix", "wrong_targets", "sparse"])
def test_bad_inputs_fail_before_model_forward(problem):
    model = ConstantVelocity()
    condition, video, audio = image_noise(np.ones((6, 96), np.float32), layout(), 42)
    if problem == "nonfinite": video[0, 0] = np.nan
    if problem == "wrong_prefix": condition = condition[:-1]
    if problem == "wrong_targets": video = video[:-1]
    if problem == "sparse": model.vsa_config = SimpleNamespace(enabled=True)
    with pytest.raises(ValueError):
        sample_image(model, np.ones((3, 5120), np.float32), condition, layout(), video, audio)
    assert not model.seen
