"""Temporal assembly must preserve every packed color phase."""
import os
import numpy as np
import pytest

mx = pytest.importorskip('mlx.core')
from h3_apple._vendor.fastvideo_mlx.minimax_h3_video_vae import _concat_video_chunks


@pytest.mark.parametrize('channels', [3, 12])
def test_temporal_copy_preserves_strided_color_and_time(channels):
    source = np.arange(channels*28*4*8, dtype=np.float32).reshape(1, channels, 28, 4, 8)
    raw = mx.array(source)
    chunks = [raw[:, :, 3:20], raw[:, :, 23:28]]
    result = np.asarray(_concat_video_chunks(chunks))
    np.testing.assert_array_equal(result, np.concatenate([source[:, :, 3:20], source[:, :, 23:28]], axis=2))


@pytest.mark.hardware
@pytest.mark.skipif(os.environ.get('H3_TEST_LARGE_ARRAYS') != '1', reason='opt in: allocates a 2.56 GB synthetic video')
def test_large_temporal_copy_keeps_last_packed_channel():
    # The real failure has 2,562,195,456 elements. uint8 keeps the regression's
    # allocation small while exercising the same element-stride overflow.
    source = np.arange(1, 13, dtype=np.uint8).reshape(1, 12, 1, 1, 1)
    raw = mx.contiguous(mx.broadcast_to(mx.array(source), (1, 12, 28, 576, 1024)))
    mx.eval(raw)
    result = np.asarray(_concat_video_chunks([raw[:, :, 3:20]]*21 + [raw[:, :, 23:28]]))
    assert result.shape == (1, 12, 362, 576, 1024)
    for frame in (0, 181, 361):
        for channel in range(12):
            assert np.all(result[0, channel, frame] == channel+1)
