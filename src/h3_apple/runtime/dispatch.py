"""Fixed VSA W8A8 projections, shared QKV packing and INT8 QK attention."""
import time

KEYS = ("attn.to_q.weight", "attn.to_k.weight", "attn.to_v.weight",
        "attn.to_out.0.weight", "ff.net.0.proj.weight", "ff.net.2.weight")
_active = False


class Dispatch:
    def __init__(self, dit):
        from .._vendor.fastvideo_mlx import minimax_h3 as model
        from . import sparse
        self.model, self.sparse, self.dit = model, sparse, dit
        self.prepared = {}
        self.preparation_seconds = 0.0
        self.projection = self.attention = None
        self.old_linear, self.old_attention = model.linear, sparse._implementation
        self.qkv = {id(block[name]): (layer, position)
                    for layer, block in enumerate(dit.blocks)
                    for position, name in enumerate(KEYS[:3])}
        self._pending = None
        self.reuses = 0

    def __enter__(self):
        global _active
        if _active:
            raise RuntimeError("VSA dispatch contexts cannot overlap")
        _active = True
        try:
            from .affine_native import NativeAffineW8A8
            from .qk_smooth import SmoothQKSparse
            self.projection = NativeAffineW8A8(output_float32=False)
            started = time.perf_counter()
            for block in self.dit.blocks:
                for name in KEYS:
                    weight = block[name]
                    self.prepared[id(weight)] = self.projection.prepare(weight)
            self.preparation_seconds = time.perf_counter() - started
            self.model.linear = self.linear
            self.attention = SmoothQKSparse(inputs_prevalidated=True)
            self.sparse._implementation = self.attention
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def linear(self, x, weight, bias=None):
        # Hold the input strongly. Only consecutive K/V calls for this layer and
        # this exact input may reuse Q's packed activation.
        pending, self._pending = self._pending, None
        prepared = self.prepared.get(id(weight))
        if prepared is None:
            return self.old_linear(x, weight, bias)
        packed = None
        member = self.qkv.get(id(weight))
        if member is not None:
            layer, position = member
            if position == 0:
                packed = self.projection.pack(x)
                self._pending = (x, packed, layer, 1)
            elif pending is not None and pending[0] is x and pending[2:] == (layer, position):
                packed = pending[1]
                self.reuses += 1
                if position == 1:
                    self._pending = (x, packed, layer, 2)
        output = self.projection(x, prepared, packed=packed)
        return output if bias is None else output + bias

    def summary(self):
        return dict(mode="VSA", projection_calls=self.projection.calls,
                    int8_fine_calls=self.attention.calls,
                    preparation_seconds=self.preparation_seconds,
                    activation_pack_calls=self.projection.pack_calls,
                    qkv_pack_reuses=self.reuses, native_output_dtype="bfloat16",
                    precision_contract="Original affine weights, approximate INT8 arithmetic; no BF16 dequantization residual")

    def __exit__(self, *_):
        global _active
        self._pending = None
        self.model.linear = self.old_linear
        self.sparse._implementation = self.old_attention
        _active = False
        self.prepared.clear()
