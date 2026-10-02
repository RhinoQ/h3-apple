"""P139 native affine CMODE1 adapter, from pinned vpipe f34e2cc.

Uses the original W8 codes, group64, unsigned MMA and BF16 two-term offset
compensation. This changes scale/compensation rounding relative to P138.
The original BF16 dequantization residual is intentionally absent.
See metal/p138_NOTICE.txt and p138_VPIPE_LICENSE.txt for upstream provenance.
"""
from pathlib import Path
import mlx.core as mx

QUANTIZE = r"""
const int row = threadgroup_position_in_grid.y;
const int sg = simdgroup_index_in_threadgroup;
const int lane = thread_index_in_simdgroup;
for (int g = sg; g < K/64; g += 8) {
  const long at = long(row)*K + g*64 + lane*2;
  const float x0 = float(X[at]), x1 = float(X[at+1]);
  const float peak = simd_max(max(abs(x0), abs(x1)));
  const float inv = peak > 0 ? 127.0f/peak : 0.0f;
  const int q0 = clamp(int(rint(x0*inv)), -127, 127);
  const int q1 = clamp(int(rint(x1*inv)), -127, 127);
  Xu[at] = uchar(q0+128); Xu[at+1] = uchar(q1+128);
  const int sum = simd_sum(q0+q1);
  if (lane == 0) {
    const bfloat scale = bfloat(peak*(1.0f/127.0f));
    A[long(row)*(K/64)+g] = scale;
    Xsum[long(row)*(K/64)+g] = short(sum);
    U[long(row)*(K/64)+g] = bfloat(float(scale)*float(sum));
  }
}
"""

PREPARE = r"""
const long group = threadgroup_position_in_grid.x;
const int lane = thread_index_in_simdgroup;
const long at = group*64 + lane*2;
const int sum = simd_sum(int(Codes[at]) + int(Codes[at+1]));
if (lane == 0) {
  Wsum[group] = short(sum);
  const float correction = -128.0f*float(Ws[group])*float(sum);
  const bfloat high = bfloat(correction);
  Chi[group] = high;
  Clo[group] = bfloat(correction-float(high));
}
"""

BODY = r"""
threadgroup int staged[8*gemm_u8q_sw<true, 1>()];
gemm_u8q_impl<8, false, 8, true, 1>(Xu, Codes, A, Xsum, Ws, Wb, Wsum,
  U, Chi, Clo, Y, nullptr, 0, nullptr, 0, staged,
  K, N, M, threadgroup_position_in_grid, thread_index_in_threadgroup);
"""

class NativeAffineW8A8:
    def __init__(self, *, output_float32=True):
        self.output_dtype = mx.float32 if output_float32 else mx.bfloat16
        self.quantize = mx.fast.metal_kernel(name="p139_native_quant_g64", input_names=["X"],
            output_names=["Xu", "A", "Xsum", "U"], source=QUANTIZE,
            compile_options={"math_mode": "safe"})
        self.weights = mx.fast.metal_kernel(name="p139_native_weight_compensation", input_names=["Codes", "Ws"],
            output_names=["Wsum", "Chi", "Clo"], source=PREPARE,
            compile_options={"math_mode": "safe"})
        header = (Path(__file__).with_name("metal") / "p138_affine.metal").read_text()
        # The default FP32 output remains available to the arithmetic oracle.
        # Tensor operands in the fused offset matmuls remain the native BF16 type.
        assert header.count("#define VPIPE_ELT float") == 1
        assert header.count("device VPIPE_ELT* y,") == 1
        assert header.count("= (VPIPE_ELT)v;") == 1
        header = header.replace("#define VPIPE_ELT float", "#define VPIPE_ELT bfloat")
        if output_float32:
            header = header.replace("device VPIPE_ELT* y,", "device float* y,")
            header = header.replace("= (VPIPE_ELT)v;", "= v;")
        name = "p139_native_affine_cmode1" if output_float32 else "p140_native_affine_bf16"
        self.gemm = mx.fast.metal_kernel(name=name, input_names=[
            "Xu", "Codes", "A", "Xsum", "Ws", "Wb", "Wsum", "U", "Chi", "Clo"],
            output_names=["Y"], header=header, source=BODY, compile_options={"math_mode": "safe"})
        self.calls = 0
        self.pack_calls = 0

    def prepare(self, weight):
        from .._vendor.fastvideo_mlx.fastwan import QuantizedMatrix
        if (not isinstance(weight, QuantizedMatrix) or
            (weight.spec.mode, weight.spec.bits, weight.spec.group_size) != ("affine", 8, 64) or
            weight.dequantized_dtype != mx.bfloat16 or weight.biases is None):
            raise ValueError("VSA requires affine W8/group64 BF16 weights")
        codes = mx.contiguous(weight.weight).view(mx.uint8)
        n, k = codes.shape
        if n <= 0 or k <= 0 or k % 64:
            raise ValueError("Invalid affine matrix shape")
        scales, biases = [mx.contiguous(x.astype(mx.bfloat16)) for x in (weight.scales, weight.biases)]
        sums, high, low = self.weights(inputs=[codes, scales], grid=(n*(k//64)*32, 1, 1),
            threadgroup=(32, 1, 1), output_shapes=[(n, k//64)]*3,
            output_dtypes=[mx.int16, mx.bfloat16, mx.bfloat16])
        result = dict(codes=codes, scales=scales, biases=biases, sums=sums, high=high, low=low)
        mx.eval(*result.values())
        return result

    def pack(self, x):
        if x.ndim != 2 or x.dtype != mx.bfloat16 or min(x.shape) <= 0 or x.shape[1] % 64:
            raise ValueError("Expected nonempty BF16 group64 rows")
        m, k = x.shape
        self.pack_calls += 1
        return self.quantize(inputs=[mx.contiguous(x)], template=[("K", k)],
            grid=(256, m, 1), threadgroup=(256, 1, 1),
            output_shapes=[(m, k), (m, k//64), (m, k//64), (m, k//64)],
            output_dtypes=[mx.uint8, mx.bfloat16, mx.int16, mx.bfloat16])

    @staticmethod
    def _operands(packed, prepared):
        xu, scale, sums, scaled_sum = packed
        def device_operand(value):
            # MLX 0.32 binds inputs with fewer than 8 elements in constant
            # address space. MPP tensors require device storage; unused tail
            # padding does not change their logical extent or arithmetic.
            return mx.pad(value.reshape(-1), (0, 8-value.size)) if value.size < 8 else value
        return [xu, prepared["codes"], device_operand(scale), sums,
            device_operand(prepared["scales"]), device_operand(prepared["biases"]),
            prepared["sums"], device_operand(scaled_sum), device_operand(prepared["high"]), device_operand(prepared["low"])]

    def native(self, packed, prepared):
        m, k = packed[0].shape
        n = prepared["codes"].shape[0]
        return self.gemm(inputs=self._operands(packed, prepared),
            template=[("M", m), ("K", k), ("N", n)],
            grid=(((n+63)//64)*128, (m+63)//64, 1), threadgroup=(128, 1, 1),
            output_shapes=[(m, n)], output_dtypes=[self.output_dtype])[0]

    def __call__(self, x, prepared, *, packed=None):
        if x.shape[1] != prepared["codes"].shape[1]:
            raise ValueError("Activation and weight inner dimensions differ")
        if packed is None:
            packed = self.pack(x)
        elif packed[0].shape != x.shape:
            raise ValueError("Packed activation shape differs from input")
        result = self.native(packed, prepared)
        self.calls += 1
        return result.astype(mx.bfloat16)
