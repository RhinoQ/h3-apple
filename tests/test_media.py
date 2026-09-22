import subprocess
from types import SimpleNamespace

import pytest

from h3_apple import media
from h3_apple.media import tool, validate


@pytest.fixture
def conda_prefix(tmp_path, monkeypatch):
    prefix = tmp_path / 'env'
    (prefix / 'conda-meta').mkdir(parents=True)
    (prefix / 'bin').mkdir()
    (prefix / 'lib').mkdir()
    monkeypatch.setattr(media.sys, 'prefix', str(prefix))
    return prefix


def test_tools_belong_to_running_python_not_path(conda_prefix, monkeypatch):
    monkeypatch.setenv('PATH', '/unrelated/bin')
    monkeypatch.setenv('CONDA_PREFIX', '/another/environment')
    monkeypatch.setenv('IMAGEIO_FFMPEG_EXE', '/unrelated/ffmpeg')
    for name in ('ffmpeg', 'ffprobe'):
        executable = conda_prefix / 'bin' / name
        executable.write_text('#!/bin/sh\nexit 99\n')
        executable.chmod(0o755)
        assert tool(name) == str(executable)


def test_missing_tool_does_not_fall_back(conda_prefix, tmp_path, monkeypatch):
    fallback = tmp_path / 'ffmpeg'
    fallback.write_text('#!/bin/sh\nexit 0\n')
    fallback.chmod(0o755)
    monkeypatch.setenv('PATH', str(tmp_path))
    with pytest.raises(RuntimeError, match='conda install'):
        tool('ffmpeg')


def test_non_conda_python_has_actionable_error(tmp_path, monkeypatch):
    monkeypatch.setattr(media.sys, 'prefix', str(tmp_path))
    with pytest.raises(RuntimeError, match='conda create -n h3'):
        tool('ffmpeg')


@pytest.mark.parametrize('outside', [False, True])
def test_missing_or_external_library_rejected(conda_prefix, tmp_path, outside):
    if outside:
        target = tmp_path / 'unrelated.dylib'
        target.write_bytes(b'not a library')
        (conda_prefix / 'lib/libavutil.dylib').symlink_to(target)
    with pytest.raises(RuntimeError, match='libavutil.dylib'):
        media.ffmpeg_libraries()


def test_native_abi_mismatch_rejected(conda_prefix, monkeypatch):
    (conda_prefix / 'lib/libavutil.dylib').write_bytes(b'placeholder')
    def avutil_version():
        return 59 << 16
    monkeypatch.setattr(media.ctypes, 'CDLL', lambda _: SimpleNamespace(avutil_version=avutil_version))
    with pytest.raises(RuntimeError, match='libavutil.dylib'):
        media.ffmpeg_libraries()


@pytest.mark.parametrize('problem,message', [('old_ffprobe', 'FFmpeg 8'), ('no_h264', 'H.264')])
def test_preflight_checks_probe_and_encoder(monkeypatch, problem, message):
    monkeypatch.setattr(media, 'tool', lambda name: name)
    monkeypatch.setattr(media, 'ffmpeg_libraries', lambda: pytest.fail('accepted incompatible tools'))
    def output(command, **kwargs):
        if command[1] == '-version':
            major = 7 if problem == 'old_ffprobe' and command[0] == 'ffprobe' else 8
            return f'{command[0]} version {major}.1.2\n'
        return ' A..... aac AAC encoder\n'
    monkeypatch.setattr(media.subprocess, 'check_output', output)
    with pytest.raises(RuntimeError, match=message):
        media.check_runtime()


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


def test_installed_conda_runtime():
    runtime = media.check_runtime()
    assert runtime['ffmpeg'] == tool('ffmpeg')
    assert runtime['ffprobe'] == tool('ffprobe')


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
