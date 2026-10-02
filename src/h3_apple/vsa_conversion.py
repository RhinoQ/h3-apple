"""Native MiniMax layout and original LightX2V fusion and FastH3 gate-only adapter conversion.

Arithmetic inherited from the verified P082 bridge; no research imports or runtime patches.
"""

from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import shutil
import time
from types import SimpleNamespace

import numpy as np


CONFIG = {
    "num_attention_heads": 56,
    "attention_head_dim": 128,
    "hidden_size": 5376,
    "num_layers": 50,
    "num_refiner_layers": 2,
    "ffn_dim": 14336,
    "in_channels": 24,
    "audio_in_channels": 32,
    "patch_size": [1, 2, 2],
    "text_dim": 5120,
    "freq_dim": 256,
    "time_embed_hidden_dim": 5376,
    "time_embed_dim": 2688,
    "rope_freq_dim": 16,
    "rope_theta": 10000.0,
    "norm_eps": 1e-5,
    "qk_norm_eps": 1e-5,
    "final_norm_eps": 1e-5,
}

ALIASES = {
    "video_patch_proj.": "proj_in.",
    "audio_patch_proj.": "audio_proj_in.",
    "condition_proj.": "context_embedder.",
    "time_embedder.proj_in.": "time_embedder.linear_1.",
    "time_embedder.proj_out.": "time_embedder.linear_2.",
    "final_layer.norm.": "norm_out.norm.",
    "final_layer.adaln_proj.linear.": "norm_out.linear.",
    "final_layer.video_out.": "proj_out.",
    "final_layer.audio_out.": "audio_proj_out.",
}

def native_key_plan(key: str) -> list[tuple[str, str]]:
    """Return exact target names and array transforms; reject unknown roots."""
    if key == "rope.inv_freq":
        return []
    if key.startswith("token_refiner.blocks."):
        target = key.replace("token_refiner.blocks.", "token_refiner.refiner_blocks.", 1)
    elif key.startswith("blocks."):
        target = key.replace("blocks.", "transformer_blocks.", 1)
    elif key == "token_refiner.final_norm.weight":
        return [(key, "identity")]
    else:
        for prefix, replacement in ALIASES.items():
            if key.startswith(prefix):
                return [(replacement + key[len(prefix) :], "identity")]
        raise ValueError(f"unknown native H3 key: {key}")
    if target.endswith(".attn.qkv_proj.weight"):
        prefix = target.removesuffix("qkv_proj.weight")
        return [(prefix + f"to_{name}.weight", name) for name in "qkv"]
    if target.endswith(".mlp.fc1.weight"):
        return [(target.replace(".mlp.fc1.", ".ff.net.0.proj."), "swap_halves")]
    for old, new in (
        (".attn.q_norm.", ".attn.norm_q."),
        (".attn.k_norm.", ".attn.norm_k."),
        (".attn.out_proj.", ".attn.to_out.0."),
        (".mlp.fc2.", ".ff.net.2."),
    ):
        target = target.replace(old, new)
    if not re.search(
        r"\.(norm[12]|attn\.(norm_[qk]|to_out\.0)|ff\.net\.2|adaln_proj\.linear)\."
        r"(weight|bias)$",
        target,
    ):
        raise ValueError(f"unknown native block key: {key}")
    return [(target, "identity")]

def transform_native(value, transform: str, *, heads: int = 56, head_dim: int = 128, xp=np):
    if transform in ("q", "k", "v"):
        if value.shape[0] != heads * 3 * head_dim:
            raise ValueError("native QKV row count mismatch")
        # Selecting the component inside each head is not slicing contiguous thirds.
        return value.reshape(heads, 3, head_dim, *value.shape[1:])[
            :, "qkv".index(transform)
        ].reshape(heads * head_dim, *value.shape[1:])
    if transform == "swap_halves":
        if value.shape[0] % 2:
            raise ValueError("SwiGLU requires two equal halves")
        return xp.concatenate(xp.split(value, 2, axis=0)[::-1], axis=0)
    if transform != "identity":
        raise ValueError(f"unknown transform {transform}")
    return value

