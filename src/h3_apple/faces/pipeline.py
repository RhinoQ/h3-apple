"""Two sequential decoding passes keep full-film memory bounded to one image."""

from collections import defaultdict
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import time

from ..io import digest, write_json
from ..media import probe, tool


def inspect_input(source):
    media = probe(source)
    videos = [s for s in media["streams"] if s["codec_type"] == "video"]
    audios = [s for s in media["streams"] if s["codec_type"] == "audio"]
    if len(videos) != 1 or len(audios) > 1:
        raise ValueError("Face enhancement accepts one video stream and zero or one AAC audio stream.")
    v = videos[0]
    if (v["width"], v["height"]) not in ((1024, 576), (576, 1024), (1366, 768), (768, 1366)):
        raise ValueError("Face enhancement currently accepts H3 576p/768p landscape or portrait dimensions.")
    if Fraction(v["avg_frame_rate"]) != 24 or Fraction(v["r_frame_rate"]) != 24 or v.get("pix_fmt") != "yuv420p":
        raise ValueError("Face enhancement requires a 24 fps, 8-bit yuv420p H3 video.")
    count = int(v.get("nb_read_frames", 0))
    if not 1 <= count <= 14400 or abs(float(v.get("duration", 0)) - count / 24) > 1 / 24000:
        raise ValueError("Video must have a known duration of at most 10 minutes with complete frames.")
    if abs(float(v.get("start_time", 0))) > 1 / 24000 or any(s.get("rotation", 0) for s in v.get("side_data_list", [])):
        raise ValueError("Rotated or nonzero-start media must be normalized before enhancement.")
    if audios:
        a = audios[0]
        if (a["codec_name"] != "aac" or abs(float(a.get("start_time", 0))) > 1 / 32000
                or not math.isfinite(float(a.get("duration", 0))) or float(a.get("duration", 0)) <= 0):
            raise ValueError("Audio must be AAC with a known positive duration and start at zero.")
    timestamps = subprocess.check_output([tool("ffprobe"), "-v", "error", "-select_streams", "v:0",
        "-show_frames", "-show_entries", "frame=best_effort_timestamp_time", "-of", "json", str(source)], timeout=300)
    frames = json.loads(timestamps)["frames"]
    if len(frames) != count or any(abs(float(f["best_effort_timestamp_time"]) - i / 24) > .00001 for i, f in enumerate(frames)):
        raise ValueError("Variable frame timing is not supported; normalize to constant 24 fps first.")
    return media, v, audios


