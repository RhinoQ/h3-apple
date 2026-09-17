"""Public video inputs and the input canvas contract, without model weights."""

import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image
import pytest

from h3_apple import resolve
from h3_apple.media import probe_reference, reference_video_size, tool
from h3_apple.runtime import ref2va_multimodal as mixed
from h3_apple.runtime.ref2va import reference_image_size
from h3_apple.runtime.reference_cache import cache_contract, load_or_build


@pytest.fixture
def reference(tmp_path):
    path = tmp_path / "input.mp4"
    subprocess.run([tool("ffmpeg"), "-v", "error", "-f", "lavfi", "-i",
        "testsrc2=size=64x36:rate=24:duration=2", "-f", "lavfi", "-i",
        "sine=frequency=500:sample_rate=32000:duration=2", "-ac", "2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(path)],
        check=True, capture_output=True)
    return path


@pytest.mark.parametrize("source,expected", [
    ((854, 480), (768, 1344)), ((1920, 1080), (768, 1344)),
    ((480, 854), (1344, 768)), ((256, 256), (768, 768)),
    ((400, 100), (512, 2016)), ((100, 400), (2016, 512)),
])
def test_upstream_canvas_preserves_ratio_and_can_upscale(source, expected):
    assert reference_video_size(*source) == expected


@pytest.mark.parametrize("source", [(0, 100), (True, 100), (1.5, 100), (1000, 10)])
def test_invalid_video_geometry_fails(source):
    with pytest.raises(ValueError, match="Reference video"):
        reference_video_size(*source)


def test_image_policy_retains_its_existing_budget():
    assert reference_image_size(854, 480, 672 * 384) == (384, 672)
    assert reference_image_size(64, 64, 672 * 384) == (64, 64)


def test_api_and_cli_preserve_video_order_without_loading_mlx(reference, tmp_path):
    r = resolve("Use Video 1, then Video 2.", reference_videos=[reference, reference], seed=42)
    assert r.reference_videos == (str(reference), str(reference))
    assert (r.task, r.resolution, r.preset_version) == ("ref2va", "768p", "ours-ref2va-video-dense-v1")
    assert resolve("A scene", reference_videos=[reference], resolution="576p").resolution == "576p"
    result = subprocess.run([sys.executable, "-m", "h3_apple", "resolve", "--prompt", r.prompt,
        "--reference-video", str(reference), "--duration", "5", "--seed", "42"],
        cwd=tmp_path, capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)["reference_videos"] == [str(reference)]
    subprocess.run([sys.executable, "-c", "import h3_apple,sys; "
        "h3_apple.resolve('Video 1', reference_videos=[sys.argv[1]]); "
        "assert 'mlx.core' not in sys.modules", str(reference)], cwd=tmp_path, check=True)


@pytest.mark.parametrize("paths", [[], "video.mp4", [None], [""], ["x"] * 4])
def test_invalid_video_list_is_rejected(paths):
    with pytest.raises(ValueError, match="video"):
        resolve("A scene", reference_videos=paths)


def test_video_task_and_keyframe_conflicts_and_mixed_image_policy(reference, tmp_path):
    image = tmp_path / "subject.png"
    Image.new("RGB", (64, 64), "red").save(image)
    for kwargs in ({"task": "t2va"}, {"task": "fl2va"}, {"first_frame": image}, {"last_frame": image}):
        with pytest.raises(ValueError):
            resolve("Video 1", reference_videos=[reference], **kwargs)
    with pytest.raises(ValueError, match="only to Ref2VA images"):
        resolve("Video 1", reference_videos=[reference], reference_resize="match")
    request = resolve("Video 1 and Picture 1", reference_videos=[reference],
                      reference_images=[image], reference_resize="match", task="ref2va")
    assert request.task == "ref2va" and request.resolution == "768p"
    assert request.reference_images == (str(image),) and request.reference_resize == "match"


def test_both_encoders_receive_same_full_canvas_and_decoding_does_not_extend(reference, tmp_path):
    image = tmp_path / "image.png"
    Image.new("RGB", (64, 64), "red").save(image)
    refs = mixed.prepare_references(dict(image_paths=[str(image)], video_paths=[str(reference)],
                                         pixel_budget=672 * 384), model_frames=124)
    assert refs[0]["image"].size == (64, 64)
    video = refs[1]
    assert video["frames"].shape == (48, 768, 1344, 3)
    assert video["frames"].dtype == np.uint8
    sampled, times = mixed.sample_vision_frames(video["frames"])
    np.testing.assert_array_equal(sampled, video["frames"][[0, 12, 24, 36]])
    assert times == [.25, 1.25]
    assert video["waveform"].shape[0] == 2 and np.isfinite(video["waveform"]).all()


def test_cache_rejects_old_canvas_and_leaves_evidence(tmp_path):
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"identity fixture")
    options = dict(video_paths=[clip], pixel_budget=672 * 384,
                   cache_model_identity="weights", cache_source_identity="runtime")
    new = cache_contract(dict(prompt="edit", seed=42), options)
    assert new["video_reference_canvas"]["short_edge"] == 768
    old = {k: v for k, v in new.items() if k != "video_reference_canvas"}
    directory = tmp_path / "cache"
    load_or_build(directory, old, lambda: ({"x": np.zeros(2)}, {}))
    before = (directory / "manifest.json").read_bytes()
    with pytest.raises(ValueError, match="mismatch"):
        load_or_build(directory, new, lambda: pytest.fail("Never overwrite old conditions"))
    assert (directory / "manifest.json").read_bytes() == before


