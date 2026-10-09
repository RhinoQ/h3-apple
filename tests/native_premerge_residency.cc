// Synthetic, temporary checkpoint: no installed models or machine artifacts.
#define _DARWIN_C_SOURCE
#include "common/session.h"
#include "apple-silicon/metal-compute/metal-compute.h"
#include "generative-models/weight-set.h"
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>
#include <unistd.h>

namespace fs = std::filesystem;
using namespace vpipe;
using vpipe::genai::WeightSet;

int main()
{
  char pattern[] = "/tmp/h3-premerge-residency-XXXXXX";
  const char* created = ::mkdtemp(pattern);
  assert(created);
  struct Cleanup {
    fs::path path;
    ~Cleanup() { std::error_code ignored; fs::remove_all(path, ignored); }
  } cleanup{created};
  const fs::path model_dir = cleanup.path / "model";
  fs::create_directory(model_dir);
  constexpr std::size_t bytes = 16ull << 20;
  std::string header =
      R"({"large.weight":{"dtype":"BF16","shape":[1024,8192],"data_offsets":[0,16777216]}})";
  header.resize(4088, ' ');
  const std::uint64_t header_bytes = header.size();
  {
    std::ofstream out(model_dir / "model.safetensors", std::ios::binary);
    out.write(reinterpret_cast<const char*>(&header_bytes), sizeof(header_bytes));
    out.write(header.data(), header.size());
    std::vector<std::uint16_t> values(bytes / 2, 0x3f80);
    out.write(reinterpret_cast<const char*>(values.data()), bytes);
    assert(out);
  }
  Session session(std::string("{\"db\":{\"path\":\"") +
                  (cleanup.path / "db").string() + "\"}}");
  auto* mc = session.metal_compute();
  assert(mc);
  auto ws = WeightSet::open(model_dir.string(), mc->session());
  assert(ws);
  const auto initial = mc->memory_budget().allocated;
  {
    auto temporary = ws->read("large.weight", mc, WeightSet::Residency::Copied);
    assert(temporary.byte_size() == bytes && temporary.is_owned());
    const auto* values = static_cast<const std::uint16_t*>(temporary.contents());
    assert(values[0] == 0x3f80 && values[bytes / 2 - 1] == 0x3f80);
    assert(mc->memory_budget().allocated >= initial + bytes);
  }
  const auto after_copy = mc->memory_budget().allocated;
  // The WeightSet is still alive. A consumed copied read must not retain
  // the source as a GPU allocation beside a transformed destination.
  assert(after_copy <= initial + (1ull << 20));
  {
    auto temporary = ws->read("large.weight", mc, WeightSet::Residency::Mapped);
    assert(temporary.byte_size() == bytes && !temporary.is_owned());
  }
  const auto after_map = mc->memory_budget().allocated;
  assert(after_map >= after_copy + bytes);
  ws.reset();
  const auto released = mc->memory_budget().allocated;
  assert(released <= initial + (1ull << 20));
  std::cout << "initial=" << initial << " after_copied_read=" << after_copy
            << " after_mapped_read=" << after_map << " after_set_release="
            << released << "; temporary copied source lifetime passes\n";
}
