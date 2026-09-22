"""Prepare the one Ref2VA model from pinned sources or a verified local copy."""

from collections import defaultdict
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from urllib.parse import quote

from .assets import (SCHEMA, RECIPE, check_file, check_model, data_file, engine_paths,
                     ensure_engine, file_record, identity, load_assets, load_manifest,
                     model_directory, register_model)
from .downloads import download, partial_path
from .host import check_machine, device_lock, snapshot
from .io import digest, write_json

LIMIT = 20_000_000_000
RESERVE = 2 * 1024**3


def ensure_ready(model_dir=None, *, allow_large_download=False, progress=None, request=None):
    """Shared first-run setup for the CLI and Python API; never prompt in Python."""
    from .api import DownloadApprovalRequired
    from .media import check_runtime

    if type(allow_large_download) is not bool:
        raise ValueError('allow_large_download must be a boolean.')
    progress = progress or (lambda event: None)
    check_machine(snapshot(), request)
    spec = plan(model_dir, progress=progress)
    if spec['download_bytes'] > LIMIT and not allow_large_download:
        raise DownloadApprovalRequired(spec)
    # Check the Conda tools, libraries and codecs before any large download.
    check_runtime()
    if spec['status'] != 'ready' or spec['download_bytes']:
        progress(dict(spec, phase='model_plan'))
    return prepare(spec, allow_large_download=allow_large_download, progress=progress)


def cache_path(cache, entry):
    return cache / entry['repo'].replace('/', '--') / entry['revision'] / entry['filename']


def candidates(entry, cache, reuse_dirs):
    yield cache_path(cache, entry)
    name = Path(entry['filename'])
    for root in reuse_dirs:
        root = Path(root).expanduser().resolve()
        if root.is_file():
            yield root
        yield root / name
        if name.parts[0] == 'Ref2VA':
            yield root / Path(*name.parts[1:])
            yield root / 'FL2VA' / Path(*name.parts[1:])
        yield root / name.name
    hub = Path(os.environ.get('HF_HUB_CACHE') or Path.home() / '.cache/huggingface/hub')
    yield hub / ('models--' + entry['repo'].replace('/', '--')) / 'snapshots' / entry['revision'] / name


def reusable_model(reuse_dirs, progress):
    roots = [Path(p).expanduser().resolve() for p in reuse_dirs]
    # Upgrade existing h3-apple installations without asking users to locate engine files.
    if not roots:
        roots += sorted(p.parent for p in (Path.home() / 'Models').glob('h3-apple*/vpipe.json'))
    for root in dict.fromkeys(roots):
        if (root / 'model.json').is_file():
            data = load_manifest(root, verify=True)
            return dict(model=data['native_model'], files=data['files'], adapter=data['adapter'])
        old = root / 'vpipe.json'
        if not old.is_file():
            continue
        old = json.loads(old.read_text())
        if old.get('partition') != 'ref2va' or old.get('recipe') != RECIPE:
            continue
        model = Path(old['native_model'])
        expected = data_file('prepared-model.json')
        records = []
        for entry in expected['files']:
            path = model / entry['path']
            if not path.is_file() or path.stat().st_size != entry['bytes']:
                break
            progress(dict(phase='checking_local_models', file=entry['path']))
            record = file_record(path)
            if record['sha256'] != entry['sha256']:
                break
            records.append(record)
        if len(records) != len(expected['files']):
            continue
        adapter = file_record(old['adapter']['path'])
        if adapter['sha256'] != expected['adapter']['sha256']:
            continue
        check_model(model)
        return dict(model=str(model), files=records, adapter=adapter)
    return None