def merge_parameter(base, edits: dict, tensors: dict, *, xp, consumed: set, lora_scale=1.0):
    """Published W_base + B @ A, then additive deltas, then replacements.

    FP32 accumulation followed by one cast to the source dtype; this reconstructs
    the compact adapter, not a claim of bitwise equivalence to the full student.
    """
    value = base.astype(xp.float32)
    if "lora_A.weight" in edits:
        a, b = edits["lora_A.weight"], edits["lora_B.weight"]
        delta = tensors[b].astype(xp.float32) @ tensors[a].astype(xp.float32)
        value = value + delta * lora_scale
    for kind in ("diff", "diff_b"):
        if kind in edits:
            value = value + tensors[edits[kind]].astype(xp.float32)
    if "set_weight" in edits:
        value = tensors[edits["set_weight"]].astype(xp.float32)
    consumed.update(edits.values())
    return value.astype(base.dtype)


def ref2va_adapter_plan(header, target_shapes: dict) -> dict:
    """Validate the dedicated LightX2V Ref2VA rank128/alpha8 PEFT adapter."""
    if header.metadata.get("format") != "pt" or header.metadata.get("alpha") != "8":
        raise ValueError("Expected the dedicated Ref2VA PEFT adapter with alpha 8.")
    prefixes = ([f"token_refiner.refiner_blocks.{i}" for i in range(2)] +
                [f"transformer_blocks.{i}" for i in range(50)])
    projections = ("attn.to_q", "attn.to_k", "attn.to_v", "attn.to_out.0", "ff.net.0.proj", "ff.net.2")
    expected = {f"{prefix}.{projection}.weight" for prefix in prefixes for projection in projections}
    plans = {}
    for key, record in header.tensors.items():
        match = re.fullmatch(r"(.+)\.(lora_[AB])\.default\.weight", key)
        if match is None:
            raise ValueError(f"Unexpected Ref2VA adapter tensor: {key}")
        module, kind = match.groups(); target = module + ".weight"
        if target not in expected or target not in target_shapes:
            raise ValueError(f"Unexpected or absent Ref2VA projection: {target}")
        shape = target_shapes[target]
        wanted = (128, shape[1]) if kind == "lora_A" else (shape[0], 128)
        if tuple(record.shape) != wanted:
            raise ValueError(f"Ref2VA rank or projection shape mismatch: {key}")
        plans.setdefault(target, {})[kind + ".weight"] = key
    if set(plans) != expected or any(set(v) != {"lora_A.weight", "lora_B.weight"} for v in plans.values()):
        raise ValueError("Ref2VA requires all 312 complete low-rank pairs and no extra tensors.")
    return plans


def ref2va_gate_plan(gate_header) -> dict:
    """Select only the 50 full gate matrices; never apply T2VA adapter deltas."""
    pattern = re.compile(
        r"^(?:transformer_blocks|(?:diffusion_model\.)?blocks)\.(\d+)\."
        r"attn\.to_gate_compress\.(?:set_weight|weight)$")
    result = {}
    for key, record in gate_header.tensors.items():
        match = pattern.fullmatch(key)
        if not match:
            if "to_gate_compress" in key:
                raise ValueError(f"Unrecognized gate tensor: {key}")
            continue
        index = int(match[1])
        target = f"transformer_blocks.{index}.attn.to_gate_compress.weight"
        if target in result or tuple(record.shape) != (7168, 5376):
            raise ValueError(f"Duplicate or incorrectly shaped gate: {key}")
        result[target] = key
    if set(result) != {f"transformer_blocks.{i}.attn.to_gate_compress.weight" for i in range(50)}:
        raise ValueError("Ref2VA VSA requires exactly one gate for every block 0 through 49.")
    return result

def video_key_plan(key: str) -> list[tuple[str, str]]:
    """Native video decoder -> the published Diffusers names; no approximation."""
    if key == "decoder.mask_token" or not key.startswith(("decoder.", "post_quant_conv.")):
        return []  # T2VA decode only; no image encoder is required.
    if ".attn.to_qkv." in key:
        prefix, suffix = key.split(".attn.to_qkv.")
        return [(f"{prefix}.attn.to_{c}.{suffix}", c) for c in "qkv"]
    target = key.replace("decoder.x_embedder.", "decoder.proj_in.")
    target = target.replace(".attn.to_out.", ".attn.to_out.0.")
    target = target.replace(".ff.w1.", ".ff.net.0.proj.").replace(".ff.w2.", ".ff.net.2.")
    return [(target, "swap_halves" if ".ff.w1." in key else "identity")]


def header(path):
    from safetensors import safe_open
    with safe_open(str(path), framework="np") as reader:
        return SimpleNamespace(path=Path(path), metadata=reader.metadata() or {}, tensors={
            key: SimpleNamespace(shape=tuple(reader.get_slice(key).get_shape()))
            for key in reader.keys()})


