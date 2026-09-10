import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.request import ProxyHandler, build_opener

import pytest

from h3_apple import preparation as prep


@pytest.fixture
def source_manifest(monkeypatch):
    payload = b"one reusable source"
    sha = hashlib.sha256(payload).hexdigest()
    data = {"sources": [dict(repo="example/h3", revision="1" * 40, filename=name,
                            bytes=len(payload), sha256=sha) for name in
                        ("FL2VA/text_encoder/model.safetensors", "FL2VA/tokenizer/copy.json")],
            "converted_sizes": {"dit": 8, "video_vae": 4}}
    monkeypatch.setattr(prep, "source_manifest", lambda: data)
    return data, payload


def test_local_reuse_deduplicates_content_and_survives_source_removal(tmp_path, source_manifest):
    manifest, payload = source_manifest
    source = tmp_path / "existing/text_encoder/model.safetensors"
    source.parent.mkdir(parents=True)
    source.write_bytes(payload)
    result = prep.plan(tmp_path / "models", reuse_dirs=[source.parents[1]])
    assert result["download_bytes"] == 0
    assert len(result["groups"]) == 1
    assert len(result["groups"][0]["files"]) == 2
    cache = prep.materialize(result, lambda event: None)
    paths = [prep.cache_path(cache, item) for item in manifest["sources"]]
    source.unlink()
    assert all(path.read_bytes() == payload for path in paths)
    assert paths[0].stat().st_ino == paths[1].stat().st_ino


def test_mismatched_cached_source_fails_before_download(tmp_path, source_manifest):
    manifest, _ = source_manifest
    cache = tmp_path / "cache"
    file = prep.cache_path(cache, manifest["sources"][0])
    file.parent.mkdir(parents=True)
    file.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="Cached model size changed"):
        prep.plan(tmp_path / "models", cache)


def test_local_source_change_after_plan_is_rejected(tmp_path, source_manifest):
    _, payload = source_manifest
    source = tmp_path / "existing/text_encoder/model.safetensors"
    source.parent.mkdir(parents=True)
    source.write_bytes(payload)
    result = prep.plan(tmp_path / "models", reuse_dirs=[source.parents[1]])
    source.write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed after planning"):
        prep.materialize(result, lambda event: None)


def test_large_download_requires_explicit_confirmation(tmp_path, monkeypatch, source_manifest):
    manifest, _ = source_manifest
    for item in manifest["sources"]:
        item["bytes"] = prep.LIMIT + 1
    monkeypatch.setattr(prep, "check_machine", lambda value: None)
    monkeypatch.setattr(prep, "snapshot", lambda: {})
    monkeypatch.setattr(prep, "materialize", lambda *args: pytest.fail("Download must not start"))
    with pytest.raises(ValueError, match="allow-large-download"):
        prep.prepare(tmp_path / "models")


@pytest.fixture
def http_source(monkeypatch):
    # Keep these local protocol tests independent of the host's HTTP proxy.
    monkeypatch.setattr(prep, "urlopen", build_opener(ProxyHandler({})).open)
    payload = b"verified bytes" * 300
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            value = self.headers.get("Range")
            requests.append(value)
            start = int(value.split("=")[1].split("-")[0]) if value and self.path != "/ignore" else 0
            content = payload[start:] if self.path != "/extra" else payload + b"extra"
            self.send_response(206 if start else 200)
            self.send_header("Content-Length", str(len(content)))
            if start:
                self.send_header("Content-Range", f"bytes {start}-{len(payload)-1}/{len(payload)}")
            self.end_headers()
            self.wfile.write(content)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", payload, requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize("partial_bytes", [0, 73])
def test_verified_resumable_download(tmp_path, http_source, partial_bytes):
    url, payload, requests = http_source
    sha = hashlib.sha256(payload).hexdigest()
    destination = tmp_path / "model"
    part = prep.partial_path(destination, sha)
    part.write_bytes(payload[:partial_bytes])
    assert prep.download(url, destination, len(payload), sha) == destination
    assert destination.read_bytes() == payload
    assert not part.exists()
    assert requests == ([f"bytes={partial_bytes}-"] if partial_bytes else [None])


def test_server_cannot_silently_increase_resume_budget(tmp_path, http_source):
    url, payload, _ = http_source
    sha = hashlib.sha256(payload).hexdigest()
    destination = tmp_path / "model"
    part = prep.partial_path(destination, sha)
    part.write_bytes(payload[:100])
    with pytest.raises(ValueError, match="did not honor download resume"):
        prep.download(url + "/ignore", destination, len(payload), sha)
    assert part.read_bytes() == payload[:100]
    assert not destination.exists()


def test_download_rejects_wrong_hash_and_retains_failure(tmp_path, http_source):
    url, payload, _ = http_source
    destination = tmp_path / "model"
    with pytest.raises(ValueError, match="corrupt download"):
        prep.download(url, destination, len(payload), "f" * 64)
    assert not destination.exists()
    assert prep.partial_path(destination, "f" * 64).read_bytes() == payload


def test_download_rejects_oversized_response(tmp_path, http_source):
    url, payload, _ = http_source
    with pytest.raises(ValueError, match="exceeds the pinned source size"):
        prep.download(url + "/extra", tmp_path / "model", len(payload), hashlib.sha256(payload).hexdigest())


def test_plan_counts_only_missing_range(tmp_path, source_manifest):
    manifest, payload = source_manifest
    cache = tmp_path / "cache"
    dest = prep.cache_path(cache, manifest["sources"][0])
    dest.parent.mkdir(parents=True)
    prep.partial_path(dest, manifest["sources"][0]["sha256"]).write_bytes(payload[:5])
    result = prep.plan(tmp_path / "model", cache)
    assert result["download_bytes"] == len(payload) - 5


def test_import_source_options_require_complete_pair():
    from h3_apple.cli import main
    assert main(["models", "prepare", "--checkpoint", "/not/used"]) == 1
