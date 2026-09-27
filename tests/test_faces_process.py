"""Worker lifetime tests use tiny subprocesses, without loading restoration models."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from h3_apple.faces import api


@pytest.fixture
def setup(tmp_path, monkeypatch):
    from h3_apple import media
    monkeypatch.setattr(media, "check_runtime", lambda: {})
    monkeypatch.setattr(api.importlib.util, "find_spec", lambda _name: True)
    source = tmp_path / "source.mp4"
    source.write_bytes(b"unchanged input")
    popen = subprocess.Popen
    def worker(code):
        monkeypatch.setattr(api.subprocess, "Popen", lambda command, **kwargs: popen([sys.executable, "-c", code], **kwargs))
    return source, tmp_path / "output.mp4", worker


def test_worker_failure_preserves_input_and_diagnostics(setup):
    source, out, worker = setup
    worker('import json,sys; json.loads(sys.stdin.readline()); print(json.dumps({"kind":"error","error":"fixture failure"}),flush=True);sys.exit(1)')
    with pytest.raises(RuntimeError, match="fixture failure"):
        api.enhance_faces(source, output=out)
    record = json.loads(out.with_suffix('.faces.json').read_text())
    assert record['status'] == 'failed'
    assert Path(record['workspace']).is_dir()
    assert source.read_bytes() == b'unchanged input' and not out.exists()


def test_timeout_stops_worker_and_retains_record(setup):
    source, out, worker = setup
    worker('import sys,time;sys.stdin.readline();time.sleep(60)')
    with pytest.raises(TimeoutError):
        api.enhance_faces(source, output=out, timeout=.1)
    assert json.loads(out.with_suffix('.faces.json').read_text())['status'] == 'failed'
    assert not out.exists()


def test_callback_cancellation_stops_worker(setup):
    source, out, worker = setup
    worker('import sys,json,time;sys.stdin.readline();print(json.dumps({"phase":"loading"}),flush=True);time.sleep(60)')
    def cancel(_event):
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        api.enhance_faces(source, output=out, on_progress=cancel)
    assert json.loads(out.with_suffix('.faces.json').read_text())['status'] == 'cancelled'
    assert not out.exists()


def test_success_publishes_then_cleans_only_private_workspace(setup):
    source, out, worker = setup
    worker('import sys,json,pathlib; s=json.loads(sys.stdin.readline()); (pathlib.Path(s["workspace"])/"output.mp4").write_bytes(b"result");print(json.dumps({"kind":"result","result":{"enhanced_frames":4,"face_passes":5}}),flush=True)')
    result = api.enhance_faces(source, output=out)
    assert result.enhanced_frames == 4 and result.face_passes == 5
    assert out.read_bytes() == b'result' and source.read_bytes() == b'unchanged input'
    assert 'workspace' not in json.loads(result.metadata_path.read_text())
    with pytest.raises(FileExistsError):
        api.enhance_faces(source, output=out)
