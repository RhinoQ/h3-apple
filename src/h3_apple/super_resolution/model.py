"""Strict VOSR2 model loading; production precision is configured separately."""

import json
from types import SimpleNamespace, MethodType

import torch
from safetensors.torch import load_file

from ._vendor.dinov2.vision_transformer import vit_large
from ._vendor.vosr.lightningdit import LightningDiT
from ._vendor.vosr.qwenimage_vae2d import AutoencoderKLQwenImage2D


def _features(self, x):
    features = {}
    x = self.prepare_tokens_with_masks(x)
    for index, block in enumerate(self.blocks):
        x = block(x)
        features[f"layer_{index}"] = x[:, 1:]
    return features, self.norm(x)[:, 1:]


class Restorer:
    def __init__(self, root):
        args = self.args = SimpleNamespace(**json.loads((root / "VOSR2/args.json").read_text()))
        self.vae, loading = AutoencoderKLQwenImage2D.from_pretrained(
            str(root / "Qwen-Image-vae-2d"), local_files_only=True, output_loading_info=True)
        if any(loading.get(k) for k in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")):
            raise RuntimeError(f"VAE state differs from the fixed recipe: {loading}")
        self.vae.to("mps").eval().requires_grad_(False)
        self.encoder = vit_large(img_size=518, patch_size=14, init_values=1.0,
            ffn_layer="mlp", block_chunks=0, num_register_tokens=0,
            interpolate_antialias=False, interpolate_offset=.1)
        self.encoder.load_state_dict(torch.load(root / "torch_cache/checkpoints/dinov2_vitl14_pretrain.pth",
            map_location="cpu", weights_only=True), strict=True)
        self.encoder.head = torch.nn.Identity()
        self.encoder.forward_with_features = MethodType(_features, self.encoder)
        self.encoder.to("mps").eval().requires_grad_(False)
        self.model = LightningDiT(input_size=args.resolution // 8, patch_size=args.patch_size,
            in_channels=32, out_channels=16, hidden_size=args.dim, depth=args.depth,
            num_heads=args.num_heads, mlp_ratio=args.mlp_ratio, z_dims=args.enc_dim,
            encdim_ratio=args.encdim_ratio, auxiliary_time_cond=args.auxiliary_time_cond,
            use_qknorm=args.use_qknorm, use_swiglu=args.use_swiglu, use_rope=args.use_rope,
            use_rmsnorm=args.use_rmsnorm, wo_shift=args.wo_shift,
            num_fused_layers=len(args.layer_dinov2b_list))
        state = load_file(str(root / "VOSR2/checkpoints/ema_model.safetensors"))
        self.model.load_state_dict(state, strict=True)
        del state
        self.model.to("mps").eval().requires_grad_(False)
        self.model.forward = self.model.forward_flexible
        torch.mps.synchronize()

