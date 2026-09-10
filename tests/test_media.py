import subprocess

import pytest

from h3_apple.media import tool, validate


@pytest.fixture
def clip(tmp_path):
    path = tmp_path / "media.mp4"
    subprocess.run([tool("ffmpeg"), "-v", "error", "-f", "lavfi", "-i",
                    "color=blue:s=64x64:r=24", "-f", "lavfi", "-i",
                    "sine=frequency=500:sample_rate=32000", "-t", "1", "-ac", "2",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(path)],
                   check=True, capture_output=True)
    return path


def spec():
    return dict(width=64, height=64, num_frames=24, fps=24,
                audio_sample_rate=32000, audio_channels=2)


def test_complete_audio_video_validation(clip):
    assert len(validate(clip, spec())["streams"]) == 2


def test_mismatched_frames_rejected(clip):
    expected = dict(spec(), num_frames=25)
    with pytest.raises(ValueError, match="specification differs"):
        validate(clip, expected)


def test_truncated_file_rejected(clip):
    clip.write_bytes(clip.read_bytes()[:100])
    with pytest.raises((subprocess.CalledProcessError, ValueError)):
        validate(clip, spec())
