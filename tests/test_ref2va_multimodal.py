from types import SimpleNamespace, MethodType

import numpy as np
import pytest

from h3_apple.api import resolve
from h3_apple.runtime.ref2va import ReferenceGeometry, build_ref2va_layout
from h3_apple.runtime.ref2va_conditioning import image_presentation
from h3_apple.runtime.ref2va_sampling import image_noise
from h3_apple.runtime.ref2va_multimodal import presentation, sample_vision_frames, mixed_noise


class Tokenizer:
    names = {"<|vision_start|>": 1, "<|vision_end|>": 2, "<|image_pad|>": 3, "<|video_pad|>": 4}

    def convert_tokens_to_ids(self, name):
        return self.names[name]

    def __call__(self, text, **kwargs):
        return {"input_ids": [ord(c) + 10 for c in text]}


def test_image_only_presentation_remains_identical():
    grids = np.array([[1, 4, 8], [1, 6, 4]])
    expected = image_presentation(Tokenizer(), "move gently", grids)
    actual = presentation(Tokenizer(), "move gently", [dict(kind="image", grid=g) for g in grids])
    for key in ("token_ids", "tags", "positions", "visual_mask"):
        np.testing.assert_array_equal(getattr(actual, key), getattr(expected, key))


def test_mixed_mrope_matches_transformers_and_audio_labels():
    import torch
    from transformers.models.qwen3_vl.modeling_qwen3_vl import Qwen3VLModel
    refs = [dict(kind="image", grid=[1, 4, 8]), dict(kind="audio", waveform=np.ones((2, 20))),
            dict(kind="video", grid=[2, 6, 4], timestamps=[.25, 1.25], waveform=np.ones((2, 20)))]
    actual = presentation(Tokenizer(), "Use Audio 1 for the new voice.", refs)
    decoded_text = "".join(chr(v - 10) for v in actual.token_ids if v >= 10)
    assert decoded_text.index("<Audio 1>") < decoded_text.index("<Audio 2>") < decoded_text.index("<Video 1>")
    assert "<0.2 seconds>" in decoded_text and "<1.2 seconds>" in decoded_text
    model = SimpleNamespace(config=SimpleNamespace(vision_config=SimpleNamespace(spatial_merge_size=2)))
    model.get_vision_position_ids = MethodType(Qwen3VLModel.get_vision_position_ids, model)
    types = np.where(actual.token_ids == 3, 1, np.where(actual.token_ids == 4, 2, 0))
    expected, _ = Qwen3VLModel.get_rope_index(model, torch.tensor(actual.token_ids[None]),
        torch.tensor(types[None]), image_grid_thw=torch.tensor([[1, 4, 8]]), video_grid_thw=torch.tensor([[2, 6, 4]]))
    np.testing.assert_array_equal(actual.positions, expected[:, 0].numpy())
    assert actual.visual_mask.sum() == 8 + 2 * 6


def test_sampling_reference_video_uses_two_fps_and_paired_timestamps():
    frames = np.arange(49)[:, None, None, None]
    sampled, timestamps = sample_vision_frames(frames)
    assert sampled[:, 0, 0, 0].tolist() == [0, 12, 24, 36, 48]
    assert timestamps == [.25, 1.25, 2.0]


def test_noise_keeps_image_streams_and_excludes_condition_audio():
    rows = np.ones((4, 96), np.float32)
    image_layout = build_ref2va_layout(np.ones(2, np.int64), [ReferenceGeometry("image", 1, 4, 4)], 2, 4, 4, 5)
    for a, b in zip(image_noise(rows, image_layout, 42), mixed_noise(rows, image_layout, 42), strict=True):
        np.testing.assert_array_equal(a, b)
    mixed_layout = build_ref2va_layout(np.ones(2, np.int64), [ReferenceGeometry("image", 1, 4, 4),
        ReferenceGeometry("audio", has_audio=True, num_audio_latents=3)], 2, 4, 4, 5)
    fixed, video, audio = mixed_noise(rows, mixed_layout, 42)
    assert fixed.shape == (4, 96) and video.shape == (8, 96) and audio.shape == (10, 32)
