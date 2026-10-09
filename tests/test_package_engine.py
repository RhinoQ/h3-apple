"""Release metadata must never invent a download destination."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.mark.parametrize('publication', [[], ['--url', 'relative.zip'], ['--url', 'http://example.com/engine.zip']])
def test_requires_explicit_publication_destination(tmp_path, publication):
    script = Path(__file__).parents[1] / 'tools/package_engine.py'
    result = subprocess.run([sys.executable, str(script), '--build-dir', str(tmp_path),
                             '--source-dir', str(tmp_path), '--output', str(tmp_path / 'engine.zip'),
                             *publication], capture_output=True, text=True)
    assert result.returncode != 0
    assert not (tmp_path / 'engine.zip').exists()


def test_archive_manifest_uses_supplied_url(tmp_path):
    script = tmp_path / 'tools/package_engine.py'
    script.parent.mkdir()
    shutil.copyfile(Path(__file__).parents[1] / 'tools/package_engine.py', script)
    manifest = tmp_path / 'src/h3_apple/data/engine.json'
    manifest.parent.mkdir(parents=True)
    build = tmp_path / 'build'
    source = tmp_path / 'native'
    for root, names in ((build, ('apps/vpipe/vpipe', 'libvpipe.0.1.dylib')),
                        (source, ('LICENSE', 'NOTICE', 'THIRD_PARTY_LICENSES.md'))):
        for name in names:
            file = root / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b'synthetic packaging fixture')
    url = 'https://example.com/releases/v0.7.0/engine.zip'
    subprocess.run([sys.executable, str(script), '--build-dir', str(build), '--source-dir', str(source),
                    '--output', str(tmp_path / 'engine.zip'), '--url', url], check=True, capture_output=True)
    record = json.loads(manifest.read_text())
    assert record['url'] == url
    assert len(record['files']) == 5
