from contextlib import contextmanager
import hashlib
import http.server
import json
from pathlib import Path
import threading

import pytest
from h3_apple import preparation as prep
from h3_apple.downloads import download, partial_path


@pytest.fixture(autouse=True)
def local_network_only(monkeypatch):
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")


@contextmanager
def server(payload, ranges=True):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            offset=int(self.headers.get('Range','bytes=0-').split('=')[1].split('-')[0])
            self.send_response(206 if offset and ranges else 200)
            if offset and ranges:self.send_header('Content-Range',f'bytes {offset}-{len(payload)-1}/{len(payload)}')
            self.end_headers();self.wfile.write(payload[offset:] if ranges else payload)
        def log_message(self,*args):pass
    httpd=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
    try:yield f'http://127.0.0.1:{httpd.server_port}/model'
    finally:httpd.shutdown();httpd.server_close();thread.join()


def test_resumed_download_is_complete_and_verified(tmp_path):
    content=b'complete model data'*1000;checksum=hashlib.sha256(content).hexdigest();destination=tmp_path/'file'
    partial_path(destination,checksum).write_bytes(content[:123])
    with server(content) as url:download(url,destination,len(content),checksum)
    assert destination.read_bytes()==content
    assert not partial_path(destination,checksum).exists()


def test_resume_never_silently_restarts_large_download(tmp_path):
    content=b'abcdef';checksum=hashlib.sha256(content).hexdigest();destination=tmp_path/'file'
    partial_path(destination,checksum).write_bytes(content[:2])
    with server(content,ranges=False) as url:
        with pytest.raises(ValueError,match='resume'):download(url,destination,len(content),checksum)
    assert not destination.exists()
    assert partial_path(destination,checksum).read_bytes()==content[:2]


def test_bad_download_is_not_published(tmp_path):
    content=b'wrong';destination=tmp_path/'file'
    with server(content) as url:
        with pytest.raises(ValueError,match='corrupt'):download(url,destination,len(content),'0'*64)
    assert not destination.exists()


def test_large_download_requires_consent_before_network_or_engine(monkeypatch):
    monkeypatch.setattr(prep,'ensure_engine',lambda *_:pytest.fail('must not download engine'))
    with pytest.raises(ValueError,match='20 GB'):
        prep.prepare(dict(download_bytes=prep.LIMIT+1))


def test_source_plan_is_ref2va_only_and_pinned():
    manifest=prep.data_file('model-sources.json')
    for entry in manifest['sources']:
        assert len(entry['sha256'])==64 and len(entry['revision'])==40
        assert not entry['filename'].startswith('FL2VA/')
    assert manifest['recipe']==prep.RECIPE


def test_conversion_keeps_the_accepted_quantization_recipe(tmp_path):
    graph=prep.quantization_graph(tmp_path/'source',tmp_path/'work')
    assert [s['config']['target'] for s in graph['stages']]==['dit','text_encoder']
    for stage in graph['stages']:
        assert stage['config']['bits']==8 and stage['config']['group_size']==64
        assert stage['config']['quant_modulation'] is True
        assert stage['config']['skip_existing'] is False


def test_reuse_changed_between_plan_and_preparation_is_rejected(tmp_path):
    source=tmp_path/'source';source.write_bytes(b'original')
    record=prep.file_record(source);source.write_bytes(b'mutated')
    spec=dict(cache_dir=str(tmp_path/'cache'),groups=[dict(source=record)])
    with pytest.raises(ValueError,match='changed'):
        prep.materialize(spec,lambda _:None)


def test_materialize_owns_links_and_checks_each_source(tmp_path):
    source=tmp_path/'source';source.write_bytes(b'content');record=prep.file_record(source)
    entry=dict(repo='example/model',revision='a'*40,filename='Ref2VA/transformer/model.safetensors')
    spec=dict(cache_dir=str(tmp_path/'cache'),groups=[dict(source=record,sha256=record['sha256'],files=[entry])])
    cache=prep.materialize(spec,lambda _:None)
    result=prep.cache_path(cache,entry);source.unlink()
    assert result.read_bytes()==b'content'