def plan(model_dir=None, reuse_dirs=(), progress=None):
    progress = progress or (lambda event: None)
    directory = model_directory(model_dir)
    engine, engine_dir, archive = engine_paths()
    engine_download = 0 if engine_dir.exists() or archive.is_file() else engine['bytes']
    if (directory / 'model.json').is_file():
        data = load_manifest(directory)
        return dict(status='ready', directory=str(directory), identity=data['identity'],
                    download_bytes=engine_download, additional_disk_bytes=engine['bytes'] * 5)
    if directory.exists() and any(directory.iterdir()):
        raise FileExistsError(f'Model directory is not empty: {directory}')
    directory.parent.mkdir(parents=True, exist_ok=True)
    prepared = reusable_model(reuse_dirs, progress)
    if prepared:
        copies = sum(e['bytes'] for e in [*prepared['files'], prepared['adapter']]
                     if Path(e['path']).stat().st_dev != directory.parent.stat().st_dev)
        return dict(status='reuse_prepared', directory=str(directory), prepared=prepared,
                    download_bytes=engine_download, additional_disk_bytes=copies + RESERVE)
    cache = directory.parent / '.sources'
    cache.mkdir(parents=True, exist_ok=True)
    manifest = data_file('model-sources.json')
    by_hash = defaultdict(list)
    for entry in manifest['sources']:
        by_hash[entry['sha256']].append(entry)
    groups = []
    downloads, copies = engine_download, 0
    for checksum, entries in by_hash.items():
        expected = entries[0]['bytes']
        source = None
        checked = set()
        for entry in entries:
            for path in candidates(entry, cache, reuse_dirs):
                if not path.is_file() or path.stat().st_size != expected:
                    continue
                path = path.resolve()
                if path in checked:
                    continue
                checked.add(path)
                progress(dict(phase='checking_local_models', file=str(path)))
                record = file_record(path)
                if record['sha256'] == checksum:
                    source = record
                    break
            if source:
                break
        destination = cache_path(cache, entries[0])
        part = partial_path(destination, checksum)
        partial = part.stat().st_size if part.is_file() else 0
        if partial > expected:
            raise ValueError(f'Oversized partial download: {part}')
        if source is None:
            downloads += expected - partial
        elif Path(source['path']).stat().st_dev != cache.stat().st_dev:
            copies += expected
        groups.append(dict(sha256=checksum, bytes=expected, source=source, files=entries))
    return dict(status='preparation_required', directory=str(directory), cache_dir=str(cache),
                download_bytes=downloads, additional_disk_bytes=downloads + copies +
                    manifest['converted_peak_bytes'] + RESERVE,
                retained_source_bytes=sum(g['bytes'] for g in groups), groups=groups)


def copy_file(source, destination, checksum):
    source, destination = Path(source), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if digest(destination) != checksum:
            raise FileExistsError(f'Different cached file: {destination}')
        return
    if source.stat().st_dev == destination.parent.stat().st_dev:
        os.link(source, destination)
    else:
        shutil.copy2(source, destination)
        if digest(destination) != checksum:
            raise ValueError(f'Copied file checksum differs: {destination}')


def materialize(spec, progress):
    cache = Path(spec['cache_dir'])
    for group in spec['groups']:
        if group['source']:
            check_file(group['source'])
            source = Path(group['source']['path'])
        else:
            entry = group['files'][0]
            url = f"https://huggingface.co/{entry['repo']}/resolve/{entry['revision']}/{quote(entry['filename'], safe='/')}"
            progress(dict(phase='downloading_models', file=entry['filename']))
            source = download(url, cache_path(cache, entry), group['bytes'], group['sha256'])
        for entry in group['files']:
            destination = cache_path(cache, entry)
            if source.resolve() != destination.resolve():
                copy_file(source, destination, group['sha256'])
            source = destination
    return cache


def quantization_graph(source, work):
    stages = []
    for index, (target, source_path, name) in enumerate((
            ('dit', source, 'local/ref2va-dit'),
            ('text_encoder', work / 'models/local/ref2va-dit', 'local/ref2va'))):
        stages.append(dict(id=f'quant-{index}', type='model-quantize',
            iports=[] if index == 0 else [dict(src='quant-0', oport=0)],
            config=dict(src_model=str(source_path), output_name=name, target=target,
                        bits=8, group_size=64, quant_modulation=True, skip_existing=False)))
    return dict(id='h3-apple-prepare', stages=stages)


