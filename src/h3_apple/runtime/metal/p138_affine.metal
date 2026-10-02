// MFA_REQUIRE_MSL4
#include <metal_stdlib>
#include <metal_tensor>
#include <MetalPerformancePrimitives/MetalPerformancePrimitives.h>
using namespace metal;
using namespace mpp::tensor_ops;
#define VPIPE_ELT float
template <bool UB, int CM>
constexpr int gemm_u8q_sw()
{
  return (UB ? 1 : 2) * 64 + (UB ? (CM == 1 ? 1 : 2) : 3) * 64;
}

template <int BITS, bool SPLIT, int STRIP = 8, bool UB_MMA = true,
          int CMODE = 0, typename AP, typename XP, typename SP, typename BP, typename WP>
static inline void gemm_u8q_impl(
    const device uint8_t* xu, const device uchar* codes,
    AP as, XP xs,
    SP ws, BP wb,
    WP wsum, const device VPIPE_ELT* uf,
    const device VPIPE_ELT* c_hi, const device VPIPE_ELT* c_lo,
    device VPIPE_ELT* y, const device VPIPE_ELT* bias, int has_bias,
    device float* planes, int gpp,
    threadgroup int* Ss, int K, int N, int M, uint3 tgid, uint lid)
{
  static_assert(CMODE == 0 || UB_MMA, "CMODE 1 rides the post-loop matmul");
  constexpr int BM = 64, BN = 64, SG = 4, CAP = 32, KC = 64;
  // Staged per group: [a | u] rows then [s | b | c] cols in the per-group
  // form; the matmul forms read only a, s (and c under CMODE 0).
  constexpr int NR = UB_MMA ? 1 : 2;
  constexpr int NC = UB_MMA ? (CMODE == 1 ? 1 : 2) : 3;
  constexpr int SW = gemm_u8q_sw<UB_MMA, CMODE>();
  static_assert(SW == NR * BM + NC * BN, "staging layout");
  using TX = tensor<device uint8_t, dextents<int32_t, 2>, tensor_inline>;
  using WE = conditional_t<BITS == 4, uint4b_format, uint8_t>;
  using TW = tensor<device WE, dextents<int32_t, 2>, tensor_inline>;
  TX tX(const_cast<device uint8_t*>(xu), dextents<int32_t, 2>(K, M));
  // A 4-bit tensor's handle is a byte pointer and its extents count
  // ELEMENTS, so the packed row of K nibbles is K wide here.
  TW tW(const_cast<device uchar*>(codes), dextents<int32_t, 2>(K, N));

  constexpr auto desc = matmul2d_descriptor(
      BM, BN, KC, /*transpose_left=*/false, /*transpose_right=*/true,
      /*relaxed_precision=*/false, matmul2d_descriptor::mode::multiply);
  matmul2d<desc, execution_simdgroups<SG>> op;

  const int m0 = (int)tgid.y * BM;
  const int n0 = (int)tgid.x * BN;
  const int G = K / KC;
  int gbeg = 0, gend = G;
  if constexpr (SPLIT) {
    gbeg = (int)tgid.z * gpp;
    gend = min(G, gbeg + gpp);
  }
  auto mX0 = tX.slice(0, m0);
  auto mW0 = tW.slice(0, n0);
  auto cP = op.template get_destination_cooperative_tensor<
      decltype(mX0), decltype(mW0), int32_t>();

  uchar lr[CAP], lc[CAP];
#pragma clang loop unroll(full)
  for (int i = 0; i < CAP; ++i) {
    const auto ids = cP.get_multidimensional_index((uint16_t)i);
    lc[i] = (uchar)ids[0];
    lr[i] = (uchar)ids[1];
  }
  float facc[CAP];
#pragma clang loop unroll(full)
  for (int i = 0; i < CAP; ++i) { facc[i] = 0.0f; }

  for (int g0 = gbeg; g0 < gend; g0 += STRIP) {
    threadgroup_barrier(mem_flags::mem_threadgroup);
    for (int e = (int)lid; e < STRIP * SW; e += SG * 32) {
      const int sidx = e / SW, r = e - sidx * SW;
      const int g = g0 + sidx;
      int v = 0;
      if (g < gend) {
        if (r < NR * BM) {
          const int gm = m0 + (r < BM ? r : r - BM);
          if (gm < M) {
            const float a = (float)as[(int64_t)gm * G + g];
            v = as_type<int>(r < BM
                ? a : a * (float)xs[(int64_t)gm * G + g]);
          }
        } else {
          const int rc = r - NR * BM;
          const int which = rc / BN;          // 0: s, 1: b or c, 2: c
          const int gn = n0 + (rc - which * BN);
          if (gn < N) {
            if (which == 0) {
              v = as_type<int>((float)ws[(int64_t)gn * G + g]);
            } else if (which == 1 && !UB_MMA) {
              v = as_type<int>((float)wb[(int64_t)gn * G + g]);
            } else {
              v = -128 * (int)wsum[(int64_t)gn * G + g];
            }
          }
        }
      }
      Ss[e] = v;
    }
    threadgroup_barrier(mem_flags::mem_threadgroup);
    for (int sidx = 0; sidx < STRIP; ++sidx) {
      const int g = g0 + sidx;
      if (g >= gend) { break; }
      auto mX = tX.slice(g * KC, m0);
      auto mW = tW.slice(g * KC, n0);
      op.run(mX, mW, cP);
      const threadgroup int* sa = Ss + sidx * SW;
      const threadgroup int* su = sa + BM;             // per-group form
      const threadgroup int* ss = sa + NR * BM;
      const threadgroup int* sb = ss + BN;             // per-group form
      const threadgroup int* sc = ss + (NC - 1) * BN;  // last column set
#pragma clang loop unroll(full)
      for (int i = 0; i < CAP; ++i) {
        const int p = CMODE == 1 ? cP[(uint16_t)i]
                                 : cP[(uint16_t)i] + sc[lc[i]];
        const float a = as_type<float>(sa[lr[i]]);
        if constexpr (UB_MMA) {
          facc[i] += a * as_type<float>(ss[lc[i]]) * (float)p;
        } else {
          const float u = as_type<float>(su[lr[i]]);
          facc[i] += a * as_type<float>(ss[lc[i]]) * (float)p +
                     u * as_type<float>(sb[lc[i]]);
        }
      }
    }
  }

  if constexpr (UB_MMA) {
    // The zero-point term as one matmul over ALL G groups, accumulated
    // into a cooperative f32 tensor and added in REGISTERS: the f16 ->
    // f32 destination of this tile has the int8 destination's element
    // layout (probed by gemm_i8.g64_register_acc, which fails if that
    // ever changes), so element i of both is the same (row, col). Under
    // a split the whole term belongs to plane 0 -- the fold is a plain
    // sum of the planes, and a slice from gbeg would contract to the
    // tensor's END, not to gend, which is how the first version
    // double-counted.
    if (!SPLIT || tgid.z == 0) {
      using TU = tensor<device VPIPE_ELT, dextents<int32_t, 2>,
                        tensor_inline>;
      TU tU(const_cast<device VPIPE_ELT*>(uf), dextents<int32_t, 2>(G, M));
      TU tB(const_cast<device VPIPE_ELT*>(wb), dextents<int32_t, 2>(G, N));
      constexpr auto descA = matmul2d_descriptor(
          BM, BN, static_cast<int>(dynamic_extent),
          /*transpose_left=*/false, /*transpose_right=*/true,
          /*relaxed_precision=*/false,
          matmul2d_descriptor::mode::multiply_accumulate);
      matmul2d<descA, execution_simdgroups<SG>> opA;
      auto mU = tU.slice(0, m0);
      auto mB = tB.slice(0, n0);
      auto cF = opA.template get_destination_cooperative_tensor<
          decltype(mU), decltype(mB), float>();
#pragma clang loop unroll(full)
      for (int i = 0; i < CAP; ++i) { cF[(uint16_t)i] = 0.0f; }
      opA.run(mU, mB, cF);
      if constexpr (CMODE == 1) {
        TU tA(const_cast<device VPIPE_ELT*>(as), dextents<int32_t, 2>(G, M));
        TU tH(const_cast<device VPIPE_ELT*>(c_hi),
              dextents<int32_t, 2>(G, N));
        TU tL(const_cast<device VPIPE_ELT*>(c_lo),
              dextents<int32_t, 2>(G, N));
        auto mA = tA.slice(0, m0);
        auto mH = tH.slice(0, n0);
        auto mL = tL.slice(0, n0);
        opA.run(mA, mH, cF);
        opA.run(mA, mL, cF);
      }
#pragma clang loop unroll(full)
      for (int i = 0; i < CAP; ++i) { facc[i] += cF[(uint16_t)i]; }
    }
  }

#pragma clang loop unroll(full)
  for (int i = 0; i < CAP; ++i) {
    const int gn = n0 + (int)lc[i], gm = m0 + (int)lr[i];
    if (gm < M && gn < N) {
      float v = facc[i];
      if constexpr (SPLIT) {
        planes[((int64_t)tgid.z * M + gm) * N + gn] = v;
      } else {
        if (has_bias != 0) { v += (float)bias[gn]; }
        y[(int64_t)gm * N + gn] = (VPIPE_ELT)v;
      }
    }
  }
}

