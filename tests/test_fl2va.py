import json
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from h3_apple.api import resolve
from h3_apple.fl2va_recipe import FL12_SAMPLING
from h3_apple.assets import import_assets, load_assets
from h3_apple.runtime.fl2va_pipeline import keyframe_layout, prepare_keyframe
from h3_apple._vendor.fastvideo_mlx.minimax_h3 import build_row_timesteps


def test_keyframes_resolve_to_a_dedicated_model_task(tmp_path):
    image = tmp_path / "frame.png"
    Image.new("RGB", (64, 32), "red").save(image)
    request = resolve("gentle motion", first_frame=image, last_frame=image, seed=42)
    assert request.task == "fl2va" and request.resolution == "768p"
    assert request.first_frame == request.last_frame == str(image)
    assert (request.model_width, request.model_height) == (1376, 768)
    with pytest.raises(ValueError, match="different model tasks"):
        resolve("motion", first_frame=image, reference_images=[image])


def test_follower_crops_while_first_anchor_stretches():
    pixels = np.zeros((32, 96, 3), np.uint8)
    pixels[:, 32:64] = 255
    image = Image.fromarray(pixels)
    first = np.asarray(prepare_keyframe(image, 32, 32, stretch=True))
    follower = np.asarray(prepare_keyframe(image, 32, 32, stretch=False))
    assert follower.min() == 255 and first[:, 0].max() < 5


def test_anchors_have_distinct_target_times_and_never_enter_target_indices():
    tags = np.array([1, 0, 0, 1], np.int64)
    geometry = dict(latent_frame_count=37, latent_height=4, latent_width=6)
    layout = keyframe_layout(tags, geometry, 124, ["first", "last"])
    first = layout.position_ids[layout.video_indices[:6]]
    last = layout.position_ids[layout.video_indices[6:12]]
    assert np.all(first[:, 0] == len(tags)) and np.all(last[:, 0] > first[:, 0])
    np.testing.assert_array_equal(first[:, 1:], last[:, 1:])
    assert layout.num_condition_video_rows == 12
    assert len(layout.video_indices[12:]) == 37 * 6
    times, inverse = build_row_timesteps(layout, .2, .5, condition_video_timestep=.999)
    rows = times[inverse]
    np.testing.assert_array_equal(rows[layout.video_indices[:12]], np.full(12, .999, np.float32))
    np.testing.assert_array_equal(rows[layout.video_indices[12:]], np.full(37 * 6, .2, np.float32))
    with pytest.raises(ValueError, match="anchors"):
        keyframe_layout(tags, geometry, 124, ["last", "first"])


def test_fl_bundle_cannot_load_as_ref_or_text(tmp_path):
    checkpoint, components, native = [tmp_path / name for name in ("dit", "components", "native")]
    checkpoint.mkdir()
    (checkpoint / "mlx_h3_dit.json").write_text(json.dumps(dict(num_blocks=50,
        vsa=dict(capable=True), quantization=dict(mode="affine", bits=8, group_size=64))))
    (checkpoint / "mlx_h3_dit.safetensors").write_bytes(b"synthetic bundle fixture")
    (checkpoint / "fl2va_recipe.json").write_text(json.dumps(dict(schema="h3-apple-fl2va/v1",
        task="fl2va", lora_rank=128, lora_alpha=8, lora_tensors=624, gate_tensors=50,
        precision="int8_group64_bf16", sampling=FL12_SAMPLING, fasth3_t2va_deltas_applied=False)))
    for relative in ("text_encoder/config.json", "text_encoder/model.safetensors", "tokenizer/tokenizer.json",
                     "vae/config.json", "vae/model.safetensors", "audio_vae/config.json", "audio_vae/model.safetensors"):
        p = components / relative; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b"{}")
    for relative in ("processor/preprocessor_config.json", "tokenizer/tokenizer.json", "text_encoder/config.json",
                     "text_encoder/model.safetensors", "video_vae/config.json", "video_vae/source/config.json",
                     "video_vae/source/model.safetensors"):
        p = native / relative; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b"{}")
    with pytest.raises(ValueError, match="fl2va_native"):
        import_assets(checkpoint, components, tmp_path / "bad")
    bundle = import_assets(checkpoint, components, tmp_path / "bundle", fl2va_native=native)
    assert bundle["task"] == "fl2va" and bundle["format_version"] == 4
    assert Path(bundle["fl2va_native"], "video_vae/source/model.safetensors").exists()
    assert load_assets(tmp_path / "bundle", verify=True)["identity"] == bundle["identity"]
