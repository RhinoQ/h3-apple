"""Publication must bind both distributions and the native engine to source."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import zipfile

import pytest


@pytest.fixture
def release(tmp_path):
    script = tmp_path / 'tools/release_assets.py'
    script.parent.mkdir()
    shutil.copyfile(Path(__file__).parents[1] / 'tools/release_assets.py', script)
    def write(name, data):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
        return path
    write('pyproject.toml', '[project]\nversion = "0.7.0"\n')
    write('src/h3_apple/__init__.py', '__version__ = "0.7.0"\n')
    engine = tmp_path / 'engine.zip'
    payload = b'synthetic native binary'
    with zipfile.ZipFile(engine, 'w') as z:
        z.writestr('h3-engine', payload)
    sha = lambda data: hashlib.sha256(data).hexdigest()
    write('src/h3_apple/data/engine.json', json.dumps(dict(
        url='https://github.com/RhinoQ/h3-apple/releases/download/v0.7.0/h3-apple-engine-macos-arm64.zip',
        bytes=engine.stat().st_size, sha256=sha(engine.read_bytes()),
        files=[dict(name='h3-engine', bytes=len(payload), sha256=sha(payload))])))
    write('skills/h3-apple-ref2va-prompting/SKILL.md', 'Test skill\n')
    write('docs/releases/0.7.0.md', '[Install](../install.md)\n')
    dist = tmp_path / 'dist'; dist.mkdir()
    with zipfile.ZipFile(dist / 'h3_apple-0.7.0-py3-none-any.whl', 'w') as z, tarfile.open(dist / 'h3_apple-0.7.0.tar.gz', 'w:gz') as t:
        for p in sorted((tmp_path / 'src').rglob('*')):
            if p.is_file():
                name = str(p.relative_to(tmp_path / 'src'))
                z.writestr(name, p.read_bytes())
                entry = tarfile.TarInfo('h3_apple-0.7.0/src/' + name)
                entry.size = p.stat().st_size
                t.addfile(entry, io.BytesIO(p.read_bytes()))
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    subprocess.run(['git', '-C', str(tmp_path), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                    'commit', '--allow-empty', '-qm', 'fixture'], check=True)
    return tmp_path, [sys.executable, str(script), '--dist', str(dist), '--engine', str(engine),
                      '--output', str(tmp_path / 'release'), '--tag', 'v0.7.0']


def test_verified_assets_have_checksums_and_versioned_links(release):
    root, command = release
    subprocess.run(command, check=True, capture_output=True)
    for line in (root / 'release/assets/SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ')
        assert hashlib.sha256((root / 'release/assets' / name).read_bytes()).hexdigest() == digest
    assert '/blob/v0.7.0/docs/install.md' in (root / 'release/release-notes.md').read_text()


@pytest.mark.parametrize('corruption', ['engine', 'wheel', 'source'])
def test_mismatched_artifacts_never_reach_upload_directory(release, corruption):
    root, command = release
    if corruption == 'engine':
        (root / 'engine.zip').write_bytes(b'wrong engine')
    elif corruption == 'wheel':
        with zipfile.ZipFile(root / 'dist/h3_apple-0.7.0-py3-none-any.whl', 'a') as z:
            z.writestr('h3_apple/unreviewed.py', 'extra code')
    else:
        (root / 'src/h3_apple/__init__.py').write_text('__version__ = "0.7.0"\n# changed\n')
    result = subprocess.run(command, capture_output=True)
    assert result.returncode != 0
    assert not (root / 'release/assets').exists()
