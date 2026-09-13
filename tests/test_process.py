import json
from pathlib import Path
import subprocess
import sys

import pytest

from h3_apple import resolve
from h3_apple.host import device_lock
from h3_apple import process as runner


def test_device_lock_is_shared_across_processes(tmp_path):
    path = tmp_path / "device.lock"
    script = "from h3_apple.host import device_lock; import sys\nwith device_lock(sys.argv[1]): pass\n"
    with device_lock(path):
        result = subprocess.run([sys.executable, "-c", script, str(path)], capture_output=True, text=True)
        assert result.returncode != 0
        assert "device lock" in result.stderr
    subprocess.run([sys.executable, "-c", script, str(path)], check=True)


def test_no_clobber_before_worker_launch(tmp_path, monkeypatch):
    output = tmp_path / "keep.mp4"
    output.write_bytes(b"user content")
    monkeypatch.setattr(runner, "load_assets", lambda _: {"identity": "fixture"})
    with pytest.raises(FileExistsError):
        runner.run_generation(resolve("Text"), output=output)
    assert output.read_bytes() == b"user content"


def test_worker_failure_preserves_evidence(tmp_path, monkeypatch):
    worker = tmp_path / "worker.py"
    worker.write_text("import json,sys\nspec=json.loads(sys.stdin.readline())\n"
                      "print(json.dumps({'kind':'error','error':'intentional test failure'}),flush=True)\n"
                      "sys.exit(7)\n")
    real_popen = subprocess.Popen
    monkeypatch.setattr(runner, "load_assets", lambda _: {"identity": "fixture"})
    monkeypatch.setattr(runner.subprocess, "Popen", lambda args, **kwargs:
                        real_popen([sys.executable, str(worker)], **kwargs))
    output = tmp_path / "failed.mp4"
    with pytest.raises(RuntimeError, match="intentional test failure"):
        runner.run_generation(resolve("Text"), output=output)
    record = json.loads(output.with_suffix(".run.json").read_text())
    assert record["status"] == "failed"
    assert Path(record["workspace"], "worker.log").is_file()
    assert not output.exists()


def test_timeout_reaps_the_worker(tmp_path, monkeypatch):
    worker = tmp_path / "worker.py"
    worker.write_text("import sys,time\nsys.stdin.readline()\ntime.sleep(60)\n")
    real_popen, children = subprocess.Popen, []
    def launch(args, **kwargs):
        child = real_popen([sys.executable, str(worker)], **kwargs)
        children.append(child)
        return child
    monkeypatch.setattr(runner, "load_assets", lambda _: {"identity": "fixture"})
    monkeypatch.setattr(runner.subprocess, "Popen", launch)
    output = tmp_path / "timeout.mp4"
    with pytest.raises(TimeoutError):
        runner.run_generation(resolve("Text"), output=output, timeout=0.5)
    assert len(children) == 1 and children[0].poll() is not None
    assert json.loads(output.with_suffix(".run.json").read_text())["status"] == "failed"


def test_model_task_mismatch_is_rejected_before_launch(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "load_assets", lambda _: {"identity": "fixture", "task": "ref2va"})
    with pytest.raises(ValueError, match="T2VA model bundle"):
        runner.run_generation(resolve("Text"), output=tmp_path / "output.mp4")
    assert not list(tmp_path.iterdir())


def test_reference_inputs_are_snapshotted_in_order(tmp_path, monkeypatch):
    from PIL import Image
    from h3_apple.io import digest
    paths = [tmp_path / "second.png", tmp_path / "first.png"]
    for path, color in zip(paths, ["red", "blue"]):
        Image.new("RGB", (32, 32), color).save(path)
    request = resolve("Picture 1 then picture 2", reference_images=paths)
    worker = tmp_path / "worker.py"
    worker.write_text("import json,sys,pathlib\nspec=json.loads(sys.stdin.readline())\n"
                      "pathlib.Path(spec['workspace'],'received.json').write_text(json.dumps(spec))\n"
                      "print(json.dumps({'kind':'error','error':'captured specification'}),flush=True)\n"
                      "sys.exit(7)\n")
    real_popen = subprocess.Popen
    monkeypatch.setattr(runner, "load_assets", lambda _: dict(identity="fixture", task="ref2va", ref2va_native="native"))
    monkeypatch.setattr(runner.subprocess, "Popen", lambda args, **kwargs:
                        real_popen([sys.executable, str(worker)], **kwargs))
    output = tmp_path / "output.mp4"
    with pytest.raises(RuntimeError, match="captured specification"):
        runner.run_generation(request, output=output)
    record = json.loads(output.with_suffix(".run.json").read_text())
    spec = json.loads(Path(record["workspace"], "received.json").read_text())
    assert spec["ref2va"]["pixel_budget"] == 672 * 384
    assert spec["ref2va"]["attention"] == "vsa"
    assert spec["ref2va"]["native_root"] == "native"
    for index, (source, snapshot) in enumerate(zip(paths, spec["ref2va"]["image_paths"])):
        assert Path(snapshot).parent == Path(record["workspace"])
        assert Path(snapshot).read_bytes() == source.read_bytes()
        assert record["reference_inputs"][index]["sha256"] == digest(source)
