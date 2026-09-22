# SPDX-License-Identifier: Apache-2.0
# Video canvas rule adapted from Diffusers (modified for fixed H3 defaults).
# Copyright 2026 The MiniMax and HuggingFace Teams. All rights reserved.
"""Validate and deliver synchronized audio/video."""

from fractions import Fraction
import ctypes
import json
import math
import os
from pathlib import Path
import subprocess
import sys


INSTALL_FFMPEG = "conda install -c conda-forge ffmpeg=8.1.2"


def _conda_prefix():
    # Use the running interpreter, including notebooks and unactivated shells.
    # CONDA_PREFIX and PATH may belong to another environment.
    prefix = Path(sys.prefix).resolve()
    if not (prefix / "conda-meta").is_dir():
        raise RuntimeError("Run H3 with Python from a Conda environment. Create one with: "
                           "conda create -n h3 -c conda-forge python=3.11 ffmpeg=8.1.2 pip -y")
    return prefix


def tool(name):
    if name not in ("ffmpeg", "ffprobe"):
        raise ValueError(f"Unknown media tool: {name}")
    prefix = _conda_prefix()
    candidate = prefix / "bin" / name
    if (not candidate.is_file() or not os.access(candidate, os.X_OK)
            or not candidate.resolve().is_relative_to(prefix)):
        raise RuntimeError(f"{name} is missing from this Python environment. Run: {INSTALL_FFMPEG}")
    return str(candidate)


def ffmpeg_libraries():
    """Check the Conda shared libraries used by the native engine."""
    majors = dict(libavutil=60, libavcodec=62, libavformat=62, libavdevice=62,
                  libavfilter=11, libswresample=6, libswscale=9)
    directory = _conda_prefix() / "lib"
    for name, major in majors.items():
        candidate = directory / f"{name}.dylib"
        try:
            target = candidate.resolve(strict=True)
            if not target.is_relative_to(directory):
                raise ValueError("library points outside this environment")
            library = ctypes.CDLL(str(target))
            version = getattr(library, name.removeprefix("lib") + "_version")
            version.argtypes = []
            version.restype = ctypes.c_uint
            if version() >> 16 != major:
                raise ValueError(f"expected ABI {major}")
        except (OSError, AttributeError, ValueError) as error:
            raise RuntimeError(f"Incompatible or missing {candidate.name}. "
                               f"In this Conda environment, run: {INSTALL_FFMPEG}") from error
    return directory


def check_runtime():
    """Fail before model setup if the environment cannot encode the delivery."""
    result = {}
    for name in ("ffmpeg", "ffprobe"):
        executable = tool(name)
        try:
            output = subprocess.check_output([executable, "-version"], text=True,
                                             stderr=subprocess.STDOUT, timeout=60)
        except (OSError, subprocess.SubprocessError) as error:
            raise RuntimeError(f"Cannot run Conda {name}. Run: {INSTALL_FFMPEG}") from error
        version = output.splitlines()[0] if output else ""
        if not version.startswith(f"{name} version 8."):
            raise RuntimeError(f"H3 requires FFmpeg 8 tools. Run: {INSTALL_FFMPEG}")
        result[name] = executable
        result[name + "_version"] = version
    try:
        encoders = subprocess.check_output([result["ffmpeg"], "-hide_banner", "-encoders"],
                                           text=True, stderr=subprocess.STDOUT, timeout=60)
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeError(f"Cannot check Conda FFmpeg encoders. Run: {INSTALL_FFMPEG}") from error
    names = {fields[1] for line in encoders.splitlines() if len(fields := line.split()) >= 2}
    if not {"libx264", "aac"} <= names:
        raise RuntimeError("H3 needs FFmpeg with H.264 and AAC encoding. Run: "
                           "conda install -c conda-forge 'ffmpeg=8.1.2=gpl_*'")
    result["ffmpeg_libraries"] = str(ffmpeg_libraries())
    return result


def probe(path):
    """Read stream metadata and count decoded frames with Conda ffprobe."""
    result = subprocess.run([tool("ffprobe"), "-v", "error", "-count_frames",
                             "-show_streams", "-show_format", "-of", "json", str(path)],
                            capture_output=True, text=True, timeout=300, check=True)
    if result.stderr.strip():
        raise ValueError("Output contains media decoding errors.")
    return json.loads(result.stdout)


def validate(path, expected, *, allow_aac_padding=False):
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"No completed video at {path}")
    data = probe(path)
    videos = [s for s in data["streams"] if s["codec_type"] == "video"]
    audios = [s for s in data["streams"] if s["codec_type"] == "audio"]
    if len(videos) != 1 or len(audios) != 1:
        raise ValueError("Output must contain exactly one video stream and one audio stream.")
    video, audio = videos[0], audios[0]
    if int(audio.get("nb_read_frames", 0)) <= 0:
        raise ValueError("Output audio contains no decoded frames.")
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
