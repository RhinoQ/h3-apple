"""Presentation and streamed deepstack boundaries without local model assets."""
from types import SimpleNamespace

import numpy as np
import pytest

from h3_apple.runtime.ref2va_conditioning import image_presentation
from h3_apple._vendor.fastvideo_mlx.minimax_h3_conditioner import (
    ConditionerConfig, StreamedMiniMaxH3TextConditioner,
)


class Tokenizer:
    def convert_tokens_to_ids(self, token):
        return {"<|vision_start|>": 90, "<|image_pad|>": 91, "<|vision_end|>": 92}[token]

    def __call__(self, text, add_special_tokens):
        assert not add_special_tokens
        return {"input_ids": [7] if text.startswith("<Picture ") else [8] * len(text)}


def test_picture_boundaries_are_visual_for_dit_but_text_for_qwen_positions():
    p = image_presentation(Tokenizer(), "ok", [[1, 4, 6]])
    np.testing.assert_array_equal(p.token_ids, [7, 90, 91, 91, 91, 91, 91, 91, 92, 8, 8])
    np.testing.assert_array_equal(p.tags, [1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1])
    np.testing.assert_array_equal(p.visual_mask, [0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0])
    np.testing.assert_array_equal(p.positions, [
        [0, 1, 2, 2, 2, 2, 2, 2, 5, 6, 7],
        [0, 1, 2, 2, 2, 3, 3, 3, 5, 6, 7],
        [0, 1, 2, 3, 4, 2, 3, 4, 5, 6, 7],
    ])


def test_full_prompt_is_retained_after_ordered_images():
    p = image_presentation(Tokenizer(), "x" * 2049, [[1, 4, 6], [1, 6, 4]])
    assert np.sum(p.token_ids == 8) == 2049
    assert np.sum(p.visual_mask) == 12
    assert p.positions.shape == (3, len(p.token_ids))


@pytest.mark.parametrize("grids", [[], [[2, 4, 6]], [[1, 3, 6]], [[1, 0, 6]], [[1.0, 4, 6]]])
def test_unsupported_image_grid_rejected(grids):
    with pytest.raises(ValueError):
        image_presentation(Tokenizer(), "p", grids)


def fake_conditioner():
    c = StreamedMiniMaxH3TextConditioner.__new__(StreamedMiniMaxH3TextConditioner)
    c.config = ConditionerConfig(hidden_size=4, head_dim=6, mrope_section=(1, 1, 1))
    c.index = SimpleNamespace(get_row=lambda key, token: np.full(4, token, np.float32))
    c._decoder_layer = lambda layer, hidden, cos, sin: hidden + 1
    return c


def test_visual_features_and_each_deepstack_only_touch_pad_rows():
    c = fake_conditioner()
    p = image_presentation(Tokenizer(), "ok", [[1, 2, 2]])
    visual = np.full((1, 4), 100, np.float32)
    deepstack = [np.full((1, 4), n, np.float32) for n in (1, 2, 3)]
    seen = []
    hidden, tags = c.encode_presentation(p.token_ids, p.tags, p.positions,
        visual_features=visual, visual_mask=p.visual_mask, deepstack_features=deepstack,
        layer_callback=lambda i, h: seen.append((i, h.copy())))
    np.testing.assert_array_equal(hidden[p.visual_mask], [[156] * 4])
    np.testing.assert_array_equal(hidden[~p.visual_mask, 0], p.token_ids[~p.visual_mask] + 50)
    np.testing.assert_array_equal(tags, p.tags)
    assert len(seen) == 50
    assert [seen[i][1][p.visual_mask, 0].item() for i in range(4)] == [102, 105, 109, 110]


def test_text_only_streaming_keeps_all_rows_and_tags():
    hidden, tags = fake_conditioner().encode_tokens([2, 4])
    np.testing.assert_array_equal(hidden, [[52] * 4, [54] * 4])
    np.testing.assert_array_equal(tags, [1, 1])


def test_partial_deepstack_is_rejected_before_weight_reads():
    c = fake_conditioner()
    with pytest.raises(ValueError, match="all three"):
        c.encode_presentation([1], [0], np.zeros((3, 1), np.int64),
            visual_features=np.ones((1, 4)), visual_mask=np.array([True]),
            deepstack_features=[np.ones((1, 4))])
