"""Public audio files, explicit soundtrack selection and immutable conditions."""

import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
from PIL import Image
import pytest

from h3_apple import resolve
from h3_apple.media import probe_reference, tool
from h3_apple.runtime import ref2va_multimodal as mixed
from h3_apple.runtime.reference_cache import cache_contract, load_or_build


@pytest.fixture
def media(tmp_path):
    picture, audio, video = (tmp_path / n for n in ("picture.png", "voice.wav", "scene.mp4"))
    Image.new("RGB", (64, 64), "navy").save(picture)
    subprocess.run([tool("ffmpeg"), "-v", "error", "-f", "lavfi", "-i",
        "sine=frequency=410:sample_rate=44100:duration=2", str(audio)], check=True, capture_output=True)
    subprocess.run([tool("ffmpeg"), "-v", "error", "-f", "lavfi", "-i",
        "testsrc2=size=64x36:rate=24:duration=2", "-f", "lavfi", "-i",
        "sine=frequency=720:sample_rate=32000:duration=2", "-ac", "2", "-c:v", "libx264",
        "-pix_fmt", "yuv420p", "-c:a", "aac", str(video)], check=True, capture_output=True)
    return picture, audio, video


def test_public_audio_infers_ref_task_and_cli_works_without_mlx(media, tmp_path):
    picture, audio, video = media
    request = resolve("Picture 1 uses Audio 1", reference_images=[picture], reference_audio=[audio], seed=12)
    assert (request.task, request.resolution, request.preset_version) == (
        "ref2va", "768p", "ours-ref2va-audio-dense-v1")
    assert request.reference_audio == (str(audio),)
    result = subprocess.run([sys.executable, "-m", "h3_apple", "resolve", "--prompt", "use Audio 1",
        "--reference-video", str(video), "--reference-audio", str(audio), "--reference-audio", str(audio),
        "--no-reference-video-audio", "--seed", "12"], cwd=tmp_path, capture_output=True, text=True, check=True)
    spec = json.loads(result.stdout)
    assert spec["reference_audio"] == [str(audio), str(audio)] and spec["reference_video_audio"] is False
    subprocess.run([sys.executable, "-c", "import h3_apple,sys; "
        "h3_apple.resolve('voice',reference_images=[sys.argv[1]],reference_audio=[sys.argv[2]]); "
        "assert 'mlx.core' not in sys.modules", str(picture), str(audio)], cwd=tmp_path, check=True)


@pytest.mark.parametrize("paths", [[], "voice.wav", [None], [""], ["voice.wav"] * 4])
def test_invalid_audio_list(paths):
    with pytest.raises(ValueError, match="audio"):
        resolve("talk", reference_audio=paths)


def test_audio_requires_visual_reference_and_cannot_mix_tasks(media):
    picture, audio, video = media
    for kwargs in ({}, {"first_frame": picture}, {"last_frame": picture}):
        with pytest.raises(ValueError, match="at least one Ref2VA"):
            resolve("talk", reference_audio=[audio], **kwargs)
    for kwargs in ({"task": "t2va"}, {"task": "fl2va"}, {"first_frame": picture}):
        with pytest.raises(ValueError):
            resolve("talk", reference_images=[picture], reference_audio=[audio], **kwargs)
    with pytest.raises(ValueError, match="at most 12"):
        resolve("talk", reference_images=[picture] * 9, reference_videos=[video] * 3, reference_audio=[audio])


@pytest.mark.parametrize("value", [None, "false", 0, 1])
def test_soundtrack_selection_requires_boolean(value):
    with pytest.raises(ValueError, match="boolean"):
        resolve("scene", reference_video_audio=value)


def test_soundtrack_selection_requires_video_and_old_defaults_survive(media):
    picture, _, video = media
    with pytest.raises(ValueError, match="requires a reference video"):
        resolve("scene", reference_images=[picture], reference_video_audio=False)
    assert resolve("scene").preset_version == "ours-v1"
    assert resolve("scene", first_frame=picture).preset_version == "ours-fl2va-vsa-v1.2"
    old = resolve("scene", reference_images=[picture])
    assert old.resolution == "576p" and old.preset_version == "ours-ref2va-v1"
    assert resolve("scene", reference_videos=[video]).reference_video_audio is True


def test_wave_and_mp3_decode_mono_to_stereo_and_video_file_is_rejected(media, tmp_path):
    _, audio, video = media
    mp3 = tmp_path / "voice.mp3"
    subprocess.run([tool("ffmpeg"), "-v", "error", "-i", str(audio), str(mp3)], check=True, capture_output=True)
    for path in (audio, mp3):
        assert probe_reference(path, "audio")["streams"][0]["channels"] == 1
        wave = mixed.decode_waveform(path, 5)
        assert wave.shape == (2, 64000) and np.isfinite(wave).all()
        np.testing.assert_array_equal(wave[0], wave[1])
    with pytest.raises(ValueError, match="no moving video"):
        probe_reference(video, "audio")


@pytest.mark.parametrize("changes", [{"duration": "nan"}, {"duration": "1"}, {"duration": "16"},
    {"channels": 6}, {"sample_rate": "0"}])
