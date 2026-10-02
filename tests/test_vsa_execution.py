"""P140 output fusion must preserve arithmetic and reuse must never go stale."""
from types import SimpleNamespace
import pytest
np = pytest.importorskip("numpy")
pytest.importorskip("mlx.core")


@pytest.mark.hardware
@pytest.mark.parametrize("m,n,k", [(1, 1, 64), (65, 67, 5376), (65, 67, 7168), (65, 67, 14336)])
def test_direct_bf16_matches_independent_f32_then_cast(m, n, k):
    import mlx.core as mx
    from h3_apple._vendor.fastvideo_mlx.fastwan import QuantizedMatrix, MLXQuantizationSpec
    from h3_apple.runtime.affine_native import NativeAffineW8A8
    rng = np.random.default_rng(140)
    x = mx.array(rng.normal(size=(m, k*2)), mx.bfloat16)[:, ::2]
    w = mx.array(rng.normal(size=(n, k)), mx.bfloat16)
    codes, scales, biases = mx.quantize(w, group_size=64, bits=8)
    weight = QuantizedMatrix(codes, scales, biases, MLXQuantizationSpec("affine", 8, 64), mx.bfloat16)
    old, direct = NativeAffineW8A8(), NativeAffineW8A8(output_float32=False)
    prepared = old.prepare(weight)
    expected, actual = old(x, prepared), direct(x, prepared)
    packed = direct.pack(x)
    reused = direct(x, prepared, packed=packed)
    mx.eval(expected, actual, reused)
    assert actual.dtype == reused.dtype == mx.bfloat16
    assert bool(mx.all(mx.isfinite(actual)))
    assert bool(mx.array_equal(actual, expected))
    assert bool(mx.array_equal(reused, expected))
    assert bool(mx.all(direct(mx.zeros_like(x), prepared) == 0))
    with pytest.raises(ValueError, match="shape differs"):
        direct(mx.zeros((m+1, k), mx.bfloat16), prepared, packed=packed)


def test_reuse_requires_same_input_layer_and_consecutive_qkv(monkeypatch):
    from h3_apple.runtime import affine_native, dispatch as vsa_dispatch, qk_smooth, sparse
    from h3_apple._vendor.fastvideo_mlx import minimax_h3 as model
    class Projection:
        def __init__(self, **kwargs):
            assert kwargs == {"output_float32": False}
            self.calls = self.pack_calls = 0
        def prepare(self, weight):
            return weight
        def pack(self, x):
            self.pack_calls += 1
            return (x, self.pack_calls)
        def __call__(self, x, prepared, *, packed=None):
            self.calls += 1
            packed = self.pack(x) if packed is None else packed
            assert packed[0] is x
            return packed[1]
    monkeypatch.setattr(affine_native, "NativeAffineW8A8", Projection)
    monkeypatch.setattr(qk_smooth, "SmoothQKSparse", lambda **kw: SimpleNamespace(calls=0))
    original = lambda x, w, bias=None: -1
    monkeypatch.setattr(model, "linear", original)
    old_sparse = sparse._implementation
    dit = SimpleNamespace(blocks=[{key: object() for key in vsa_dispatch.KEYS} for _ in range(2)])
    weights = [[block[k] for k in vsa_dispatch.KEYS] for block in dit.blocks]
    x, other = object(), object()
    with pytest.raises(RuntimeError, match="deliberate"):
        with vsa_dispatch.Dispatch(dit) as dispatch:
            assert [model.linear(x, w) for w in weights[0][:3]] == [1, 1, 1]
            assert dispatch._pending is None
            # New input, different layer, intervening call, and out-of-order V
            # must each invalidate Q's retained graph.
            assert model.linear(x, weights[0][0]) == 2
            assert model.linear(other, weights[0][1]) == 3
            assert model.linear(x, weights[0][2]) == 4
            assert model.linear(x, weights[0][0]) == 5
            assert model.linear(x, weights[1][1]) == 6
            assert model.linear(x, weights[0][0]) == 7
            assert model.linear(x, object()) == -1
            assert model.linear(x, weights[0][1]) == 8
            assert model.linear(x, weights[0][0]) == 9
            assert model.linear(x, weights[0][2]) == 10
            assert dispatch.summary()["qkv_pack_reuses"] == 2
            with pytest.raises(RuntimeError, match="cannot overlap"):
                with vsa_dispatch.Dispatch(dit):
                    pass
            raise RuntimeError("deliberate")
    assert dispatch._pending is None and not dispatch.prepared
    assert model.linear is original and sparse._implementation is old_sparse
    assert not vsa_dispatch._active


def test_failed_prepare_restores_p140_scope(monkeypatch):
    from h3_apple.runtime import affine_native, dispatch as vsa_dispatch, sparse
    from h3_apple._vendor.fastvideo_mlx import minimax_h3 as model
    class Failed:
        def __init__(self, **kwargs):
            pass
        def prepare(self, weight):
            raise ValueError("invalid weight")
    monkeypatch.setattr(affine_native, "NativeAffineW8A8", Failed)
    old_linear, old_sparse = model.linear, sparse._implementation
    dit = SimpleNamespace(blocks=[{key: object() for key in vsa_dispatch.KEYS}])
    with pytest.raises(ValueError, match="invalid weight"):
        with vsa_dispatch.Dispatch(dit):
            pass
    assert model.linear is old_linear and sparse._implementation is old_sparse
    assert not vsa_dispatch._active
