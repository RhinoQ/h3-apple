"""Pair integrity and gate isolation; no trained model or quality claims."""

from dataclasses import dataclass
import json
from types import SimpleNamespace

import mlx.core as mx
import numpy as np
import pytest

from h3_apple.runtime.reference_cache import cache_contract, load_or_build
from h3_apple.runtime import ref2va_multimodal as ref
from h3_apple.runtime.ref2va import ReferenceGeometry, build_ref2va_layout
from h3_apple._vendor.fastvideo_mlx.minimax_h3 import MLXMiniMaxH3DiT
from h3_apple._vendor.fastvideo_mlx.minimax_h3_vsa import MiniMaxH3VSAConfig


def test_snapshot_reloads_identical_arrays_and_never_rebuilds(tmp_path):
    path = tmp_path / "pair"
    source = np.arange(12, dtype=np.float32).reshape(3, 4)
    first, m1 = load_or_build(path, {"seed": 1}, lambda: ({"x": source}, {"tag": "source"}))
    source[:] = -1
    def forbidden():
        raise AssertionError("The second arm must not recompute conditioning")
    second, m2 = load_or_build(path, {"seed": 1}, forbidden)
    np.testing.assert_array_equal(first["x"], second["x"])
    assert m1["conditioning_cache"]["created"] and not m2["conditioning_cache"]["created"]
    assert m1["conditioning_cache"]["arrays_sha256"] == m2["conditioning_cache"]["arrays_sha256"]
    with pytest.raises(ValueError, match="mismatch"):
        load_or_build(path, {"seed": 2}, forbidden)
    with (path / "arrays.npz").open("ab") as stream:
        stream.write(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        load_or_build(path, {"seed": 1}, forbidden)


def test_incomplete_snapshot_is_preserved_and_rejected(tmp_path):
    path = tmp_path / "pair"; path.mkdir()
    evidence = path / "failure.txt"; evidence.write_text("retain this failure")
    with pytest.raises(FileNotFoundError):
        load_or_build(path, {}, lambda: pytest.fail("Must not overwrite incomplete cache"))
    assert evidence.read_text() == "retain this failure"


def test_contract_uses_ordered_bytes_instead_of_workspace_paths(tmp_path):
    a, b, same = [tmp_path / n for n in ("a", "b", "same")]
    a.write_bytes(b"one"); b.write_bytes(b"two"); same.write_bytes(b"one")
    request = dict(prompt="replace two people", seed=1103, reference_images=[str(a)])
    options = dict(image_paths=[str(a), str(b)], video_paths=[], pixel_budget=256,
                   cache_model_identity="model", cache_source_identity="code")
    expected = cache_contract(request, options)
    assert cache_contract(dict(request, reference_images=[str(same)]),
                          dict(options, image_paths=[str(same), str(b)])) == expected
    assert cache_contract(request, dict(options, image_paths=[str(b), str(a)])) != expected
    assert cache_contract(dict(request, prompt="replace one person"), options) != expected
    assert cache_contract(request, dict(options, cache_model_identity="other")) != expected


def test_disabled_vsa_never_activates_or_reads_a_gate():
    model = object.__new__(MLXMiniMaxH3DiT)
    model.vsa_config = MiniMaxH3VSAConfig(enabled=False, sparsity=.75)
    model._vsa_geometry = object()
    model._block_gate_active = lambda _: pytest.fail("Dense must not inspect a gate")
    for block in range(50):
        kwargs = model._vsa_block_kwargs(block, 0)
        assert kwargs["vsa_geometry"] is None and kwargs["vsa_sparsity"] == 0
        assert kwargs["use_gate_compress"] is False


def test_mixed_sampler_preserves_both_modalities_and_updates_only_generated_rows():
    layout = build_ref2va_layout([1, 0, 1],
        [ReferenceGeometry("video", 2, 4, 4, True, 3)], 2, 4, 4, 5)
    fixed_v = np.full((8, 96), 7, np.float32)
    fixed_a = np.full((6, 32), 11, np.float32)
    initial_v = np.zeros((8, 96), np.float32)
    initial_a = np.zeros((10, 32), np.float32)
    seen = []
    class Model:
        _adaln_cache = None
        def precompute_adaln(self, ts): self._adaln_cache = SimpleNamespace(timesteps=ts)
        def forward_with_cache(self, video, audio, text, **kwargs):
            seen.append((np.asarray(video), np.asarray(audio)))
            return (mx.concatenate([mx.full(fixed_v.shape, 1e6), mx.full(initial_v.shape, 2)]),
                    mx.concatenate([mx.full(fixed_a.shape, 1e6), mx.full(initial_a.shape, -3)]))
    observer = SimpleNamespace(block=lambda *_: None, step=lambda *_: None)
    v, a = ref.sample_mixed(Model(), np.zeros((3, 5120), np.float32), fixed_v, fixed_a,
                            layout, initial_v, initial_a, observer)
    assert len(seen) == 4
    for vv, aa in seen:
        np.testing.assert_array_equal(vv[:8], fixed_v)
        np.testing.assert_array_equal(aa[:6], fixed_a)
    np.testing.assert_allclose(v, 2, atol=1e-6)
    np.testing.assert_allclose(a, -3, atol=1e-6)


@pytest.mark.parametrize("dense_sparse_calls", [0, 1])
def test_full_mixed_pair_shares_states_and_rejects_dense_sparse_calls(tmp_path, monkeypatch, dense_sparse_calls):
    recipe = dict(schema="h3-apple-ref2va/v1", task="ref2va", lora_rank=128, lora_alpha=8,
                  lora_tensors=624, gate_tensors=50, fasth3_t2va_deltas_applied=False)
    (tmp_path / "ref2va_recipe.json").write_text(json.dumps(recipe))
    clip = tmp_path / "clip.mp4"; clip.write_bytes(b"synthetic media identity only")
    encodes = []
    monkeypatch.setattr(ref, "prepare_references", lambda *_: [])
    def encode(*args):
        encodes.append(1)
        return (np.ones((3, 5120), np.float32), np.array([1, 0, 1]), np.ones((2, 96), np.float32),
                np.zeros((0, 32), np.float32), [ReferenceGeometry("video", 2, 2, 2)], [])
    monkeypatch.setattr(ref, "encode_references", encode)
    @dataclass
    class Stats:
        sparse_calls: int = 200
        fallback_reasons: tuple = ()
    class Model:
        vsa_capable = True
        blocks = [{}] * 50
        def configure_vsa(self, config):
            self.vsa_config = config
            self.last_vsa_stats = Stats() if config.enabled else None
    monkeypatch.setattr(ref, "load_mlx_h3_checkpoint", lambda _: Model())
    counter, seen = [0], []
    monkeypatch.setattr(ref, "sparse_calls", lambda: counter[0])
    def sample(model, text, fv, fa, layout, video, audio, observer):
        seen.append([x.copy() for x in (text, fv, fa, video, audio)])
        counter[0] += 200 if model.vsa_config.enabled else dense_sparse_calls
        observer.nfe, observer.blocks = 4, 200
        return video, audio
    monkeypatch.setattr(ref, "sample_mixed", sample)
    request = dict(num_steps=4, model_height=32, model_width=32, model_num_frames=124,
                   prompt="replace two actors", seed=1103)
    options = dict(attention="vsa", conditioning_cache=tmp_path / "pair",
                   native_root=tmp_path, audio_vae="unused", video_paths=[clip], pixel_budget=256,
                   cache_model_identity="model", cache_source_identity="runtime")
    observer = SimpleNamespace(nfe=0, blocks=0)
    first = ref.condition_and_denoise(request, options, tmp_path, observer, lambda _, f: f())
    args = (request, dict(options, attention="dense"), tmp_path, observer, lambda _, f: f())
    if dense_sparse_calls:
        with pytest.raises(ValueError, match="unexpectedly used VSA"):
            ref.condition_and_denoise(*args)
    else:
        second = ref.condition_and_denoise(*args)
        assert first[3]["sparse_calls"] == 200 and second[3] is None
        assert second[2]["conditioning_cache"]["created"] is False
    assert encodes == [1]
    for a, b in zip(*seen, strict=True): np.testing.assert_array_equal(a, b)
