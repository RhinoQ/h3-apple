"""Both public modes preserve input semantics and route to separate models."""
import json
from pathlib import Path

import pytest
from PIL import Image

from h3_apple import DownloadApprovalRequired, generate, resolve
from h3_apple.cli import parser
from h3_apple import vsa_assets, vsa_preparation


@pytest.fixture
def image(tmp_path):
    path = tmp_path / 'reference.png'
    Image.new('RGB', (64, 48), 'blue').save(path)
    return path


def test_modes_keep_geometry_and_distinct_recipe(image):
    sol = resolve('Scene', reference_images=[image], seed=1, mode='SOL')
    vsa = resolve('Scene', reference_images=[image], seed=1, mode='VSA')
    assert sol.mode == 'SOL' and vsa.mode == 'VSA'
    assert sol.recipe != vsa.recipe
    assert {k: v for k, v in sol.to_dict().items() if k not in ('mode', 'recipe')} == {
        k: v for k, v in vsa.to_dict().items() if k not in ('mode', 'recipe')}
    for mode in ('vsa', 'sol', 'auto', None):
        with pytest.raises(ValueError, match='mode'):
            resolve('Scene', reference_images=[image], mode=mode)


@pytest.mark.parametrize('command', ('generate', 'resolve', 'prepare', 'doctor', 'verify'))
def test_cli_selects_mode_consistently(command):
    inputs = ['--image', 'ref.png', '--prompt', 'Scene'] if command in ('generate', 'resolve') else []
    assert parser().parse_args([command, *inputs, '--mode', 'VSA']).mode == 'VSA'
    assert parser().parse_args([command, *inputs]).mode == 'SOL'


def test_vsa_consent_precedes_model_work_and_output(image, monkeypatch, tmp_path):
    from h3_apple.runtime import backend
    monkeypatch.setattr(vsa_preparation, 'snapshot', lambda: {})
    monkeypatch.setattr(vsa_preparation, 'check_machine', lambda *_: None)
    monkeypatch.setattr(backend, 'check_dependencies', lambda: None)
    monkeypatch.setattr(vsa_preparation, 'plan', lambda *a, **kw: dict(
        status='preparation_required', download_bytes=150_000_000_000,
        additional_disk_bytes=340_000_000_000))
    monkeypatch.setattr(vsa_preparation, 'prepare', lambda *a, **kw: pytest.fail('unapproved download'))
    output = tmp_path / 'out' / 'video.mp4'
    with pytest.raises(DownloadApprovalRequired):
        generate('Scene', reference_images=[image], output=output, mode='VSA',
                 resolution='576p', x2=False)
    assert not output.parent.exists()


def tiny_bundle(root, monkeypatch):
    from h3_apple.io import digest
    root.mkdir()
    files = []
    contents = {'dit/model.safetensors': b'original weights',
        'dit/ref2va_recipe.json': json.dumps(dict(schema='h3-apple-ref2va/v1', task='ref2va',
        lora_rank=128, lora_alpha=8, lora_tensors=624, gate_tensors=50,
        precision='int8_group64_bf16', fasth3_t2va_deltas_applied=False)).encode()}
    for name, content in contents.items():
        path = root / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(content)
        stat = path.stat()
        files.append(dict(path=name, size=stat.st_size, sha256=digest(path), mtime_ns=stat.st_mtime_ns))
    expected = [{k: f[k] for k in ('path', 'size', 'sha256')} for f in files[:1]]
    monkeypatch.setattr(vsa_assets, 'data_file', lambda name: dict(files=expected))
    manifest = dict(format_version=3, preset='ours', task='ref2va', checkpoint='dit',
                    components='components', ref2va_native='ref2va', files=files, derivation={})
    manifest['identity'] = vsa_assets.bundle_identity(manifest)
    (root / 'bundle.json').write_text(json.dumps(manifest))
    return manifest


def test_model_content_pin_rejects_alternate_weights_even_with_consistent_receipt(tmp_path, monkeypatch):
    root = tmp_path / 'bundle'
    manifest = tiny_bundle(root, monkeypatch)
    assert vsa_assets.load_assets(root, verify=True)['identity'] == manifest['identity']
    manifest['files'][0]['sha256'] = 'a' * 64
    manifest['identity'] = vsa_assets.bundle_identity(manifest)
    (root / 'bundle.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='original LightX2V'):
        vsa_assets.load_assets(root)


def test_default_model_directories_are_independent(monkeypatch, tmp_path):
    from h3_apple.assets import model_directory
    monkeypatch.setenv('H3_MODEL_DIR', str(tmp_path / 'SOL'))
    monkeypatch.setenv('H3_VSA_MODEL_DIR', str(tmp_path / 'VSA'))
    assert model_directory() == tmp_path / 'SOL'
    assert vsa_assets.model_directory() == tmp_path / 'VSA'


def test_vsa_never_treats_native_sol_model_as_prepared(tmp_path, monkeypatch):
    root = tmp_path / 'native'
    root.mkdir()
    (root / 'model.json').write_text('{}')
    monkeypatch.setattr(vsa_preparation, 'source_plan', lambda *a: pytest.fail('unexpected source plan'))
    with pytest.raises(FileExistsError, match='empty VSA'):
        vsa_preparation.plan(root)
