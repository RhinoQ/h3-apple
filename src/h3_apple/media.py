"""Complete, common audio/video validation for generation and comparison."""

from fractions import Fraction
import json
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


def probe_reference(path, kind):
    """Bound local input inspection before launching the model worker."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    result = subprocess.run([tool("ffprobe"), "-v", "error", "-show_streams", "-show_format",
                             "-of", "json", str(path)], capture_output=True, text=True,
                            check=True, timeout=30)
    data = json.loads(result.stdout)
    streams = [s for s in data.get("streams", []) if s["codec_type"] == ("video" if kind == "videos" else "audio")]
    if len(streams) != 1:
        raise ValueError(f"Expected one {kind} stream in {path.name}.")
    duration = float(streams[0].get("duration", data["format"].get("duration", 0)))
    if not 0 < duration <= 60:
        raise ValueError("Reference media must have a finite duration up to 60 seconds.")
    return data


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
