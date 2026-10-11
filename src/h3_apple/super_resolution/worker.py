"""Isolated VOSR worker: ordered frame restoration, resource limits and audio copy."""

from contextlib import redirect_stdout
import ctypes
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time

from ..host import device_lock, snapshot
from ..io import digest, write_json
from ..media import probe, tool


def footprint():
    # Darwin rusage_info_v4; include GPU allocations charged to this process.
    class Usage(ctypes.Structure):
        _fields_ = [('uuid', ctypes.c_uint8 * 16), ('values', ctypes.c_uint64 * 35)]
    library = ctypes.CDLL('/usr/lib/libproc.dylib', use_errno=True)
    library.proc_pid_rusage.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(Usage)]
    library.proc_pid_rusage.restype = ctypes.c_int
    value = Usage()
    if library.proc_pid_rusage(os.getpid(), 4, ctypes.byref(value)):
        raise OSError('Cannot read VOSR process memory.')
    return int(value.values[7])


def main():
    output = sys.stdout

    def emit(value):
        print(json.dumps(value, allow_nan=False), file=output, flush=True)

    done = threading.Event()
    errors = []
    resources = dict(peak_physical_bytes=0, max_added_swap_bytes=0, thermal_states=[])
    try:
        spec = json.loads(sys.stdin.readline())
        workspace = Path(spec['workspace'])
        request = spec['request']
        with device_lock(), redirect_stdout(sys.stderr):
            initial = snapshot()

            def stop(signum, frame):
                raise RuntimeError(errors[-1] if errors else 'VOSR resource limit exceeded.')

            def watch():
                while not done.wait(2):
                    try:
                        current = snapshot()
                        physical = footprint()
                        resources['peak_physical_bytes'] = max(resources['peak_physical_bytes'], physical)
                        resources['max_added_swap_bytes'] = max(resources['max_added_swap_bytes'], current['swap_bytes'] - initial['swap_bytes'])
                        if current['thermal']['state'] not in resources['thermal_states']:
                            resources['thermal_states'].append(current['thermal']['state'])
                        if physical > 96 * 1024**3:
                            raise RuntimeError('VOSR process memory exceeded 96 GiB.')
                        if current['swap_bytes'] - initial['swap_bytes'] > 2 * 1024**3:
                            raise RuntimeError('Swap usage grew by more than 2 GiB.')
                        if current['thermal']['state'] in ('serious', 'critical'):
                            raise RuntimeError('macOS reports serious or critical thermal pressure.')
                        if shutil.disk_usage(workspace).free < 20 * 1024**3:
                            raise RuntimeError('Free disk fell below 20 GiB.')
                    except BaseException as error:
                        errors.append(str(error))
                        os.kill(os.getpid(), signal.SIGUSR1)
                        return

            signal.signal(signal.SIGUSR1, stop)
            threading.Thread(target=watch, daemon=True).start()
            import cv2
            from PIL import Image
            from .engine import Upscaler
            cv2.setNumThreads(4)
            emit(dict(phase='loading', message='Loading VOSR2'))
            model = Upscaler(spec['models']['directory'], request['width'], request['height'])
            frames = workspace / 'frames'
            frames.mkdir()
            capture = cv2.VideoCapture(request['input'])
            rows = []
            try:
                for index in range(request['num_frames']):
                    started = time.monotonic()
                    ok, bgr = capture.read()
                    if not ok:
                        raise RuntimeError(f'Cannot decode frame {index}.')
                    image = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
                    result = model.restore(image)
                    path = frames / f'frame-{index:03}.png'
                    result.save(path)
                    rows.append(dict(frame=index, seconds=time.monotonic() - started, sha256=digest(path)))
                    write_json(workspace / 'frames.json', rows)
                    emit(dict(phase='upscale', message=f"Restored {index + 1}/{request['num_frames']} frames"))
                if request['num_frames'] == request['source_frames'] and capture.read()[0]:
                    raise RuntimeError('Input contains more frames than declared.')
            finally:
                capture.release()
            emit(dict(phase='mux', message='Writing the upscaled video'))
            destination = workspace / 'output.mp4'
            command = [tool('ffmpeg'), '-v', 'error', '-nostdin', '-n', '-framerate', '24',
                '-i', str(frames / 'frame-%03d.png'), '-i', request['input'], '-map', '0:v:0',
                '-map', '1:a:0?', '-t', str(request['duration']),
                '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,setsar=1',
                '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-threads', '4',
                '-color_range', 'tv', '-colorspace', 'bt709', '-color_primaries', 'bt709',
                '-color_trc', 'bt709', '-c:a', 'copy', '-movflags', '+faststart', str(destination)]
            subprocess.run(command, check=True, timeout=300)
            data = probe(destination)
            video = next(s for s in data['streams'] if s['codec_type'] == 'video')
            if ((video['width'], video['height']) != (request['width'] * 2, request['height'] * 2)
                    or int(video['nb_frames']) != request['num_frames']
                    or video['avg_frame_rate'] != '24/1'
                    or abs(float(video['duration']) - request['duration']) > .001):
                raise RuntimeError('Output format differs from the requested delivery.')
            audio_hash = None
            if request['audio']:
                def pcm(path):
                    return subprocess.check_output([tool('ffmpeg'), '-v', 'error', '-i', str(path),
                        '-map', '0:a:0', '-t', str(request['duration']), '-f', 's16le',
                        '-acodec', 'pcm_s16le', 'pipe:1'], timeout=120)
                original, restored = pcm(request['input']), pcm(destination)
                if not original or original != restored:
                    raise RuntimeError('Source audio was not preserved.')
                import hashlib
                audio_hash = hashlib.sha256(restored).hexdigest()
            emit(dict(kind='result', result=dict(frames=rows, video_sha256=digest(destination),
                media=data, audio_pcm_sha256=audio_hash, export_command=command,
                resources=resources, final_host=snapshot())))
        return 0
    except Exception as error:
        import traceback
        traceback.print_exc(file=sys.stderr)
        emit(dict(kind='error', error=str(error)))
        return 1
    finally:
        done.set()


if __name__ == '__main__':
    raise SystemExit(main())