def _audio_hash(path):
    process = subprocess.Popen([tool("ffmpeg"), "-v", "error", "-xerror", "-i", str(path),
        "-map", "0:a:0", "-c:a", "pcm_f32le", "-f", "f32le", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = hashlib.sha256()
    try:
        for block in iter(lambda: process.stdout.read(1024 * 1024), b""):
            result.update(block)
        error = process.stderr.read()
        if process.wait(timeout=300):
            raise ValueError(f"Audio decode failed: {error[-1000:]!r}")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stdout.close()
        process.stderr.close()
    return result.hexdigest()


def run(workspace, root, emit, diagnostics=False):
    import cv2
    import numpy as np
    import torch
    from PIL import Image
    from facexlib.detection import init_detection_model
    from .geometry import fill_single_gaps, association, alpha_mask, composite

    source = workspace / "source.mp4"
    start = time.monotonic()
    media, video, audios = inspect_input(source)
    count = int(video["nb_read_frames"])
    width, height = video["width"], video["height"]
    torch.set_num_threads(4)
    torch.set_grad_enabled(False)
    cv2.setNumThreads(4)
    if not torch.backends.mps.is_available():
        raise RuntimeError("MPS is unavailable; face enhancement has no implicit CPU fallback.")
    emit(dict(phase="face_detection", message="Finding small faces"))
    detector = init_detection_model("retinaface_resnet50", device="mps", model_rootpath=str(root))
    cap = cv2.VideoCapture(str(source))
    rows, previous = [], None
    try:
        for index in range(count):
            ok, bgr = cap.read()
            if not ok:
                raise RuntimeError(f"Cannot decode source frame {index}.")
            thumb = cv2.resize(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), (64, 36)).astype(np.float32)
            cut = previous is None or float(np.abs(thumb - previous).mean()) > 35
            previous = thumb
            with torch.inference_mode():
                detected = detector.detect_faces(bgr, .97)
            boxes = [r[:5].tolist() for r in detected if np.isfinite(r[:5]).all() and r[2] > r[0] and r[3] > r[1]]
            rows.append(dict(frame=index, cut=cut, boxes=boxes))
            if index % 24 == 0:
                emit(dict(phase="face_detection", frame=index + 1, total=count))
    finally:
        cap.release()
    del detector
    torch.mps.empty_cache()
    fill_single_gaps(rows)
    records, _tracks = association(rows, width, height)
    if diagnostics:
        write_json(workspace / "detections.json", rows)
        write_json(workspace / "geometry.json", records)
    if not records:
        shutil.copyfile(source, workspace / "output.mp4")
        return dict(enhanced_frames=0, face_passes=0, selected_tracks=0, media=media,
                    unchanged_copy=True, video_sha256=digest(source), audio_preserved=True)
    from .model import Restorer
    emit(dict(phase="face_loading", message="Loading the optional face restorer"))
    restorer = Restorer(root)
    frames_dir = workspace / "frames"
    frames_dir.mkdir()
    by_frame = defaultdict(list)
    for rec in records:
        by_frame[rec["frame"]].append(rec)
    cap = cv2.VideoCapture(str(source))
    checks = []
    try:
        for index in range(count):
            ok, bgr = cap.read()
            if not ok:
                raise RuntimeError(f"Cannot decode source frame {index} on the restoration pass.")
            original = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            candidate = original.copy()
            union = np.zeros((height, width), dtype=bool)
            for rec in by_frame[index]:
                native = restorer.restore(original.crop(rec["crop"]))
                candidate = composite(candidate, native, rec)
                x0, y0, x1, y1 = rec["crop"]
                union[y0:y1, x0:x1] |= alpha_mask(rec) > 0
            pixels = np.asarray(candidate)
            if not np.array_equal(np.asarray(original)[~union], pixels[~union]):
                raise RuntimeError("Compositing changed pixels outside the selected face regions.")
            candidate.save(frames_dir / f"{index:06}.png")
            if diagnostics:
                checks.append(dict(frame=index, rgb_sha256=hashlib.sha256(pixels.tobytes()).hexdigest(), mask_pixels=int(union.sum())))
            emit(dict(phase="face_restoration", frame=index + 1, total=count))
    finally:
        cap.release()
    del restorer
    torch.mps.empty_cache()
    if diagnostics:
        write_json(workspace / "frame-checks.json", checks)
    emit(dict(phase="face_export", message="Saving enhanced video and preserving source audio"))
    command = [tool("ffmpeg"), "-v", "error", "-xerror", "-nostdin", "-n", "-framerate", "24",
        "-i", str(frames_dir / "%06d.png"), "-i", str(source), "-map", "0:v:0", "-map", "1:a:0?",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "copy",
        "-movflags", "+faststart", str(workspace / "output.mp4")]
    subprocess.run(command, capture_output=True, check=True, timeout=300)
    delivered, dv, da = inspect_input(workspace / "output.mp4")
    if any(dv[k] != video[k] for k in ("width", "height", "nb_read_frames", "avg_frame_rate")) or len(da) != len(audios):
        raise ValueError("Enhanced output has different video timing, dimensions or audio streams.")
    if audios and any(da[0][k] != audios[0][k] for k in ("sample_rate", "channels", "duration", "start_time")):
        raise ValueError("Enhanced output changed source audio timing or format.")
    if audios and _audio_hash(source) != _audio_hash(workspace / "output.mp4"):
        raise ValueError("Enhanced output audio differs from the source.")
    return dict(enhanced_frames=len({r["frame"] for r in records}), face_passes=len(records),
                selected_tracks=len({r["track"] for r in records}), media=delivered,
                audio_preserved=True, unchanged_copy=False, exterior_pixels_exact_before_encoding=True,
                worker_seconds=time.monotonic() - start, video_sha256=digest(workspace / "output.mp4"),
                precision="float32", inference_steps=1, canvas=512, crop_size=256,
                seed_per_face=42, temporal_conditioning=False)
