
constexpr int cB=1, cHq=HEADS, cHk=HEADS, cQL=TOKEN_COUNT, cKL=TOKEN_COUNT;
constexpr int cD=128, cGQA=1;
constexpr int V6NAX_SPARSE_BQ=64, V6NAX_SPARSE_BK=32, V6NAX_SPARSE_BD=128;
constexpr int V6NAX_SPARSE_WM=4, V6NAX_SPARSE_TQ=1, V6NAX_SPARSE_TD=8, V6NAX_SPARSE_TK=2;
const float V6NAX_SPARSE_DOT_SCALE=scale_value[0]*1.44269504089f;


// V6NAX sparse kernel body — adapted from V6NAX forward (NAAttentionKernel.cpp:2767-2960).
// Key sparse modifications:
//   - block_mask scan in outer loop: skip kb when mask[qi, kb] == false
//   - K/V base pointers saved; per-iteration jump via kb offset (no linear advance)
//   - is_last_q/is_last_k remainder logic dropped (front-end enforces qL/kL % BT == 0)
//   - All-False row zero-output preservation (v2.34.0 contract)

// Per-shape-emitted constants (constexpr at JIT time):
//   cB, cHq, cHk, cQL, cKL, cD, cNQ, cNK, cGQA, V6NAX_SPARSE_BQ, V6NAX_SPARSE_BK,
//   V6NAX_SPARSE_BD, V6NAX_SPARSE_WM, V6NAX_SPARSE_TQ, V6NAX_SPARSE_TD,
//   V6NAX_SPARSE_TK, V6NAX_SPARSE_DOT_SCALE

ulong3 tidl{threadgroup_position_in_grid.x,
            threadgroup_position_in_grid.y,
            threadgroup_position_in_grid.z};

// BHND strides (Q seq stride = D, head stride = qL * D, batch stride = Hq * qL * D)
const long Q_seq_stride = cD;
const long K_seq_stride = cD;
const long V_seq_stride = cD;
const long O_seq_stride = cD;
const long Q_head_stride = cQL * cD;
const long K_head_stride = cKL * cD;
const long V_head_stride = cKL * cD;
const long O_head_stride = cQL * cD;
const long Q_batch_stride = cHq * cQL * cD;
const long K_batch_stride = cHk * cKL * cD;
const long V_batch_stride = cHk * cKL * cD;
const long O_batch_stride = cHq * cQL * cD;

Q += PREFIX_TILE_COUNT * 64 * Q_seq_stride + tidl.z * Q_batch_stride
   + tidl.y * Q_head_stride
   + tidl.x * V6NAX_SPARSE_BQ * Q_seq_stride;
ulong kv_head_idx = ulong(tidl.y) / ulong(cGQA);
device const int8_t* K_base = K + tidl.z * K_batch_stride + kv_head_idx * K_head_stride;
device const T* V_base = V + tidl.z * V_batch_stride + kv_head_idx * V_head_stride;
O += PREFIX_TILE_COUNT * 64 * O_seq_stride + tidl.z * O_batch_stride
   + tidl.y * O_head_stride
   + tidl.x * V6NAX_SPARSE_BQ * O_seq_stride;

const uint qi = uint(tidl.x);

// Mask offset for this (b, hq, qi). Emitted per mask_ndim by source-gen.
// 2-D: mask_qrow_base = block_mask + qi * cNK
// 3-D: mask_qrow_base = block_mask + tidl.y * cNQ * cNK + qi * cNK
// 4-D: mask_qrow_base = block_mask + tidl.z * cHq * cNQ * cNK
//                                  + tidl.y * cNQ * cNK + qi * cNK
const float scale2 = V6NAX_SPARSE_DOT_SCALE;

using otile_t = NAXTile<float, V6NAX_SPARSE_TQ, V6NAX_SPARSE_TD>;
otile_t Otile;
Otile.clear();

const short tm = 16 * V6NAX_SPARSE_TQ * simdgroup_index_in_threadgroup;
Q += tm * int(Q_seq_stride);

