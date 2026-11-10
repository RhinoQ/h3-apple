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
    assert sol.attention is None and vsa.attention == 'vsa'
    assert {k: v for k, v in sol.to_dict().items() if k not in ('mode', 'recipe', 'attention')} == {
        k: v for k, v in vsa.to_dict().items() if k not in ('mode', 'recipe', 'attention')}
    for mode in ('vsa', 'sol', 'auto'):
        with pytest.raises(ValueError, match='mode'):
            resolve('Scene', reference_images=[image], mode=mode)


@pytest.mark.parametrize('command', ('generate', 'resolve', 'prepare', 'doctor', 'verify'))
def test_cli_selects_mode_consistently(command):
    inputs = ['--image', 'ref.png', '--prompt', 'Scene'] if command in ('generate', 'resolve') else []
    assert parser().parse_args([command, *inputs, '--mode', 'VSA']).mode == 'VSA'
    assert parser().parse_args([command, *inputs]).mode == (None if inputs else 'VSA')
    assert parser().parse_args([command, *inputs, '--mode', 'SOL']).mode == 'SOL'


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


def test_pika_preparation_rechecks_a_concurrently_published_four_step_bundle(tmp_path, monkeypatch):
    from contextlib import nullcontext
    from h3_apple import media
    from h3_apple.runtime import backend

    root = tmp_path / "bundle"
    tiny_bundle(root, monkeypatch)
    monkeypatch.setattr(vsa_preparation, "check_machine", lambda *args: None)
    monkeypatch.setattr(vsa_preparation, "device_lock", nullcontext)
    monkeypatch.setattr(backend, "check_dependencies", lambda: None)
    monkeypatch.setattr(media, "check_runtime", lambda: None)
    stale = dict(status="preparation_required", directory=str(root), pika=True,
                 download_bytes=0, additional_disk_bytes=0)
    with pytest.raises(ValueError, match="recipe and prepared Ref2VA"):
        vsa_preparation.prepare(stale)
    with pytest.raises(ValueError, match="LightX2V v1.0"):
        vsa_preparation.prepare(dict(stale, pika=False))
    # A caller may explicitly select the historical native Dense checkpoint.
    legacy = vsa_preparation.plan(root, allow_legacy=True)
    assert vsa_preparation.prepare(legacy)["identity"] == vsa_assets.load_assets(root)["identity"]


def test_pika_import_and_reuse_keep_author_notice_and_license(tmp_path, monkeypatch):
    from h3_apple import pika_recipe
    from h3_apple.io import digest

    components = tmp_path / "components"
    components.mkdir()
    (components / "NOTICE").write_text(vsa_assets.model_notice())
    # The fixture isolates packaging. Runtime tests cover checkpoint validation separately.
    monkeypatch.setattr(vsa_assets, "load_assets", lambda root: json.loads((root / "bundle.json").read_text()))
    args = (tmp_path/"dit", components, tmp_path/"native")
    provenance = {"adapter_sha256": pika_recipe.ADAPTER}
    for name, notices in [("fresh", components), ("reuse", tmp_path/"fresh")]:
        directory = tmp_path/name
        manifest = vsa_assets.import_assets(*args, directory, provenance=provenance, notices_directory=notices)
        notice = (directory/"NOTICE").read_text()
        assert "Copyright © 2026 Mellis, Inc." in notice and "Pika H3 Flex Ref2VA" in notice
        assert "original LightX2V" not in notice
        assert digest(directory/"LICENSE") == digest(Path(vsa_assets.__file__).parent/"data/MiniMax-H3-LICENSE.txt")
        entries = {row["path"]: row["sha256"] for row in manifest["files"]}
        assert entries["NOTICE"] == digest(directory/"NOTICE") and entries["LICENSE"] == digest(directory/"LICENSE")
    assert (components/"NOTICE").read_text() == vsa_assets.model_notice()
