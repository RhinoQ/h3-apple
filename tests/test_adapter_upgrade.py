"""A prepared adapter is part of the checkpoint, never a runtime-only upgrade."""
from contextlib import nullcontext
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
            quantization=dict(bits=8, group_size=64), _class_name='MiniMaxH3DiTModel',
            num_layers=50, _h3_lora_premerged=name == 'transformer')))
    (model / 'model_index.json').write_text(json.dumps(dict(_minimax_h3=dict(partition='ref2va'))))
    files = [dict(path=str(p.relative_to(model)), bytes=p.stat().st_size, sha256=assets.digest(p))
             for p in sorted(model.rglob('*')) if p.is_file()]
    (root / 'adapter.safetensors').write_bytes(b'pinned-adapter')
    adapter = dict(repo='fixture/adapter', revision='a' * 40, filename='turbo.safetensors',
                   bytes=14, sha256=assets.digest(root / 'adapter.safetensors'))
    base = dict(repo='fixture/base', revision='b' * 40, filename='Ref2VA/model_index.json',
                bytes=(model / 'model_index.json').stat().st_size,
                sha256=assets.digest(model / 'model_index.json'))
    expected = dict(files=files, adapter=adapter)
    sources = dict(sources=[base, adapter], converted_peak_bytes=1024, recipe=assets.RECIPE)
    original = assets.data_file
    def data(name):
        return expected if name == 'prepared-model.json' else sources if name == 'model-sources.json' else original(name)
    monkeypatch.setattr(assets, 'data_file', data)
    monkeypatch.setattr(prep, 'data_file', data)
    assets.register_model(root, provenance=dict(kind='fixture'))
    receipt = (root / 'model.json').read_bytes()
    engine = tmp_path / 'engine';engine.mkdir()
    monkeypatch.setattr(prep, 'engine_paths', lambda: (dict(bytes=10), engine, tmp_path / 'engine.zip'))
    monkeypatch.setattr(prep, 'ensure_engine', lambda *_: {})
    monkeypatch.setattr(assets, 'load_engine', lambda: {})
    monkeypatch.setattr(prep, 'snapshot', lambda: {})
    monkeypatch.setattr(prep, 'check_machine', lambda *_: None)
    monkeypatch.setattr(prep, 'device_lock', nullcontext)
    monkeypatch.setattr(Path, 'home', lambda: tmp_path / 'home')
    monkeypatch.setenv('HF_HUB_CACHE', str(tmp_path / 'hub'))
    monkeypatch.setattr(prep, 'quantize', lambda *_: pytest.fail('exact prepared weights must be reused'))
    return dict(root=root, expected=expected, receipt=receipt, base=base)


def rewrite_receipt(root, **changes):
    path = root / 'model.json';record = json.loads(path.read_text());record.update(changes)
    record['identity'] = assets.identity({k: v for k, v in record.items() if k != 'identity'})
    path.write_text(json.dumps(record))


def test_legacy_recipe_requires_new_directory_and_leaves_old_receipt(installation):
    i = installation;rewrite_receipt(i['root'], recipe=assets.LEGACY_RECIPE)
    old = (i['root'] / 'model.json').read_bytes()
    with pytest.raises(assets.ModelRecipeUpgradeRequired, match='NEW_DIRECTORY'):
        prep.plan(i['root'])
    assert (i['root'] / 'model.json').read_bytes() == old
    assert not (i['root'] / 'adapters').exists()


def test_legacy_quantized_model_is_not_reused_as_premerged(installation):
    i = installation;rewrite_receipt(i['root'], recipe=assets.LEGACY_RECIPE)
    assert prep.reusable_model([i['root']], lambda _: None) is None
    # Fresh preparation still finds pinned raw assets in explicitly supplied sources.
    spec = prep.plan(i['root'].parent / 'new', reuse_dirs=[i['root']])
    assert spec['status'] == 'preparation_required'


