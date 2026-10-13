"""Public quality choices, legacy compatibility and non-discrete durations."""
import json

from PIL import Image
import pytest

from h3_apple import generate, resolve
from h3_apple.cli import parser


@pytest.fixture
def reference(tmp_path):
    path = tmp_path / 'reference.png'
    Image.new('RGB', (96, 64), 'blue').save(path)
    return path


@pytest.mark.parametrize('quality,expected', [
    ('fast', ('SOL', None, '544p', True, False, 1920, 1088)),
    ('medium', ('VSA', 'vsa', '768p', False, False, 1366, 768)),
    ('high', ('VSA', 'dense', '768p', False, True, 1366, 768)),
])
@pytest.mark.parametrize('duration', [5, 7, 8.5, 10, 15, 121 / 24])
@pytest.mark.parametrize('aspect', ['16:9', '9:16'])
def test_quality_cli_api_and_workflow_agree(reference, monkeypatch, quality, expected, duration, aspect):
    from h3_apple import process, workflow
    calls = []
    monkeypatch.setattr(process, 'run_generation', lambda r, **kw: calls.append('native') or r)
    monkeypatch.setattr(workflow, 'generate_upscaled', lambda r, **kw: calls.append('restored') or r)
    request = generate('Scene', reference_images=[reference], quality=quality, duration=duration,
                       aspect_ratio=aspect, seed=42)
    args = vars(parser().parse_args(['resolve', '--prompt', 'Scene', '--image', str(reference),
        '--quality', quality, '--duration', str(duration), '--aspect-ratio', aspect, '--seed', '42']))
    args.pop('command')
    assert request == resolve(**args)
    mode, attention, resolution, x2, upscale, width, height = expected
    assert (request.mode, request.attention, request.resolution, request.x2, request.upscale) == expected[:5]
    assert (request.width, request.height) == ((width, height) if aspect == '16:9' else (height, width))
    assert request.num_frames == round(duration * 24)
    assert request.quality == quality and request.num_steps == 4
    assert calls == ['restored' if upscale else 'native']


@pytest.mark.parametrize('quality,change', [
    ('fast', dict(mode='VSA')), ('fast', dict(x2=False)), ('fast', dict(upscale=True)),
    ('medium', dict(resolution='544p')), ('medium', dict(upscale=True)),
    ('medium', dict(attention='dense')), ('high', dict(attention='vsa')),
    ('high', dict(upscale=False)), ('high', dict(x2=True)), ('high', dict(mode='SOL')),
])
def test_conflicting_advanced_settings_fail_before_inputs_or_setup(quality, change):
    with pytest.raises(ValueError, match='omit .* or omit quality'):
        generate('Scene', reference_images=['missing.png'], quality=quality, **change)


@pytest.mark.parametrize('value', ['auto', 'FAST', '', [], True])
def test_invalid_quality_fails_early(value):
    with pytest.raises(ValueError, match='quality'):
        resolve('Scene', reference_images=['missing.png'], quality=value)


@pytest.mark.parametrize('duration', [4, 15.01, 5.01, True, float('nan'), float('inf')])
def test_quality_preserves_frame_validation(reference, duration):
    with pytest.raises(ValueError, match='duration'):
        resolve('Scene', reference_images=[reference], quality='high', duration=duration)


def test_matching_advanced_settings_are_allowed(reference):
    request = resolve('Scene', reference_images=[reference], quality='high', mode='VSA',
                      resolution='768p', attention='dense', x2=False, upscale=True)
    assert request.upscale and request.attention == 'dense'


@pytest.mark.parametrize('field', ['x2', 'upscale'])
def test_quality_does_not_treat_integers_as_boolean_overrides(reference, field):
    with pytest.raises(ValueError, match='boolean'):
        resolve('Scene', reference_images=[reference], quality='high', **{field: 0})


def test_explicit_quality_does_not_change_legacy_default_recipe(reference):
    baseline = resolve('Scene', reference_images=[reference], seed=42).to_dict()
    fast = resolve('Scene', reference_images=[reference], seed=42, quality='fast').to_dict()
    assert {k for k in baseline if baseline[k] != fast[k]} == {'quality'}
    custom = resolve('Scene', reference_images=[reference], mode='VSA', resolution='576p', x2=True)
    assert custom.quality is None and (custom.width, custom.height) == (2048, 1152)


def test_high_memory_guard_cannot_be_bypassed(monkeypatch, reference):
    from h3_apple import host
    monkeypatch.setattr(host, 'command', lambda *_: json.dumps(
        {'SPDisplaysDataType': [{'sppci_cores': '40'}]}))
    request = resolve('Scene', reference_images=[reference], quality='high').to_dict()
    machine = dict(system='Darwin', machine='arm64', chip='Apple M5 Max', macos='26.6.1')
    with pytest.raises(RuntimeError, match='128 GiB'):
        host.check_machine(dict(machine, memory_bytes=96 * 1024**3), request)
    host.check_machine(dict(machine, memory_bytes=128 * 1024**3), request)
