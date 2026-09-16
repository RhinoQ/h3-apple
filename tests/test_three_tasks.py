import copy
import json
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image

from h3_apple import resolve
from h3_apple.fl2va_recipe import FL12_SAMPLING, fl2va_sampling
from h3_apple.runtime.ref2va_pipeline import prepare_images


@pytest.mark.parametrize("task,argument", [("t2va", None), ("fl2va", "first_frame"), ("fl2va", "last_frame"), ("ref2va", "reference_images")])
def test_explicit_and_inferred_tasks_agree_and_reject_mixed_inputs(tmp_path, task, argument):
    p = tmp_path / "input.png"
    Image.new("RGB", (64, 64), "red").save(p)
    inputs = {} if argument is None else {argument: [p] if argument == "reference_images" else p}
    expected = resolve("move gently", task=task, seed=7, **inputs)
    assert resolve("move gently", seed=7, **inputs) == expected
    for wrong in {"t2va", "fl2va", "ref2va"} - {task}:
        with pytest.raises(ValueError, match="does not match"):
            resolve("move gently", task=wrong, **inputs)
    command = [sys.executable, "-m", "h3_apple", "resolve", "--prompt", "move gently", "--task", task, "--seed", "7"]
    if argument:
        command += [{"reference_images": "--reference-image"}.get(argument, "--" + argument.replace("_", "-")), str(p)]
    result = subprocess.run(command, cwd=tmp_path, text=True, capture_output=True, check=True)
    assert json.loads(result.stdout) == json.loads(json.dumps(expected.to_dict()))


def test_match_retains_more_large_image_pixels_without_upscaling_small_inputs(tmp_path):
    large, small = tmp_path / "large.png", tmp_path / "small.png"
    Image.new("RGB", (1920, 1080), "blue").save(large)
    Image.new("RGB", (320, 192), "red").save(small)
    request = resolve("Use Picture 1", reference_images=[large, small], resolution="768p", reference_resize="match")
    assert request.preset_version == "ours-ref2va-match-v1"
    options = dict(image_paths=request.reference_images, pixel_budget=request.model_width * request.model_height)
    matched = prepare_images(options)
    legacy = prepare_images(dict(options, pixel_budget=672 * 384))
    assert matched[0].size == (1376, 768) and legacy[0].size == (672, 384)
    assert matched[1].size == legacy[1].size == (320, 192)
    with pytest.raises(ValueError, match="only to Ref2VA"):
        resolve("text", reference_resize="match")


def valid_recipe():
    return dict(schema="h3-apple-fl2va/v1", task="fl2va", lora_tensors=624,
        lora_rank=128, lora_alpha=8, gate_tensors=50, precision="int8_group64_bf16",
        fasth3_t2va_deltas_applied=False, sampling=copy.deepcopy(FL12_SAMPLING))


@pytest.mark.parametrize("change", ["missing", "old_shift", "wrong_adapter", "t2va_delta", "wrong_task"])
def test_old_or_mismatched_fl_recipes_cannot_masquerade_as_v12(change):
    recipe = valid_recipe()
    assert fl2va_sampling(recipe) == FL12_SAMPLING
    if change == "missing": del recipe["sampling"]
    elif change == "old_shift": recipe["sampling"]["video_shift"] = 12
    elif change == "wrong_adapter": recipe["sampling"]["adapter_sha256"] = "0" * 64
    elif change == "t2va_delta": recipe["fasth3_t2va_deltas_applied"] = True
    else: recipe["task"] = "ref2va"
    with pytest.raises(ValueError, match="pinned LightX2V v1.2"):
        fl2va_sampling(recipe)


def test_fl6_schedule_reaches_forward_and_old_adaln_cache_is_rejected():
    from types import SimpleNamespace
    import mlx.core as mx
    from h3_apple.runtime.fl2va_pipeline import keyframe_layout
    from h3_apple.runtime.ref2va_sampling import sample_image
    layout = keyframe_layout(np.array([1, 0, 1]),
        dict(latent_frame_count=2, latent_height=4, latent_width=6), 124, ["first", "last"])
    class Model:
        vsa_config = SimpleNamespace(enabled=False)
        _adaln_cache = None
        def __init__(self): self.seen = []
        def precompute_adaln(self, times): self._adaln_cache = SimpleNamespace(timesteps=times)
        def forward_with_cache(self, video, audio, text, **kwargs):
            times = kwargs["step_timesteps"][kwargs["row_timestep_inverse"]]
            t = float(times[layout.video_indices[-1]])
            self.seen.append(t)
            return mx.full(video.shape, t), mx.zeros(audio.shape)
    arguments = (np.ones((3, 5120), np.float32), np.ones((12, 96), np.float32), layout,
        np.zeros((12, 96), np.float32), np.zeros((len(layout.audio_indices), 32), np.float32))
    model = Model()
    video, _ = sample_image(model, *arguments, video_shift=6)
    # Independently calculated from q=[1,3/4,1/2,1/4,0] and 6q/(1+5q).
    sigma = np.array([1, 18/19, 6/7, 2/3, 0])
    np.testing.assert_allclose(model.seen, 1-sigma[:-1], atol=1e-7)
    np.testing.assert_allclose(video, np.sum((sigma[:-1]-sigma[1:])*(1-sigma[:-1])), atol=1e-6)
    old = Model()
    sample_image(old, *arguments)
    with pytest.raises(ValueError, match="missing required cached timesteps"):
        sample_image(old, *arguments, video_shift=6)
