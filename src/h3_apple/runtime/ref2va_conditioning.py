# SPDX-License-Identifier: Apache-2.0
"""Image-only Ref2VA conditioning primitives; no generation API qualification.

The caller prepares each RGB image once with ``prepare_reference_image`` and
passes those same pixels to Qwen and the H3 VAE. PyTorch is loaded lazily for
the official CPU vision tower and the native posterior random-number stream.
"""

from dataclasses import dataclass
import gc
import json
from pathlib import Path
import re

import numpy as np

from .._vendor.fastvideo_mlx.minimax_h3_conditioner import _ShardIndex


@dataclass(frozen=True)
class ImagePresentation:
    token_ids: np.ndarray
    tags: np.ndarray
    positions: np.ndarray
    visual_mask: np.ndarray


def image_presentation(tokenizer, prompt: str, grids, *, merge_size: int = 2) -> ImagePresentation:
    """Ordered picture labels and native Qwen MRoPE, followed by the full prompt."""
    grids = np.asarray(grids)
    if (grids.ndim != 2 or grids.shape[1] != 3 or not 1 <= len(grids) <= 9 or
            grids.dtype.kind not in "iu" or np.any(grids <= 0) or
            np.any(grids[:, 0] != 1) or merge_size != 2 or np.any(grids[:, 1:] % merge_size)):
        raise ValueError("Image conditioning needs 1–9 positive, spatially aligned image grids (T=1).")
    start, pad, end = [tokenizer.convert_tokens_to_ids(x) for x in
                       ("<|vision_start|>", "<|image_pad|>", "<|vision_end|>")]
    if any(x is None for x in (start, pad, end)) or len({start, pad, end}) != 3:
        raise ValueError("Tokenizer lacks the distinct Qwen image boundary and pad tokens.")
    ids, tags, masks, positions = [], [], [], []
    offset = 0

    def text_tokens(tokens, tag=1):
        nonlocal offset
        ids.extend(tokens); tags.extend([tag] * len(tokens)); masks.extend([False] * len(tokens))
        positions.append(np.tile(np.arange(len(tokens), dtype=np.int64) + offset, (3, 1)))
        offset += len(tokens)

    def tokenize(text):
        tokens = list(tokenizer(text, add_special_tokens=False)["input_ids"])
        if any(t in {start, pad, end} for t in tokens):
            raise ValueError("Literal Qwen image control tokens cannot occur in the prompt text.")
        return tokens

    for index, (_, height, width) in enumerate(grids):
        text_tokens(tokenize(f"<Picture {index + 1}>: "))
        text_tokens([start], tag=0)
        height, width = int(height) // merge_size, int(width) // merge_size
        coords = np.indices((1, height, width), dtype=np.int64).reshape(3, -1)
        count = height * width
        ids.extend([pad] * count); tags.extend([0] * count); masks.extend([True] * count)
        positions.append(coords + offset)
        offset += max(height, width)
        text_tokens([end], tag=0)
    text_tokens(tokenize(prompt))
    return ImagePresentation(np.asarray(ids, dtype=np.int64), np.asarray(tags, dtype=np.int64),
                             np.concatenate(positions, axis=1), np.asarray(masks, dtype=np.bool_))


def qwen_image_inputs(processor_dir: Path, images):
    from transformers import AutoProcessor
    if any(image.mode != "RGB" for image in images):
        raise ValueError("Prepare RGB images once before passing them to both encoders.")
    processor = AutoProcessor.from_pretrained(str(processor_dir), local_files_only=True)
    result = processor.image_processor(images=images, return_tensors="pt")
    # A second resize would make Qwen and H3 see different reference geometry.
    grids = result["image_grid_thw"]
    patch = processor.image_processor.patch_size
    for image, (_, height, width) in zip(images, grids, strict=True):
        if (int(width) * patch, int(height) * patch) != image.size:
            raise ValueError("Qwen processor resized a prepared image; use a compatible reference budget.")
    return result