constexpr short kRowsPT = otile_t::kRowsPerThread;
metal::vec<float, kRowsPT> max_score;
metal::vec<float, kRowsPT> sum_score{0};
STEEL_PRAGMA_UNROLL
for (short i = 0; i < kRowsPT; ++i) {
  max_score[i] = Limits<float>::finite_min;
}


const int route_offset = (int(tidl.y) * VIDEO_TILE_COUNT + int(qi)) * K_MAX;
const int route_count = block_num[int(tidl.y) * VIDEO_TILE_COUNT + int(qi)];
for (int route_half = 0; route_half < route_count * 2; ++route_half) {
  const int route = block_idx[route_offset + route_half / 2];
  const int half_offset = (route_half % 2) * 32;
  const int key_valid = block_sizes[route] - half_offset;
  if (key_valid <= 0) continue;
  const int kb = route * 2 + route_half % 2;
  // Per-iteration K and V pointers — JUMP via kb (no incremental advance).
  device const int8_t* K_kb = K_base + kb * V6NAX_SPARSE_BK * int(K_seq_stride);
  device const T* V_kb = V_base + kb * V6NAX_SPARSE_BK * int(V_seq_stride);

  using stile_t = NAXTile<float, V6NAX_SPARSE_TQ, V6NAX_SPARSE_TK>;
  stile_t Stile;
  Stile.clear();

  // Only QK is replaced. The original 32-key online softmax and float
  // PV fragments below are retained verbatim.
  constexpr auto i8desc = mpp::tensor_ops::matmul2d_descriptor(
      16, 32, 32, false, true, true,
      mpp::tensor_ops::matmul2d_descriptor::mode::multiply_accumulate);
  mpp::tensor_ops::matmul2d<i8desc, metal::execution_simdgroup> intqk;
  auto qt = tensor(const_cast<device int8_t*>(Q), dextents<int, 2>(128, 16));
  auto kt = tensor(const_cast<device int8_t*>(K_kb), dextents<int, 2>(128, 32));
  auto qm = qt.slice<32, 16>(0, 0);
  auto km = kt.slice<32, 32>(0, 0);
  auto dots = intqk.get_destination_cooperative_tensor<decltype(qm), decltype(km), int32_t>();
  STEEL_PRAGMA_UNROLL
  for (ushort i = 0; i < dots.get_capacity(); ++i)
    if (dots.is_valid_element(i)) dots[i] = 0;
  STEEL_PRAGMA_UNROLL
  for (int d = 0; d < 128; d += 32) {
    auto qslice = qt.slice<32, 16>(d, 0);
    auto kslice = kt.slice<32, 32>(d, 0);
    intqk.run(qslice, kslice, dots);
  }
  NAXTile<int32_t, V6NAX_SPARSE_TQ, V6NAX_SPARSE_TK> IStile;
  STEEL_PRAGMA_UNROLL
  for (ushort i = 0; i < stile_t::kElemsPerTile; ++i) IStile.elems()[i] = dots[i];
  const short2 sc = stile_t::NAXFrag_t::get_coord();
  STEEL_PRAGMA_UNROLL
  for (short ik = 0; ik < V6NAX_SPARSE_TK; ++ik) {
    thread auto& sf = Stile.frag_at(0, ik);
    thread auto& si = IStile.frag_at(0, ik);
    STEEL_PRAGMA_UNROLL
    for (short i = 0; i < stile_t::kFragThrRows; ++i) {
      const int qr = PREFIX_TILE_COUNT * 64 + int(qi) * 64 + tm + sc.y + i * stile_t::kFragRowsJump;
      STEEL_PRAGMA_UNROLL
      for (short j = 0; j < stile_t::kFragThrCols; ++j) {
        const int kr = kb * 32 + ik * 16 + sc.x + j;
        const int e = i * stile_t::kFragThrCols + j;
        if constexpr (DEBUG) {
          const long off = (((long(tidl.y) * VIDEO_TILE_COUNT + qi) * K_MAX + route_half/2) * 64 + qr - (PREFIX_TILE_COUNT + qi)*64) * 64 + kr - route*64;
          DebugDots[off] = si[e];
        }
        sf[e] = (float(si[e]) * Qscale[long(tidl.y)*TOKEN_COUNT+qr]
            * Kscale[long(tidl.y)*TOKEN_COUNT+kr]
            + Qcorrection[long(tidl.y)*TOKEN_COUNT+kr]) * scale2;
      }
    }
  }

  if (key_valid < 32) {
    const short sn = stile_t::NAXFrag_t::get_coord().x;
    STEEL_PRAGMA_UNROLL
    for (short ik = 0; ik < V6NAX_SPARSE_TK; ++ik) {
      thread auto& frag = Stile.frag_at(0, ik);
      STEEL_PRAGMA_UNROLL
      for (short ii = 0; ii < stile_t::kFragThrRows; ++ii) {
        STEEL_PRAGMA_UNROLL
        for (short jj = 0; jj < stile_t::kFragThrCols; ++jj) {
          if (ik * 16 + sn + jj >= key_valid)
            frag[ii * stile_t::kFragThrCols + jj] = Limits<float>::finite_min;
        }
      }
    }
  }


  // Online softmax (Apple lines 380-409)
  metal::vec<float, kRowsPT> new_max;
  metal::vec<float, kRowsPT> factor;
  STEEL_PRAGMA_UNROLL
  for (short i = 0; i < kRowsPT; ++i) new_max[i] = max_score[i];
  Stile.template row_reduce<MaxOp>(new_max);
  Stile.template row_bin_op<ExpSubOp>(new_max);
  STEEL_PRAGMA_UNROLL
  for (short i = 0; i < kRowsPT; ++i) {
    factor[i] = fast::exp2(max_score[i] - new_max[i]);
    max_score[i] = new_max[i];
  }
  STEEL_PRAGMA_UNROLL
  for (short i = 0; i < kRowsPT; ++i) {
    sum_score[i] = sum_score[i] * factor[i];
  }
  Stile.template row_reduce<SumOp>(sum_score);
  Otile.template row_bin_op<MulOp>(factor);

  simdgroup_barrier(mem_flags::mem_none);

  // PV matmul (Apple lines 417-452)
  STEEL_PRAGMA_UNROLL
  for (short iq = 0; iq < V6NAX_SPARSE_TQ; iq++) {
    STEEL_PRAGMA_UNROLL
    for (short id = 0; id < V6NAX_SPARSE_TD; id += 2) {
      if (V6NAX_SPARSE_BD == 128) {
        if (id == 4) {
          threadgroup_barrier(mem_flags::mem_none);
        }
      }
      STEEL_PRAGMA_UNROLL
      for (short ik = 0; ik < V6NAX_SPARSE_TK; ik++) {
        NAXTile<T, 1, 2> Vtile;
        const int V_load_off = ik * 16 * int(V_seq_stride) + id * 16;
        Vtile.load(V_kb + V_load_off, int(V_seq_stride));
        otile_t::NAXFrag_t::mma(
            Otile.frag_at(iq, id),
            Otile.frag_at(iq, id + 1),
            Stile.frag_at(iq, ik),
            metal::false_type{},
            Vtile.frag_at(0, 0),
            Vtile.frag_at(0, 1),
            metal::false_type{});
      }
    }
  }
}

// Normalize + store (Apple lines 461-481)
threadgroup_barrier(mem_flags::mem_none);
metal::vec<float, kRowsPT> rcp;
STEEL_PRAGMA_UNROLL
for (short i = 0; i < kRowsPT; ++i) {
  // All-False row preservation (v2.34.0 contract): if sum_score == 0 → output 0
  
  const int query_row = tm + i * otile_t::kFragRowsJump + otile_t::NAXFrag_t::get_coord().y;
  rcp[i] = (sum_score[i] > 0.f && query_row < block_sizes[PREFIX_TILE_COUNT + qi])
      ? (1.f / sum_score[i]) : 0.f;
}
Otile.template row_bin_op<MulOp>(rcp);
O += tm * int(O_seq_stride);
Otile.store(O, int(O_seq_stride));

