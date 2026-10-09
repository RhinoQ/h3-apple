"""Check the private native-store numerical diagnostic and scoped restoration."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


def test_runtime_lora_reference(tmp_path, monkeypatch):
    mx = pytest.importorskip('mlx.core')
    from h3_apple._vendor.fastvideo_mlx import minimax_h3 as h3
    from h3_apple import vsa_conversion as conversion
    path = Path(__file__).parents[1] / 'tools/runtime_lora_reference.py'
    spec = importlib.util.spec_from_file_location('runtime_lora_reference', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    adapter = tmp_path / 'adapter.safetensors'
    rng = np.random.default_rng(71)
    a = mx.array(rng.standard_normal((4, 16)).astype(np.float32)).astype(mx.bfloat16)
    b = mx.array(rng.standard_normal((12, 4)).astype(np.float32)).astype(mx.bfloat16)
    w = mx.array(rng.standard_normal((12, 16)).astype(np.float32)).astype(mx.bfloat16)
    x = mx.array(rng.standard_normal((7, 16)).astype(np.float32)).astype(mx.bfloat16)
    mx.save_safetensors(str(adapter), {'a': a, 'b': b})
    monkeypatch.setattr(conversion, 'ref2va_adapter_plan', lambda *_: {
        'transformer_blocks.0.attn.to_q.weight': {'lora_A.weight': 'a', 'lora_B.weight': 'b'}})
    dit = SimpleNamespace(blocks=[{'attn.to_q.weight': w}], refiner=[])
    original = h3.linear
    with pytest.raises(RuntimeError, match='restore'):
        with module.runtime_lora(dit, adapter) as receipt:
            y = h3.linear(x, w)
            scaled = (a.astype(mx.float32) * (8 / 128)).astype(mx.bfloat16)
            base = np.array((x @ w.T).astype(mx.float32))
            down = np.array((x @ scaled.T).astype(mx.float32))
            expected = mx.array(base + down @ np.array(b.astype(mx.float32)).T).astype(mx.bfloat16)
            np.testing.assert_array_equal(np.array(y.astype(mx.float32)), np.array(expected.astype(mx.float32)))
            assert receipt == {'modules': 1, 'adapted_calls': 1}
            with pytest.raises(ValueError, match='BF16'):
                h3.linear(x.astype(mx.float32), w)
            assert h3.linear(x, w.astype(mx.float32)).shape == y.shape
            raise RuntimeError('restore')
    assert h3.linear is original
