"""Public X2 geometry, setup policy and color packing, without model inference."""

import hashlib
import json

import numpy as np
from PIL import Image
import pytest

from h3_apple import DownloadApprovalRequired, generate, resolve
from h3_apple import cli, process, vsa_preparation, x2_assets


@pytest.fixture
def reference(tmp_path):
    path = tmp_path / "new-reference.png"
    Image.new("RGB", (96, 64), "green").save(path)
    return path


@pytest.mark.parametrize("resolution,sample,output", [
    ("544p", (960, 544), (1920, 1088)),
    ("576p", (1024, 576), (2048, 1152)),
    ("768p", (1376, 768), (2732, 1536)),
])
@pytest.mark.parametrize("aspect", ["16:9", "9:16"])
def test_x2_resolves_both_orientations(reference, resolution, sample, output, aspect):
    req = resolve("Picture 1", reference_images=[reference], resolution=resolution,
                  aspect_ratio=aspect, x2=True, duration=5, seed=0)
    if aspect == "9:16":
        sample, output = sample[::-1], output[::-1]
    assert (req.model_width, req.model_height) == sample
    assert (req.width, req.height) == output
    assert (req.num_frames, req.model_num_frames, req.num_steps) == (120, 124, 4)
    assert req.x2 and req.mode == "VSA"


@pytest.mark.parametrize("options", [{"resolution": "544p"}, {"x2": 1}, {"x2": "yes"}])
def test_invalid_combinations_fail_before_preparation(reference, monkeypatch, options):
    monkeypatch.setattr(process, "ensure_ready", lambda *a, **kw: pytest.fail("setup before validation"))
    with pytest.raises(ValueError):
        generate("Scene", reference_images=[reference], **options)


def test_model_override_cannot_be_silently_ignored(reference):
    with pytest.raises(ValueError, match="requires x2"):
        generate("Scene", reference_images=[reference], x2_model_dir="/models/x2")


def test_cli_passes_x2_and_portrait_to_public_api(monkeypatch, tmp_path):
    from h3_apple import GenerationResult
    seen = []
    monkeypatch.setattr(cli, "generate", lambda **kw: seen.append(kw) or
                        GenerationResult(tmp_path / "out.mp4", tmp_path / "out.json", 1, 0))
    assert cli.main(["generate", "--image", "ref.png", "--prompt", "Scene", "--x2",
                     "--resolution", "544p", "--aspect-ratio", "9:16", "--no-progress"]) == 0
    assert seen[0]["x2"] is True
    assert (seen[0]["resolution"], seen[0]["aspect_ratio"]) == ("544p", "9:16")


def test_combined_download_is_approved_before_either_setup(reference, monkeypatch, tmp_path):
    monkeypatch.setattr(vsa_preparation, "plan", lambda *a, **kw:
                        dict(download_bytes=18_000_000_000, additional_disk_bytes=190_000_000_000))
    monkeypatch.setattr(x2_assets, "plan", lambda *a, **kw:
                        dict(download_bytes=5_000_000_000, additional_disk_bytes=7_000_000_000))
    monkeypatch.setattr(process, "ensure_ready", lambda *a, **kw: pytest.fail("base downloaded"))
    monkeypatch.setattr(x2_assets, "prepare", lambda *a, **kw: pytest.fail("X2 downloaded"))
    output = tmp_path / "outputs" / "out.mp4"
    with pytest.raises(DownloadApprovalRequired) as caught:
        generate("Scene", reference_images=[reference], x2=True, output=output)
    assert caught.value.download_bytes == 23_000_000_000
    assert caught.value.additional_disk_bytes == 197_000_000_000
    assert not output.parent.exists()


