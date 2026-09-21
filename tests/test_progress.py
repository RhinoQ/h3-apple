import io
import json
from pathlib import Path

import pytest

from h3_apple.api import GenerationResult
from h3_apple.progress import ProgressBar


class Terminal(io.StringIO):
    def isatty(self):
        return True


@pytest.mark.parametrize("stream_type", [io.StringIO, Terminal])
def test_completed_work_and_stages(stream_type):
    stream = stream_type()
    with ProgressBar(stream, clock=lambda: 10) as progress:
        progress({"phase": "loading"})
        for step in range(1, 5):
            progress({"phase": "denoise", "step": step, "steps": 4, "block": 50, "blocks": 50})
        progress({"phase": "video_decode", "tiles_completed": 20})
    output = stream.getvalue()
    assert all(f"{percent}%" in output for percent in (25, 50, 75, 100))
    assert "Step 4/4" in output and "20 tiles complete" in output
    assert "Complete" in output and output.endswith("\n")
    if stream_type is Terminal:
        assert output.count("\n") == 1 and "\r" in output
    else:
        assert "\r" not in output and "\x1b" not in output


def test_failed_generation_finishes_terminal_line_without_success():
    stream = Terminal()
    with pytest.raises(KeyboardInterrupt):
        with ProgressBar(stream) as progress:
            progress({"phase": "loading"})
            raise KeyboardInterrupt
    assert stream.getvalue().endswith("\n")
    assert "Complete" not in stream.getvalue()


def test_disabled_progress_is_silent():
    stream = Terminal()
    with ProgressBar(stream, enabled=False) as progress:
        progress({"phase": "loading"})
    assert stream.getvalue() == ""


@pytest.mark.parametrize("disabled", [False, True])
def test_cli_keeps_result_json_on_stdout(monkeypatch, capsys, disabled):
    from h3_apple import cli

    def generate(**kwargs):
        kwargs["on_progress"]({"phase": "denoise", "step": 4, "steps": 4, "block": 50, "blocks": 50})
        assert kwargs["reference_images"] == ["first.png", "second.png"]
        return GenerationResult(Path("result.mp4"), Path("result.run.json"), 12.0, 42)

    monkeypatch.setattr(cli, "generate", generate)
    args = ["generate", "--prompt", "A film.", "--image", "first.png",
            "--image", "second.png"]
    assert cli.main(args + (["--no-progress"] if disabled else [])) == 0
    output = capsys.readouterr()
    assert json.loads(output.out)["video_path"] == "result.mp4"
    assert output.err == "" if disabled else "100%" in output.err