def test_unsupported_audio_is_rejected_before_model(tmp_path, monkeypatch, changes):
    path = tmp_path / "voice.wav"
    path.touch()
    stream = dict(codec_type="audio", channels=1, sample_rate="44100", duration="2")
    stream.update(changes)
    monkeypatch.setattr("h3_apple.media.subprocess.run", lambda *a, **k:
        SimpleNamespace(stdout=json.dumps(dict(streams=[stream]))))
    with pytest.raises(ValueError):
        probe_reference(path, "audio")


def test_audio_cover_art_is_allowed_but_multiple_audio_streams_are_not(tmp_path, monkeypatch):
    path = tmp_path / "cover.mp3"
    path.touch()
    stream = dict(codec_type="audio", channels=2, sample_rate="32000", duration="2")
    data = dict(streams=[stream, dict(codec_type="video", disposition=dict(attached_pic=1))])
    monkeypatch.setattr("h3_apple.media.subprocess.run", lambda *a, **k:
        SimpleNamespace(stdout=json.dumps(data)))
    assert probe_reference(path, "audio") == data
    data["streams"].append(stream)
    with pytest.raises(ValueError, match="one audio stream"):
        probe_reference(path, "audio")


def test_turning_off_video_audio_preserves_visuals_and_explicit_audio(media):
    picture, audio, video = media
    options = dict(image_paths=[picture], audio_paths=[audio], video_paths=[video], pixel_budget=256)
    enabled = mixed.prepare_references(options, 5)
    disabled = mixed.prepare_references(dict(options, video_audio=False), 5)
    assert [r["kind"] for r in disabled] == ["image", "audio", "video"]
    assert "waveform" in enabled[-1] and "waveform" not in disabled[-1]
    np.testing.assert_array_equal(enabled[0]["image"], disabled[0]["image"])
    np.testing.assert_array_equal(enabled[1]["waveform"], disabled[1]["waveform"])
    np.testing.assert_array_equal(enabled[2]["frames"], disabled[2]["frames"])
    assert enabled[1]["waveform"].shape == (2, round(5 / 24 * 32000))


def test_cached_audio_uses_bytes_and_never_reuses_a_different_soundtrack_policy(media, tmp_path):
    picture, audio, video = media
    copied = tmp_path / "copied.wav"
    copied.write_bytes(audio.read_bytes())
    request = dict(prompt="talk", reference_audio=[str(audio)])
    options = dict(image_paths=[picture], audio_paths=[audio], video_paths=[video], pixel_budget=256,
                   cache_model_identity="model", cache_source_identity="code")
    original = cache_contract(request, options)
    assert original == cache_contract(dict(request, reference_audio=[str(copied)]), dict(options, audio_paths=[copied]))
    changed = cache_contract(request, dict(options, video_audio=False))
    directory = tmp_path / "cache"
    load_or_build(directory, original, lambda: ({"audio": np.ones(2)}, {}))
    before = (directory / "manifest.json").read_bytes()
    with pytest.raises(ValueError, match="mismatch"):
        load_or_build(directory, changed, lambda: pytest.fail("Wrong audio reused"))
    assert before == (directory / "manifest.json").read_bytes()


@pytest.mark.parametrize("with_video", [False, True])
def test_audio_worker_receives_dense_snapshots_and_explicit_soundtrack_policy(media, tmp_path, monkeypatch, with_video):
    from h3_apple import process as runner
    from h3_apple.io import digest
    picture, audio, video = media
    request = resolve("Use Audio 1", reference_images=[picture], reference_audio=[audio],
        reference_videos=[video] if with_video else None, reference_video_audio=not with_video,
        reference_resize="match", duration=5, seed=42)
    worker = tmp_path / "worker.py"
    worker.write_text("import json,sys,pathlib\ns=json.loads(sys.stdin.readline())\n"
        "pathlib.Path(s['workspace'],'received.json').write_text(json.dumps(s))\n"
        "print(json.dumps({'kind':'error','error':'captured'}),flush=True)\nsys.exit(7)\n")
    real_popen = subprocess.Popen
    monkeypatch.setattr(runner, "load_assets", lambda _: dict(identity="model", task="ref2va", ref2va_native="native"))
    monkeypatch.setattr(runner.subprocess, "Popen", lambda args, **kwargs: real_popen([sys.executable, str(worker)], **kwargs))
    output = tmp_path / "generated.mp4"
    with pytest.raises(RuntimeError, match="captured"):
        runner.run_generation(request, output=output)
    record = json.loads(output.with_suffix(".run.json").read_text())
    options = json.loads(Path(record["workspace"], "received.json").read_text())["ref2va"]
    assert options["attention"] == "dense" and options["video_audio"] is (not with_video)
    assert options["pixel_budget"] == 1376 * 768
    copied = Path(options["audio_paths"][0])
    assert copied.parent == Path(record["workspace"]) and copied.read_bytes() == audio.read_bytes()
    source = next(r for r in record["reference_inputs"] if r.get("kind") == "audio")
    assert source["sha256"] == digest(copied)
