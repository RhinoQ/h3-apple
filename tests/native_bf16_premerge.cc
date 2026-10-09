#include "generative-models/minimax-h3/bf16-premerge.h"
#include <cassert>
#include <iostream>

namespace h3 = vpipe::genai::minimax_h3;

int main()
{
  // Binary fractions keep these scalar double-precision dot products exact
  // in FP32 too. 257 rows crosses the implementation's 256-row band.
  constexpr int n = 257, k = 13, rank = 7;
  std::vector<std::uint16_t> w(n*k), a(rank*k), b(n*rank), out(n*k+2, 0x1234);
  for (int i=0; i<n*k; ++i) w[i]=h3::premerge_bf16(float(i%17-8)/16);
  for (int i=0; i<rank*k; ++i) a[i]=h3::premerge_bf16(float(i%11-5)/128);
  for (int i=0; i<n*rank; ++i) b[i]=h3::premerge_bf16(float(i%13-6)/64);
  const auto before=w;
  h3::premerge_bf16_weight(w.data(),a.data(),b.data(),out.data()+1,n,k,rank);
  for (int row=0; row<n; ++row) for (int col=0; col<k; ++col) {
    double delta=0;
    for (int r=0; r<rank; ++r) {
      delta += double(h3::premerge_f32(b[row*rank+r])) *
               double(h3::premerge_f32(a[r*k+col]));
    }
    const float value=float(double(h3::premerge_f32(w[row*k+col]))+delta);
    const auto bits=std::bit_cast<std::uint32_t>(value);
    // Independent nearest-even selection between neighboring BF16 values.
    std::uint16_t expected=std::uint16_t(bits>>16);
    const auto discarded=bits&0xffff;
    if (discarded>0x8000 || (discarded==0x8000 && (expected&1))) ++expected;
    assert(out[1+row*k+col]==expected);
  }
  assert(w==before && out.front()==0x1234 && out.back()==0x1234);
  assert(h3::premerge_bf16(std::bit_cast<float>(0x3f808000u))==0x3f80);
  assert(h3::premerge_bf16(std::bit_cast<float>(0x3f818000u))==0x3f82);
  bool rejected=false;
  try {h3::premerge_bf16_weight(w.data(),a.data(),b.data(),w.data(),n,k,rank);}
  catch (const std::invalid_argument&) {rejected=true;}
  assert(rejected);
  rejected=false;
  try {h3::premerge_bf16(std::bit_cast<float>(0x7fc00000u));}
  catch (const std::invalid_argument&) {rejected=true;}
  assert(rejected);
  std::cout << "BF16 premerge: scalar oracle, tail, ties, source and guards pass\n";
}
