# SPDX-License-Identifier: Apache-2.0
# Video canvas rule adapted from Diffusers (modified for fixed H3 defaults).
# Copyright 2026 The MiniMax and HuggingFace Teams. All rights reserved.
"""Complete, common audio/video validation for generation and comparison."""

from fractions import Fraction
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys


VIDEO_REFERENCE_CANVAS = dict(schema="minimax-h3-video-canvas/v1", short_edge=768,
                              max_pixels=768 * 1344, multiple=32)


def reference_video_size(width, height):
    """Return H,W using the released H3 canvas rule, including upscaling.

    Match Diffusers' resolve_canvas_size: short edge 768, pre-rounding area
    at most 768*1344, then round both axes to multiples of 32. Still-image
    budgets and the requested output resolution do not change this policy.
    """
    if any(type(v) is not int or v <= 0 for v in (width, height)):
        raise ValueError("Reference video dimensions must be positive integers.")
    ratio = width / height
    if not .25 <= ratio <= 4:
        raise ValueError("Reference video aspect ratio must be between 1:4 and 4:1.")
    short = VIDEO_REFERENCE_CANVAS["short_edge"]
    width, height = (short * ratio, float(short)) if ratio >= 1 else (float(short), short / ratio)
    area = width * height
    if area > VIDEO_REFERENCE_CANVAS["max_pixels"]:
        scale = math.sqrt(VIDEO_REFERENCE_CANVAS["max_pixels"] / area)
        width, height = width * scale, height * scale
    multiple = VIDEO_REFERENCE_CANVAS["multiple"]
    return max(multiple, round(height / multiple) * multiple), max(multiple, round(width / multiple) * multiple)


def probe_reference(path, kind):
    """Validate bounded local audio/video inputs before starting the worker."""
    if kind not in ("videos", "audio"):
        raise ValueError("Reference probe kind must be videos or audio.")
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    label = "video" if kind == "videos" else "audio"
    try:
        result = subprocess.run([tool("ffprobe"), "-v", "error", "-show_streams", "-show_format",
                                 "-of", "json", str(path)], capture_output=True, text=True,
                                check=True, timeout=30)
    except subprocess.CalledProcessError as error:
        raise ValueError(f"Cannot read reference {label}: {path}. "
                         "Check that the file is complete and playable in FFmpeg.") from error
    except subprocess.TimeoutExpired as error:
        raise ValueError(f"Timed out reading reference {label}: {path}. "
                         "Try a complete local media file.") from error
    data = json.loads(result.stdout)
    videos = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    audios = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
    if kind == "audio":
        # MP3/M4A cover art is not a moving video reference.
        if len(audios) != 1 or any(not s.get("disposition", {}).get("attached_pic") for s in videos):
            raise ValueError("Reference audio needs one audio stream and no moving video; use --reference-video for videos.")
        audio = audios[0]
        duration = float(audio.get("duration") or data.get("format", {}).get("duration", 0))
        if not math.isfinite(duration) or not 2 <= duration <= 15:
            raise ValueError("Reference audio must be between 2 and 15 seconds.")
        if audio.get("channels") not in (1, 2) or int(audio.get("sample_rate", 0)) <= 0:
            raise ValueError("Reference audio must be mono or stereo with a valid sample rate.")
        return data
    if len(videos) != 1 or len(audios) > 1:
        raise ValueError("Reference video needs exactly one video stream and at most one soundtrack.")
    video = videos[0]
    duration = float(video.get("duration") or data.get("format", {}).get("duration", 0))
    if not math.isfinite(duration) or not 2 <= duration <= 15:
        raise ValueError("Reference videos must be between 2 and 15 seconds.")
    reference_video_size(video["width"], video["height"])
    if video.get("sample_aspect_ratio", "1:1") not in ("1:1", "N/A", "0:1"):
        raise ValueError("Reference video must use square pixels; normalize its display aspect ratio first.")
    rotations = [s.get("rotation", 0) for s in video.get("side_data_list", [])]
    if any(float(rotation) % 90 for rotation in rotations):
        raise ValueError("Reference video rotation must be a multiple of 90 degrees.")
    return data


