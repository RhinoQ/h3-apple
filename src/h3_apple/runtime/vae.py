"""P090 experimental VideoVAE SmoothQuant: weight256 / activation512.

Native integer primitives derive from the frozen MIT h3.c source in p087_NOTICE.txt.
The block follows the frozen Apache-2.0 FastVideo VAE; FP32 residual math is retained.
No original checkpoint tensor is replaced or modified.
"""

import mlx.core as mx

from .quantization import HEADER, QHEADER, kernel_body, quantize, linear_fp16


def make_quantizer():
    body = kernel_body("h3_quantize_bf16_int8_groups").replace("bfloat4", "float4")
    expression = "float4(input4[start + local])"
    assert body.count(expression) == 2
    body = body.replace(
        expression, "(float4(input4[start + local]) * inverse4[group * vectors_per_group + local])"
    )
    body = body.replace(
        "scales[row * args.groups + group] = 1.0f;", "scales[row * args.groups + group] = 0.0f;"
    )
    prelude = """uint tid=thread_index_in_threadgroup;
        ushort simdgroup=simdgroup_index_in_threadgroup;
        ushort lane=thread_index_in_simdgroup;
        uint row=threadgroup_position_in_grid.x;
        int8_group_quant_args args={uint(ROWS),uint(COLS),512,uint(COLS/512)};
        device const float4 *inverse4=reinterpret_cast<device const float4 *>(inverse_smoothing);
        """
    quantizer = mx.fast.metal_kernel(
        name="p090_vae_smooth_quant_fp32_group512",
        input_names=["input", "inverse_smoothing"],
        output_names=["output", "scales"],
        header=QHEADER,
        source=prelude + body,
        compile_options={"math_mode": "safe"},
    )
    return quantizer


def make_gemm():
    body = kernel_body("h3_linear_int8_grouped_local_nax_r128x64")
    body = body.replace(
        "constexpr uint SCALE_GROUPS = 14;", "constexpr uint SCALE_GROUPS = INPUT_DIM / 256;"
    )
    body = body.replace("constexpr uint K_TILE = 512;", "constexpr uint K_TILE = 256;").replace(
        "constexpr uint SCALE_GROUP = 1024;", "constexpr uint SCALE_GROUP = 256;"
    )
    body = body.replace(
        "input_scales[row * SCALE_GROUPS + scale_group]",
        "input_scales[row * (SCALE_GROUPS / 2) + scale_group / 2]",
    )
    body = body.replace(
        "threadgroup float local_weight_scales[COLUMN_TILE];",
        "threadgroup float local_weight_scales[COLUMN_TILE * SCALE_GROUPS];",
    )
    old = """    if (tid < COLUMN_TILE)
        local_weight_scales[tid] = weight_scales[column_start + tid];"""
    new = """    for (uint local = tid; local < COLUMN_TILE * SCALE_GROUPS; local += 256) {
        uint column = column_start + local / SCALE_GROUPS;
        uint group = local % SCALE_GROUPS;
        local_weight_scales[local] = weight_scales[column * SCALE_GROUPS + group];
    }"""
    assert old in body
    body = body.replace(old, new)
    factor = "local_weight_scales[(uint)index[0]]"
    assert body.count(factor) == 2
    body = body.replace(
        factor, "local_weight_scales[(uint)index[0] * SCALE_GROUPS + scale_group]", 1
    )
    body = body.replace(
        factor, "local_weight_scales[(uint)index[0] * SCALE_GROUPS + scale_group + 1]", 1
    )
    body = body.replace("(bfloat)totals[element]", "totals[element] + bias[column]")
    prelude = """device int8_t *input=const_cast<device int8_t *>(qx);
    device int8_t *weight=const_cast<device int8_t *>(qw);
    linear_args args={uint(ROWS),uint(INPUT_DIM),uint(OUT_DIM),1};
    uint code=threadgroup_position_in_grid.x;
    ushort tid=thread_index_in_threadgroup;
    """
    return mx.fast.metal_kernel(
        name="p090_vae_w8a8_weight256_act512_fp32_bias",
        input_names=["qx", "qw", "input_scales", "weight_scales", "bias"],
        output_names=["output"],
        header=HEADER,
        source=prelude + body,
        compile_options={"math_mode": "safe"},
    )