def quantize(source, work, engine, progress):
    from .engine import runtime_environment
    graph = work / 'prepare.vpipeline'
    write_json(graph, quantization_graph(source, work))
    (work / 'db').mkdir()
    write_json(work / 'session.json', dict(db=dict(path=str(work / 'db'))))
    command = [engine['binary']['path'], '--config', str(work / 'session.json'), '--launch', str(graph)]
    progress(dict(phase='preparing_models', file=str(work / 'preparation.log')))
    initial, started = snapshot(), time.monotonic()
    with (work / 'preparation.log').open('x') as log:
        child = subprocess.Popen(command, cwd=work, env=runtime_environment(engine),
                                 stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True)
        try:
            while child.poll() is None:
                if time.monotonic() - started > 3600:
                    raise TimeoutError(f'Model preparation exceeded one hour; see {work}')
                current = snapshot()
                if current['swap_bytes'] - initial['swap_bytes'] > 2 * 1024**3:
                    raise RuntimeError('Model preparation stopped: swap grew more than 2 GiB.')
                if current['thermal']['state'] in ('serious', 'critical'):
                    raise RuntimeError('Model preparation stopped: serious thermal pressure.')
                if shutil.disk_usage(work).free < RESERVE:
                    raise OSError('Model preparation stopped: insufficient free disk.')
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
            if child.returncode:
                raise RuntimeError(f'Model preparation failed; see {work / "preparation.log"}')
        finally:
            from .process import _stop
            _stop(child)
    return work / 'models/local/ref2va'


def prepare(spec, *, allow_large_download=False, progress=None):
    progress = progress or (lambda event: None)
    if spec['download_bytes'] > LIMIT and not allow_large_download:
        raise ValueError('Downloads exceed 20 GB. Review h3 prepare --plan, then confirm with '
                         'h3 prepare --allow-large-download.')
    check_machine(snapshot())
    directory = Path(spec['directory'])
    directory.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(directory.parent).free < spec['additional_disk_bytes']:
        raise OSError('Insufficient free disk for preparation; see h3 prepare --plan.')
    with device_lock():
        engine = ensure_engine(progress)
        if spec['status'] == 'ready' or (directory / 'model.json').exists():
            return load_assets(directory)
        if directory.exists():
            raise FileExistsError(f'Choose a new model directory: {directory}')
        work = Path(tempfile.mkdtemp(prefix='.h3-prepare-', dir=directory.parent))
        write_json(work / 'plan.json', spec)
        staging = work / 'output'
        staging.mkdir()
        records = None
        if spec['status'] == 'reuse_prepared':
            prepared = spec['prepared']
            model = Path(prepared['model'])
            records = []
            for entry in prepared['files']:
                check_file(entry)
                relative = Path(entry['path']).relative_to(model)
                target = staging / 'model' / relative
                copy_file(entry['path'], target, entry['sha256'])
                records.append(dict(entry, path=str(target), mtime_ns=target.stat().st_mtime_ns))
            check_file(prepared['adapter'])
            copy_file(prepared['adapter']['path'], staging / 'adapter.safetensors', prepared['adapter']['sha256'])
            provenance = dict(kind='verified_local_reuse', model=str(model), download_bytes=spec['download_bytes'])
        else:
            cache = materialize(spec, progress)
            entries = data_file('model-sources.json')['sources']
            base = next(e for e in entries if e['filename'] == 'Ref2VA/model_index.json')
            source = cache_path(cache, base).parent
            model = quantize(source, work, engine, progress)
            model.rename(staging / 'model')
            adapter = next(e for e in entries if e['repo'] == 'silveroxides/MiniMax-H3_tests')
            copy_file(cache_path(cache, adapter), staging / 'adapter.safetensors', adapter['sha256'])
            provenance = dict(kind='source_preparation', sources=entries, engine=engine,
                              graph_sha256=digest(work / 'prepare.vpipeline'),
                              log_sha256=digest(work / 'preparation.log'), download_bytes=spec['download_bytes'])
        # Retain the upstream model license with the prepared model.
        license_path = Path(__file__).parent / 'data/MiniMax-H3-LICENSE.txt'
        shutil.copy2(license_path, staging / 'LICENSE.txt')
        manifest = register_model(staging, provenance=provenance, records=records)
        # Rewrite only paths into our staging directory before the atomic move.
        manifest['native_model'] = str(directory / 'model')
        for entry in [*manifest['files'], manifest['adapter']]:
            entry['path'] = str(directory / Path(entry['path']).relative_to(staging))
        manifest['identity'] = identity({k:v for k,v in manifest.items() if k != 'identity'})
        write_json(staging / 'model.json', manifest)
        staging.rename(directory)
        result = load_assets(directory)
        write_json(work / 'result.json', dict(directory=str(directory), identity=result['identity']))
        # Only our successful intermediate quantization links are removed; source cache and logs stay.
        if (work / 'models').exists():
            shutil.rmtree(work / 'models')
        return result
