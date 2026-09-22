# SPDX-License-Identifier: Apache-2.0
# Video canvas rule adapted from Diffusers (modified for fixed H3 defaults).
# Copyright 2026 The MiniMax and HuggingFace Teams. All rights reserved.
"""Validate and deliver synchronized audio/video."""

from fractions import Fraction
import ctypes
import hashlib
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def tool(name):
    """Use the pip wheel's executable, independently of PATH and Conda."""
    import imageio_ffmpeg

    if name != "ffmpeg":
        raise ValueError(f"Unsupported media tool: {name}")
    candidates = list((Path(imageio_ffmpeg.__file__).parent / "binaries").glob("ffmpeg-*-v*"))
    if len(candidates) != 1 or not os.access(candidates[0], os.X_OK):
        raise RuntimeError("The bundled FFmpeg executable is missing. Reinstall h3-apple with pip.")
    return str(candidates[0])


def ffmpeg_libraries():
    """Expose PyAV's matching FFmpeg ABI to the unchanged native engine."""
    import av

    majors = dict(libavutil=60, libavcodec=62, libavformat=62, libavdevice=62,
                  libavfilter=11, libswresample=6, libswscale=9)
    root = Path(av.__file__).parent / ".dylibs"
    libraries = {}
    for name, major in majors.items():
        candidates = list(root.glob(f"{name}.{major}.*.dylib"))
        if av.library_versions.get(name, (None,))[0] != major or len(candidates) != 1:
            raise RuntimeError("H3 needs the pinned PyAV macOS wheel and FFmpeg 8 libraries. "
                               "Reinstall h3-apple with pip on an Apple Silicon Mac.")
        target = candidates[0].resolve(strict=True)
        ctypes.CDLL(str(target))  # Fail before inference instead of falling back to system libraries.
        libraries[name + ".dylib"] = target
    key = hashlib.sha256('\n'.join(map(str, libraries.values())).encode()).hexdigest()
    directory = Path.home() / ".cache/h3-apple/media" / key
    if not directory.exists():
        directory.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".media-", dir=directory.parent))
        try:
            for name, target in libraries.items():
                (temporary / name).symlink_to(target)
            try:
                temporary.rename(directory)
            except FileExistsError:
                pass  # Another process prepared the same links.
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
    for name, target in libraries.items():
        if not (directory / name).is_symlink() or (directory / name).resolve() != target:
            raise ValueError(f"FFmpeg library link changed: {directory / name}")
    return directory


def probe(path):
    """Read stream metadata and count decoded frames without an external ffprobe."""
    import av

    streams = []
    with av.open(str(path)) as container:
        for stream in container.streams:
            if stream.type not in ("video", "audio"):
                continue
            if stream.duration is None or stream.time_base is None:
                raise ValueError("Output stream has no duration.")
            entry = dict(index=stream.index, codec_type=stream.type,
                         codec_name=stream.codec_context.name,
                         start_time=str(float((stream.start_time or 0) * stream.time_base)),
                         duration=str(float(stream.duration * stream.time_base)))
            if stream.type == "video":
                entry.update(width=stream.width, height=stream.height,
                             avg_frame_rate=str(stream.average_rate), nb_read_frames=0)
            else:
                entry.update(sample_rate=str(stream.sample_rate),
                             channels=len(stream.layout.channels), decoded_samples=0)
            streams.append(entry)
        by_index = {entry['index']: entry for entry in streams}
        for packet in container.demux():
            if packet.stream.index not in by_index:
                continue
            if packet.is_corrupt:
                raise ValueError("Output contains a corrupt media packet.")
            for frame in packet.decode():
                if frame.is_corrupt:
                    raise ValueError("Output contains a corrupt decoded frame.")
                entry = by_index[packet.stream.index]
                if entry['codec_type'] == 'video':
                    entry['nb_read_frames'] += 1
                else:
                    entry['decoded_samples'] += frame.samples
    return dict(streams=streams)


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
    if audio['decoded_samples'] == 0:
        raise ValueError("Output audio contains no decoded samples.")
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