class Projection:
    def __init__(self):
        self.quantizer = make_quantizer()
        self.gemm = make_gemm()

    def pack(self, x, inverse):
        if x.dtype != mx.float32 or inverse.dtype != mx.float32 or x.ndim != 2:
            raise ValueError("activation and inverse must be FP32 matrices/vectors")
        m, k = x.shape
        if m <= 0 or k not in (2048, 8192) or inverse.shape != (k,):
            raise ValueError("unsupported VAE activation or inverse shape")
        mp = (m + 127) // 128 * 128
        return self.quantizer(
            inputs=[x, inverse],
            template=[("ROWS", m), ("COLS", k)],
            grid=(mp * 256, 1, 1),
            threadgroup=(256, 1, 1),
            output_shapes=[(mp, k), (mp, k // 512)],
            output_dtypes=[mx.int8, mx.float32],
        )

    def __call__(self, x, qw, ws, bias, inverse):
        if x.ndim < 2 or qw.ndim != 2:
            raise ValueError("projection requires matrix dimensions")
        shape = x.shape
        x = x.reshape(-1, shape[-1])
        m, k = x.shape
        n = qw.shape[0]
        if qw.dtype != mx.int8 or ws.dtype != mx.float32 or bias.dtype != mx.float32:
            raise ValueError("projection weight/scale/bias dtype differs")
        if qw.shape[1] != k or ws.shape != (n, k // 256) or bias.shape != (n,) or n <= 0 or n % 64:
            raise ValueError("projection weight/scale/bias shape differs")
        q, sc = self.pack(x, inverse)
        out = self.gemm(
            inputs=[q, qw, sc, ws, bias],
            template=[("ROWS", m), ("INPUT_DIM", k), ("OUT_DIM", n)],
            grid=((m + 127) // 128 * (n // 64) * 256, 1, 1),
            threadgroup=(256, 1, 1),
            output_shapes=[(m, n)],
            output_dtypes=[mx.float32],
        )[0]
        return out.reshape(*shape[:-1], n)


def prepare(block, calibration, index):
    result = dict(block)
    for j, key in enumerate(("ff.net.0.proj.weight", "ff.net.2.weight")):
        w = block[key]
        if (
            w.dtype != mx.float32
            or w.ndim != 2
            or w.shape[1] not in (2048, 8192)
            or w.shape[0] % 64
        ):
            raise ValueError("prepare requires original FP32 VAE FFN weights")
        a = mx.array(calibration[f"block{index}_projection{j}"])
        if a.dtype != mx.float32 or a.shape != (w.shape[1],):
            raise ValueError("calibration channel vector shape/dtype differs")
        if not bool(mx.all(mx.isfinite(a) & (a >= 0)).item()):
            raise ValueError("calibration ranges must be finite and nonnegative")
        colmax = mx.max(mx.abs(w), axis=0)
        smooth = mx.clip(mx.sqrt(mx.maximum(a, 1e-05) / mx.maximum(colmax, 1e-05)), 1e-05, 100000.0)
        inverse = 1.0 / smooth
        qw, ws = quantize(w * smooth[None, :], 256)
        mx.eval(qw, ws, inverse)
        if not bool(mx.all(mx.isfinite(ws) & (ws > 0)).item()) or not bool(
            mx.all(mx.isfinite(inverse) & (inverse > 0)).item()
        ):
            raise ValueError("nonfinite prepared weight scales or inverse")
        result[f"qweight{j}"] = qw
        result[f"qscale{j}"] = ws
        result[f"inverse{j}"] = inverse
    return dict(sorted(result.items()))


def make_compiled_block(vm, traces, integer=None):
    """One pure graph with explicit current-layer weights; no captured arrays."""
    import mlx.core as mx

    def body(block, x, scale1, scale2, cos, sin, *, num_heads, head_dim, norm_eps, qk_norm_eps):
        traces.append(
            {"shape": list(x.shape), "weight_dtype": str(block["attn.to_q.weight"].dtype)}
        )
        normed = vm._rms_norm_affine(x.astype(mx.float32), block["norm1.weight"], norm_eps).astype(
            x.dtype
        )
        seq_len, batch, hidden = normed.shape
        q, k, v = [
            linear_fp16(
                normed, block[f"attn.to_{name}.weight"], block[f"attn.to_{name}.bias"]
            ).reshape(seq_len, batch, num_heads, head_dim)
            for name in ("q", "k", "v")
        ]
        q = vm._rms_norm_no_affine(q.astype(mx.float32), qk_norm_eps).astype(normed.dtype)
        k = vm._rms_norm_no_affine(k.astype(mx.float32), qk_norm_eps).astype(normed.dtype)
        if cos is not None:
            q, k = vm._apply_rotary(q, k, cos, sin)
        q, k, v = [vm._ct(a, 1, 2, 0, 3).astype(mx.float16) for a in (q, k, v)]
        attended = mx.fast.scaled_dot_product_attention(q, k, v, scale=head_dim ** (-0.5)).astype(
            mx.float32
        )
        attended = vm._ct(attended, 2, 0, 1, 3).reshape(seq_len, batch, hidden)
        attended = linear_fp16(attended, block["attn.to_out.0.weight"], block["attn.to_out.0.bias"])
        x = x + attended * scale1
        normed = vm._rms_norm_affine(x.astype(mx.float32), block["norm2.weight"], norm_eps).astype(
            x.dtype
        )
        if integer is None:
            projected = linear_fp16(
                normed, block["ff.net.0.proj.weight"], block["ff.net.0.proj.bias"]
            )
        else:
            projected = integer(
                normed,
                block["qweight0"],
                block["qscale0"],
                block["ff.net.0.proj.bias"],
                block["inverse0"],
            )
        value, gate = mx.split(projected, 2, axis=-1)
        activated = value * vm._silu(gate)
        if integer is None:
            ff = linear_fp16(activated, block["ff.net.2.weight"], block["ff.net.2.bias"])
        else:
            ff = integer(
                activated,
                block["qweight1"],
                block["qscale1"],
                block["ff.net.2.bias"],
                block["inverse1"],
            )
        return x + ff * scale2

    return mx.compile(body)


from h3_apple._vendor.fastvideo_mlx import minimax_h3_video_vae as _video


class OptimizedVideoVAE(_video.MLXMiniMaxH3VideoVAE):
    """Own prepared weights and the compiled graph for exactly one decode."""

    def __init__(self, base, calibration, observer):
        super().__init__(base.weights, base.config, has_encoder=False)
        if self.config.decoder_num_layers != 36 or any(
            w.dtype != mx.float32 for w in self.weights.values()
        ):
            raise ValueError("Ours requires the complete 36-layer FP32 VideoVAE.")
        self.observer = observer
        self.traces = []
        self.compiled_block = make_compiled_block(_video, self.traces, Projection())
        self._blocks = [prepare(block, calibration, i)
                        for i, block in enumerate(super()._decoder_blocks())]
        self.block_count = 0

    def _decoder_linear(self, x, weight, bias=None):
        return linear_fp16(x, weight, bias)

    def _decoder_block(self, *args, **kwargs):
        result = self.compiled_block(*args, **kwargs)
        if result.dtype != mx.float32 or result.shape != args[1].shape:
            raise ValueError("VAE block changed its FP32 residual shape or dtype.")
        self.block_count += 1
        return result

    def _decode_clip(self, z):
        if z.ndim != 5 or z.shape[0] != 1 or z.dtype != mx.float32:
            raise ValueError("VAE requires a batch-one FP32 latent tile.")
        before = self.block_count
        result = super()._decode_clip(z)
        if self.block_count - before != 36 or result.dtype != mx.float32:
            raise ValueError("Incomplete VAE tile.")
        if not bool(mx.all(mx.isfinite(result)).item()):
            raise ValueError("Nonfinite VAE tile.")
        if mx.get_peak_memory() > 80 * 1024**3:
            raise RuntimeError("MLX peak memory exceeded 80 GiB during video decode.")
        self.observer.tile()
        return result
