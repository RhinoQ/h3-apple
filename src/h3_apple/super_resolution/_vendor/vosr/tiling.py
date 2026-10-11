# Adapted from VOSR 516f292b99cf23c76fdc33351e86dc4f97711fe8; Apache-2.0.
# H3 Apple: fixed Qwen full-frame VAE, explicit noise and native FP16 tile execution.
import torch
from .conditioning import get_venc_features


def _gaussian_weights(tile_h, tile_w, channels, device):
    """2-D Gaussian blend mask (1, C, tile_h, tile_w) peaked at the centre."""
    var = 0.01
    mid_h, mid_w = (tile_h - 1) / 2, (tile_w - 1) / 2
    y = torch.arange(tile_h, dtype=torch.float32)
    x = torch.arange(tile_w, dtype=torch.float32)
    wy = torch.exp(-((y - mid_h) / tile_h) ** 2 / (2 * var))
    wx = torch.exp(-((x - mid_w) / tile_w) ** 2 / (2 * var))
    w = wy[:, None] * wx[None, :]                       # (tile_h, tile_w)
    return w.to(device).unsqueeze(0).unsqueeze(0).expand(1, channels, -1, -1)


def _make_tile_grid(length, tile, overlap):
    """Return sorted, deduplicated starting positions that cover *length*."""
    stride = max(tile - overlap, 1)
    if length <= tile:
        return [0]
    positions = list(range(0, length - tile + 1, stride))
    if positions[-1] + tile < length:
        positions.append(length - tile)
    return sorted(set(positions))


def encode_latent(vae, x, args, device, posterior_mode=True):
    """Single-shot VAE encode -> normalized latent. Mirrors the old _encode_latent,
    but defaults to deterministic `latent_dist.mode()` instead of `.sample()`.

    qwen: (z - latents_mean) * (1/latents_std)   (latents_std returned as 1/std)
    sd2 : z * vae.config.scaling_factor
    Returns (latent, latents_mean, latents_std); sd2 -> (latent, None, None).
    """
    if args.ae_type == 'qwen':
        latents_mean = torch.tensor(vae.config.latents_mean).view(1, -1, 1, 1).to(device)
        latents_std = 1.0 / torch.tensor(vae.config.latents_std).view(1, -1, 1, 1).to(device)
        posterior = vae.encode(x).latent_dist
        z = posterior.mode() if posterior_mode else posterior.sample()
        return (z - latents_mean) * latents_std, latents_mean, latents_std
    elif args.ae_type == 'sd2':
        posterior = vae.encode(x).latent_dist
        z = posterior.mode() if posterior_mode else posterior.sample()
        return z * vae.config.scaling_factor, None, None


def decode_latent(vae, sr_latent, args, latents_mean, latents_std, light_decoder=None):
    """Single-shot VAE decode -> pixels in [-1, 1]. Mirrors the old _decode_latent."""
    if args.ae_type == 'sd2':
        sr_u = sr_latent / vae.config.scaling_factor
        return light_decoder(sr_u).clamp(-1, 1)
    elif args.ae_type == 'qwen':
        sr_latent = sr_latent / latents_std + latents_mean
        return vae.decode(sr_latent, return_dict=False)[0].clamp(-1, 1)


