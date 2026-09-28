"""A new adapter must reuse pinned base weights without changing old receipts."""
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import shutil

import pytest

from h3_apple import assets, preparation as prep


@pytest.fixture
def installation(tmp_path, monkeypatch):
    root = tmp_path / 'existing'
    model = root / 'model'
    for name in ('transformer', 'text_encoder', 'video_vae', 'audio_vae'):
        directory = model / name
        directory.mkdir(parents=True)
        (directory / 'model.safetensors').write_bytes(name.encode())
        (directory / 'config.json').write_text(json.dumps(dict(
            quantization=dict(bits=8, group_size=64), _class_name='MiniMaxH3DiTModel', num_layers=50)))
    (model / 'model_index.json').write_text(json.dumps(dict(_minimax_h3=dict(partition='ref2va'))))
    files = [dict(path=str(p.relative_to(model)), bytes=p.stat().st_size, sha256=assets.digest(p))
             for p in sorted(model.rglob('*')) if p.is_file()]
    (root / 'adapter.safetensors').write_bytes(b'old-adapter')
    old_adapter = dict(sha256=assets.digest(root / 'adapter.safetensors'))
    new_bytes = b'original-lightx2v-adapter'
    new_adapter = dict(repo='fixture/lightx2v', revision='a' * 40, filename='turbo.safetensors',
                       bytes=len(new_bytes), sha256=hashlib.sha256(new_bytes).hexdigest())
    prepared = dict(files=files, adapter=old_adapter)
    base_source = dict(repo='fixture/base', revision='b' * 40, filename='Ref2VA/model_index.json',
                       bytes=(model / 'model_index.json').stat().st_size,
                       sha256=assets.digest(model / 'model_index.json'))
    sources = dict(sources=[base_source, new_adapter], converted_peak_bytes=1024, recipe=assets.RECIPE)
    original = assets.data_file
    def data(name):
        return prepared if name == 'prepared-model.json' else sources if name == 'model-sources.json' else original(name)
    monkeypatch.setattr(assets, 'data_file', data)
    monkeypatch.setattr(prep, 'data_file', data)
    assets.register_model(root, provenance=dict(kind='fixture'))
    old_receipt = (root / 'model.json').read_bytes()
    prepared['adapter'] = new_adapter
    local = tmp_path / 'downloaded.safetensors'
    local.write_bytes(new_bytes)
    engine = tmp_path / 'engine'
    engine.mkdir()
    monkeypatch.setattr(prep, 'engine_paths', lambda: (dict(bytes=10), engine, tmp_path / 'engine.zip'))
    monkeypatch.setattr(prep, 'ensure_engine', lambda *_: {})
    monkeypatch.setattr(assets, 'load_engine', lambda: {})
    monkeypatch.setattr(prep, 'snapshot', lambda: {})
    monkeypatch.setattr(prep, 'check_machine', lambda *_: None)
    monkeypatch.setattr(prep, 'device_lock', nullcontext)
    monkeypatch.setattr(Path, 'home', lambda: tmp_path / 'home')
    monkeypatch.setenv('HF_HUB_CACHE', str(tmp_path / 'hub'))
    monkeypatch.setattr(prep, 'quantize', lambda *_: pytest.fail('base weights must not be quantized again'))
    return dict(root=root, local=local, prepared=prepared, adapter=new_adapter,
                old_receipt=old_receipt, base_source=base_source)


def test_upgrade_reuses_weights_and_keeps_old_installation(installation):
    i = installation
    with pytest.raises(assets.AdapterUpgradeRequired):
        assets.load_manifest(i['root'])
    spec = prep.plan(i['root'], reuse_dirs=[i['local']])
    assert spec['status'] == 'upgrade_adapter' and spec['download_bytes'] == 0
    result = prep.prepare(spec)
    assert result['adapter']['sha256'] == i['adapter']['sha256']
    assert result['native_model'] == str(i['root'] / 'model')
    assert (i['root'] / 'model.json').read_bytes() == i['old_receipt']
    assert (i['root'] / 'adapter.safetensors').read_bytes() == b'old-adapter'
    assert assets.load_manifest(i['root'], verify=True)['identity'] == result['identity']
    assert prep.plan(i['root'])['status'] == 'ready'
    # Another caller may have planned the upgrade before the device lock was acquired.
    assert prep.prepare(spec)['identity'] == result['identity']


def test_upgrade_downloads_only_missing_adapter_and_uses_pinned_source(installation, monkeypatch):
    i = installation
    spec = prep.plan(i['root'])
    assert spec['download_bytes'] == i['adapter']['bytes']
    assert len(spec['groups']) == 1
    calls = []
    def download(url, path, size, checksum):
        calls.append((url, size, checksum))
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(i['local'], path)
        return path
    monkeypatch.setattr(prep, 'download', download)
    prep.prepare(spec)
    assert calls == [(f"https://huggingface.co/fixture/lightx2v/resolve/{'a' * 40}/turbo.safetensors",
                      i['adapter']['bytes'], i['adapter']['sha256'])]


