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