def test_premerged_adapter_change_requires_repreparation(installation):
    i = installation;i['expected']['adapter'] = dict(i['expected']['adapter'], sha256='0' * 64)
    with pytest.raises(assets.ModelRecipeUpgradeRequired):
        assets.load_manifest(i['root'])
    assert prep.reusable_model([i['root']], lambda _: None) is None
    assert (i['root'] / 'model.json').read_bytes() == i['receipt']


def test_exact_premerged_bundle_can_be_reused_without_requantization(installation):
    i = installation;target = i['root'].parent / 'new'
    spec = prep.plan(target, reuse_dirs=[i['root']])
    assert spec['status'] == 'reuse_prepared' and spec['download_bytes'] == 0
    result = prep.prepare(spec)
    assert result['native_model'] == str(target / 'model')
    assert result['recipe'] == assets.RECIPE
    assert assets.load_manifest(target, verify=True)['identity'] == result['identity']
    assert prep.prepare(spec)['identity'] == result['identity']
    assert prep.plan(target)['status'] == 'ready'
    assert (i['root'] / 'model.json').read_bytes() == i['receipt']


@pytest.mark.parametrize('stage', ['before_plan', 'after_plan'])
def test_mutated_source_is_rejected_without_publishing(installation, stage):
    i = installation;target = i['root'].parent / 'new'
    if stage == 'after_plan':spec = prep.plan(target, reuse_dirs=[i['root']])
    path = i['root'] / 'model/video_vae/model.safetensors';stat = path.stat()
    path.write_bytes(b'bad-model')
    if stage == 'before_plan':os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    with pytest.raises(ValueError):
        prep.plan(target, reuse_dirs=[i['root']]) if stage == 'before_plan' else prep.prepare(spec)
    assert not target.exists()
    assert (i['root'] / 'model.json').read_bytes() == i['receipt']


def test_rehashed_unpinned_weights_are_not_admitted(installation):
    i = installation;record = json.loads(i['receipt']);record['files'][0]['sha256'] = '0' * 64
    rewrite_receipt(i['root'], files=record['files'])
    with pytest.raises(ValueError, match='base weights'):
        assets.load_manifest(i['root'])
    with pytest.raises(ValueError, match='base weights'):
        prep.plan(i['root'].parent / 'new', reuse_dirs=[i['root']])


def test_recipe_mutation_is_not_treated_as_supported_legacy(installation):
    i = installation;recipe = dict(assets.RECIPE, lora_scale=0.5)
    rewrite_receipt(i['root'], recipe=recipe)
    with pytest.raises(ValueError, match='recipe'):
        prep.plan(i['root'])


def test_fresh_preparation_passes_verified_adapter_to_native_quantizer(installation, monkeypatch):
    i = installation;target = i['root'].parent / 'fresh'
    spec = prep.plan(target, reuse_dirs=[i['root'] / 'model/model_index.json', i['root'] / 'adapter.safetensors'])
    assert spec['status'] == 'preparation_required' and spec['download_bytes'] == 0
    def quantize(source, work, engine, progress, adapter):
        assert adapter.read_bytes() == b'pinned-adapter'
        model = work / 'models/local/ref2va';shutil.copytree(i['root'] / 'model', model)
        (work / 'prepare.vpipeline').write_text('fixture');(work / 'preparation.log').write_text('fixture')
        return model
    monkeypatch.setattr(prep, 'quantize', quantize)
    result = prep.prepare(spec)
    assert assets.load_manifest(target, verify=True)['identity'] == result['identity']


def test_marking_manifest_premerged_cannot_enable_unmerged_checkpoint(installation):
    i = installation;p = i['root'] / 'model/transformer/config.json'
    c = json.loads(p.read_text());c.pop('_h3_lora_premerged');p.write_text(json.dumps(c))
    with pytest.raises(ValueError):assets.register_model(i['root'], provenance=dict(kind='bad'))
