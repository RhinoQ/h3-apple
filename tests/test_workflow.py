"""First-run choices, stage handoff and recovery through the public interfaces."""

import importlib
import io
import json
from pathlib import Path

from PIL import Image
import pytest

from h3_apple import DownloadApprovalRequired, GenerationResult, UpscaleResult, generate
from h3_apple import cli, workflow


@pytest.fixture
def setup(tmp_path, monkeypatch):
    from h3_apple import preparation, vsa_preparation
    from h3_apple.runtime import backend
    monkeypatch.chdir(tmp_path)
    ref = tmp_path / "ref.png"
    Image.new("RGB", (96, 64), "blue").save(ref)
    calls = []
    base = dict(download_bytes=0, additional_disk_bytes=0)
    sr = dict(download_bytes=0, additional_disk_bytes=0)
    monkeypatch.setattr(preparation, "plan", lambda *a, **kw: base)
    monkeypatch.setattr(vsa_preparation, "plan", lambda *a, **kw: base)
    monkeypatch.setattr(backend, "check_dependencies", lambda: None)
    monkeypatch.setattr(workflow, "check_environment", lambda video: calls.append("preflight"))
    monkeypatch.setattr(workflow.assets, "plan", lambda *a, **kw: sr)
    monkeypatch.setattr(workflow.assets, "prepare", lambda *a, **kw: calls.append("models"))

    def generation(request, **kw):
        calls.append(("generate", request, kw))
        video = kw["output"]
        video.parent.mkdir(parents=True)
        video.write_bytes(b"native")
        record = video.with_suffix(".run.json")
        record.write_text(json.dumps(dict(status="complete", request=request.to_dict())))
        return GenerationResult(video, record, 8, request.seed)

    def restoration(source, **kw):
        calls.append(("upscale", source, kw))
        assert source.read_bytes() == b"native"
        video = kw["output"]
        video.write_bytes(b"restored")
        record = video.with_suffix(".run.json")
        record.write_text(json.dumps(dict(status="complete", elapsed_seconds=20)))
        return UpscaleResult(video, record, 20)

    monkeypatch.setattr(workflow, "run_generation", generation)
    monkeypatch.setattr(workflow, "upscale", restoration)
    return ref, calls, base, sr


@pytest.mark.parametrize("mode,quality", [("SOL", None), ("VSA", None), ("VSA", "high")])
@pytest.mark.parametrize("aspect,shape", [("16:9", (1366, 768)), ("9:16", (768, 1366))])
def test_one_call_restoration_preserves_native_and_records_both_stages(setup, mode, quality, aspect, shape):
    ref, calls, _, _ = setup
    result = generate("Scene", reference_images=[ref], upscale=True, quality=quality,
                      seed=42, mode=mode, aspect_ratio=aspect)
    assert calls[:2] == ["preflight", "models"]
    _, request, options = calls[2]
    assert (request.width, request.height) == shape
    assert request.duration == 5 and request.resolution == "768p" and not request.x2
    assert request.mode == mode
    assert request.attention == ('dense' if quality == 'high' else 'vsa' if mode == 'VSA' else None)
    assert result.video_path.read_bytes() == b"restored"
    assert result.native_video_path.read_bytes() == b"native"
    assert calls[3][1] == result.native_video_path
    record = json.loads(result.metadata_path.read_text())
    assert record["generation"]["seed"] == 42
    assert Path(record["generation"]["metadata_path"]).is_file()
    assert result.elapsed_seconds == record["total_elapsed_seconds"] == 28
    assert record["elapsed_seconds"] == 20
    assert record["quality"] == quality


def test_cli_uses_automatic_paths_for_repeated_runs(setup, capsys):
    ref, _, _, _ = setup
    results = []
    for _ in range(2):
        assert cli.main(["generate", "--image", str(ref), "--prompt", "Scene", "--upscale", "--no-progress"]) == 0
        results.append(json.loads(capsys.readouterr().out))
    assert results[0]["video_path"] != results[1]["video_path"]
    assert all(Path(r["video_path"]).read_bytes() == b"restored" for r in results)


def test_explicit_duration_native_size_and_restoration_options_are_preserved(setup):
    ref, calls, _, _ = setup
    generate("Scene", reference_images=[ref], upscale=True, duration=15, resolution="576p",
             x2=False, upscale_model_dir="custom-vosr", upscale_timeout=99, timeout=88)
    assert calls[2][1].duration == 15 and calls[2][1].num_frames == 360
    assert (calls[2][1].width, calls[2][1].height) == (1024, 576)
    assert calls[2][2]["timeout"] == 88
    assert calls[3][2]["timeout"] == 99 and calls[3][2]["model_dir"] == "custom-vosr"


