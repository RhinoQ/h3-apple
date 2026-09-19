from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest

from h3_apple.conversion import dareties_adapter_plan, merge_parameter, transform_lora_b
from h3_apple.ref2va_recipe import DARETIES_RECIPE, validate_ref2va_recipe


def fixture():
    tensors, shapes = {}, {}
    for old, new in [(f"blocks.{i}", f"transformer_blocks.{i}") for i in range(50)] + [
            (f"token_refiner.blocks.{i}", f"token_refiner.refiner_blocks.{i}") for i in range(2)]:
        for source, targets, rows in [
            ("attn.qkv_proj", ["attn.to_q", "attn.to_k", "attn.to_v"], 12),
            ("attn.out_proj", ["attn.to_out.0"], 4),
            ("mlp.fc1", ["ff.net.0.proj"], 8), ("mlp.fc2", ["ff.net.2"], 4),
        ]:
            rank = rows // 2
            tensors[f"diffusion_model.{old}.{source}.lora_A.weight"] = SimpleNamespace(shape=(rank, 6))
            tensors[f"diffusion_model.{old}.{source}.lora_B.weight"] = SimpleNamespace(shape=(rows, rank))
            shapes.update({f"{new}.{t}.weight": (rows // len(targets), 6) for t in targets})
    for old, new in [(f"blocks.{i}.adaln_proj.linear", f"transformer_blocks.{i}.adaln_proj.linear")
                     for i in range(50)] + [("final_layer.adaln_proj.linear", "norm_out.linear")]:
        tensors[f"diffusion_model.{old}.lora_A.weight"] = SimpleNamespace(shape=(2, 3))
        tensors[f"diffusion_model.{old}.lora_B.weight"] = SimpleNamespace(shape=(12, 2))
        shapes[new + ".weight"] = (12, 3)
    return SimpleNamespace(tensors=tensors, metadata=dict(alpha_normalized="true",
        alpha_normalization="lora_up := lora_up * (alpha / rank); alpha tensors removed")), shapes


def test_complete_dynamic_inventory_includes_all_adaln_and_fused_qkv():
    h, shapes = fixture()
    plans, transforms = dareties_adapter_plan(h, shapes)
    assert len(plans) == 363
    assert {k for p in plans.values() for k in p.values()} == set(h.tensors)
    assert sum(t.startswith("comfy_") for t in transforms.values()) == 156
    assert sum(t == "swap_halves" for t in transforms.values()) == 52
    assert "norm_out.linear.weight" in plans
    assert all(f"transformer_blocks.{i}.adaln_proj.linear.weight" in plans for i in range(50))


@pytest.mark.parametrize("change", ["alpha", "missing_adaln", "extra", "rank", "shape", "missing_base"])
def test_invalid_or_incomplete_candidate_rejected(change):
    h, shapes = fixture()
    key = next(iter(h.tensors))
    if change == "alpha": h.metadata["alpha_normalized"] = "false"
    elif change == "missing_adaln": del h.tensors["diffusion_model.blocks.49.adaln_proj.linear.lora_B.weight"]
    elif change == "extra": h.tensors["diffusion_model.blocks.0.attn.qkv_proj.alpha"] = SimpleNamespace(shape=())
    elif change == "rank": h.tensors[key].shape = (999, 6)
    elif change == "shape": h.tensors[key].shape = (6, 7)
    else: del shapes[next(iter(shapes))]
    with pytest.raises(ValueError): dareties_adapter_plan(h, shapes)


def test_comfy_delta_rows_are_contiguous_and_alpha_is_not_applied_twice():
    tensors = dict(a=np.array([[1, 2]], dtype=np.float32),
                   b=np.array([[10], [11], [20], [21], [30], [31]], dtype=np.float32))
    used = set()
    for kind, rows in [("q", [10, 11]), ("k", [20, 21]), ("v", [30, 31])]:
        actual = merge_parameter(np.ones((2, 2), np.float32),
            {"lora_A.weight": "a", "lora_B.weight": "b"}, tensors,
            xp=np, consumed=used, lora_b_transform="comfy_"+kind)
        np.testing.assert_array_equal(actual, [[1+rows[0], 1+rows[0]*2], [1+rows[1], 1+rows[1]*2]])
    assert used == {"a", "b"}
    np.testing.assert_array_equal(transform_lora_b(np.arange(4)[:, None], "swap_halves"),
                                  [[2], [3], [0], [1]])


def test_candidate_recipe_is_explicit_and_cannot_masquerade_as_official():
    validate_ref2va_recipe(DARETIES_RECIPE)
    for key, value in [("schema", "h3-apple-ref2va/v1"), ("lora_tensors", 624),
                       ("alpha_normalized", False), ("lora_strength", .5),
                       ("adaln_targets", 50), ("gate_tensors", 49),
                       ("adapter_source", {}), ("qkv_layout", "native_per_head")]:
        bad = deepcopy(DARETIES_RECIPE)
        bad[key] = value
        with pytest.raises(ValueError): validate_ref2va_recipe(bad)
