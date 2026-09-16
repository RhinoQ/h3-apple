"""Structural VSA admission; these synthetic checks do not rate generated quality."""
from dataclasses import dataclass
from types import SimpleNamespace
import json

import mlx.core as mx
import numpy as np
import pytest

from h3_apple.runtime import fl2va_pipeline as fl
from h3_apple.fl2va_recipe import FL12_SAMPLING
from h3_apple.runtime.ref2va_sampling import sample_image
from h3_apple._vendor.fastvideo_mlx.minimax_h3_pipeline import MiniMaxH3MLXPipeline
from h3_apple._vendor.fastvideo_mlx.minimax_h3_vsa import (
    prefix_segments_from_layout, build_h3_tile_geometry, build_block_mask,
)


@pytest.mark.parametrize('height,width', [(576, 1024), (768, 1376), (1376, 768)])
@pytest.mark.parametrize('anchors', [('first',), ('last',), ('first', 'last')])
def test_all_keyframe_segments_are_protected_and_keep_their_own_tiles(height, width, anchors):
    tags = np.array([1, 0, 0, 1, 1], np.int64)
    shape = MiniMaxH3MLXPipeline.resolve_geometry(height, width, 124)
    layout = fl.keyframe_layout(tags, shape, 124, anchors)
    frame_rows = (height // 32) * (width // 32)
    segments = prefix_segments_from_layout(layout, (1, 2, 2))
    assert segments[1:-1] == (frame_rows,) * len(anchors)
    if height != 576:
        assert frame_rows == 1032 and frame_rows % 64 == 8
    geometry = build_h3_tile_geometry(segments,
        (shape['latent_frame_count'], shape['latent_height']//2, shape['latent_width']//2))
    boundaries = np.cumsum((0, *segments)); used = set()
    for lo, hi in zip(boundaries[:-1], boundaries[1:]):
        tiles = set(geometry.untile_combined_index[lo:hi] // 64)
        assert not used.intersection(tiles)
        used.update(tiles)
    assert sum(geometry.variable_block_sizes) == layout.sequence_length
    # Independent small routing fixture: all prefix queries and keys remain visible.
    prefix = geometry.num_prefix_tiles; n = prefix + 9
    scores = np.broadcast_to(np.arange(n, dtype=np.float32), (1, n, n)).copy()
    mask = build_block_mask(scores, prefix, 9, .75, True, routing_mode='kablex')
    assert mask[:, :prefix, :].all() and mask[:, :, :prefix].all()
    assert not mask[:, prefix:, prefix:].all()


def test_fixed_first_and_last_conditions_never_enter_the_solver_or_decode():
    layout = fl.keyframe_layout(np.array([1, 0, 1]),
        dict(latent_frame_count=2, latent_height=4, latent_width=6), 124, ['first', 'last'])
    fixed = np.concatenate([np.full((6, 96), 7, np.float32), np.full((6, 96), 11, np.float32)])
    class Model:
        vsa_config = SimpleNamespace(enabled=True, exempt=True)
        vsa_capable = True
        _adaln_cache = None
        def __init__(self): self.seen = []
        def precompute_adaln(self, times): self._adaln_cache = SimpleNamespace(timesteps=times)
        def forward_with_cache(self, video, audio, text, **kwargs):
            self.seen.append(np.array(video[:12]))
            return mx.concatenate([mx.full((12, 96), 1e6), mx.ones((12, 96))]), mx.zeros(audio.shape)
    model = Model()
    v, _ = sample_image(model, np.ones((3, 5120), np.float32), fixed, layout,
        np.zeros((12, 96), np.float32), np.zeros((len(layout.audio_indices), 32), np.float32))
    assert len(model.seen) == 4 and v.shape == (12, 96)
    for seen in model.seen: np.testing.assert_array_equal(seen, fixed)
    np.testing.assert_allclose(v, 1, atol=1e-6)


def recipe(path, gates=50):
    (path / 'fl2va_recipe.json').write_text(json.dumps(dict(schema='h3-apple-fl2va/v1',
        task='fl2va', lora_tensors=624, lora_rank=128, lora_alpha=8,
        fasth3_t2va_deltas_applied=False, gate_tensors=gates,
        precision="int8_group64_bf16", sampling=FL12_SAMPLING)))


def test_vsa_rejects_missing_gates_before_encoding(tmp_path):
    recipe(tmp_path, 49)
    with pytest.raises(ValueError, match='50 VSA gates'):
        fl.condition_and_denoise(dict(task='fl2va', num_steps=4), dict(attention='vsa'), tmp_path, None, None)


@pytest.mark.parametrize('calls,fallback,passes', [(200, False, True), (0, False, False), (199, False, False), (200, True, False)])
def test_experimental_path_requires_200_actual_sparse_calls(tmp_path, monkeypatch, calls, fallback, passes):
    from PIL import Image
    recipe(tmp_path); picture = tmp_path / 'anchor.png'; Image.new('RGB', (32, 32), 'blue').save(picture)
    monkeypatch.setattr(fl, 'encode_images', lambda *_: (np.ones((3, 5120), np.float32), np.array([1, 0, 1]),
        np.ones((1, 96), np.float32), {}))
    @dataclass
    class Stats:
        sparse_calls: int = calls
        fallback_reasons: tuple = ('unexpected fallback',) if fallback else ()
    model = SimpleNamespace(vsa_capable=True, blocks=[{'attn.to_gate_compress.weight': None} for _ in range(50)],
        last_vsa_stats=Stats())
    model.configure_vsa = lambda config: setattr(model, 'configuration', config)
    monkeypatch.setattr(fl, 'load_mlx_h3_checkpoint', lambda _: model)
    monkeypatch.setattr(fl, 'sample_image', lambda *_, **__: (np.ones((1, 96)), np.ones((1, 32))))
    counter = iter([0, calls]); monkeypatch.setattr(fl, 'sparse_calls', lambda: next(counter))
    args = (dict(task='fl2va', num_steps=4, model_width=32, model_height=32, model_num_frames=124, prompt='fixture', seed=42),
        dict(attention='vsa', image_paths=[str(picture)], anchors=['first'], native_root=str(tmp_path)),
        tmp_path, SimpleNamespace(nfe=4, blocks=200), lambda _, f: f())
    if passes:
        _, _, metadata, _ = fl.condition_and_denoise(*args)
        assert model.configuration.enabled and model.configuration.exempt
        assert model.configuration.sparsity == .75 and model.configuration.routing_mode == 'kablex'
        assert metadata['attention'] == 'vsa' and metadata['vsa_gates_used']
    else:
        with pytest.raises(ValueError, match='200 FL2VA VSA'):
            fl.condition_and_denoise(*args)