def qwen_vision_features(component_dir: Path, pixel_values, grid_thw):
    """Official Transformers vision tower on CPU, loading only its 351 tensors."""
    import torch
    from transformers.models.qwen3_vl.configuration_qwen3_vl import Qwen3VLVisionConfig
    from transformers.models.qwen3_vl.modeling_qwen3_vl import Qwen3VLVisionModel, Qwen3VLVisionRotaryEmbedding

    config = Qwen3VLVisionConfig(**json.loads((Path(component_dir) / "config.json").read_text())["vision_config"])
    config._attn_implementation = "sdpa"
    with torch.device("meta"):
        model = Qwen3VLVisionModel(config)
    index = _ShardIndex(Path(component_dir))
    weights = {key.removeprefix("model.visual."): torch.from_numpy(index.get(key))
               for key in index.key_to_shard if key.startswith("model.visual.")}
    model.load_state_dict(weights, strict=True, assign=True)
    model.rotary_pos_emb = Qwen3VLVisionRotaryEmbedding(config.hidden_size // config.num_heads // 2)
    model.eval()
    with torch.inference_mode():
        result = model(pixel_values.to(device="cpu", dtype=torch.float32), grid_thw.to("cpu"))
    features = result.pooler_output.numpy().copy()
    deepstack = [value.numpy().copy() for value in result.deepstack_features]
    del model, weights, result
    index.close(); gc.collect()
    return features, deepstack


def native_vae_encoder_key(key: str) -> str:
    """Lossless names-only mapping of original encoder parameters."""
    key = re.sub(r"^encoder\.down\.(\d+)\.block\.(\d+)\.", r"encoder.down_blocks.\1.resnets.\2.", key)
    key = re.sub(r"^encoder\.down\.(\d+)\.downsample\.", r"encoder.down_blocks.\1.downsamplers.0.", key)
    return key.replace(".nin_shortcut.", ".conv_shortcut.")


def load_native_image_vae(vae_dir: Path):
    """Load the original FP32 encoder subset; never materialize decoder tensors."""
    import mlx.core as mx
    from .._vendor.fastvideo_mlx.minimax_h3_video_vae import MLXMiniMaxH3VideoVAE, MiniMaxH3VideoVAEConfigView

    vae_dir = Path(vae_dir)
    wrapper = json.loads((vae_dir / "config.json").read_text())
    raw = json.loads((vae_dir / "source/config.json").read_text())
    if not (raw["causal_encoder"] and raw["use_t_isolated_gn"] and raw["use_3d_conv"] and
            raw["padding_mode"] == "reflect" and raw["pixel_norm_type"] == "imagenet" and
            raw["embed_dim"] == raw["z_channels"] == wrapper["latent_channels"] and
            wrapper["vae_encoder_tiling"] == 1 and wrapper["vae_tile_size"] == 256 and
            wrapper["vae_tile_overlap_min"] == 64):
        raise ValueError("Unsupported native H3 image encoder architecture or tiling configuration.")
    cfg = MiniMaxH3VideoVAEConfigView(
        in_channels=raw["in_channels"], latent_channels=raw["embed_dim"],
        block_out_channels=tuple(raw["ch"] * factor for factor in raw["ch_mult"]),
        layers_per_block=raw["num_res_blocks"],
        spatial_downsample_factors=tuple(raw["space_down"]),
        temporal_downsample_factors=tuple(raw["time_down"]),
        latents_mean=tuple(wrapper["latents_mean"]), latents_std=tuple(wrapper["latents_std"]))
    index = _ShardIndex(vae_dir / "source")
    weights = {}
    for key in index.key_to_shard:
        if not key.startswith(("encoder.", "quant_conv.")):
            continue
        value = index.get(key)
        if value.dtype != np.float32:
            raise ValueError("Native H3 VAE encoder parameters must be FP32.")
        if value.ndim == 5:
            value = np.ascontiguousarray(value.transpose(0, 2, 3, 4, 1))
        name = native_vae_encoder_key(key)
        if name in weights:
            raise ValueError(f"Duplicate encoder parameter: {name}")
        weights[name] = mx.array(value)
        mx.eval(weights[name])
    index.close()
    return MLXMiniMaxH3VideoVAE(weights, cfg, has_encoder=True)


def encode_image_latents(vae, image, *, return_intermediates=False):
    """Native keyframe posterior sampling, FP16 roundtrip, then normalization."""
    import mlx.core as mx
    import torch
    if image.mode != "RGB" or any(value % 32 for value in image.size):
        raise ValueError("H3 image conditioning requires the shared RGB image aligned to 32 pixels.")
    pixels = np.asarray(image, dtype=np.float32).transpose(2, 0, 1)[None, :, None] / 255.0
    normalized_pixels = vae.normalize_pixels(mx.array(pixels))
    mean, logvar = vae.encode_keyframe(normalized_pixels, tile_size=256, min_overlap=64)
    noise = torch.randn(tuple(mean.shape), generator=torch.Generator("cpu").manual_seed(42), dtype=torch.float32).numpy()
    sampled = vae.sample_posterior(mean, logvar, mx.array(noise)).astype(mx.float16).astype(mx.float32)
    latents = vae.normalize_latents(sampled)
    mx.eval(latents)
    if return_intermediates:
        return {"pixels": pixels, "normalized_pixels": np.asarray(normalized_pixels), "mean": np.asarray(mean),
                "logvar": np.asarray(logvar), "noise": noise, "sampled": np.asarray(sampled),
                "latents": np.asarray(latents)}
    return np.asarray(latents)
