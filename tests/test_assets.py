import hashlib
import json
import os
from pathlib import Path
import zipfile

import pytest
from h3_apple import assets


def model_fixture(tmp_path, monkeypatch):
    root=tmp_path/'bundle';root.mkdir()
    for name in ('transformer','text_encoder','video_vae','audio_vae'):
        p=root/'model'/name;p.mkdir(parents=True)
        (p/'model.safetensors').write_bytes(b'model')
        (p/'config.json').write_text(json.dumps(dict(quantization=dict(bits=8,group_size=64),
            _class_name='MiniMaxH3DiTModel',num_layers=50)))
    (root/'model/model_index.json').write_text(json.dumps(dict(_minimax_h3=dict(partition='ref2va'))))
    adapter=root/'adapter.safetensors';adapter.write_bytes(b'adapter')
    read=assets.data_file
    monkeypatch.setattr(assets,'data_file',lambda name:dict(adapter=dict(sha256=assets.digest(adapter))) if name=='prepared-model.json' else read(name))
    assets.register_model(root,provenance=dict(kind='synthetic-fixture'))
    return root


def test_model_verification_rejects_weight_mutation(tmp_path,monkeypatch):
    root=model_fixture(tmp_path,monkeypatch)
    assets.load_manifest(root,verify=True)
    p=root/'model/video_vae/model.safetensors';stat=p.stat();p.write_bytes(b'other')
    os.utime(p,ns=(stat.st_atime_ns,stat.st_mtime_ns))
    with pytest.raises(ValueError,match='Checksum'):
        assets.load_manifest(root,verify=True)


def test_rejects_changed_recipe_even_if_manifest_is_rehashed(tmp_path,monkeypatch):
    root=model_fixture(tmp_path,monkeypatch);p=root/'model.json';d=json.loads(p.read_text())
    d['recipe']['video_shift']=6;d['identity']=assets.identity({k:v for k,v in d.items() if k!='identity'})
    p.write_text(json.dumps(d))
    with pytest.raises(ValueError,match='manifest'):
        assets.load_manifest(root)


def engine_fixture(tmp_path,monkeypatch,extra=False):
    directory=tmp_path/'engine';archive=tmp_path/'download.zip';entries=[]
    with zipfile.ZipFile(archive,'w') as z:
        for name in ('h3-engine','libvpipe.0.dylib','LICENSE.txt'):
            data=b'fixture-'+name.encode();z.writestr(name,data)
            entries.append(dict(name=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mode=0o755))
        if extra:z.writestr('../escape',b'bad')
    record=dict(commit='fixture',bytes=archive.stat().st_size,sha256=assets.digest(archive),files=entries)
    monkeypatch.setattr(assets,'engine_paths',lambda:(record,directory,archive))
    return directory


def test_engine_is_installed_without_external_project(tmp_path,monkeypatch):
    directory=engine_fixture(tmp_path,monkeypatch)
    result=assets.ensure_engine()
    assert Path(result['binary']['path']).parent==directory
    assert os.access(result['binary']['path'],os.X_OK)
    assert assets.ensure_engine()==result
    (directory/'h3-engine').write_bytes(b'bad')
    with pytest.raises(ValueError,match='engine'):
        assets.load_engine()


def test_engine_archive_cannot_escape_destination(tmp_path,monkeypatch):
    engine_fixture(tmp_path,monkeypatch,extra=True)
    with pytest.raises(ValueError,match='members'):
        assets.ensure_engine()
    assert not (tmp_path/'escape').exists()


def test_explicit_model_directory_precedes_environment(tmp_path,monkeypatch):
    monkeypatch.setenv('H3_MODEL_DIR',str(tmp_path/'env'))
    assert assets.model_directory()==tmp_path/'env'
    assert assets.model_directory(tmp_path/'explicit')==tmp_path/'explicit'
