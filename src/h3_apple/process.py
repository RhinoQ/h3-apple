"""Own output reservations and the complete lifetime of an isolated worker."""

from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import queue
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid

from .api import GenerationResult
from .assets import load_assets
from .io import digest, write_json


def _stop(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=10)


def run_generation(request, *, output=None, model_dir=None, on_progress=None,
                   diagnostics=False, timeout=7200):
    if isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a positive finite number of seconds.")
    if type(diagnostics) is not bool:
        raise ValueError("diagnostics must be a boolean.")
    assets = load_assets(model_dir)
    if assets.get("task", "t2va") != request.task:
        raise ValueError(f"This request needs a {request.task.upper()} model bundle; select the matching --model-dir.")
    if request.task in ("ref2va", "fl2va"):
        from importlib.util import find_spec
        if find_spec("torch") is None or find_spec("torchvision") is None:
            raise RuntimeError("Reference-image generation needs the ref2va extra. Run ./install.sh --ref2va.")
    if output is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        directory = Path.cwd() / "runs" / f"{stamp}-{uuid.uuid4().hex[:8]}"
        directory.mkdir(parents=True, exist_ok=False)
        video = directory / "output.mp4"
        metadata = directory / "run.json"
    else:
        video = Path(output).expanduser().absolute()
        if video.suffix.lower() != ".mp4":
            raise ValueError("output must be an .mp4 path.")
        video.parent.mkdir(parents=True, exist_ok=True)
        metadata = video.with_suffix(".run.json")
    if os.path.lexists(video):
        raise FileExistsError(f"Output already exists: {video}")
    started = time.monotonic()
    run = dict(status="starting", request=request.to_dict(), seed=request.seed,
               started_utc=datetime.now(timezone.utc).isoformat(),
               model_identity=assets["identity"], video_path=str(video),
               diagnostics_enabled=diagnostics)
    with metadata.open("x") as stream:
        json.dump(run, stream, ensure_ascii=False)
        stream.write("\n")
    workspace = Path(tempfile.mkdtemp(prefix=".h3-", dir=video.parent))
    run["workspace"] = str(workspace)
    process = None
    worker_result = None
    try:
        environment = dict(os.environ, MLX_ENABLE_TF32="0", FASTVIDEO_MLX_DQ_GEMM="1",
                           MLX_METAL_GPU_ARCH="",
                           HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                           TOKENIZERS_PARALLELISM="false")
        environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment.get("PATH", "")
        with (workspace / "worker.log").open("w") as log:
            process = subprocess.Popen([sys.executable, "-m", "h3_apple.worker"],
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=log, text=True, env=environment,
                                       start_new_session=True)
            spec = dict(request=request.to_dict(), assets=assets, workspace=str(workspace),
                        diagnostics=diagnostics)
            if request.task == "fl2va":
                paths, anchors = [], []
                for anchor, source in (("first", request.first_frame), ("last", request.last_frame)):
                    if source is None:
                        continue
                    target = workspace / f"keyframe-{anchor}{Path(source).suffix}"
                    shutil.copyfile(source, target)
                    paths.append(str(target)); anchors.append(anchor)
                    run.setdefault("reference_inputs", []).append(dict(kind="keyframe", anchor=anchor,
                        source=source, sha256=digest(target), size=target.stat().st_size))
                spec["ref2va"] = dict(task="fl2va", native_root=assets["fl2va_native"],
                    image_paths=paths, anchors=anchors, attention="vsa")
            if request.reference_images:
                # Snapshot the small user inputs so one run has immutable references.
                references = []
                run["reference_inputs"] = []
                for index, source in enumerate(request.reference_images):
                    target = workspace / f"reference-{index + 1}{Path(source).suffix}"
                    shutil.copyfile(source, target)
                    references.append(str(target))
                    run["reference_inputs"].append(dict(index=index + 1, source=source,
                                                        sha256=digest(target), size=target.stat().st_size))
                spec["ref2va"] = dict(native_root=assets["ref2va_native"], image_paths=references,
                                      pixel_budget=672 * 384, attention="vsa")
            if request.reference_videos or request.reference_audio:
                options = spec.setdefault("ref2va", dict(native_root=assets["ref2va_native"],
                    image_paths=[], pixel_budget=672 * 384, attention="vsa"))
                for kind, paths in (("video", request.reference_videos), ("audio", request.reference_audio)):
                    options[f"{kind}_paths"] = []
                    for index, source in enumerate(paths):
                        target = workspace / f"reference-{kind}-{index + 1}{Path(source).suffix}"
                        shutil.copyfile(source, target)
                        options[f"{kind}_paths"].append(str(target))
                        run.setdefault("reference_inputs", []).append(dict(kind=kind, index=index + 1,
                            source=source, sha256=digest(target), size=target.stat().st_size))
            process.stdin.write(json.dumps(spec) + "\n")
            process.stdin.close()
            run.update(status="running", worker_pid=process.pid)
            write_json(metadata, run)
            events = queue.Queue()

            def read_stdout():
                for line in process.stdout:
                    events.put(line)
                events.put(None)

            reader = threading.Thread(target=read_stdout, daemon=True)
            reader.start()
            while True:
                if time.monotonic() - started > timeout:
                    raise TimeoutError(f"Generation exceeded {timeout} seconds.")
                try:
                    line = events.get(timeout=0.2)
                except queue.Empty:
                    continue
                if line is None:
                    break
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    log.write(line)
                    log.flush()
                    continue
                if isinstance(event, dict) and event.get("kind") == "result":
                    worker_result = event["result"]
                elif isinstance(event, dict) and event.get("kind") == "error":
                    run["worker_error"] = event["error"]
                elif isinstance(event, dict) and on_progress is not None:
                    on_progress(event)
            process.wait(timeout=max(0.1, timeout - (time.monotonic() - started)))
            reader.join(timeout=1)
        if process.returncode != 0 or worker_result is None:
            reason = run.get("worker_error", f"worker exited {process.returncode}")
            raise RuntimeError(f"{reason}. Log: {workspace / 'worker.log'}")
        # Atomic, no-clobber publication of this worker's validated output.
        os.link(workspace / "output.mp4", video)
        elapsed = time.monotonic() - started
        run.update(worker_result, status="complete", elapsed_seconds=elapsed)
        if diagnostics:
            run["diagnostics_path"] = str(workspace / "diagnostics")
        else:
            run.pop("workspace", None)
        write_json(metadata, run)
        if not diagnostics:
            shutil.rmtree(workspace)
        return GenerationResult(video.resolve(), metadata.resolve(), elapsed, request.seed)
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
            if process.stdout is not None:
                process.stdout.close()
