"""CPU float64 oracle for the declared native affine rounded arithmetic."""
import pytest
np = pytest.importorskip("numpy")
pytest.importorskip("mlx.core")

pytestmark = pytest.mark.hardware


@pytest.mark.parametrize("m,n,k", [(1, 1, 64), (17, 67, 192), (65, 65, 128),
                                  (17, 67, 5376), (17, 67, 7168), (17, 67, 14336)])
def test_native_affine_components_and_ragged_output(m, n, k):
    import mlx.core as mx
    from h3_apple._vendor.fastvideo_mlx.fastwan import QuantizedMatrix, MLXQuantizationSpec
    from h3_apple.runtime.affine_native import NativeAffineW8A8
    rng = np.random.default_rng(139)
    x = mx.array(rng.normal(size=(m, k*2)), mx.bfloat16)[:, ::2]
    w = mx.array(rng.normal(size=(n, k)), mx.bfloat16)
    codes, scales, biases = mx.quantize(w, group_size=64, bits=8)
    weight = QuantizedMatrix(codes, scales, biases, MLXQuantizationSpec("affine", 8, 64), mx.bfloat16)
    kernel = NativeAffineW8A8()
    prepared = kernel.prepare(weight)
    packed = kernel.pack(x)
    def as_float(value):
        value = value.astype(mx.float32)
        mx.eval(value)
        return np.asarray(value).astype(np.float64)
    rounded = lambda value: as_float(mx.array(value, mx.bfloat16))
    xu = np.asarray(packed[0]).astype(np.int32)
    raw = np.asarray(prepared["codes"]).astype(np.int32)
    a, sums, u = as_float(packed[1]), np.asarray(packed[2]), as_float(packed[3])
    xf = np.asarray(x.astype(mx.float32)).reshape(m, -1, 64)
    peak = np.max(abs(xf), axis=-1)
    inv = np.divide(np.float32(127), peak, out=np.zeros_like(peak), where=peak > 0)
    q = np.clip(np.rint(xf*inv[..., None]), -127, 127).astype(np.int32)
    np.testing.assert_array_equal(xu.reshape(q.shape), q+128)
    np.testing.assert_array_equal(sums, q.sum(-1))
    np.testing.assert_array_equal(a, rounded(peak*np.float32(1/127)))
    np.testing.assert_array_equal(u, rounded(a*sums))
    ws, wb = as_float(prepared["scales"]), as_float(prepared["biases"])
    total = raw.reshape(n, -1, 64).sum(-1)
    np.testing.assert_array_equal(np.asarray(prepared["sums"]), total)
    correction = -128*ws*total
    high = rounded(correction); low = rounded(correction-high)
    np.testing.assert_array_equal(as_float(prepared["high"]), high)
    np.testing.assert_array_equal(as_float(prepared["low"]), low)
    expected = u @ wb.T + a @ high.T + a @ low.T
    magnitude = abs(u) @ abs(wb).T + abs(a) @ (abs(high) + abs(low)).T
    for g in range(k//64):
        dot = xu[:, g*64:(g+1)*64] @ raw[:, g*64:(g+1)*64].T
        term = a[:, g, None]*ws[None, :, g]*dot
        expected += term
        magnitude += abs(term)
    actual = as_float(kernel.native(packed, prepared))
    # The unsigned partials and negative offset have substantial cancellation.
    # Bound FP32 roundoff by the absolute sum of terms, not the small cancelled
    # result. gamma_n covers products, group sums and the three offset matmuls.
    unit_roundoff = np.finfo(np.float32).eps / 2
    count = 4*(k//64) + 4
    gamma = count*unit_roundoff / (1-count*unit_roundoff)
    assert np.all(abs(actual-expected) <= gamma*magnitude + 1e-6)
    if k <= 192:
        np.testing.assert_allclose(actual, expected, atol=.003, rtol=1e-4)
    np.testing.assert_array_equal(as_float(kernel(x, prepared)), rounded(actual))
    np.testing.assert_array_equal(as_float(kernel(mx.zeros((m, k), mx.bfloat16), prepared)), 0)