@pytest.mark.parametrize("changes", [
    {"duration": "nan"}, {"duration": "1"}, {"duration": "16"},
    {"sample_aspect_ratio": "4:3"}, {"side_data_list": [{"rotation": 45}]},
])
def test_probe_rejects_unsupported_media_before_worker(tmp_path, monkeypatch, changes):
    from types import SimpleNamespace
    path = tmp_path / "video.mp4"
    path.touch()
    stream = dict(codec_type="video", width=640, height=360, duration="2")
    stream.update(changes)
    monkeypatch.setattr("h3_apple.media.subprocess.run", lambda *a, **k:
        SimpleNamespace(stdout=json.dumps({"streams": [stream]})))
    with pytest.raises(ValueError):
        probe_reference(path, "videos")


@pytest.mark.parametrize("with_image", [False, True])
def test_product_worker_receives_immutable_ordered_video_inputs(reference, tmp_path, monkeypatch, with_image):
    from h3_apple import process as runner
    from h3_apple.io import digest
    image = tmp_path / "picture.png"
    Image.new("RGB", (64, 64), "red").save(image)
    request = resolve("Edit Video 1", reference_videos=[reference],
                      reference_images=[image] if with_image else None, duration=5, seed=42)
    worker = tmp_path / "worker.py"
    worker.write_text("import json,sys,pathlib\ns=json.loads(sys.stdin.readline())\n"
        "pathlib.Path(s['workspace'],'received.json').write_text(json.dumps(s))\n"
        "print(json.dumps({'kind':'error','error':'captured'}),flush=True)\nsys.exit(7)\n")
    real_popen = subprocess.Popen
    monkeypatch.setattr(runner, "load_assets", lambda _: dict(identity="model", task="ref2va", ref2va_native="native"))
    monkeypatch.setattr(runner.subprocess, "Popen", lambda args, **kwargs:
        real_popen([sys.executable, str(worker)], **kwargs))
    output = tmp_path / "generated.mp4"
    with pytest.raises(RuntimeError, match="captured"):
        runner.run_generation(request, output=output)
    record = json.loads(output.with_suffix(".run.json").read_text())
    spec = json.loads(Path(record["workspace"], "received.json").read_text())
    options = spec["ref2va"]
    snapshot = Path(options["video_paths"][0])
    assert snapshot.parent == Path(record["workspace"])
    assert snapshot.read_bytes() == reference.read_bytes()
    assert options["attention"] == "dense" and len(options["image_paths"]) == int(with_image)
    assert record["reference_inputs"][-1]["sha256"] == digest(reference)


def test_video_display_rotation_is_applied_before_canvas_selection(reference, tmp_path):
    rotated = tmp_path / "rotated.mp4"
    subprocess.run([tool("ffmpeg"), "-v", "error", "-display_rotation:v:0", "90", "-i", str(reference),
        "-c", "copy", str(rotated)], check=True, capture_output=True)
    refs = mixed.prepare_references(dict(video_paths=[str(rotated)], pixel_budget=672 * 384), model_frames=5)
    assert refs[0]["frames"].shape == (5, 1344, 768, 3)
