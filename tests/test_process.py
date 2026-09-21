import json
from pathlib import Path
import subprocess
import sys
import time

import pytest

from h3_apple import resolve as resolve_request
from PIL import Image


@pytest.fixture
def request_image(tmp_path):
    path = tmp_path / "reference.png"
    Image.new("RGB", (32, 32)).save(path)
    return path


def resolve(prompt, **kwargs):
    return resolve_request(prompt, **kwargs)
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


def test_no_clobber_before_worker_launch(tmp_path, monkeypatch, request_image):
    output = tmp_path / "keep.mp4"
    output.write_bytes(b"user content")
    monkeypatch.setattr(runner, "load_assets", lambda _: {"identity": "fixture"})
    with pytest.raises(FileExistsError):
        runner.run_generation(resolve("Text", reference_images=[request_image]), output=output)
    assert output.read_bytes() == b"user content"


def test_worker_failure_preserves_evidence(tmp_path, monkeypatch, request_image):
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
        runner.run_generation(resolve("Text", reference_images=[request_image]), output=output)
    record = json.loads(output.with_suffix(".run.json").read_text())
    assert record["status"] == "failed"
    assert Path(record["workspace"], "worker.log").is_file()
    assert not output.exists()


def test_timeout_reaps_the_worker(tmp_path, monkeypatch, request_image):
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
        runner.run_generation(resolve("Text", reference_images=[request_image]), output=output, timeout=0.5)
    assert len(children) == 1 and children[0].poll() is not None
    assert json.loads(output.with_suffix(".run.json").read_text())["status"] == "failed"


def test_reference_inputs_are_snapshotted_in_order(tmp_path, monkeypatch):
    import importlib.util
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
    assert spec["ref2va"]["pixel_budget"] == 1024 * 576
    for index, (source, snapshot) in enumerate(zip(paths, spec["ref2va"]["image_paths"])):
        assert Path(snapshot).parent == Path(record["workspace"])
        assert Path(snapshot).read_bytes() == source.read_bytes()
        assert record["reference_inputs"][index]["sha256"] == digest(source)


@pytest.mark.parametrize("mode", ["timeout","callback"])
def test_cancellation_reaps_native_descendant(tmp_path,monkeypatch,mode,request_image):
    # A real two-process worker tree exercises the same group used by vpipe.
    worker=tmp_path/"worker.py"
    worker.write_text("import subprocess,sys,json,pathlib,time\n"
        "s=json.loads(sys.stdin.readline())\n"
        "p=subprocess.Popen([sys.executable,'-c',\"import time,signal;signal.signal(signal.SIGTERM,signal.SIG_IGN);print('ready',flush=True);time.sleep(60)\"],stdout=subprocess.PIPE)\n"
        "p.stdout.readline()\n"
        "pathlib.Path(s['workspace'],'native.pid').write_text(str(p.pid))\n"
        "print(json.dumps({'phase':'native_generation'}),flush=True)\ntime.sleep(60)\n")
    real_popen=subprocess.Popen
    monkeypatch.setattr(runner,"load_assets",lambda _:dict(identity="fixture",tasks=["t2va"]))
    monkeypatch.setattr(runner.subprocess,"Popen",lambda args,**kw:real_popen([sys.executable,str(worker)],**kw))
    def cancel(_event):raise KeyboardInterrupt()
    output=tmp_path/"out.mp4"
    with pytest.raises(TimeoutError if mode=="timeout" else KeyboardInterrupt):
        runner.run_generation(resolve("Text",reference_images=[request_image]),output=output,timeout=0.5,
            on_progress=cancel if mode=="callback" else None)
    record=json.loads(output.with_suffix(".run.json").read_text())
    assert record["status"]==("failed" if mode=="timeout" else "cancelled")
    assert not output.exists()
    pid=int(Path(record["workspace"],"native.pid").read_text())
    for _ in range(20):
        status=subprocess.run(["ps","-o","stat=","-p",str(pid)],capture_output=True,text=True).stdout.strip()
        if not status or status.startswith("Z"):break
        time.sleep(.05)
    assert not status or status.startswith("Z")
