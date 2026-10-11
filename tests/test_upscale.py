"""Restoration boundaries must fail before loading models or altering outputs."""

import importlib
import json
from pathlib import Path

import pytest

api = importlib.import_module('h3_apple.upscale')


@pytest.fixture
def media(tmp_path, monkeypatch):
    path = tmp_path / 'input.mp4'
    path.write_bytes(b'fixture')
    info = dict(streams=[dict(codec_type='video', width=1366, height=768,
        avg_frame_rate='24/1', r_frame_rate='24/1', nb_frames='120', duration='5.000'),
        dict(codec_type='audio', codec_name='aac')])
    monkeypatch.setattr(api, 'probe', lambda p: info)
    return path, info


@pytest.mark.parametrize('size', [(1366,768),(768,1366),(1024,576),(576,1024)])
def test_native_shapes_and_audio(media, size):
    path, info = media
    info['streams'][0].update(width=size[0], height=size[1])
    result = api.resolve_video(path)
    assert (result['width'], result['height']) == size
    assert result['num_frames'] == 120 and result['audio']
    info['streams'].pop()
    assert not api.resolve_video(path)['audio']


@pytest.mark.parametrize('change', [dict(width=1920,height=1088),dict(avg_frame_rate='25/1'),
    dict(r_frame_rate='30/1'),dict(nb_frames='361'),dict(duration='4.0'),
    dict(side_data_list=[dict(rotation=90)])])
def test_invalid_video_is_rejected(media, change):
    path, info = media
    info['streams'][0].update(change)
    with pytest.raises(ValueError):
        api.resolve_video(path)


def test_unsupported_audio_and_multiple_streams(media):
    path, info = media
    info['streams'][1]['codec_name'] = 'pcm_s16le'
    with pytest.raises(ValueError, match='AAC'):
        api.resolve_video(path)
    info['streams'].append(dict(info['streams'][0]))
    with pytest.raises(ValueError, match='one video'):
        api.resolve_video(path)


def test_short_excerpt_keeps_source_frame_count(media):
    path, _ = media
    result = api.resolve_video(path, duration=2)
    assert result['num_frames'] == 48 and result['source_frames'] == 120
    assert result['duration'] == 2
    for invalid in (True, 0, -1, 6, .01, float('nan')):
        with pytest.raises(ValueError):
            api.resolve_video(path, duration=invalid)


def test_existing_output_rejected_before_model_setup(media, tmp_path, monkeypatch):
    path, _ = media
    from h3_apple.super_resolution import assets
    monkeypatch.setattr(assets, 'prepare', lambda *a, **kw: pytest.fail('Model preparation reached'))
    output = tmp_path / 'existing.mp4'
    output.write_bytes(b'keep')
    with pytest.raises(FileExistsError):
        api.upscale(path, output=output)
    assert output.read_bytes() == b'keep'
    output.unlink()
    output.with_suffix('.run.json').write_text('{}')
    with pytest.raises(FileExistsError):
        api.upscale(path, output=output)


def test_model_reuse_and_corruption(tmp_path, monkeypatch):
    from h3_apple.super_resolution import assets
    from h3_apple.io import digest
    source = tmp_path / 'source'; source.mkdir()
    item = source / 'model.bin'; item.write_bytes(b'fixed model')
    spec = dict(recipe='fixture',model_revision='test',files=[dict(path='model.bin',
        bytes=item.stat().st_size,sha256=digest(item),url='https://invalid.example/model')])
    monkeypatch.setattr(assets,'manifest',lambda:spec)
    monkeypatch.setattr(assets,'download',lambda *a:pytest.fail('Unexpected download'))
    monkeypatch.setenv('H3_DEVICE_LOCK',str(tmp_path/'device.lock'))
    destination = tmp_path / 'prepared'
    assert assets.plan(destination,[source])['download_bytes'] == 0
    assets.prepare(destination,[source])
    assert (destination/'model.bin').read_bytes() == b'fixed model'
    (destination/'model.bin').write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='checksum'):
        assets.plan(destination)


@pytest.mark.parametrize('dtype_name',['float32','float16'])
def test_native_normalization_preserves_rounding(dtype_name):
    import torch
    from h3_apple.super_resolution._vendor.vosr.rmsnorm import RMSNorm
    dtype = getattr(torch,dtype_name)
    x = torch.linspace(-4,4,192).reshape(3,64).to(dtype)
    norm = RMSNorm(64)
    with torch.no_grad():
        norm.weight.copy_(torch.linspace(.2,1.8,64))
        result = norm(x)
        normalized = (x.double() / torch.sqrt(x.double().square().mean(-1,keepdim=True)+norm.eps)).to(dtype)
        oracle = normalized * norm.weight
    torch.testing.assert_close(result,oracle,atol=2e-3 if dtype==torch.float16 else 1e-6,rtol=1e-5)


def test_recipe_noise_is_bound_and_finite():
    import numpy as np
    from h3_apple.super_resolution import assets
    from h3_apple.io import digest
    path = Path(assets.__file__).parents[1] / 'data/vosr-noise.npz'
    assert digest(path) == assets.manifest()['noise']['sha256']
    with np.load(path,allow_pickle=False) as arrays:
        for width,height in [(1366,768),(768,1366),(1024,576),(576,1024)]:
            x=arrays[f'{width}x{height}']
            assert x.shape==(1,16,((height*2+15)//16)*2,((width*2+15)//16)*2)
            assert x.dtype==np.float32 and np.isfinite(x).all()


@pytest.mark.parametrize('stop', ['timeout', 'callback'])
def test_upscale_interruption_reaps_worker_and_keeps_logs(media, tmp_path, monkeypatch, stop):
    import subprocess
    import sys
    from h3_apple import host
    from h3_apple.super_resolution import assets
    source, _ = media
    monkeypatch.setattr(host, 'snapshot', lambda: dict(memory_bytes=128 * 1024**3))
    monkeypatch.setattr(host, 'check_machine', lambda _: None)
    monkeypatch.setattr(api, 'check_runtime', lambda: None)
    monkeypatch.setattr(assets, 'prepare', lambda *a, **kw: dict(recipe='test'))
    worker = tmp_path / 'worker.py'
    worker.write_text("import json,sys,time\njson.loads(sys.stdin.readline())\n"
                      "print(json.dumps({'phase':'test'}),flush=True)\ntime.sleep(60)\n")
    real_popen = subprocess.Popen
    children = []

    def launch(args, **kwargs):
        if args == [sys.executable, '-m', 'h3_apple.super_resolution.worker']:
            child = real_popen([sys.executable, str(worker)], **kwargs)
            children.append(child)
            return child
        return real_popen(args, **kwargs)

    monkeypatch.setattr(api.subprocess, 'Popen', launch)

    def cancel(event):
        raise KeyboardInterrupt()

    output = tmp_path / 'out.mp4'
    with pytest.raises(TimeoutError if stop == 'timeout' else KeyboardInterrupt):
        api.upscale(source, output=output, timeout=.5,
                    on_progress=cancel if stop == 'callback' else None)
    record = json.loads(output.with_suffix('.run.json').read_text())
    assert record['status'] == ('failed' if stop == 'timeout' else 'cancelled')
    assert len(children) == 1 and children[0].poll() is not None
    assert Path(record['workspace'], 'worker.log').is_file()
    assert Path(record['workspace'], 'source.mp4').read_bytes() == source.read_bytes()
    assert not output.exists()