def convert_dit(native, adapter, output, progress, *, task="ref2va", gate_source=None):
    """Stream transformed shards through an explicit loader, without monkeypatching."""
    import mlx.core as mx
    from ._vendor.fastvideo_mlx import minimax_h3 as h3
    native, adapter, output = Path(native), Path(adapter), Path(output)
    if task != "ref2va" or gate_source is None:
        raise ValueError("VSA preparation requires Ref2VA and a separate FastH3 gate source.")
    if output.exists():
        raise FileExistsError(output)
    shards = sorted(native.glob("model-*.safetensors"))
    if len(shards) != 13:
        raise ValueError("Expected the 13 pinned native DiT shards.")
    shapes = {}
    for shard in shards:
        for key, record in header(shard).tensors.items():
            for target, op in native_key_plan(key):
                if target in shapes:
                    raise ValueError(f"Duplicate native parameter: {target}")
                shapes[target] = ((record.shape[0] // 3, *record.shape[1:])
                                  if op in ("q", "k", "v") else record.shape)
    adapter_header = header(adapter)
    plans = ref2va_adapter_plan(adapter_header, shapes)
    adapter_tensors = mx.load(str(adapter))
    consumed = set()
    gates = ref2va_gate_plan(header(gate_source)) if gate_source is not None else {}
    gate_tensors = mx.load(str(gate_source)) if gates else {}
    gates_consumed = set()

    def load(shard, phase):
        arrays = mx.load(str(shard))
        converted = {}
        for key, value in arrays.items():
            if key.startswith("time_embedder.") != (phase == "time_embedder"):
                continue
            for target, op in native_key_plan(key):
                base = transform_native(value, op, xp=mx)
                converted[target] = (merge_parameter(base, plans[target], adapter_tensors,
                    xp=mx, consumed=consumed, lora_scale=8/128) if target in plans else base)
        if phase == "weights" and shard == shards[-1]:
            for target, edits in plans.items():
                if "set_weight" in edits:
                    converted[target] = adapter_tensors[edits["set_weight"]]
                    consumed.add(edits["set_weight"])
            for target, key in gates.items():
                converted[target] = gate_tensors[key]
                gates_consumed.add(key)
        progress({"phase": "dit_conversion", "file": f"{phase}/{shard.name}"})
        return converted

    timesteps = np.unique(np.concatenate([
        1 - h3.minimax_h3_sigmas(12, 4)[:-1],
        1 - h3.minimax_h3_sigmas(3, 4)[:-1], [1.0, 0.999]]).astype(np.float32))
    dit = h3.mlx_h3_dit_from_diffusers_safetensors(native, config=CONFIG, dtype="bf16",
        quantization="int8", adaln_cache_timesteps=timesteps,
        include_vsa=True, _shard_loader=load)
    if consumed != set(adapter_header.tensors):
        raise ValueError("The converted model did not consume every official adapter tensor.")
    if gates_consumed != set(gates.values()):
        raise ValueError("The converted model did not consume all selected gates.")
    h3.save_mlx_h3_checkpoint(dit, output)
    (output / "ref2va_recipe.json").write_text(json.dumps(dict(
        schema="h3-apple-ref2va/v1", task="ref2va", lora_rank=128, lora_alpha=8,
        lora_tensors=len(consumed), gate_tensors=len(gates_consumed),
        base_directory=str(native.resolve()), adapter_path=str(adapter.resolve()),
        gate_source=str(Path(gate_source).resolve()),
        precision="int8_group64_bf16", fasth3_t2va_deltas_applied=False,
    ), indent=2) + "\n")
    return dict(base_shards=len(shards), adapter_tensors=len(consumed),
                gate_tensors=len(gates_consumed), timesteps=timesteps.tolist())


def convert_components(native, output, progress):
    import mlx.core as mx
    from ._vendor.fastvideo_mlx.minimax_h3_audio_vae import MiniMaxH3AudioVAEConfigView
    from ._vendor.fastvideo_mlx.minimax_h3_video_vae import MiniMaxH3VideoVAEConfigView
    native, output = Path(native), Path(output)
    output.mkdir(exist_ok=False)
    shutil.copyfile(native.parent / "LICENSE", output / "LICENSE")
    (output / "NOTICE").write_text(
        "MiniMax H3 is licensed under the MiniMax H3 Community License Agreement, "
        "Copyright © 2026 MiniMax. All Rights Reserved.\n\n"
        "Modified by H3 Apple: native DiT layout conversion, original LightX2V fusion and FastH3 gate-only "
        "adapter fusion, affine INT8 group64 quantization and fixed AdaLN tables; "
        "VideoVAE decoder key conversion with the image encoder omitted. "
        "AudioVAE, text encoder and tokenizer payloads are retained unchanged. "
        "Source checksums and converter identity are recorded in bundle.json.\n")
    for name in ("text_encoder", "tokenizer"):
        (output / name).symlink_to((native / name).resolve(), target_is_directory=True)
    video = native / "video_vae"
    config = json.loads((video / "source/config.json").read_text())
    vc = asdict(MiniMaxH3VideoVAEConfigView())
    if (config["vit_decoder_kwargs"]["num_layers"] != vc["decoder_num_layers"]
            or config["vit_decoder_kwargs"]["heads"] != vc["decoder_num_attention_heads"]
            or config["vit_decoder_kwargs"]["dim_head"] != vc["decoder_attention_head_dim"]
            or config["space_down"] != list(vc["spatial_downsample_factors"])
            or config["time_down"] != list(vc["temporal_downsample_factors"])):
        raise ValueError("Native VideoVAE configuration differs from this converter.")
    wrapper = json.loads((video / "config.json").read_text())
    for key in ("latents_mean", "latents_std"):
        vc[key] = wrapper[key]
    (output / "vae").mkdir()
    (output / "vae/config.json").write_text(json.dumps(vc, indent=2) + "\n")
    arrays = mx.load(str(video / "source/model.safetensors"))
    converted = {}
    for key, value in arrays.items():
        for target, op in video_key_plan(key):
            converted[target] = transform_native(value, op, heads=32, head_dim=64, xp=mx)
    mx.eval(converted)
    mx.save_safetensors(str(output / "vae/diffusion_pytorch_model.safetensors"), converted,
                        metadata={"format": "pt"})
    del arrays, converted
    mx.clear_cache()
    progress({"phase": "video_vae_conversion"})
    audio = native / "audio_vae"
    ac = asdict(MiniMaxH3AudioVAEConfigView())
    config = json.loads((audio / "metadata.json").read_text())["metadata"]["kwargs"]
    for key in ("encoder_dim", "encoder_rates", "latent_dim", "decoder_dim", "decoder_rates"):
        if json.dumps(config[key]) != json.dumps(ac[key]):
            raise ValueError(f"Native AudioVAE configuration differs: {key}")
    wrapper = json.loads((audio / "config.json").read_text())
    for key in ("latents_mean", "latents_std"):
        ac[key] = wrapper[key]
    (output / "audio_vae").mkdir()
    (output / "audio_vae/config.json").write_text(json.dumps(ac, indent=2) + "\n")
    (output / "audio_vae/diffusion_pytorch_model.safetensors").symlink_to(
        (audio / "model.safetensors").resolve())


def main():
    import argparse
    from .host import check_machine, snapshot
    from .runtime.backend import backend_identity
    from .io import write_json, source_identity
    parser = argparse.ArgumentParser(description="Private VSA model conversion worker")
    for name in ("native", "adapter", "gate-source", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    initial = snapshot()
    check_machine(initial)
    started = time.monotonic()
    os.environ["MLX_METAL_GPU_ARCH"] = ""
    os.environ["MLX_ENABLE_TF32"] = "0"
    backend = backend_identity()
    import mlx.core as mx
    mx.set_memory_limit(80 * 1024**3)
    mx.set_cache_limit(4 * 1024**3)
    args.output.mkdir(exist_ok=False)
    def progress(event):
        print(json.dumps(event), flush=True)
    dit = convert_dit(args.native / "transformer", args.adapter, args.output / "dit", progress,
                      task="ref2va", gate_source=args.gate_source)
    mx.clear_cache()
    convert_components(args.native, args.output / "components", progress)
    write_json(args.output / "conversion.json", dict(converter="original-lightx2v-ref2va-v1", dit=dit,
               backend=backend, package_source_sha256=source_identity(),
               physical_host=initial, elapsed_seconds=time.monotonic() - started,
               settings=dict(metal_gpu_arch_override="", tf32=False,
                             dtype="bf16", quantization="affine-int8-group64",
                             task="ref2va", video_shift=12, audio_shift=3, num_steps=4,
                             video_vae_dtype="fp32"),
               peak_memory_gib=mx.get_peak_memory() / 1024**3))


if __name__ == "__main__":
    main()
