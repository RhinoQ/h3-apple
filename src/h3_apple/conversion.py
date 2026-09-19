"""Native MiniMax layout and official FastH3 VSA adapter conversion.

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

def adapter_plan(header, target_shapes: dict, *, vsa: bool) -> dict:
    """Close every released adapter tensor against the converted base geometry."""
    meta = header.metadata
    if meta.get("format") != "fastvideo-lora-v2" or meta.get("rank") != "64":
        raise ValueError("expected finalized FastH3 rank-64 adapter")
    plans = {}
    counts = {"lora_A": 0, "lora_B": 0, "diff": 0, "set_weight": 0}
    for key, record in header.tensors.items():
        match = re.fullmatch(r"(.+)\.(lora_[AB]\.weight|diff_b|diff|set_weight)", key)
        if not match:
            raise ValueError(f"unrecognized adapter tensor: {key}")
        module, suffix = match.groups()
        target = module + (".bias" if suffix == "diff_b" else ".weight")
        if suffix == "set_weight":
            if not vsa or not re.fullmatch(
                r"transformer_blocks\.\d+\.attn\.to_gate_compress", module
            ):
                raise ValueError(f"unexpected replacement {key}")
            expected = (7168, 5376)
            counts["set_weight"] += 1
        else:
            if target not in target_shapes:
                raise ValueError(f"adapter target absent from base: {target}")
            shape = target_shapes[target]
            if suffix == "lora_A.weight":
                expected = (64, shape[1])
                counts["lora_A"] += 1
            elif suffix == "lora_B.weight":
                expected = (shape[0], 64)
                counts["lora_B"] += 1
            else:
                expected = shape
                counts["diff"] += 1
        if record.shape != expected:
            raise ValueError(f"adapter shape mismatch for {key}: {record.shape} != {expected}")
        plans.setdefault(target, {})[suffix] = key
    expected_counts = {
        "lora_A": 362,
        "lora_B": 362,
        "diff": 82 if vsa else 85,
        "set_weight": 50 if vsa else 0,
    }
    if counts != expected_counts:
        raise ValueError(f"adapter inventory does not close: {counts} != {expected_counts}")
    if vsa:
        actual_gates = {k for k, edits in plans.items() if "set_weight" in edits}
        expected_gates = {f"transformer_blocks.{i}.attn.to_gate_compress.weight" for i in range(50)}
        if actual_gates != expected_gates:
            raise ValueError("VSA gates must cover exactly blocks 0 through 49")
    for target, items in plans.items():
        if ("lora_A.weight" in items) != ("lora_B.weight" in items):
            raise ValueError(f"incomplete low-rank pair: {target}")
    return plans

def transform_lora_b(value, transform, *, xp=np):
    """ComfyUI QKV is contiguous Q/K/V, unlike native per-head QKV."""
    if transform in ("comfy_q", "comfy_k", "comfy_v"):
        if value.shape[0] % 3:
            raise ValueError("ComfyUI QKV row count mismatch")
        return xp.split(value, 3, axis=0)["qkv".index(transform[-1])]
    return transform_native(value, transform, xp=xp)


def merge_parameter(base, edits: dict, tensors: dict, *, xp, consumed: set, lora_scale=1.0,
                    lora_b_transform="identity"):
    """Published W_base + B @ A, then additive deltas, then replacements.

    FP32 accumulation followed by one cast to the source dtype; this reconstructs
    the compact adapter, not a claim of bitwise equivalence to the full student.
    """
    value = base.astype(xp.float32)
    if "lora_A.weight" in edits:
        a, b = edits["lora_A.weight"], edits["lora_B.weight"]
        b_value = transform_lora_b(tensors[b], lora_b_transform, xp=xp)
        delta = b_value.astype(xp.float32) @ tensors[a].astype(xp.float32)
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


def dareties_adapter_plan(header, target_shapes: dict) -> tuple[dict, dict]:
    """Validate the normalized dynamic-rank ComfyUI adapter, including AdaLN.

    The 52 fused QKV pairs expand to 156 Diffusers projections. FC1 changes
    from ComfyUI gate-first to Diffusers value-first; AdaLN stays unpermuted.
    Source-file identity is checked separately before conversion.
    """
    if (header.metadata.get("alpha_normalized") != "true" or
            header.metadata.get("alpha_normalization") !=
            "lora_up := lora_up * (alpha / rank); alpha tensors removed"):
        raise ValueError("DARE/TIES requires explicitly normalized alpha metadata.")
    prefixes = [f"token_refiner.blocks.{i}" for i in range(2)] + [f"blocks.{i}" for i in range(50)]
    modules = {f"{p}.{s}" for p in prefixes for s in
               ("attn.qkv_proj", "attn.out_proj", "mlp.fc1", "mlp.fc2")}
    modules |= {f"blocks.{i}.adaln_proj.linear" for i in range(50)}
    modules.add("final_layer.adaln_proj.linear")
    expected = {f"diffusion_model.{m}.lora_{ab}.weight" for m in modules for ab in "AB"}
    if set(header.tensors) != expected:
        raise ValueError("DARE/TIES requires exactly 259 complete pairs, including 51 AdaLN pairs.")
    plans, transforms = {}, {}
    for module in sorted(modules):
        a, b = (f"diffusion_model.{module}.lora_{ab}.weight" for ab in "AB")
        ashape, bshape = header.tensors[a].shape, header.tensors[b].shape
        targets = native_key_plan(module + ".weight")
        if len(ashape) != 2 or len(bshape) != 2 or ashape[0] <= 0 or ashape[0] != bshape[1]:
            raise ValueError(f"Invalid DARE/TIES low-rank pair: {module}")
        for target, transform in targets:
            shape = target_shapes.get(target)
            if shape is None or len(shape) != 2 or (bshape[0] // len(targets), ashape[1]) != tuple(shape) or bshape[0] % len(targets):
                raise ValueError(f"DARE/TIES projection shape mismatch: {module}")
            plans[target] = {"lora_A.weight": a, "lora_B.weight": b}
            transforms[target] = "comfy_" + transform if transform in ("q", "k", "v") else transform
    return plans, transforms


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


def convert_dit(native, adapter, output, progress, *, task="t2va", gate_source=None,
                adapter_flavor="lightx2v"):
    """Stream transformed shards through an explicit loader, without monkeypatching."""
    import mlx.core as mx
    from ._vendor.fastvideo_mlx import minimax_h3 as h3
    native, adapter, output = Path(native), Path(adapter), Path(output)
    if task not in ("t2va", "ref2va", "fl2va"):
        raise ValueError("DiT conversion task must be t2va, ref2va or fl2va.")
    if adapter_flavor not in ("lightx2v", "dareties-fro0995"):
        raise ValueError("Unknown adapter flavor.")
    dareties = adapter_flavor == "dareties-fro0995"
    if dareties:
        from .ref2va_recipe import DARETIES_SOURCE
        from .io import digest
        if task != "ref2va" or gate_source is None:
            raise ValueError("DARE/TIES requires Ref2VA and a separate gate-only source.")
        if adapter.stat().st_size != DARETIES_SOURCE["bytes"] or digest(adapter) != DARETIES_SOURCE["sha256"]:
            raise ValueError("Expected the pinned silveroxides fro0995 adapter.")
    if gate_source is not None and task == "t2va":
        raise ValueError("A separate gate source is only valid for conditioned LightX2V tasks.")
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
    if task == "fl2va":
        from .fl2va_recipe import FL12_SOURCE
        from .io import digest
        if digest(adapter) != FL12_SOURCE["sha256"]:
            raise ValueError("Expected the pinned official LightX2V FL2VA v1.2 BF16 LoRA.")
        if gate_source is None:
            raise ValueError("FL2VA VSA preparation requires a separate gate source.")
    if dareties:
        plans, b_transforms = dareties_adapter_plan(adapter_header, shapes)
    else:
        plans = ref2va_adapter_plan(adapter_header, shapes) if task != "t2va" else adapter_plan(adapter_header, shapes, vsa=True)
        b_transforms = {}
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
                    xp=mx, consumed=consumed,
                    lora_scale=8/128 if task != "t2va" and not dareties else 1.0,
                    lora_b_transform=b_transforms.get(target, "identity")) if target in plans else base)
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
        1 - h3.minimax_h3_sigmas(6 if task == "fl2va" else 12, 4)[:-1],
        1 - h3.minimax_h3_sigmas(3, 4)[:-1], [1.0, 0.999] if task != "t2va" else [1.0]]).astype(np.float32))
    dit = h3.mlx_h3_dit_from_diffusers_safetensors(native, config=CONFIG, dtype="bf16",
        quantization="int8", adaln_cache_timesteps=timesteps,
        include_vsa=task == "t2va" or bool(gates), _shard_loader=load)
    if consumed != set(adapter_header.tensors):
        raise ValueError("The converted model did not consume every adapter tensor.")
    if gates_consumed != set(gates.values()):
        raise ValueError("The converted model did not consume all selected gates.")
    h3.save_mlx_h3_checkpoint(dit, output)
    if task != "t2va":
        from .fl2va_recipe import FL12_SAMPLING
        from .ref2va_recipe import DARETIES_RECIPE
        recipe = dict(
            schema=f"h3-apple-{task}/v1", task=task, lora_rank=128, lora_alpha=8,
            lora_tensors=len(consumed), gate_tensors=len(gates_consumed),
            base_directory=str(native.resolve()), adapter_path=str(adapter.resolve()),
            gate_source=None if gate_source is None else str(Path(gate_source).resolve()),
            precision="int8_group64_bf16", fasth3_t2va_deltas_applied=False,
            **({"sampling": FL12_SAMPLING} if task == "fl2va" else {}),
        )
        if dareties:
            recipe = dict(DARETIES_RECIPE, base_directory=str(native.resolve()),
                          adapter_path=str(adapter.resolve()), gate_source=str(Path(gate_source).resolve()))
        (output / f"{task}_recipe.json").write_text(json.dumps(recipe, indent=2) + "\n")
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
        "Modified by H3 Apple: native DiT layout conversion, official FastH3 VSA "
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
    from .host import backend_identity, check_machine, device_lock, snapshot
    from .io import write_json
    from .worker import source_identity
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task", choices=("t2va", "fl2va"), default="t2va")
    parser.add_argument("--gate-source", type=Path, help="FastH3 source for the 50 FL2VA VSA gates only")
    parser.add_argument("--components", type=Path, help="Reuse an existing converted decoder/component directory")
    args = parser.parse_args()
    with device_lock():
        initial = snapshot()
        check_machine(initial)
        started = time.monotonic()
        # The adopted checkpoint was prepared with pre-NAX Steel GEMM. MLX's
        # own architecture override reproduces its BF16 AdaLN cache rounding.
        # This setting is confined to conversion; generation uses the real GPU.
        os.environ["MLX_METAL_GPU_ARCH"] = "applegpu_g16s"
        backend = backend_identity()
        import mlx.core as mx
        mx.set_memory_limit(80 * 1024**3)
        mx.set_cache_limit(4 * 1024**3)
        args.output.mkdir(exist_ok=False)
        def progress(event):
            print(json.dumps(event), flush=True)
        dit = convert_dit(args.native / "transformer", args.adapter, args.output / "dit", progress,
                          task=args.task, gate_source=args.gate_source)
        mx.clear_cache()
        if args.components is None:
            convert_components(args.native, args.output / "components", progress)
        else:
            if not args.components.is_dir():
                raise FileNotFoundError(args.components)
            (args.output / "components").symlink_to(args.components.resolve(), target_is_directory=True)
        write_json(args.output / "conversion.json", dict(converter="native-fasth3-v2" if args.task == "t2va" else "native-lightx2v-fl12-v1", dit=dit,
                   backend=backend, package_source_sha256=source_identity(),
                   physical_host=initial, elapsed_seconds=time.monotonic() - started,
                   settings={"metal_gpu_arch_override": "applegpu_g16s", "tf32": False,
                             "dtype": "bf16", "quantization": "affine-int8-group64",
                             "task": args.task, "video_shift": 6 if args.task == "fl2va" else 12, "audio_shift": 3, "num_steps": 4,
                             "video_vae_dtype": "fp32"},
                   peak_memory_gib=mx.get_peak_memory() / 1024**3,
                   full_student_bitwise_equivalence_claimed=False))


if __name__ == "__main__":
    main()
