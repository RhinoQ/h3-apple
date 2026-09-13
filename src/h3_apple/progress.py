"""Terminal progress from completed work, without importing the model runtime."""

import shutil
import sys
import time


class ProgressBar:
    """A stderr renderer usable as the generation API's on_progress callback.

    Interactive terminals reuse one line. Redirected output uses plain lines,
    without terminal escape sequences. Percentages describe denoising only;
    stages without a known work count display their name and elapsed time.
    """

    LABELS = {
        "loading": "Loading models", "conditioning": "Encoding prompt / references",
        "denoise": "Denoising", "video_decode": "Decoding video",
        "audio_decode": "Decoding audio", "mux": "Writing video",
        "validating": "Validating video",
    }

    def __init__(self, stream=None, *, enabled=True, clock=time.monotonic):
        self.stream = stream if stream is not None else sys.stderr
        self.enabled = enabled
        self.clock = clock
        self.started = clock()
        self.interactive = bool(getattr(self.stream, "isatty", lambda: False)())
        self.line_width = 0
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close(success=exc_type is None)

    def _write(self, text):
        if not self.enabled or self.closed:
            return
        if self.interactive:
            width = max(20, shutil.get_terminal_size(fallback=(100, 24)).columns - 1)
            text = text[:width]
            self.stream.write("\r" + text + " " * max(0, min(self.line_width, width) - len(text)))
            self.line_width = len(text)
        else:
            self.stream.write(text + "\n")
        self.stream.flush()

    def elapsed(self):
        seconds = max(0, int(self.clock() - self.started))
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def __call__(self, event):
        phase = event.get("phase", "progress")
        label = self.LABELS.get(phase, phase.replace("_", " ").capitalize())
        if phase == "denoise" and "block" in event:
            step, steps = int(event["step"]), int(event["steps"])
            block, blocks = int(event["block"]), int(event["blocks"])
            if steps <= 0 or blocks <= 0 or not 1 <= step <= steps or not 0 <= block <= blocks:
                raise ValueError("Invalid denoising progress counts.")
            completed, total = (step - 1) * blocks + block, steps * blocks
            filled = completed * 20 // total
            bar = "#" * filled + "-" * (20 - filled)
            line = f"{label} [{bar}] {completed * 100 // total:3d}%  Step {step}/{steps}"
        elif phase == "video_decode" and "tiles_completed" in event:
            line = f"{label}: {event['tiles_completed']} tiles complete"
        else:
            line = label
        self._write(f"{line}  |  elapsed {self.elapsed()}")

    def close(self, *, success=False):
        if self.closed:
            return
        if success:
            self._write(f"Complete  |  elapsed {self.elapsed()}")
        if self.enabled and self.interactive and self.line_width:
            self.stream.write("\n")
            self.stream.flush()
        self.closed = True
