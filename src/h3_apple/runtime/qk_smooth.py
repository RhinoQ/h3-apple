"""P138 Q-only: centered INT8 QK, original P085 float PV/softmax.

Q mean restoration follows SageAttention2 Eq.4; this is a local VSA adaptation,
not its CUDA implementation or an INT4/FP8 reproduction. Public API unchanged.
"""
from pathlib import Path
import numpy as np
from .sparse import validate_inputs

ACTIVE = r"""
const uint i = thread_position_in_grid.x;
if (i >= ENTRIES) return;
const int slot = i % KMAX;
const int q = (i / KMAX) % QUERIES;
const int h = i / (KMAX * QUERIES);
if (slot < Counts[h*QUERIES+q])
  atomic_fetch_or_explicit(Used + h*BLOCKS + Indices[i], 1u, memory_order_relaxed);
"""

BLOCK_SUM = r"""
const int b = threadgroup_position_in_grid.x;
const int h = threadgroup_position_in_grid.y;
const int d = thread_position_in_threadgroup.x;
float sum = 0;
if (!QUERY || b >= PREFIX)
  for (int r = 0; r < Sizes[b]; ++r)
    sum += float(X[(long(b*64+r)*HEADS+h)*128+d]);
Sum[(long(h)*BLOCKS+b)*128+d] = sum;
"""

MEAN = r"""
const int h = threadgroup_position_in_grid.x;
const int d = thread_position_in_threadgroup.x;
float sum = 0;
for (int b = 0; b < BLOCKS; ++b) sum += Sum[(long(h)*BLOCKS+b)*128+d];
Mean[h*128+d] = sum / float(COUNT);
"""

PACK = r"""
const int r = threadgroup_position_in_grid.x;
const int h = threadgroup_position_in_grid.y;
const int lane = thread_index_in_simdgroup;
const bool valid = r%64 < Sizes[r/64] && (QUERY ? r/64 >= PREFIX : Used[h*BLOCKS+r/64] != 0);
float values[4];
float peak = 0, correction = 0;
#pragma clang loop unroll(full)
for (int i=0; i<4; ++i) {
  const int d=lane*4+i;
  values[i] = valid ? float(X[(long(r)*HEADS+h)*128+d])-Center[h*128+d] : 0;
  peak = max(peak, abs(values[i]));
  if (!QUERY) correction += Qmean[h*128+d]*values[i];
}
peak = simd_max(peak);
correction = simd_sum(correction);
const float scale = peak > 0 ? peak/127.0f : 1.0f/127.0f;
if (lane==0) { Scale[long(h)*TOKENS+r]=scale; Correction[long(h)*TOKENS+r]=correction; }
#pragma clang loop unroll(full)
for (int i=0; i<4; ++i)
  Codes[(long(h)*TOKENS+r)*128+lane*4+i] = int8_t(clamp(int(rint(values[i]/scale)), -127, 127));
"""