@pytest.fixture
def tiny_assets(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    entries = []
    for name in ("model.safetensors", "LICENSE", "NOTICE"):
        content = ("test " + name).encode()
        (source / name).write_bytes(content)
        entries.append(dict(path=name, bytes=len(content), sha256=hashlib.sha256(content).hexdigest(),
                            url="https://example.invalid/never-download"))
    monkeypatch.setattr(x2_assets, "manifest", lambda: dict(files=entries, recipe="test", revision="a" * 40))
    monkeypatch.setenv("H3_DEVICE_LOCK", str(tmp_path / "device.lock"))
    return source, tmp_path / "destination", entries


def test_prepare_reuses_weights_and_notices_without_network(tiny_assets, monkeypatch):
    source, destination, entries = tiny_assets
    monkeypatch.setattr(x2_assets, "download", lambda *a: pytest.fail("download despite reuse"))
    assert x2_assets.plan(destination, [source])["download_bytes"] == 0
    assert not destination.exists()
    result = x2_assets.prepare(destination, [source])
    assert result["sha256"] == entries[0]["sha256"]
    assert x2_assets.plan(destination)["additional_disk_bytes"] == 0
    for entry in entries:
        assert (destination / entry["path"]).read_bytes() == (source / entry["path"]).read_bytes()


def test_corrupt_weight_is_rejected_and_preserved(tiny_assets):
    source, destination, _ = tiny_assets
    destination.mkdir()
    target = destination / "model.safetensors"
    target.write_bytes(b"broken")
    with pytest.raises(ValueError, match="checksum mismatch"):
        x2_assets.prepare(destination, [source])
    assert target.read_bytes() == b"broken"


def test_setup_resumes_pinned_downloads_and_retains_notices(tiny_assets, monkeypatch):
    source, destination, entries = tiny_assets
    destination.mkdir()
    part = x2_assets.partial_path(destination / entries[0]["path"], entries[0]["sha256"])
    part.write_bytes(b"test")
    assert x2_assets.plan(destination)["download_bytes"] == sum(x["bytes"] for x in entries) - 4
    calls = []
    def download(url, target, size, sha):
        calls.append((size, sha))
        target.write_bytes((source / target.name).read_bytes())
    monkeypatch.setattr(x2_assets, "download", download)
    x2_assets.prepare(destination)
    assert calls == [(x["bytes"], x["sha256"]) for x in entries]


def test_pixel_shuffle_preserves_each_rgb_phase():
    mx = pytest.importorskip("mlx.core")
    from h3_apple.runtime.x2_vae import pixel_shuffle
    packed = np.arange(12 * 2 * 2 * 3, dtype=np.float32).reshape(1, 12, 2, 2, 3)
    actual = np.asarray(pixel_shuffle(mx.array(packed)))
    expected = np.empty((1, 3, 2, 4, 6), np.float32)
    for color in range(3):
        for dy in range(2):
            for dx in range(2):
                expected[:, color, :, dy::2, dx::2] = packed[:, 4 * color + 2 * dy + dx]
    np.testing.assert_array_equal(actual, expected)


@pytest.mark.parametrize("x2", [False, True])
@pytest.mark.parametrize("portrait", [False, True])
def test_delivery_only_crops_alignment_and_time(x2, portrait):
    pytest.importorskip("mlx.core")
    from h3_apple.runtime.engine import delivery_frames
    scale = 2 if x2 else 1
    mw, mh, width, height = (8, 4, 6, 4) if not portrait else (4, 8, 4, 6)
    request = dict(model_width=mw, model_height=mh, width=width * scale, height=height * scale,
                   model_num_frames=4, num_frames=3, x2=x2)
    frames = np.arange(4 * mh * mw * scale**2 * 3).reshape(4, mh * scale, mw * scale, 3)
    actual = delivery_frames(frames, request)
    expected = frames[:3, :, scale:-scale] if not portrait else frames[:3, scale:-scale, :]
    np.testing.assert_array_equal(actual, expected)
    assert np.shares_memory(actual, frames)
    with pytest.raises(ValueError, match="geometry"):
        delivery_frames(frames[:-1], request)


def test_asset_manifest_is_pinned():
    data = x2_assets.manifest()
    assert len(data["revision"]) == 40
    assert {x["path"] for x in data["files"]} >= {"LICENSE", "NOTICE"}
    for item in data["files"]:
        assert len(item["sha256"]) == 64 and data["revision"] in item["url"]
    assert sum(x["bytes"] for x in data["files"]) < 20_000_000_000
