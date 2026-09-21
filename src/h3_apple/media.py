# SPDX-License-Identifier: Apache-2.0
# Video canvas rule adapted from Diffusers (modified for fixed H3 defaults).
# Copyright 2026 The MiniMax and HuggingFace Teams. All rights reserved.
"""Validate and deliver synchronized audio/video."""

from fractions import Fraction
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys


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