def tiled_latent_inference(
    model, vae, venc, lq_tensor, args,
    device='mps', light_decoder=None, noise=None,
):
    """
    Latent-space tiled inference for VOSR DiT.

    1. VAE-encode the full image once (no tile seams from encoder).
    2. For each tile, crop the corresponding LQ pixel region, resize to
       dinov2_size, and extract DINOv2 features independently.  This keeps
       exact spatial correspondence (same as training) while producing a
       constant feature shape across tiles (avoids @torch.compile recompilation).
    3. Generate noise z for the full latent (consistent across overlapping tiles).
    4. For each flow step, tile only the DiT forward pass in latent space,
       blend velocity predictions with Gaussian weights, then update z globally.
    5. VAE-decode the full result latent once.
    """
    AE_FACTOR = 8
    b = lq_tensor.shape[0]
    patch_size = getattr(args, 'patch_size', 2)

    # --- Full-image encode (done once) ---
    with torch.no_grad():
        lq_latent, latents_mean, latents_std = encode_dispatch(vae, lq_tensor, args, device)

    _, lc, lh, lw = lq_latent.shape

    # --- Pixel tile params -> latent tile params (aligned to patch_size) ---
    lt_size = max((args.tile_size // AE_FACTOR // patch_size) * patch_size, patch_size)
    lt_overlap = max(args.tile_overlap // AE_FACTOR, lt_size // 8)
    lt_size = min(lt_size, min(lh, lw))
    lt_overlap = min(lt_overlap, lt_size - 1)

    # --- Fast path: no tiling needed ---
    if lh <= lt_size and lw <= lt_size:
        print(f"[Tiled Latent]: latent {lh}x{lw} fits in tile {lt_size}, no tiling needed.")
        with torch.no_grad():
            z_fea = get_venc_features(venc, lq_tensor, args) if venc is not None else None
            z = noise.clone()
            n_steps = args.infer_steps
            t_seq = torch.linspace(1., 0., n_steps + 1, device=device)
            for i in range(n_steps):
                t_cur, t_nxt = t_seq[i], t_seq[i + 1]
                u = model(torch.cat([lq_latent, z], 1),
                          t_cur.expand(b), t_nxt.expand(b), z_fea)
                z = z - (t_cur - t_nxt) * u
            return decode_dispatch(vae, z, args, latents_mean, latents_std, light_decoder)

    # --- Build tile grid & Gaussian weights ---
    h_pos = _make_tile_grid(lh, lt_size, lt_overlap)
    w_pos = _make_tile_grid(lw, lt_size, lt_overlap)
    g_weight = _gaussian_weights(lt_size, lt_size, lc, device)
    print(f"[Tiled Latent]: latent {lh}x{lw}, tile={lt_size}, overlap={lt_overlap}, "
          f"grid={len(h_pos)}x{len(w_pos)}")

    # --- Per-tile DINOv2 features (pre-computed once) ---
    # Each tile's pixel crop is independently resized to dinov2_size and fed
    # through DINOv2, producing features with constant shape that exactly match
    # the tile's spatial content (same as training-time behaviour).
    tile_venc = {}
    if venc is not None:
        with torch.no_grad():
            for hi in h_pos:
                for wi in w_pos:
                    ph_s, pw_s = hi * AE_FACTOR, wi * AE_FACTOR
                    ph_e = min((hi + lt_size) * AE_FACTOR, lq_tensor.shape[2])
                    pw_e = min((wi + lt_size) * AE_FACTOR, lq_tensor.shape[3])
                    lq_crop = lq_tensor[:, :, ph_s:ph_e, pw_s:pw_e]
                    tile_venc[(hi, wi)] = get_venc_features(venc, lq_crop, args)

    # --- Full-latent noise (shared across tiles for consistency) ---
    z = noise.clone()

    # --- Flow matching loop with tiled DiT ---
    n_steps = args.infer_steps
    t_seq = torch.linspace(1., 0., n_steps + 1, device=device)

    with torch.no_grad():
        for step_i in range(n_steps):
            t_cur, t_nxt = t_seq[step_i], t_seq[step_i + 1]
            dt = t_cur - t_nxt

            u_acc = torch.zeros_like(lq_latent)
            w_acc = torch.zeros_like(lq_latent)

            for hi in h_pos:
                for wi in w_pos:
                    he, we = hi + lt_size, wi + lt_size

                    inp = torch.cat([lq_latent[:, :, hi:he, wi:we],
                                     z[:, :, hi:he, wi:we]], dim=1)

                    z_fea_tile = tile_venc.get((hi, wi))
                    u_tile = model(inp, t_cur.expand(b), t_nxt.expand(b), z_fea_tile)

                    u_acc[:, :, hi:he, wi:we] += u_tile * g_weight
                    w_acc[:, :, hi:he, wi:we] += g_weight

            z = z - dt * (u_acc / w_acc)

    # --- Full-latent decode (done once) ---
    with torch.no_grad():
        return decode_dispatch(vae, z, args, latents_mean, latents_std, light_decoder)


def encode_dispatch(vae, x, args, device):
    with torch.autocast(device, enabled=False):
        return encode_latent(vae, x, args, device, True)


def decode_dispatch(vae, latent, args, mean, std, light_decoder=None):
    with torch.autocast(latent.device.type, enabled=False):
        return decode_latent(vae, latent, args, mean, std, light_decoder)
