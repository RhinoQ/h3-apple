"""Dense generation preserves the recipe and bypasses sparse gates."""
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from h3_apple import generate, resolve
from h3_apple.cli import parser


@pytest.fixture
def references(tmp_path):
    image = tmp_path / 'rabbit.png'
    Image.new('RGB', (96, 160), 'pink').save(image)
    return [image]


def options(references):
    return dict(prompt='A rabbit blinks.', reference_images=references, mode='VSA',
                attention='dense', resolution='768p', x2=False, duration=5,
                aspect_ratio='9:16', seed=7)


def test_dense_request_and_cli_forwarding(references, monkeypatch):
    from h3_apple import process
    monkeypatch.setattr(process, 'run_generation', lambda request, **kw: request)
    request = generate(**options(references))
    args = vars(parser().parse_args(['resolve', '--prompt', 'A rabbit blinks.',
        '--image', str(references[0]), '--mode', 'VSA', '--attention', 'dense',
        '--resolution', '768p', '--no-x2', '--aspect-ratio', '9:16', '--seed', '7']))
    args.pop('command')
    assert request == resolve(**args)
    assert request.recipe == 'ref2va-w8a8-dense-bf16-v1'
    assert (request.model_width, request.model_height, request.num_steps) == (768, 1376, 4)
    sparse = resolve(**dict(options(references), attention='vsa'))
    a, b = request.to_dict(), sparse.to_dict()
    assert {k for k in a if a[k] != b[k]} == {'attention', 'recipe'}


@pytest.mark.parametrize('change', [dict(mode='SOL'), dict(attention='unknown'),
    dict(resolution='576p'), dict(x2=True)])
def test_dense_rejects_incompatible_settings(references, change):
    with pytest.raises(ValueError):
        resolve(**dict(options(references), **change))


@pytest.mark.parametrize('duration', [5, 7, 8.5, 10, 15])
@pytest.mark.parametrize('aspect', ['16:9', '9:16'])
def test_dense_supports_full_product_scope(references, duration, aspect):
    request = resolve(**dict(options(references), reference_images=references * 9,
                             duration=duration, aspect_ratio=aspect), upscale=True)
    assert request.num_frames == duration * 24
    assert request.model_num_frames >= request.num_frames
    assert request.upscale and not request.x2 and len(request.reference_images) == 9
    assert request.recipe == 'ref2va-w8a8-dense-bf16-v1'


def test_dense_dispatch_guards_and_restores(monkeypatch):
    from h3_apple.runtime import affine_native, dispatch, sparse
    from h3_apple._vendor.fastvideo_mlx import minimax_h3 as model
    class Projection:
        def __init__(self, **kw):
            self.calls = self.pack_calls = 0
        def prepare(self, w):
            return w
    monkeypatch.setattr(affine_native, 'NativeAffineW8A8', Projection)
    gate = object()
    dit = SimpleNamespace(blocks=[dict({k: object() for k in dispatch.KEYS},
                                      **{'attn.to_gate_compress.weight': gate})])
    old_linear, old_sparse = model.linear, sparse._implementation
    original = lambda *args, **kwargs: 'ordinary-attention'
    monkeypatch.setattr(model, '_attention', original)
    with pytest.raises(RuntimeError, match='deliberate'):
        with dispatch.Dispatch(dit, attention='dense') as run:
            assert sparse._implementation is old_sparse
            assert model._attention(use_rope=True, vsa_geometry=None, use_gate_compress=False) == 'ordinary-attention'
            assert model._attention(use_rope=False) == 'ordinary-attention'
            assert run.summary()['dense_self_attention_calls'] == 1
            assert run.summary()['int8_fine_calls'] == 0
            with pytest.raises(RuntimeError, match='gate projections'):
                model.linear(None, gate)
            with pytest.raises(RuntimeError, match='bypass'):
                model._attention(use_rope=True, use_gate_compress=True)
            with pytest.raises(RuntimeError, match='bypass'):
                model._attention(use_rope=True, vsa_geometry=object())
            raise RuntimeError('deliberate')
    assert model._attention is original and model.linear is old_linear
    assert sparse._implementation is old_sparse and not dispatch._active


@pytest.mark.hardware
def test_model_dense_branch_matches_independent_attention(monkeypatch):
    import mlx.core as mx
    from h3_apple._vendor.fastvideo_mlx import minimax_h3 as model
    rng = np.random.default_rng(176)
    x = mx.array(rng.normal(size=(19, 256)), mx.bfloat16)
    weights = {key: mx.eye(256, dtype=mx.bfloat16) for key in
               ('attn.to_q.weight', 'attn.to_k.weight', 'attn.to_v.weight', 'attn.to_out.0.weight')}
    weights.update({'attn.norm_q.weight': mx.ones(128, mx.bfloat16),
                    'attn.norm_k.weight': mx.ones(128, mx.bfloat16),
                    'attn.to_gate_compress.weight': mx.ones((256, 256), mx.bfloat16)})
    def fail(*a, **kw):
        raise AssertionError('Dense branch invoked sparse attention')
    monkeypatch.setattr(model, 'h3_vsa_attention', fail)
    monkeypatch.setattr(model, 'apply_h3_rotary', lambda x, cos, sin: x)
    out = model._attention(weights, x, None, None, num_heads=2, head_dim=128,
                           eps=1e-6, use_rope=True, vsa_geometry=None, use_gate_compress=False)
    q = model._h3_rms_norm(x.reshape(19, 2, 128), weights['attn.norm_q.weight'], 1e-6)
    a = np.asarray(q.astype(mx.float32)).astype(np.float64).transpose(1, 0, 2)
    v = np.asarray(x.astype(mx.float32)).astype(np.float64).reshape(19, 2, 128).transpose(1, 0, 2)
    logits = a @ a.transpose(0, 2, 1) / np.sqrt(128)
    probability = np.exp(logits - logits.max(-1, keepdims=True))
    probability /= probability.sum(-1, keepdims=True)
    expected = (probability @ v).transpose(1, 0, 2).reshape(19, 256)
    np.testing.assert_allclose(np.asarray(out.astype(mx.float32)), expected, atol=.035, rtol=.012)
