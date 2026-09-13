"""Protect the association between an output, its resolution and its command."""
import hashlib
import json
from pathlib import Path

import build


def write_state(path, run):
    path.write_text(json.dumps(dict(cases=[run])))
    return path


def test_new_attempt_supersedes_status_without_discarding_old_video(tmp_path):
    old_dir = tmp_path / 'old'; old_dir.mkdir()
    (old_dir / 'output.run.json').write_text(json.dumps(dict(video_sha256='original')))
    first = write_state(tmp_path / 'first.json', dict(number=1, status='generated', directory=str(old_dir)))
    second = write_state(tmp_path / 'second.json', dict(number=1, status='running', resolution_policy=dict(resolution='768p')))
    runs, completed = build.merge_states([first, second])
    assert runs[1]['status'] == 'running'
    assert runs[1]['resolution_policy']['resolution'] == '768p'
    assert completed[1]['original']['directory'] == str(old_dir)


def test_new_resolution_never_relabels_an_existing_576p_video(tmp_path):
    root = tmp_path / 'site'; (root / 'media').mkdir(parents=True)
    (root / 'media/01-output.mp4').write_bytes(b'original 576p')
    (root / 'media/01-poster.jpg').write_bytes(b'old poster')
    run = tmp_path / 'run'; run.mkdir()
    data = b'new native 768p'; (run / 'output.mp4').write_bytes(data)
    checksum = hashlib.sha256(data).hexdigest()
    stem = f'01-768p-{checksum[:12]}'
    (root / f'media/{stem}-poster.jpg').write_bytes(b'new poster')
    media = build.export_media(root, run, 1, dict(video_sha256=checksum, request=dict(resolution='768p')))
    assert media['video'] == f'media/{stem}-output.mp4'
    assert (root / media['video']).read_bytes() == data
    assert (root / 'media/01-output.mp4').read_bytes() == b'original 576p'


def test_archived_command_fetches_pinned_record_and_has_unique_copy_ids():
    record = dict(case=1, prompt='Visible exact prompt', source='https://example.org/guide',
        archived_record='records/01-576p-0123456789ab.json',
        reproduction=dict(configuration_state='executed', references=[], task='t2va',
            runtime=build.RUNTIMES['0.1.0.dev2'], parameters=dict(resolution='576p', seed=42, duration=15)))
    panel = build.reproduction_panel(record)
    assert '--record case-01-576p-0123456789ab.json' in panel
    assert 'records/01-576p-0123456789ab.json' in panel
    assert 'id="prompt-01-576p-0123456789ab"' in panel
    assert 'Visible exact prompt' in panel
    assert "resolution=&#x27;576p&#x27;" in panel