@pytest.mark.parametrize("options", [{"x2": True}, {"resolution": "544p"}, {"x2_model_dir": "x2"},
    {"timeout": 0}, {"upscale_timeout": -1}, {"diagnostics": "yes"}, {"allow_large_download": "yes"}])
def test_conflicts_and_bad_options_fail_before_work(setup, options):
    ref, calls, _, _ = setup
    with pytest.raises(ValueError):
        generate("Scene", reference_images=[ref], upscale=True, **options)
    assert not calls
    assert not Path("runs").exists()


@pytest.mark.parametrize("suffix", [".mp4", ".run.json", ".native.mp4", ".native.run.json"])
def test_existing_final_or_intermediate_is_never_overwritten(setup, suffix):
    ref, calls, _, _ = setup
    existing = ref.parent / f"keep{suffix}"
    existing.write_text("keep")
    with pytest.raises(FileExistsError):
        generate("Scene", reference_images=[ref], upscale=True, output=ref.parent / "keep.mp4")
    assert not calls and existing.read_text() == "keep"


def test_memory_guard_precedes_models_and_generation(setup, monkeypatch):
    ref, calls, _, _ = setup
    from h3_apple import host
    up = importlib.import_module("h3_apple.upscale")
    monkeypatch.setattr(workflow, "check_environment", up.check_environment)
    monkeypatch.setattr(host, "snapshot", lambda: {"memory_bytes": 96 * 1024**3})
    monkeypatch.setattr(host, "check_machine", lambda _: None)
    with pytest.raises(RuntimeError, match="128 GiB"):
        generate("Scene", reference_images=[ref], upscale=True)
    assert not calls and not Path("runs").exists()


@pytest.mark.parametrize("quality", [None, "high"])
def test_download_consent_covers_both_stages_before_any_download(setup, quality):
    ref, calls, base, sr = setup
    base["download_bytes"] = 15_000_000_000
    sr["download_bytes"] = 6_970_000_000
    with pytest.raises(DownloadApprovalRequired) as error:
        generate("Scene", reference_images=[ref], upscale=True, quality=quality)
    assert error.value.download_bytes == 21_970_000_000
    assert calls == ["preflight"] and not Path("runs").exists()
    result = generate("Scene", reference_images=[ref], upscale=True, quality=quality, allow_large_download=True)
    assert result.video_path.is_file()
    assert calls[3][2]["allow_large_download"] is True


def test_bad_restoration_models_fail_before_generation(setup, monkeypatch):
    ref, calls, _, _ = setup
    def fail(*a, **kw):
        raise ValueError("VOSR model checksum mismatch")
    monkeypatch.setattr(workflow.assets, "prepare", fail)
    with pytest.raises(ValueError, match="checksum"):
        generate("Scene", reference_images=[ref], upscale=True)
    assert calls == ["preflight"] and not Path("runs").exists()


@pytest.mark.parametrize("failure", [RuntimeError("worker failed"), KeyboardInterrupt()])
@pytest.mark.parametrize("quality", [None, "high"])
def test_restoration_failure_keeps_native_and_explains_retry(setup, monkeypatch, failure, quality):
    ref, calls, _, _ = setup
    def fail(*a, **kw):
        raise failure
    monkeypatch.setattr(workflow, "upscale", fail)
    with pytest.raises(type(failure), match="h3 upscale --input"):
        generate("Scene", reference_images=[ref], upscale=True, quality=quality)
    native = calls[2][2]["output"]
    assert native.read_bytes() == b"native" and native.with_suffix(".run.json").is_file()
    assert not native.with_name("output.mp4").exists()


def test_generation_failure_never_starts_restoration(setup, monkeypatch):
    ref, calls, _, _ = setup
    def fail(*a, **kw):
        raise RuntimeError("generation failed")
    monkeypatch.setattr(workflow, "run_generation", fail)
    with pytest.raises(RuntimeError, match="generation failed"):
        generate("Scene", reference_images=[ref], upscale=True)
    assert calls == ["preflight", "models"]


def test_terminal_results_are_readable_and_json_remains_available(monkeypatch):
    result = GenerationResult(Path("/final.mp4"), Path("/final.run.json"), 1, 42, Path("/native.mp4"))
    monkeypatch.setattr(cli, "generate", lambda **kw: result)
    class Terminal(io.StringIO):
        def isatty(self):
            return True
    for flag in ([], ["--json"]):
        output = Terminal()
        monkeypatch.setattr(cli.sys, "stdout", output)
        assert cli.main(["generate", "--image", "ref.png", "--prompt", "Scene", "--no-progress", *flag]) == 0
        if flag:
            assert json.loads(output.getvalue())["video_path"] == "/final.mp4"
        else:
            assert output.getvalue() == "Saved video: /final.mp4\nNative video: /native.mp4\n"
