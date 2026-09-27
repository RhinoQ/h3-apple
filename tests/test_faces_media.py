"""Real tiny media tests for optional enhancement, without restoration inference."""
import hashlib
import subprocess

import pytest

from h3_apple.faces.pipeline import inspect_input
from h3_apple.media import tool


@pytest.fixture
def movie(tmp_path):
    path = tmp_path / 'source.mp4'
    subprocess.run([tool('ffmpeg'), '-v', 'error', '-nostdin', '-n', '-f', 'lavfi',
        '-i', 'color=black:s=1024x576:r=24:d=1', '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=32000:duration=1.05',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-ac', '2', str(path)], check=True)
    return path


def test_edited_audio_tail_is_valid_and_preserved_as_input(movie):
    _media, video, audio = inspect_input(movie)
    assert int(video['nb_read_frames']) == 24
    assert float(audio[0]['duration']) > float(video['duration'])


def test_no_face_returns_exact_input_without_loading_restorer(movie, monkeypatch):
    np = pytest.importorskip('numpy')
    torch = pytest.importorskip('torch')
    pytest.importorskip('cv2')
    detection = pytest.importorskip('facexlib.detection')
    from h3_apple.faces.pipeline import run
    from h3_apple.faces import model
    class EmptyDetector:
        def detect_faces(self, *_args):
            return np.empty((0, 15))
    monkeypatch.setattr(detection, 'init_detection_model', lambda *a, **k: EmptyDetector())
    monkeypatch.setattr(torch.backends.mps, 'is_available', lambda: True)
    monkeypatch.setattr(torch.mps, 'empty_cache', lambda: None)
    monkeypatch.setattr(model, 'Restorer', lambda *_args: pytest.fail('Must not load VOSR without eligible faces'))
    before = hashlib.sha256(movie.read_bytes()).hexdigest()
    result = run(movie.parent, movie.parent, lambda _event: None)
    assert result['face_passes'] == 0 and result['unchanged_copy']
    assert hashlib.sha256((movie.parent/'output.mp4').read_bytes()).hexdigest() == before
    assert hashlib.sha256(movie.read_bytes()).hexdigest() == before