def test_upgrade_resumes_only_the_adapter_remainder(installation):
    i = installation
    path = prep.cache_path(i['root'].parent / '.sources', i['adapter'])
    path.parent.mkdir(parents=True)
    prep.partial_path(path, i['adapter']['sha256']).write_bytes(b'orig')
    assert prep.plan(i['root'])['download_bytes'] == i['adapter']['bytes'] - 4


def test_reuse_old_installation_into_new_directory(installation):
    i = installation
    target = i['root'].parent / 'new'
    spec = prep.plan(target, reuse_dirs=[i['root'], i['local']])
    assert spec['status'] == 'reuse_prepared' and spec['download_bytes'] == 0
    result = prep.prepare(spec)
    assert result['native_model'] == str(target / 'model')
    assert assets.load_manifest(target, verify=True)['adapter']['sha256'] == i['adapter']['sha256']
    assert (i['root'] / 'model.json').read_bytes() == i['old_receipt']


def test_legacy_vpipe_base_reuse_does_not_require_the_new_adapter(installation):
    i = installation
    legacy = i['root'].parent / 'legacy'
    legacy.mkdir()
    (legacy / 'vpipe.json').write_text(json.dumps(dict(
        partition='ref2va', recipe=assets.RECIPE, native_model=str(i['root'] / 'model'),
        adapter=dict(path=str(i['root'] / 'adapter.safetensors')))))
    target = i['root'].parent / 'from-legacy'
    spec = prep.plan(target, reuse_dirs=[legacy, i['local']])
    assert spec['status'] == 'reuse_prepared' and spec['download_bytes'] == 0
    assert prep.prepare(spec)['adapter']['sha256'] == i['adapter']['sha256']


@pytest.mark.parametrize('stage', ['before_plan', 'after_plan'])
def test_upgrade_does_not_publish_after_model_mutation(installation, stage):
    i = installation
    if stage == 'after_plan':
        spec = prep.plan(i['root'], reuse_dirs=[i['local']])
    path = i['root'] / 'model/video_vae/model.safetensors'
    stat = path.stat()
    path.write_bytes(b'bad-model')
    if stage == 'before_plan':
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    with pytest.raises(ValueError):
        prep.plan(i['root'], reuse_dirs=[i['local']]) if stage == 'before_plan' else prep.prepare(spec)
    assert not (assets.adapter_directory(i['root']) / 'model.json').exists()
    assert (i['root'] / 'model.json').read_bytes() == i['old_receipt']


def test_rehashed_unpinned_weights_are_not_admitted_for_reuse(installation):
    i = installation
    path = i['root'] / 'model.json'
    receipt = json.loads(path.read_text())
    receipt['files'][0]['sha256'] = '0' * 64
    receipt['identity'] = assets.identity({k: v for k, v in receipt.items() if k != 'identity'})
    path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='base weights'):
        prep.plan(i['root'], reuse_dirs=[i['local']])


def test_download_failure_leaves_old_manifest_usable_and_retryable(installation, monkeypatch):
    i = installation
    def fail(*_):
        raise OSError('interrupted')
    monkeypatch.setattr(prep, 'download', fail)
    with pytest.raises(OSError, match='interrupted'):
        prep.prepare(prep.plan(i['root']))
    assert (i['root'] / 'model.json').read_bytes() == i['old_receipt']
    assert not (assets.adapter_directory(i['root']) / 'model.json').exists()
    assert prep.prepare(prep.plan(i['root'], reuse_dirs=[i['local']]))['adapter']['sha256'] == i['adapter']['sha256']


def test_changed_upgrade_receipt_does_not_fall_back_to_old_adapter(installation):
    i = installation
    prep.prepare(prep.plan(i['root'], reuse_dirs=[i['local']]))
    path = assets.adapter_directory(i['root']) / 'model.json'
    receipt = json.loads(path.read_text())
    receipt['recipe']['lora_scale'] = 0.5
    path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='manifest'):
        assets.load_manifest(i['root'])


def test_fresh_preparation_uses_catalog_adapter_without_old_repo_assumption(installation, monkeypatch):
    i = installation
    target = i['root'].parent / 'fresh'
    spec = prep.plan(target, reuse_dirs=[i['root'] / 'model/model_index.json', i['local']])
    assert spec['status'] == 'preparation_required' and spec['download_bytes'] == 0
    def quantize(source, work, engine, progress):
        model = work / 'models/local/ref2va'
        shutil.copytree(i['root'] / 'model', model)
        (work / 'prepare.vpipeline').write_text('fixture')
        (work / 'preparation.log').write_text('fixture')
        return model
    monkeypatch.setattr(prep, 'quantize', quantize)
    result = prep.prepare(spec)
    assert result['adapter']['sha256'] == i['adapter']['sha256']
    assert assets.load_manifest(target, verify=True)['identity'] == result['identity']
