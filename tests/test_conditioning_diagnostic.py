import struct

import numpy as np
import pytest

from h3_apple import engine
from h3_apple.assets import RECIPE
from h3_apple.conditioning_diagnostic import prepare
from h3_apple.io import digest


def fixture(tmp_path, kind, values, tags=None):
    path = tmp_path / (kind + '.npz')
    np.savez(path, values=values, **({} if tags is None else dict(tags=tags)))
    return {kind: dict(path=str(path), sha256=digest(path))}


def test_text_roundtrip_and_only_conditioning_port_changes(tmp_path):
    values = np.zeros((2, 5120), dtype='<f4')
    values[0, :4] = [1, 1 + 1/256, 1 + 3/256, -2]
    prepared = [dict(path='/ref.png', height=960, width=544)]
    result = prepare(fixture(tmp_path, 'text', values, np.array([0, 1])), prepared, tmp_path)
    raw = (tmp_path / 'diagnostic-text.tensor').read_bytes()
    assert struct.unpack('<8sIIIIQqq', raw[:48]) == (b'VPTENSOR', 1, 2, 2, 0, values.size, 2, 5120)
    restored = (np.frombuffer(raw[48:], '<u2').astype(np.uint32) << 16).view('<f4')
    np.testing.assert_array_equal(restored[:4], [1, 1, 1 + 1/64, -2])
    assert result['text']['sideband']['references'][0]['latent_width'] == 34
    req = dict(prompt='one person', model_num_frames=124, model_width=544,
               model_height=960, fps=24, seed=1)
    assets = dict(native_model='/model', adapter=dict(path='/adapter'), recipe=RECIPE)
    original = engine.build_graph(req, assets, prepared, tmp_path/'out.mp4')
    graph = engine.build_graph(req, assets, prepared, tmp_path/'out.mp4', conditioning=result)
    diagnostic = graph['stages'].pop(4)
    assert diagnostic['id'] == 'diagnostic-text'
    bridge = graph['stages'].pop(4)
    assert bridge['type'] == 'passthrough'
    assert bridge['iports'] == [dict(src='diagnostic-text', oport=0)]
    port = graph['stages'][4]['iports'][0]
    assert port == dict(src='diagnostic-text-conditioning', oport=0)
    graph['stages'][4]['iports'][0] = dict(src='video-ref-encoder', oport=0)
    assert graph == original


@pytest.mark.parametrize('failure', ['hash', 'shape', 'nan', 'tags'])
def test_bad_conditioning_rejected_before_native_work(tmp_path, failure):
    values = np.zeros((2, 5120), dtype='<f4')
    tags = np.array([0, 1])
    if failure == 'shape': values = values[:, :96]
    if failure == 'nan': values[0, 0] = np.nan
    if failure == 'tags': tags[0] = 3
    entry = fixture(tmp_path, 'text', values, tags)
    if failure == 'hash': entry['text']['sha256'] = '0'*64
    with pytest.raises(ValueError):
        prepare(entry, [dict(height=960, width=544)], tmp_path)
    assert not (tmp_path/'diagnostic-text.tensor').exists()


def test_reference_geometry_and_lossless_float_transport(tmp_path):
    values = np.arange(510*96, dtype='<f4').reshape(510, 96) / 100
    entry = fixture(tmp_path, 'video', values)
    with pytest.raises(ValueError, match='geometry'):
        prepare(entry, [dict(height=544, width=544)], tmp_path)
    result = prepare(entry, [dict(height=960, width=544)], tmp_path)
    raw = (tmp_path/'diagnostic-video.tensor').read_bytes()
    assert raw[48:] == values.tobytes()
    assert result['video']['dtype'] == 3