def tool(name):
    candidate = Path(sys.executable).parent / name
    if candidate.is_file():
        return str(candidate)
    found = shutil.which(name)
    if found is None:
        raise RuntimeError(f"{name} is missing; run ./install.sh to install the Conda media tools.")
    return found


def validate(path, expected, *, allow_aac_padding=False):
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"No completed video at {path}")
    result = subprocess.run([tool("ffprobe"), "-v", "error", "-count_frames",
                             "-show_streams", "-show_format", "-of", "json", str(path)],
                            capture_output=True, text=True, timeout=300, check=True)
    data = json.loads(result.stdout)
    videos = [s for s in data["streams"] if s["codec_type"] == "video"]
    audios = [s for s in data["streams"] if s["codec_type"] == "audio"]
    if len(videos) != 1 or len(audios) != 1:
        raise ValueError("Output must contain exactly one video stream and one audio stream.")
    video, audio = videos[0], audios[0]
    measured = (video["width"], video["height"], int(video["nb_read_frames"]),
                Fraction(video["avg_frame_rate"]), int(audio["sample_rate"]), audio["channels"])
    wanted = (expected["width"], expected["height"], expected["num_frames"],
              Fraction(expected["fps"]), expected["audio_sample_rate"], expected["audio_channels"])
    if measured != wanted:
        raise ValueError(f"Output media specification differs: {measured}, expected {wanted}")
    duration = expected["num_frames"] / expected["fps"]
    for stream in (video, audio):
        if abs(float(stream.get("start_time", 0))) > 1 / expected["audio_sample_rate"] + 1e-5:
            raise ValueError("Output audio/video does not start at zero.")
        tolerance = 1 / expected["audio_sample_rate"] + 1e-5
        delta = float(stream["duration"]) - duration
        # Native AAC endpoints can round either way by one packet. Callers
        # trimming native media must also check that audio covers the delivery.
        # Final delivered media always uses strict timing.
        padding = (allow_aac_padding and stream is audio and stream["codec_name"] == "aac"
                   and abs(delta) <= 1024 / expected["audio_sample_rate"] + tolerance)
        if abs(delta) > tolerance and not padding:
            raise ValueError("Output audio/video duration differs from the requested delivery.")
    subprocess.run([tool("ffmpeg"), "-v", "error", "-xerror", "-i", str(path),
                    "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"],
                   capture_output=True, timeout=300, check=True)
    return data


def finish_native(source, destination, request):
    """Validate full native media before the common center crop and fixed trim."""
    native=dict(request,width=request["model_width"],height=request["model_height"],num_frames=request["model_num_frames"])
    media=validate(source,native,allow_aac_padding=True)
    audio=next(s for s in media["streams"] if s["codec_type"]=="audio")
    if float(audio["duration"])+1/request["audio_sample_rate"]+1e-5 < request["num_frames"]/request["fps"]:
        raise ValueError("Native audio does not cover the requested delivery duration.")
    left=(native["width"]-request["width"])//2; top=(native["height"]-request["height"])//2
    command=[tool("ffmpeg"),"-v","error","-nostdin","-n","-i",str(source),"-map","0:v:0","-map","0:a:0","-vf",
        f"format=rgb24,crop={request['width']}:{request['height']}:{left}:{top},setsar=1",
        "-af", f"atrim=end_sample={(request['num_frames']*request['audio_sample_rate']+request['fps']-1)//request['fps']},asetpts=PTS-STARTPTS",
        "-frames:v",str(request["num_frames"]),"-t",str(request["duration"]),"-c:v","libx264","-preset","fast","-crf","18",
        "-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-ar","32000","-ac","2","-movie_timescale",str(math.lcm(request["fps"],request["audio_sample_rate"])),
        "-movflags","+faststart",str(destination)]
    subprocess.run(command,check=True,capture_output=True,timeout=300)
    return command

