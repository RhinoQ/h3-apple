import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from h3_apple.media import tool, validate

spec = importlib.util.spec_from_file_location("compare", Path(__file__).parents[1] / "benchmarks/compare.py")
compare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compare)


def test_receipt_identity_and_asset_mutation(tmp_path):
    asset = tmp_path / "weights"
    asset.write_bytes(b"test")
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps({"files": [{"path": "weights", "size": 4,
        "mtime_ns": asset.stat().st_mtime_ns, "sha256": hashlib.sha256(b"test").hexdigest()}]}))
    method = {"asset_receipts": [{"path": str(receipt), "sha256": compare.digest(receipt)}]}
    assert compare.verify_assets(method)[0]["files"] == 1
    asset.write_bytes(b"changed")
    with pytest.raises(ValueError, match="size changed"):
        compare.verify_assets(method)


def test_vpipe_preserves_official_recipe(tmp_path):
    template = {"stages": [{"id": name, "type": name, "config": values} for name, values in {
        "text-prompt": {"text": "old"}, "generate-video": {"width": 960, "height": 544,
            "frames": 124, "seed": 6, "steps": 6, "i8_gemm": True},
        "save-video": {"output_url": "old.mp4", "enable_audio": True},
        "minimax-h3-model-config": {"video_shift": 12, "linear_branch": "official"}}.items()]}
    file = tmp_path / "official.json"
    file.write_text(json.dumps(template))
    request = dict(prompt='Full {prompt} "with" $() text', seed=2026,
                   model_width=1376, model_height=768, model_num_frames=362)
    target = tmp_path / "input.vpipeline"
    changes = compare.vpipe_input(dict(pipeline_template=str(file), pipeline_template_sha256=compare.digest(file)),
                                  request, tmp_path / "native.mp4", target)
    actual = json.loads(target.read_text())
    before = copy.deepcopy(template)
    for stage in before["stages"]:
        stage["config"].update(changes.get(stage["id"], {}))
    assert actual == before
    assert actual["stages"][1]["config"]["steps"] == 6
    assert actual["stages"][3] == template["stages"][3]
    assert json.loads(file.read_text()) == template


def test_public_prompt_hash_is_checked(tmp_path):
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("Text with trailing newline.\n")
    suite = tmp_path / "suite.json"
    suite.write_text(json.dumps(dict(resolution="768p", duration=15, cases=[dict(
        id="case", prompt_file="prompt.txt", prompt_sha256=compare.digest(prompt), seed=2026)])))
    _, cases = compare.load_cases(suite)
    assert cases[0]["request"]["prompt"].endswith("\n")
    prompt.write_text("shortened")
    with pytest.raises(ValueError, match="Public prompt changed"):
        compare.load_cases(suite)


def test_command_substitution_is_not_a_shell(tmp_path):
    prompt = tmp_path / "prompt.txt"
    prompt.write_text('Unchanged {braces} and $(touch danger) "quotes"\n')
    directory = tmp_path / "job"
    directory.mkdir()
    request = dict(prompt=prompt.read_text(), seed=123, model_width=1376, model_height=768, model_num_frames=362)
    command, _, _ = compare.expand_command(dict(id="ours", command=[sys.executable, "{prompt}", "{output}"]),
                                           dict(request=request, prompt_file=str(prompt)), directory)
    assert command[1] == prompt.read_text()
    assert not (tmp_path / "danger").exists()
    assert (directory / "prompt.txt").read_bytes() == prompt.read_bytes()
    assert not list((directory / "empty-prompt-cache").iterdir())


def test_native_crop_and_trim_keeps_delivery_specification(tmp_path):
    native, output = tmp_path / "native.mp4", tmp_path / "output.mp4"
    subprocess.run([tool("ffmpeg"), "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=96x64:r=10:d=2",
                    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=32000:duration=2", "-ac", "2",
                    "-c:v", "libx264", "-c:a", "aac", str(native)], check=True)
    request = dict(width=64, height=64, num_frames=10, fps=10, audio_sample_rate=32000,
                   audio_channels=2, duration=1.0, model_width=96, model_height=64, model_num_frames=20)
    compare.finish_native(native, output, request)
    assert validate(output, request)["streams"][0]["nb_read_frames"] == "10"
    assert native.exists()


def test_real_timeout_and_failure_evidence(tmp_path, monkeypatch):
    first = dict(system="Darwin", power="AC Power", thermal=dict(state="nominal", low_power_mode=False), swap_bytes=0)
    monkeypatch.setattr(compare, "preflight", lambda method: {})
    monkeypatch.setattr(compare, "snapshot", lambda: first)
    monkeypatch.setattr(compare, "wait_ready", lambda timeout: (first, 0))
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("test")
    case = dict(id="case", prompt_file=str(prompt), prompt_sha256=compare.digest(prompt), request=dict(
        prompt="test", seed=1, model_width=1376, model_height=768, model_num_frames=362))
    method = dict(id="ours", label="test fixture", cwd=str(tmp_path), command=[sys.executable, "-c",
                  "import time; print('started', flush=True); time.sleep(60)"])
    row = compare.run_job(method, case, tmp_path / "job", timeout=0.15, cooldown_timeout=1)
    assert row["status"] == "failed"
    assert "exceeded" in row["error"]
    assert row["elapsed_seconds"] is None
    assert row["attempt_seconds"] < 4
    assert (tmp_path / "job/command.log").exists()
    assert json.loads((tmp_path / "job/run.json").read_text())["status"] == "failed"


def test_report_does_not_rank_failed_time(tmp_path):
    row = dict(case="test", method="ours", label="Ours", status="failed", elapsed_seconds=None,
               attempt_seconds=1, quality_review="pending", error="example")
    compare.summarize(tmp_path, dict(runs=[row]))
    assert "| test | Ours | failed | — |" in (tmp_path / "README.md").read_text()
    assert json.loads((tmp_path / "results.json").read_text())["runs"][0] == row
