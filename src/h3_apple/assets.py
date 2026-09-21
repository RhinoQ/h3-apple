"""The single pinned Ref2VA model and managed native engine."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile

from .downloads import download
from .io import digest, write_json

SCHEMA = "h3-apple-model/v1"
RECIPE = dict(steps=4, graph_steps=5, video_shift=12.0, audio_shift=3.0, lora_scale=1.0)


def data_file(name):
    return json.loads((Path(__file__).parent / 'data' / name).read_text())


def model_directory(value=None):
    return Path(value or os.environ.get('H3_MODEL_DIR') or
                Path.home() / 'Models/h3-apple/ref2va').expanduser().resolve()


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def file_record(path):
    path = Path(path).resolve(strict=True)
    before = path.stat()
    checksum = digest(path)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError(f'File changed while checking: {path}')
    return dict(path=str(path), bytes=after.st_size, mtime_ns=after.st_mtime_ns, sha256=checksum)


def check_file(entry, *, verify=False):
    file = Path(entry['path'])
    stat = file.stat()
    if (stat.st_size, stat.st_mtime_ns) != (entry['bytes'], entry['mtime_ns']):
        raise ValueError(f'Model file changed; run h3 prepare in a new model directory: {file}')
    if verify and digest(file) != entry['sha256']:
        raise ValueError(f'Checksum differs: {file}')


def check_model(root):
    root = Path(root)
    config = json.loads((root / 'transformer/config.json').read_text())
    text = json.loads((root / 'text_encoder/config.json').read_text())
    meta = json.loads((root / 'model_index.json').read_text())
    if (config.get('_class_name') != 'MiniMaxH3DiTModel' or config.get('num_layers') != 50
            or config.get('quantization') != dict(bits=8, group_size=64)
            or text.get('quantization') != dict(bits=8, group_size=64)
            or meta.get('_minimax_h3', {}).get('partition') != 'ref2va'):
        raise ValueError('Expected the pinned H3 Ref2VA 8-bit model. Run h3 prepare.')
    for name in ('transformer', 'text_encoder', 'video_vae', 'audio_vae'):
        if not list((root / name).rglob('*.safetensors')):
            raise ValueError(f'Missing model weights: {name}')


def engine_paths():
    record = data_file('engine.json')
    cache = Path.home() / '.cache/h3-apple'
    return record, cache / 'engines' / record['sha256'], cache / 'downloads' / (record['sha256'] + '.zip')


def load_engine():
    record, directory, _ = engine_paths()
    for entry in record['files']:
        path = directory / entry['name']
        if not path.is_file() or path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
            raise ValueError('H3 engine is missing or changed. Run h3 prepare.')
    if not os.access(directory / 'h3-engine', os.X_OK):
        raise ValueError('H3 engine is not executable. Run h3 prepare.')
    return dict(binary=file_record(directory / 'h3-engine'),
                library=file_record(directory / 'libvpipe.0.dylib'),
                tested_interface_commit=record['commit'])


def ensure_engine(progress=None):
    record, directory, archive = engine_paths()
    if directory.exists():
        return load_engine()
    if archive.exists():
        if archive.stat().st_size != record['bytes'] or digest(archive) != record['sha256']:
            raise ValueError(f'Engine download cache changed: {archive}')
    else:
        if progress:
            progress(dict(phase='installing_engine'))
        download(record['url'], archive, record['bytes'], record['sha256'])
    directory.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.engine-', dir=directory.parent))
    try:
        with zipfile.ZipFile(archive) as z:
            if sorted(z.namelist()) != sorted(f['name'] for f in record['files']):
                raise ValueError('Unexpected engine archive members.')
            for entry in record['files']:
                name = entry['name']
                if Path(name).name != name or z.getinfo(name).file_size != entry['bytes']:
                    raise ValueError('Invalid engine archive path or size.')
                data = z.read(name)
                if hashlib.sha256(data).hexdigest() != entry['sha256']:
                    raise ValueError('Engine file checksum differs.')
                (temporary / name).write_bytes(data)
                (temporary / name).chmod(entry['mode'])
        temporary.rename(directory)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return load_engine()


def load_manifest(model_dir=None, *, verify=False):
    directory = model_directory(model_dir)
    path = directory / 'model.json'
    if not path.is_file():
        raise ValueError('H3 models are not prepared. Run h3 prepare once.')
    data = json.loads(path.read_text())
    expected_adapter = data_file('prepared-model.json')['adapter']
    if (data.get('schema') != SCHEMA or data.get('recipe') != RECIPE
            or data.get('adapter', {}).get('sha256') != expected_adapter['sha256']
            or data.get('identity') != identity({k: v for k, v in data.items() if k != 'identity'})):
        raise ValueError('Model manifest changed or is unsupported. Run h3 prepare in a new model directory.')
    for entry in [*data['files'], data['adapter']]:
        check_file(entry, verify=verify)
    check_model(data['native_model'])
    return dict(data, directory=str(directory))


def load_assets(model_dir=None, *, verify=False):
    return dict(load_manifest(model_dir, verify=verify), **load_engine())


def register_model(directory, *, provenance, records=None):
    """Commit a prepared directory only after all weights and the adapter are checked."""
    directory = Path(directory)
    check_model(directory / 'model')
    entries = records or [file_record(p) for p in sorted((directory / 'model').rglob('*')) if p.is_file()]
    adapter = file_record(directory / 'adapter.safetensors')
    if adapter['sha256'] != data_file('prepared-model.json')['adapter']['sha256']:
        raise ValueError('The Ref2VA adapter checksum differs.')
    manifest = dict(schema=SCHEMA, native_model=str(directory / 'model'), files=entries,
                    adapter=adapter, recipe=RECIPE, provenance=provenance)
    manifest['identity'] = identity(manifest)
    write_json(directory / 'model.json', manifest)
    return manifest
