// Link against the candidate libvpipe; no model weights or GEMMs are needed.
#include "apple-silicon/metal-compute/metal-compute.h"
#include "generative-models/shared/i8-gemm.h"

#include <cstdio>
#include <cstdlib>
#include <stdexcept>

static void require(bool condition, const char* message) {
  if (!condition) { throw std::runtime_error(message); }
}

int main() {
  using vpipe::genai::I8GemmContext;
  using vpipe::metal_compute::MetalCompute;
  try {
    unsetenv("VPIPE_I8_SPLITK_MAX_MB");
    MetalCompute mc(nullptr);
    require(mc.valid() && mc.supports_matrix_cores(), "M5 matrix cores required");
    I8GemmContext normal(&mc, true, true);
    require(normal.enabled() && normal.split_available(), "INT8 kernels unavailable");
    require(normal.restore_plan(4096, 5376, 14336, 2), "legal split rejected");
    require(normal.restore_plan(4096, 5376, 14336, 2), "same plan not idempotent");
    require(!normal.restore_plan(4096, 5376, 14336, 0), "conflicting plan accepted");
    require(!normal.restore_plan(4096, 21504, 5376, 999), "invalid split accepted");
    require(!normal.restore_plan(32, 5376, 14336, 2), "ineligible shape accepted");
    setenv("VPIPE_I8_SPLITK_MAX_MB", "1", 1);
    I8GemmContext tight(&mc, true, true);
    require(!tight.restore_plan(4096, 5376, 14336, 2), "insufficient budget accepted");
    require(tight.restore_plan(4096, 5376, 14336, 0), "legal unsplit plan rejected");
    std::puts("{\"legal\":true,\"conflict_rejected\":true,\"invalid_rejected\":true,\"insufficient_budget_rejected\":true}");
    return 0;
  } catch (const std::exception& error) {
    std::fprintf(stderr, "%s\n", error.what());
    return 1;
  }
}
