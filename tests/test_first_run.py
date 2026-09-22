import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from h3_apple import DownloadApprovalRequired, generate
from h3_apple import cli, preparation, process


@pytest.fixture
def local_setup(monkeypatch):
    monkeypatch.setattr(preparation, 'snapshot', lambda: {})
    monkeypatch.setattr(preparation, 'check_machine', lambda *_: None)
    return dict(status='ready', directory='/models', download_bytes=0, additional_disk_bytes=0)


def test_api_requests_consent_before_downloading_or_reserving_output(tmp_path, monkeypatch, local_setup):
    image = tmp_path / 'ref.png'
    Image.new('RGB', (32, 32)).save(image)
    spec = dict(local_setup, status='preparation_required', download_bytes=145_000_000_000)
    monkeypatch.setattr(preparation, 'plan', lambda *a, **kw: spec)
    monkeypatch.setattr(preparation, 'prepare', lambda *a, **kw: pytest.fail('download without consent'))
    target = tmp_path / 'outputs/video.mp4'
    with pytest.raises(DownloadApprovalRequired) as error:
        generate('A scene', reference_images=[image], output=target)
    assert error.value.download_bytes == spec['download_bytes']
    assert not target.parent.exists()


def test_automatic_setup_shares_explicit_consent_and_progress(monkeypatch, local_setup):
    from h3_apple import media
    spec = dict(local_setup, status='preparation_required', download_bytes=145_000_000_000)
    monkeypatch.setattr(preparation, 'plan', lambda *a, **kw: spec)
    monkeypatch.setattr(media, 'tool', lambda _: 'bundled-ffmpeg')
    monkeypatch.setattr(media, 'ffmpeg_libraries', lambda: Path('/bundled/libs'))
    calls = []
    monkeypatch.setattr(preparation, 'prepare', lambda value, **kw: calls.append((value, kw)) or {'identity':'ready'})
    events = []
    result = preparation.ensure_ready(allow_large_download=True, progress=events.append)
    assert result['identity'] == 'ready'
    assert calls[0][0] == spec and calls[0][1]['allow_large_download'] is True
    assert events[0]['phase'] == 'model_plan'


def test_noninteractive_cli_never_prompts(monkeypatch, capsys):
    monkeypatch.setattr(cli, 'generate', lambda **kw: (_ for _ in ()).throw(
        DownloadApprovalRequired(dict(download_bytes=145_000_000_000, additional_disk_bytes=233_000_000_000))))
    monkeypatch.setattr(cli.sys, 'stdin', SimpleNamespace(isatty=lambda: False))
    assert cli.main(['generate', '--image', 'ref.png', '--prompt', 'Scene']) == 1
    assert '--allow-large-download' in capsys.readouterr().err


@pytest.mark.parametrize('answer,expected_calls,exit_code', [('yes\n',2,0), ('no\n',1,1)])
def test_interactive_cli_consent(monkeypatch, capsys, answer, expected_calls, exit_code):
    from h3_apple import GenerationResult
    calls = []
    def generate(**kw):
        calls.append(kw)
        if not kw['allow_large_download']:
            raise DownloadApprovalRequired(dict(download_bytes=145_000_000_000,additional_disk_bytes=233_000_000_000))
        return GenerationResult(Path('video.mp4'),Path('video.run.json'),1,42)
    monkeypatch.setattr(cli, 'generate', generate)
    monkeypatch.setattr(cli.sys, 'stdin', SimpleNamespace(isatty=lambda: True, readline=lambda:answer))
    assert cli.main(['generate','--image','ref.png','--prompt','Scene','--no-progress']) == exit_code
    assert len(calls) == expected_calls
    if exit_code == 0:
        assert json.loads(capsys.readouterr().out)['video_path'] == 'video.mp4'


def test_invalid_output_does_not_trigger_setup(tmp_path, monkeypatch):
    from h3_apple import resolve
    ref = tmp_path/'ref.png'
    Image.new('RGB',(32,32)).save(ref)
    monkeypatch.setattr(process, 'ensure_ready', lambda *a, **kw:pytest.fail('setup before validation'))
    with pytest.raises(ValueError, match='.mp4'):
        generate('Scene', reference_images=[ref], output=tmp_path/'bad.mov')
    record = tmp_path/'exists.run.json'
    record.write_text('keep')
    with pytest.raises(FileExistsError):
        generate('Scene', reference_images=[ref], output=tmp_path/'exists.mp4')
    assert record.read_text() == 'keep'


def test_media_tools_are_from_pip_not_path(tmp_path, monkeypatch):
    from h3_apple.media import tool, ffmpeg_libraries
    monkeypatch.setenv('PATH', str(tmp_path))
    monkeypatch.setenv('IMAGEIO_FFMPEG_EXE', '/unrelated/ffmpeg')
    assert 'site-packages/imageio_ffmpeg/binaries' in tool('ffmpeg')
    assert all('.dylibs' in str(p.resolve()) for p in ffmpeg_libraries().iterdir())


def test_changed_library_links_cannot_fall_back_to_system(tmp_path, monkeypatch):
    import h3_apple.media as media
    monkeypatch.setattr(media.Path, 'home', lambda: tmp_path)
    directory = media.ffmpeg_libraries()
    link = directory / 'libavcodec.dylib'
    link.unlink()
    link.symlink_to(tmp_path / 'unrelated.dylib')
    with pytest.raises(ValueError, match='link changed'):
        media.ffmpeg_libraries()
