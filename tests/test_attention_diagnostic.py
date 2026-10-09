"""The diagnostic must isolate routing and reject unrequested acceleration."""
from copy import deepcopy

import pytest

from h3_apple import engine
from h3_apple.assets import RECIPE


@pytest.mark.parametrize("mode,changed", [
    ("sage-only", dict(sol_attn=False)),
    ("dense", dict(sol_attn=False, sage_attn=False)),
])
def test_only_declared_attention_switches_change(tmp_path, mode, changed):
    request = dict(prompt="test", model_width=544, model_height=960,
                   model_num_frames=124, fps=24, seed=42, x2=True)
    assets = dict(native_model="/model", adapter=dict(path="/adapter"), recipe=RECIPE)
    base = engine.build_graph(request, assets, [], tmp_path / "native.wav")
    expected = deepcopy(base)
    next(s for s in expected["stages"] if s["id"] == "generate-video")["config"].update(changed)
    actual = engine.build_graph(request, assets, [], tmp_path / "native.wav", diagnostic_attention=mode)
    assert actual == expected


@pytest.mark.parametrize("mode,text", [
    (None, "Sol-Attn ON\nSol-Attn kept 20%\nSageAttention ON"),
    ("sage-only", "SageAttention ON"),
    ("dense", ""),
])
def test_audit_binds_actual_attention_to_control(mode, text):
    log = "baked AdaLN for 4 steps\n" + text
    engine.audit_log(log, diagnostic_attention=mode)
    for other in (None, "sage-only", "dense"):
        if other != mode:
            with pytest.raises(RuntimeError):
                engine.audit_log(log, diagnostic_attention=other)


def test_bad_diagnostic_fails_before_model_work(tmp_path):
    with pytest.raises(ValueError, match="diagnostic"):
        engine.run({}, {}, tmp_path, lambda e: None, diagnostic_attention="typo")


def noise_fixture(tmp_path):
    import numpy as np
    from h3_apple.io import digest
    value = np.arange(4 * 96, dtype=np.float32).reshape(4, 96)
    path = tmp_path / "noise.npy"
    np.save(path, value, allow_pickle=False)
    return value, dict(path=str(path), sha256=digest(path)), dict(
        model_num_frames=5, model_height=32, model_width=64)


def test_noise_handoff_keeps_all_target_rows_and_is_bound(tmp_path):
    import numpy as np
    from h3_apple.io import digest
    value, entry, request = noise_fixture(tmp_path)
    result = engine.prepare_video_noise(request, [dict(height=32, width=64)], entry, tmp_path)
    actual = np.fromfile(result["packed"]["path"], dtype="<f4").reshape(6, 96)
    np.testing.assert_array_equal(actual[:2], 0)
    np.testing.assert_array_equal(actual[2:], value)
    assert result["source"] == entry
    assert result["prefix_rows"] == 2 and result["native_floats"] == 576
    assert result["packed"]["sha256"] == digest(result["packed"]["path"])


@pytest.mark.parametrize("fault", ["checksum", "shape", "dtype", "nan"])
def test_noise_rejects_bad_input_before_native_launch(tmp_path, fault):
    import numpy as np
    from h3_apple.io import digest
    value, entry, request = noise_fixture(tmp_path)
    if fault == "checksum":
        entry["sha256"] = "0" * 64
    else:
        if fault == "shape": value = value[:3]
        elif fault == "dtype": value = value.astype(np.float64)
        else: value[0, 0] = np.nan
        np.save(entry["path"], value, allow_pickle=False)
        entry["sha256"] = digest(entry["path"])
    with pytest.raises(ValueError):
        engine.prepare_video_noise(request, [], entry, tmp_path)
    assert not (tmp_path / "diagnostic-video-noise.f32").exists()


@pytest.mark.parametrize("fault", [None, "checksum", "shape", "dtype", "nan"])
def test_audio_noise_transport_or_early_rejection(tmp_path, fault):
    import numpy as np
    from h3_apple.io import digest
    from h3_apple._vendor.fastvideo_mlx.minimax_h3 import audio_latent_num_frames
    request = dict(model_num_frames=5)
    value = np.arange(2 * audio_latent_num_frames(5) * 32, dtype='<f4').reshape(-1, 32)
    if fault == 'shape': value = value[:1]
    if fault == 'dtype': value = value.astype(np.float64)
    if fault == 'nan': value[0, 0] = np.nan
    source = tmp_path / 'audio.npy'; np.save(source, value, allow_pickle=False)
    entry = dict(path=str(source), sha256='0'*64 if fault == 'checksum' else digest(source))
    if fault:
        with pytest.raises(ValueError):
            engine.prepare_audio_noise(request, entry, tmp_path)
        assert not (tmp_path / 'diagnostic-audio-noise.f32').exists()
    else:
        result = engine.prepare_audio_noise(request, entry, tmp_path)
        assert result['source'] == entry and result['native_floats'] == value.size
        np.testing.assert_array_equal(np.fromfile(result['packed']['path'], '<f4').reshape(value.shape), value)
