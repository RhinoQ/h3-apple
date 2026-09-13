from types import SimpleNamespace
import numpy as np
import pytest

from h3_apple.conversion import ref2va_adapter_plan, merge_parameter


def adapter():
    tensors, shapes = {}, {}
    for prefix in ([f"token_refiner.refiner_blocks.{i}" for i in range(2)] +
                   [f"transformer_blocks.{i}" for i in range(50)]):
        for projection in ("attn.to_q", "attn.to_k", "attn.to_v", "attn.to_out.0", "ff.net.0.proj", "ff.net.2"):
            name = f"{prefix}.{projection}"
            shapes[name + ".weight"] = (4, 6)
            tensors[name + ".lora_A.default.weight"] = SimpleNamespace(shape=(128, 6))
            tensors[name + ".lora_B.default.weight"] = SimpleNamespace(shape=(4, 128))
    return SimpleNamespace(metadata={"format":"pt", "alpha":"8"}, tensors=tensors), shapes


def test_all_ref2va_projection_pairs_close_against_base():
    h, shapes = adapter()
    plans = ref2va_adapter_plan(h, shapes)
    assert len(plans) == 312
    assert {key for plan in plans.values() for key in plan.values()} == set(h.tensors)


@pytest.mark.parametrize("change", ["alpha", "missing_pair", "rank", "wrong_block", "absent_base"])
def test_ref2va_adapter_errors_are_rejected(change):
    h, shapes = adapter()
    key = next(iter(h.tensors))
    if change == "alpha": h.metadata["alpha"] = "128"
    elif change == "missing_pair": del h.tensors[key]
    elif change == "rank": h.tensors[key].shape = (64, 6)
    elif change == "wrong_block": h.tensors[key.replace("blocks.0", "blocks.9")] = h.tensors.pop(key)
    else: del shapes[next(iter(shapes))]
    with pytest.raises(ValueError): ref2va_adapter_plan(h, shapes)


def test_ref2va_alpha_over_rank_is_applied_before_rounding():
    used = set()
    result = merge_parameter(np.zeros((1, 1), np.float16),
        {"lora_A.weight":"a", "lora_B.weight":"b"},
        {"a":np.ones((128, 1), np.float16), "b":np.ones((1, 128), np.float16)},
        xp=np, consumed=used, lora_scale=8/128)
    assert result.item() == 8 and used == {"a", "b"}
