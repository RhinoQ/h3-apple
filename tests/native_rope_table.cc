// The exact helper used by the patched native transformer, tested against
// independently generated Torch goldens by the accompanying research harness.
#include "generative-models/minimax-h3/minimax-h3-rope.h"
#include <cstdio>
#include <stdexcept>

int main(int argc, char** argv) try {
  if (argc != 3) throw std::runtime_error("input output");
  FILE* input = std::fopen(argv[1], "rb");
  FILE* output = std::fopen(argv[2], "wbx");
  if (!input || !output) throw std::runtime_error("Cannot open fixture or exclusive output");
  double position;
  while (std::fread(&position, sizeof position, 1, input) == 1) {
    float frequency;
    if (std::fread(&frequency, sizeof frequency, 1, input) != 1)
      throw std::runtime_error("Truncated fixture");
    const auto pair = vpipe::genai::minimax_h3::rope_table_entry(position, frequency);
    const float values[] = {pair.first, pair.second};
    if (std::fwrite(values, sizeof values, 1, output) != 1)
      throw std::runtime_error("Cannot save values");
  }
  if (std::ferror(input)) throw std::runtime_error("Cannot read fixture");
  std::fclose(input);std::fclose(output);
  return 0;
} catch (const std::exception& e) {
  std::fprintf(stderr, "%s\n", e.what());return 1;
}
