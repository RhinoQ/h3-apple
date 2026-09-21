"""Package the pinned native build; run with the project's Conda Python."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

p = argparse.ArgumentParser()
p.add_argument('--build-dir', type=Path, required=True)
p.add_argument('--source-dir', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
entries = {
    'h3-engine': (a.build_dir / 'apps/vpipe/vpipe', 0o755),
    'libvpipe.0.dylib': (a.build_dir / 'libvpipe.0.1.dylib', 0o755),
    'LICENSE.txt': (a.source_dir / 'LICENSE', 0o644),
    'NOTICE.txt': (a.source_dir / 'NOTICE', 0o644),
    'THIRD_PARTY_LICENSES.txt': (a.source_dir / 'THIRD_PARTY_LICENSES.md', 0o644),
}
a.output.parent.mkdir(parents=True, exist_ok=True)
files = []
with zipfile.ZipFile(a.output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name, (source, mode) in sorted(entries.items()):
        data = source.read_bytes()
        info = zipfile.ZipInfo(name, (2026, 9, 21, 0, 0, 0))
        info.create_system = 3
        info.external_attr = (0o100000 | mode) << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, data)
        files.append(dict(name=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), mode=mode))
record = dict(schema='h3-apple-engine/v1', upstream='https://github.com/tgo-app-dev/vpipe',
    commit='f34e2cc3a3adae759eea254419f436f5b7800057',
    url='https://github.com/RhinoQ/h3-apple/releases/download/v0.4.0/' + a.output.name,
    bytes=a.output.stat().st_size, sha256=hashlib.sha256(a.output.read_bytes()).hexdigest(), files=files)
(root / 'src/h3_apple/data/engine.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(dict(archive=str(a.output), bytes=record['bytes'], sha256=record['sha256'])))