class SmoothQKSparse:
    def __init__(self, *, inputs_prevalidated=False):
        import mlx.core as mx
        self.inputs_prevalidated = inputs_prevalidated
        self.calls = 0
        def kernel(name, inputs, outputs, body, header="", atomic=False):
            return mx.fast.metal_kernel(name=name, input_names=inputs, output_names=outputs,
                source=body, header=header, atomic_outputs=atomic, compile_options={"math_mode":"safe"})
        self.active = kernel("p138_selected_keys", ["Indices","Counts"], ["Used"], ACTIVE, atomic=True)
        self.block_sum = kernel("p138_qk_block_sum", ["X","Sizes"], ["Sum"], BLOCK_SUM)
        self.mean = kernel("p138_qk_mean", ["Sum"], ["Mean"], MEAN)
        self.quantize = kernel("p138_centered_token_pack", ["X","Center","Qmean","Sizes","Used"],
            ["Codes","Scale","Correction"], PACK)
        metal = Path(__file__).with_name("metal")
        self.attention = kernel("p138_selected_centered_qk", ["Q","K","V","Qscale","Kscale","Qcorrection",
            "block_idx","block_num","block_sizes","scale_value"], ["O","DebugDots"],
            (metal/"p138_qk_smooth.metal").read_text(), (metal/"p085_nax_header.metal").read_text())

    def pack(self, q, k, v, idx, num, g):
        import mlx.core as mx
        n, heads, _ = q.shape
        blocks = n//64
        sizes = mx.array(g.variable_block_sizes.astype(np.int32))
        used = self.active(inputs=[mx.contiguous(idx),mx.contiguous(num)],
            template=[("ENTRIES",idx.size),("KMAX",idx.shape[-1]),("QUERIES",g.num_video_tiles),("BLOCKS",blocks)],
            grid=(((idx.size+255)//256)*256,1,1),threadgroup=(256,1,1),
            output_shapes=[(heads,blocks)],output_dtypes=[mx.uint32],init_value=0)[0]
        means = []
        for query,x in [(True,q),(False,k)]:
            sums = self.block_sum(inputs=[mx.contiguous(x),sizes],
                template=[("HEADS",heads),("BLOCKS",blocks),("PREFIX",g.num_prefix_tiles),("QUERY",query)],
                grid=(blocks*128,heads,1),threadgroup=(128,1,1),
                output_shapes=[(heads,blocks,128)],output_dtypes=[mx.float32])[0]
            count = int(sum(g.variable_block_sizes[g.num_prefix_tiles:])) if query else int(sum(g.variable_block_sizes))
            means.append(self.mean(inputs=[sums],template=[("BLOCKS",blocks),("COUNT",count)],
                grid=(heads*128,1,1),threadgroup=(128,1,1),output_shapes=[(heads,128)],output_dtypes=[mx.float32])[0])
        packed, scales, correction = [], [], None
        for query,x,center in [(True,q,means[0]),(False,k,means[1])]:
            code,scale,corr = self.quantize(inputs=[mx.contiguous(x),center,means[0],sizes,used],
                template=[("HEADS",heads),("BLOCKS",blocks),("PREFIX",g.num_prefix_tiles),("TOKENS",n),("QUERY",query)],
                grid=(n*32,heads,1),threadgroup=(32,1,1),
                output_shapes=[(heads,n,128),(heads,n),(heads,n)],output_dtypes=[mx.int8,mx.float32,mx.float32])
            packed.append(code); scales.append(scale)
            if not query: correction=corr
        packed.append(mx.contiguous(v.transpose(1,0,2)))
        return packed,scales,correction,sizes

    def run_packed(self, packed, scales, correction, sizes, idx, num, g, scale, *, debug=False):
        import mlx.core as mx
        heads,n,_=packed[0].shape
        return self.attention(inputs=[*packed,*scales,correction,mx.contiguous(idx),mx.contiguous(num),sizes,mx.array([scale],mx.float32)],
            template=[("T",mx.bfloat16),("HEADS",heads),("TOKEN_COUNT",n),("PREFIX_TILE_COUNT",g.num_prefix_tiles),
                ("VIDEO_TILE_COUNT",g.num_video_tiles),("K_MAX",idx.shape[-1]),("DEBUG",debug)],
            grid=(g.num_video_tiles*128,heads,1),threadgroup=(128,1,1),
            output_shapes=[(heads,n,128),(heads,g.num_video_tiles,idx.shape[-1],64,64) if debug else (1,)],
            output_dtypes=[mx.bfloat16,mx.int32],init_value=0)

    def __call__(self,q,k,v,idx,num,g,scale):
        if not self.inputs_prevalidated: validate_inputs(q,k,v,idx,num,g,scale)
        self.calls += 1
        return self.run_packed(*self.pack(q,k,v,idx,num,g),idx,num,g,scale)[0].transpose(1,0,2)
