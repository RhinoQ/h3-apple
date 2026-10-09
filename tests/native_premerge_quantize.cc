// Full tiny checkpoint: independent scalar merge and real native quantizer.
#define _DARWIN_C_SOURCE
#include "common/session.h"
#include "generative-models/minimax-h3/metal-minimax-h3-transformer.h"
#include "generative-models/llama3/metal-llama-weights.h"
#include "generative-models/quantize/model-quantizer.h"
#include "generative-models/quantize/safetensors-writer.h"
#include <bit>
#include <cassert>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>
#include <unistd.h>
using namespace vpipe;
using namespace vpipe::genai;
namespace fs=std::filesystem;
static uint16_t bf(float x) {
  const auto bits=std::bit_cast<uint32_t>(x);
  auto top=uint16_t(bits>>16); const auto low=bits&65535;
  return top+(low>32768 || (low==32768 && (top&1)));
}
static float fp(uint16_t x) { return std::bit_cast<float>(uint32_t(x)<<16); }
int main() {
  char pattern[]="/tmp/h3-premerge-quantize-XXXXXX"; const char* made=mkdtemp(pattern); assert(made);
  struct Cleanup {fs::path path;~Cleanup(){std::error_code e;fs::remove_all(path,e);}} cleanup{made};
  auto root=cleanup.path; auto raw=root/"raw", gold=root/"gold", ad=root/"adapter";
  for(auto p:{raw,gold,ad}) fs::create_directory(p);
  const std::string config=R"({"_class_name":"MiniMaxH3DiTModel","hidden_size":256,"num_attention_heads":2,"attention_head_dim":128,"num_layers":1,"token_refiner_num_layers":1,"ffn_hidden_size":256})";
  for(auto p:{raw,gold}) {std::ofstream f(p/"config.json");f<<config;}
  SafetensorsWriter base(raw.string()), expected(gold.string()), adapter(ad.string());
  constexpr int H=256, R=2;
  for(int layer=0;layer<2;++layer) {
    const std::string native=layer?"token_refiner.blocks.0.":"blocks.0.";
    const std::string peft=layer?"token_refiner.refiner_blocks.0.":"transformer_blocks.0.";
    const char* mods[]={"attn.to_q","attn.to_k","attn.to_v","attn.to_out.0","ff.net.0.proj","ff.net.2"};
    std::vector<std::vector<uint16_t>> aa(6),bb(6);
    for(int part=0;part<6;++part) {
      int n=part==4?2*H:H;
      aa[part].resize(R*H);bb[part].resize(n*R);
      for(int i=0;i<R*H;++i)aa[part][i]=bf(float((i+part+layer)%13-6)/32);
      for(int i=0;i<n*R;++i)bb[part][i]=bf(float((i*3+part+layer)%11-5)/64);
      assert(adapter.add(peft+mods[part]+".lora_A.default.weight","BF16",{R,H},aa[part].data(),aa[part].size()*2));
      assert(adapter.add(peft+mods[part]+".lora_B.default.weight","BF16",{n,R},bb[part].data(),bb[part].size()*2));
    }
    const char* projections[]={"attn.qkv_proj.weight","attn.out_proj.weight","mlp.fc1.weight","mlp.fc2.weight"};
    for(int projection=0;projection<4;++projection) {
      int n=projection==0?3*H:(projection==2?2*H:H);
      std::vector<uint16_t> w(n*H),merged(n*H);
      for(int row=0;row<n;++row) for(int col=0;col<H;++col) {
        const int index=row*H+col; w[index]=bf(float((index+layer)%23-11)/64);
        int part,source_row;
        if(projection==0){part=(row%384)/128;source_row=(row/384)*128+row%128;}
        else {part=projection+2;source_row=projection==2?(row+H)%(2*H):row;}
        double delta=0;
        for(int r=0;r<R;++r)delta+=double(fp(bb[part][source_row*R+r]))*fp(aa[part][r*H+col]);
        merged[index]=bf(float(double(fp(w[index]))+delta));
      }
      assert(base.add(native+projections[projection],"BF16",{n,H},w.data(),w.size()*2));
      assert(expected.add(native+projections[projection],"BF16",{n,H},merged.data(),merged.size()*2));
    }
  }
  const uint16_t bias=0x3f80;
  assert(base.add("untouched.bias","BF16",{1},&bias,2));
  assert(expected.add("untouched.bias","BF16",{1},&bias,2));
  assert(base.close() && expected.close() && adapter.close());
  Session session(std::string("{\"db\":{\"path\":\"")+(root/"db").string()+"\"}}");
  auto* mc=session.metal_compute();assert(mc);
  ModelQuantizer q(mc);QuantizeOptions opt;opt.quant_linears={"qkv_proj","out_proj","fc1","fc2"};
  auto control=root/"control", got=root/"got";std::string err;
  assert(q.run(gold.string(),control.string(),opt,&err));
  const auto adapter_path=(ad/"model-00001-of-00001.safetensors").string();
  opt.h3_premerge_lora=adapter_path;
  const bool prepared=q.run(raw.string(),got.string(),opt,&err);
  if (!prepared) std::cerr<<err<<std::endl;
  assert(prepared);
  auto a=MetalLlamaWeights::open_model(control.string()),b=MetalLlamaWeights::open_model(got.string());
  assert(a && b && a->tensor_names().size()==25);
  for(const auto& name:a->tensor_names()) {
    assert(a->info(name)->dtype==b->info(name)->dtype && a->info(name)->shape==b->info(name)->shape);
    auto x=a->load(name,mc),y=b->load(name,mc);
    assert(x.byte_size()==y.byte_size() && std::memcmp(x.contents(),y.contents(),x.byte_size())==0);
  }
  MetalMiniMaxH3Transformer::Config cfg;
  assert(MetalMiniMaxH3Transformer::config_from_json(got.string(),cfg,&err) && cfg.lora_premerged);
  bool rejected=false;
  try { rejected=!MetalMiniMaxH3Transformer::load(got.string(),mc,cfg,false,{{adapter_path,1.f}}); }
  catch(const std::runtime_error& e) { rejected=std::string(e.what()).find("rejects runtime adapters")!=std::string::npos; }
  assert(rejected);
  assert(!q.run(got.string(),(root/"double").string(),opt,&err));
  assert(!fs::exists(root/"double"));
  assert(!q.run(control.string(),(root/"quantized").string(),opt,&err));
  assert(!fs::exists(root/"quantized"));
  assert(!q.run(raw.string(),raw.string(),opt,&err));
  opt.bits=4;assert(!q.run(raw.string(),(root/"bad-bits").string(),opt,&err));
  assert(!fs::exists(root/"bad-bits"));
  std::cout<<"Premerge quantization: scalar oracle for per-head QKV, FFN half swap and both blocks; all25quantized/passthrough tensors bit-exact; duplicate, quantized-source, in-place and precision guards pass\n";
}
