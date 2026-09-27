"""A separate, lazy public operation for enhancing an existing H3 video."""

from dataclasses import dataclass
from datetime import datetime, timezone
import importlib.util
import json
import math
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid

from ..io import digest, write_json


@dataclass(frozen=True)
class EnhancementResult:
    video_path: Path
    metadata_path: Path
    elapsed_seconds: float
    enhanced_frames: int
    face_passes: int


def enhance_faces(video, *, output=None, model_dir=None, on_progress=None,
                  diagnostics=False, timeout=7200):
    """Enhance eligible 32–160 pixel face tracks in an existing 24 fps H3 MP4.

    Requires the optional ``faces`` dependencies and ``h3 prepare-faces`` assets.
    Uses a separate process and the generator's device lock. Does not overwrite
    inputs, redownload models, change the generator or regenerate entire shots.
    Fine facial detail is generatively restored, not recovered with a fidelity guarantee.
    """
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a positive finite number of seconds.")
    if type(diagnostics) is not bool:
        raise ValueError("diagnostics must be a boolean.")
    source = Path(video).expanduser().resolve()
    if not source.is_file() or source.suffix.lower() != ".mp4":
        raise ValueError("video must be an existing .mp4 file.")
    if output is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        target = Path.cwd() / "runs" / f"{stamp}-{uuid.uuid4().hex[:8]}" / "enhanced.mp4"
    else:
        target = Path(output).expanduser().absolute()
    if target.suffix.lower() != ".mp4":
        raise ValueError("output must be an .mp4 path.")
    metadata = target.with_suffix(".faces.json")
    for path in (target, metadata):
        if os.path.lexists(path):
            raise FileExistsError(f"Output already exists: {path}")
    for name in ("torch", "torchvision", "cv2", "numpy", "diffusers", "transformers", "timm", "facexlib", "einops", "safetensors"):
        if importlib.util.find_spec(name) is None:
            raise RuntimeError("Face enhancement needs optional dependencies. Install this release with the [faces] extra; see docs/face-enhancement.md.")
    from .assets import directory
    from ..media import check_runtime
    from ..process import _stop
    check_runtime()
    target.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    run = dict(status="starting", operation="enhance_faces", recipe="local-vosr-v1",
               source=str(source), video_path=str(target), started_utc=datetime.now(timezone.utc).isoformat())
    with metadata.open("x") as stream:
        json.dump(run, stream)
    workspace = Path(tempfile.mkdtemp(prefix=".h3-faces-", dir=target.parent))
    run["workspace"] = str(workspace)
    process = None
    try:
        # Snapshot the user input; every pass and copied audio uses the same bytes.
        shutil.copyfile(source, workspace / "source.mp4")
        run["source_sha256"] = digest(workspace / "source.mp4")
        spec = dict(workspace=str(workspace), model_dir=str(directory(model_dir)), diagnostics=diagnostics)
        env = dict(os.environ, TORCH_COMPILE_DISABLE="1", TORCHDYNAMO_DISABLE="1",
                   HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", XFORMERS_DISABLED="1")
        env.pop("PYTORCH_ENABLE_MPS_FALLBACK", None)
        with (workspace / "worker.log").open("w") as log:
            process = subprocess.Popen([sys.executable, "-m", "h3_apple.faces.worker"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True, env=env, start_new_session=True)
            process.stdin.write(json.dumps(spec) + "\n")
            process.stdin.close()
            run.update(status="running", worker_pid=process.pid)
            write_json(metadata, run)
            events = queue.Queue()
            def read():
                for line in process.stdout:
                    events.put(line)
                events.put(None)
            reader = threading.Thread(target=read, daemon=True)
            reader.start()
            result = None
            while True:
                if time.monotonic() - started > timeout:
                    raise TimeoutError(f"Face enhancement exceeded {timeout} seconds.")
                try:
                    line = events.get(timeout=.2)
                except queue.Empty:
                    continue
                if line is None:
                    break
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    log.write(line)
                    continue
                if isinstance(event, dict) and event.get("kind") == "result":
                    result = event["result"]
                elif isinstance(event, dict) and event.get("kind") == "error":
                    run["worker_error"] = event["error"]
                elif isinstance(event, dict) and on_progress:
                    on_progress(event)
            process.wait(timeout=max(.1, timeout - (time.monotonic() - started)))
            reader.join(timeout=1)
        if process.returncode or result is None:
            raise RuntimeError(f"{run.get('worker_error', 'Face enhancement worker failed')}. Log: {workspace / 'worker.log'}")
        os.link(workspace / "output.mp4", target)
        elapsed = time.monotonic() - started
        run.update(result, status="complete", elapsed_seconds=elapsed)
        if not diagnostics:
            run.pop("workspace", None)
        write_json(metadata, run)
        if not diagnostics:
            shutil.rmtree(workspace)
        return EnhancementResult(target.resolve(), metadata.resolve(), elapsed, result["enhanced_frames"], result["face_passes"])
    except BaseException as error:
        if process is not None:
            _stop(process)
        run.update(status="cancelled" if isinstance(error, KeyboardInterrupt) else "failed",
                   error=str(error) or type(error).__name__, elapsed_seconds=time.monotonic() - started)
        write_json(metadata, run)
        raise
    finally:
        if process is not None:
            _stop(process)
            process.stdout.close()
