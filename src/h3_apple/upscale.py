"""Public video super-resolution API; heavy inference runs in a child process."""

from dataclasses import dataclass
from fractions import Fraction
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

from .io import digest, source_identity, write_json
from .media import probe, check_runtime


@dataclass(frozen=True)
class UpscaleResult:
    video_path: Path
    metadata_path: Path
    elapsed_seconds: float


def resolve_video(path, duration=None):
    source = Path(path).expanduser().resolve(strict=True)
    if not source.is_file():
        raise ValueError('Input must be a video file.')
    data = probe(source)
    videos = [s for s in data['streams'] if s['codec_type'] == 'video']
    audio = [s for s in data['streams'] if s['codec_type'] == 'audio']
    if len(videos) != 1 or len(audio) > 1:
        raise ValueError('VOSR needs one video stream and at most one audio stream.')
    video = videos[0]
    width, height = video['width'], video['height']
    if (width, height) not in ((1366, 768), (768, 1366), (1024, 576), (576, 1024)):
        raise ValueError('VOSR accepts native 576p or 768p H3 video in either orientation. Generate with --no-x2.')
    if any(Fraction(video.get(key, '0')) != 24 for key in ('avg_frame_rate', 'r_frame_rate')):
        raise ValueError('VOSR requires a constant 24 fps input.')
    count = int(video.get('nb_frames', 0))
    if not 1 <= count <= 360 or abs(float(video.get('duration', 0)) - count / 24) > .001:
        raise ValueError('VOSR requires 1–360 ordered frames at 24 fps (up to 15 seconds).')
    if any(int(side.get('rotation', 0)) for side in video.get('side_data_list', [])):
        raise ValueError('Rotate the video pixels before upscaling; rotation metadata is unsupported.')
    if audio and audio[0]['codec_name'] != 'aac':
        raise ValueError('Use AAC audio, or a silent video, to preserve audio without re-encoding.')
    selected = count
    if duration is not None:
        if (isinstance(duration, bool) or not isinstance(duration, (int, float))
                or not math.isfinite(duration) or not 0 < duration <= count / 24):
            raise ValueError('duration must be positive and no longer than the input video.')
        selected = round(duration * 24)
        if selected < 1 or abs(duration * 24 - selected) > 1e-6:
            raise ValueError('duration must correspond to a whole frame at 24 fps.')
    return dict(input=str(source), width=width, height=height, fps=24, num_frames=selected,
                source_frames=count, duration=selected / 24, audio=bool(audio))


def upscale(input, *, output, duration=None, model_dir=None, on_progress=None, diagnostics=False, timeout=14400):
    """Double a native 576p/768p H3 video's dimensions with VOSR2; keep its audio."""
    if isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('timeout must be positive and finite.')
    if type(diagnostics) is not bool:
        raise ValueError('diagnostics must be a boolean.')
    request = resolve_video(input, duration)
    video = Path(output).expanduser().absolute()
    metadata = video.with_suffix('.run.json')
    if video.suffix.lower() != '.mp4':
        raise ValueError('output must be an .mp4 path.')
    for path in (video, metadata):
        if os.path.lexists(path):
            raise FileExistsError(f'Output already exists: {path}')
    from .host import snapshot, check_machine
    host = snapshot()
    check_machine(host)
    if host['memory_bytes'] < 128 * 1024**3:
        raise RuntimeError('VOSR upscaling requires 128 GiB unified memory.')
    check_runtime()
    from .super_resolution.assets import prepare
    assets = prepare(model_dir, on_progress=on_progress)
    video.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(video.parent).free < 20 * 1024**3:
        raise OSError('VOSR requires at least 20 GiB free disk space.')
    run = dict(status='starting', recipe=assets['recipe'], request=request, models=assets,
               input_sha256=digest(request['input']), package_source_sha256=source_identity())
    with metadata.open('x') as handle:
        json.dump(run, handle)
    workspace = Path(tempfile.mkdtemp(prefix='.h3-upscale-', dir=video.parent))
    run['workspace'] = str(workspace)
    process = None
    started = time.monotonic()
    result = None
    from .process import _stop
    try:
        # Bind the exact media being processed, even if the caller edits the input.
        snapshot_path = workspace / 'source.mp4'
        shutil.copyfile(request['input'], snapshot_path)
        if digest(snapshot_path) != run['input_sha256']:
            raise RuntimeError('Input changed while being snapshotted.')
        environment = dict(os.environ, HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                           XFORMERS_DISABLED='1', TORCH_COMPILE_DISABLE='1', TORCHDYNAMO_DISABLE='1')
        for name in ('PYTORCH_ENABLE_MPS_FALLBACK', 'PYTORCH_MPS_PREFER_METAL',
                     'PYTORCH_MPS_FAST_MATH', 'PYTORCH_MPS_DISABLE_PREFILL_ATTENTION', 'PYTORCH_MPS_LOG_PROFILE_INFO'):
            environment.pop(name, None)
        with (workspace / 'worker.log').open('w') as log:
            process = subprocess.Popen([sys.executable, '-m', 'h3_apple.super_resolution.worker'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True,
                env=environment, start_new_session=True)
            process.stdin.write(json.dumps(dict(request=dict(request, input=str(snapshot_path)),
                workspace=str(workspace), models=assets, diagnostics=diagnostics)) + '\n')
            process.stdin.close()
            events = queue.Queue()

            def read():
                for line in process.stdout:
                    events.put(line)
                events.put(None)

            reader = threading.Thread(target=read, daemon=True)
            reader.start()
            while True:
                if time.monotonic() - started > timeout:
                    raise TimeoutError(f'Upscaling exceeded {timeout} seconds.')
                try:
                    line = events.get(timeout=.2)
                except queue.Empty:
                    continue
                if line is None:
                    break
                event = json.loads(line)
                if event.get('kind') == 'result':
                    result = event['result']
                elif event.get('kind') == 'error':
                    run['worker_error'] = event['error']
                elif on_progress:
                    on_progress(event)
            process.wait(timeout=max(.1, timeout - (time.monotonic() - started)))
            reader.join(timeout=1)
        if process.returncode or result is None:
            raise RuntimeError(f"{run.get('worker_error', 'VOSR worker failed')}. Log: {workspace / 'worker.log'}")
        os.link(workspace / 'output.mp4', video)
        elapsed = time.monotonic() - started
        run.update(result, status='complete', elapsed_seconds=elapsed,
                   timing='Input snapshot, worker startup/imports, model load, all frames and export; initial model verification/preparation excluded.')
        if not diagnostics:
            run.pop('workspace')
        write_json(metadata, run)
        if not diagnostics:
            shutil.rmtree(workspace)
        return UpscaleResult(video.resolve(), metadata.resolve(), elapsed)
    except BaseException as error:
        run.update(status='cancelled' if isinstance(error, KeyboardInterrupt) else 'failed',
                   error=str(error) or type(error).__name__, elapsed_seconds=time.monotonic() - started)
        write_json(metadata, run)
        raise
    finally:
        if process is not None:
            _stop(process)
            process.stdout.close()
