import numpy as np
from safetensors.numpy import save_file

from h3_apple.conversion import header, merge_parameter, native_key_plan, transform_native, video_key_plan


def test_native_qkv_is_interleaved_per_head():
    native = np.array([10, 11, 20, 21, 30, 31, 40, 41, 50, 51, 60, 61]).reshape(-1, 1)
    assert transform_native(native, "q", heads=2, head_dim=2).ravel().tolist() == [10, 11, 40, 41]
    assert transform_native(native, "k", heads=2, head_dim=2).ravel().tolist() == [20, 21, 50, 51]
    assert transform_native(native, "v", heads=2, head_dim=2).ravel().tolist() == [30, 31, 60, 61]


def test_native_swiglu_gate_half_moves_after_value_half():
    assert transform_native(np.array([1, 2, 3, 4]), "swap_halves").tolist() == [3, 4, 1, 2]
    assert native_key_plan("blocks.3.mlp.fc1.weight") == [("transformer_blocks.3.ff.net.0.proj.weight", "swap_halves")]
    assert video_key_plan("decoder.blocks.2.ff.w1.weight") == [("decoder.blocks.2.ff.net.0.proj.weight", "swap_halves")]


def test_lora_merge_and_consumption_have_known_numeric_result():
    base = np.array([[1, 2], [3, 4]], dtype=np.float16)
    tensors = dict(a=np.array([[1, 2]], dtype=np.float16), b=np.array([[0.5], [1]], dtype=np.float16))
    consumed = set()
    result = merge_parameter(base, {"lora_A.weight": "a", "lora_B.weight": "b"}, tensors,
                             xp=np, consumed=consumed)
    np.testing.assert_array_equal(result, np.array([[1.5, 3], [4, 6]], dtype=np.float16))
    assert consumed == {"a", "b"}


def test_header_inspection_requires_no_gpu(tmp_path):
    path = tmp_path / "adapter.safetensors"
    save_file({"matrix": np.ones((2, 3), dtype=np.float32)}, path, metadata={"format": "example"})
    parsed = header(path)
    assert parsed.tensors["matrix"].shape == (2, 3)
    assert parsed.metadata == {"format": "example"}
