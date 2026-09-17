"""Public bundle fields must reach the correct condition encoder before loading weights."""
from types import SimpleNamespace

import pytest

from h3_apple.runtime import engine, fl2va_pipeline, ref2va_pipeline, ref2va_multimodal


@pytest.mark.parametrize('task,options,expected', [
    ('t2va', None, 'text'),
    ('fl2va', {'image_paths': ['first.png']}, 'keyframes'),
    ('ref2va', {'image_paths': ['picture.png']}, 'images'),
    ('ref2va', {'image_paths': [], 'video_paths': ['video.mp4']}, 'videos'),
    ('ref2va', {'image_paths': ['picture.png'], 'video_paths': ['video.mp4']}, 'videos'),
])
def test_all_task_routes_use_the_public_bundle_contract(tmp_path, monkeypatch, task, options, expected):
    class ReachedEncoder(Exception):
        pass

    seen = []
    def text(*args):
        seen.append('text')
        raise ReachedEncoder

    def encoder(name):
        def condition(request, ref, checkpoint, observer, phase):
            seen.append(name)
            assert checkpoint == 'checkpoint'
            if name == 'videos':
                assert ref['audio_vae'] == str(tmp_path / 'components' / 'audio_vae')
                assert 'audio_vae' not in options  # Do not mutate the caller's spec.
            raise ReachedEncoder
        return condition

    monkeypatch.setattr(engine, 'Pipeline', lambda **_: SimpleNamespace(encode_prompt=text))
    for name in ('set_memory_limit', 'set_cache_limit', 'set_wired_limit', 'reset_peak_memory'):
        monkeypatch.setattr(engine.mx, name, lambda *args: None)
    monkeypatch.setattr(engine.mx, 'device_info', lambda: {'max_recommended_working_set_size': 100 * 1024**3})
    for module, name in ((fl2va_pipeline, 'keyframes'), (ref2va_pipeline, 'images'), (ref2va_multimodal, 'videos')):
        monkeypatch.setattr(module, 'condition_and_denoise', encoder(name))
    request = dict(task=task, prompt='move', model_width=1376, model_height=768, model_num_frames=124)
    assets = dict(components=str(tmp_path / 'components'), checkpoint='checkpoint')
    with pytest.raises(ReachedEncoder):
        engine.run(request, assets, tmp_path / 'output.mp4', lambda _: None, ref2va=options)
    assert seen == [expected]
