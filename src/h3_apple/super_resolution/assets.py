"""Checksum-pinned VOSR models; preparation reuses local files when requested."""

import errno
import json
import os
from pathlib import Path
import shutil

from ..downloads import download, partial_path
from ..host import device_lock
from ..io import digest


def manifest():
    return json.loads((Path(__file__).parents[1] / 'data/vosr-model-sources.json').read_text())


def verified(path, item):
    return path.is_file() and path.stat().st_size == item['bytes'] and digest(path) == item['sha256']


def plan(model_dir=None, reuse_dirs=()):
    root = Path(model_dir or os.environ.get('H3_VOSR_MODEL_DIR', Path.home() / 'Models/h3-apple/vosr')).expanduser().resolve()
    files = []
    download_bytes = disk = 0
    for item in manifest()['files']:
        target = root / item['path']
        source = None
        if os.path.lexists(target):
            if not verified(target, item):
                raise ValueError(f'VOSR model checksum mismatch: {target}. Move it aside before preparing again.')
            source = target
        else:
            for directory in reuse_dirs:
                candidate = Path(directory).expanduser().resolve() / item['path']
                if verified(candidate, item):
                    source = candidate
                    break
        partial = partial_path(target, item['sha256'])
        offset = partial.stat().st_size if partial.is_file() else 0
        if offset > item['bytes']:
            raise ValueError(f'Oversized partial VOSR download: {partial}')
        if source is None:
            download_bytes += item['bytes'] - offset
        if source != target:
            disk += item['bytes'] - (offset if source is None else 0)
        files.append(dict(item, reuse=str(source) if source else None))
    return dict(directory=str(root), recipe=manifest()['recipe'], files=files,
                download_bytes=download_bytes, additional_disk_bytes=disk)


def prepare(model_dir=None, reuse_dirs=(), *, on_progress=None):
    with device_lock():
        spec = plan(model_dir, reuse_dirs)
        if spec['download_bytes'] > 20_000_000_000:
            raise ValueError('Unexpected VOSR download above 20 GB; inspect the pinned manifest.')
        root = Path(spec['directory'])
        root.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(root).free < spec['additional_disk_bytes'] + 2 * 1024**3:
            raise OSError('Insufficient disk for VOSR model preparation.')
        for item in spec['files']:
            target = root / item['path']
            source = Path(item['reuse']) if item['reuse'] else None
            if source == target:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if on_progress:
                on_progress(dict(phase='models', message='Reusing' if source else 'Downloading', file=item['path']))
            if source is None:
                download(item['url'], target, item['bytes'], item['sha256'])
            else:
                try:
                    os.link(source, target)
                except OSError as error:
                    if error.errno != errno.EXDEV:
                        raise
                    with source.open('rb') as inp, target.open('xb') as out:
                        shutil.copyfileobj(inp, out)
                if not verified(target, item):
                    raise ValueError(f'VOSR reuse source changed: {target}')
        return dict(directory=str(root), recipe=spec['recipe'], model_revision=manifest()['model_revision'],
                    files=[{k: item[k] for k in ('path', 'bytes', 'sha256')} for item in spec['files']])
