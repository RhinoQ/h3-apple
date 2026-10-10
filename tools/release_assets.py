"""Verify release artifacts and assemble the GitHub upload directory."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tomllib
from urllib.parse import urljoin
import re
import zipfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def assemble(dist, engine, output, tag):
    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root / 'pyproject.toml').read_text())['project']['version']
    tree = ast.parse((root / 'src/h3_apple/__init__.py').read_text())
    api_version = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == '__version__' for t in n.targets))
    if tag != 'v' + version or api_version != version:
        raise ValueError('Tag and package versions differ')
    spec = json.loads((root / 'src/h3_apple/data/engine.json').read_text())
    engine_name = 'h3-apple-engine-macos-arm64.zip'
    expected_url = f'https://github.com/RhinoQ/h3-apple/releases/download/{tag}/{engine_name}'
    if spec['url'] != expected_url:
        raise ValueError('Engine URL does not target this release')
    data = engine.read_bytes()
    if len(data) != spec['bytes'] or sha(data) != spec['sha256']:
        raise ValueError('Engine archive checksum differs')
    with zipfile.ZipFile(engine) as archive:
        if sorted(archive.namelist()) != sorted(f['name'] for f in spec['files']):
            raise ValueError('Engine member list differs')
        for entry in spec['files']:
            member = archive.read(entry['name'])
            if len(member) != entry['bytes'] or sha(member) != entry['sha256']:
                raise ValueError('Engine member checksum differs: ' + entry['name'])
    wheel = dist / f'h3_apple-{version}-py3-none-any.whl'
    sdist = dist / f'h3_apple-{version}.tar.gz'
    source = {str(p.relative_to(root / 'src')): p.read_bytes()
              for p in sorted((root / 'src/h3_apple').rglob('*'))
              if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    with zipfile.ZipFile(wheel) as archive:
        actual = {name: archive.read(name) for name in archive.namelist() if name.startswith('h3_apple/')}
        if actual != source:
            raise ValueError('Wheel does not match the source tree')
    with tarfile.open(sdist) as archive:
        prefix = f'h3_apple-{version}/src/'
        actual = {m.name[len(prefix):]: archive.extractfile(m).read() for m in archive.getmembers()
                  if m.isfile() and m.name.startswith(prefix + 'h3_apple/')}
        if actual != source:
            raise ValueError('Source distribution does not match the source tree')
    uploads = output / 'assets'
    uploads.mkdir(parents=True, exist_ok=False)
    for path in (wheel, sdist):
        shutil.copyfile(path, uploads / path.name)
    shutil.copyfile(engine, uploads / engine_name)
    skill = root / 'skills/h3-apple-ref2va-prompting'
    with zipfile.ZipFile(uploads / 'h3-apple-ref2va-prompting.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(skill.rglob('*')):
            if path.is_file():
                archive.write(path, str(path.relative_to(skill.parent)))
    commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    hashes = {k.removeprefix('h3_apple/'): sha(v) for k, v in source.items()
              if Path(k).suffix in ('.py', '.metal', '.npz', '.json', '.txt')}
    entries = [{'name': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
               for p in sorted(uploads.iterdir())]
    manifest = dict(schema='h3-apple-release/v1', tag=tag, source_commit=commit,
                    runtime_sha256=sha(json.dumps(hashes, sort_keys=True).encode()),
                    runtime_files=len(source), engine_sha256=spec['sha256'], assets=entries)
    (uploads / 'release-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (uploads / 'SHA256SUMS').write_text(''.join(f'{sha(p.read_bytes())}  {p.name}\n'
                                             for p in sorted(uploads.iterdir())))
    note_path = root / f'docs/releases/{version}.md'
    base = f'https://github.com/RhinoQ/h3-apple/blob/{tag}/docs/releases/{version}.md'
    notes = re.sub(r'(\]\()([^\s)]+)(\))', lambda m: m[1] + urljoin(base, m[2]) + m[3], note_path.read_text())
    (output / 'release-notes.md').write_text(notes)
    print(json.dumps(manifest))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path, required=True)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    assemble(args.dist, args.engine, args.output, args.tag)
