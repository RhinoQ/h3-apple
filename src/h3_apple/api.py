"""Resolve user intent before launching a fresh, isolated model worker."""

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
import secrets


@dataclass(frozen=True)
class GenerationRequest:
    prompt: str
    preset: str
    resolution: str
    duration: float
    seed: int
    width: int
    height: int
    num_frames: int
    model_width: int
    model_height: int
    model_num_frames: int
    preset_version: str = "ours-v1"
    fps: int = 24
    audio_sample_rate: int = 32000
    audio_channels: int = 2
    num_steps: int = 4
    reference_images: tuple[str, ...] = ()
    task: str = "t2va"
    first_frame: str | None = None
    last_frame: str | None = None
    reference_resize: str = "legacy"
    reference_videos: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class GenerationResult:
    video_path: Path
    metadata_path: Path
    elapsed_seconds: float
    seed: int


def resolve(prompt=None, *, prompt_file=None, preset="ours", resolution=None,
            duration=15, seed=None, reference_images=None, task=None,
            first_frame=None, last_frame=None, reference_resize="legacy", reference_videos=None):
    """Return the delivery and model geometry without importing MLX.

    Durations are 5–15 seconds in whole delivery frames at 24 fps. The model
    generates the next valid 17*n+5 frame count, followed by a fixed trim.
    """
    if (prompt is None) == (prompt_file is None):
        raise ValueError("Provide exactly one of prompt or prompt_file.")
    if prompt_file is not None:
        prompt = Path(prompt_file).read_text(encoding="utf-8")
    if not isinstance(prompt, str) or not prompt.strip() or "\x00" in prompt:
        raise ValueError("prompt must be nonempty text without NUL characters.")
    if preset != "ours":
        raise ValueError("The supported preset is 'ours'.")
    references = ()
    if reference_images is not None:
        if not isinstance(reference_images, (list, tuple)) or not 1 <= len(reference_images) <= 9:
            raise ValueError("reference_images must be an ordered list of 1–9 image paths.")
        if any(not isinstance(p, (str, Path)) or not str(p).strip() for p in reference_images):
            raise ValueError("Each reference image needs a nonempty file path.")
        references = tuple(str(Path(p).expanduser().resolve()) for p in reference_images)
        from PIL import Image
        for path in references:
            with Image.open(path) as image:
                if getattr(image, "n_frames", 1) != 1:
                    raise ValueError("Reference inputs must be still images, not animations or videos.")
                image.verify()
    videos = ()
    if reference_videos is not None:
        if not isinstance(reference_videos, (list, tuple)) or not 1 <= len(reference_videos) <= 3:
            raise ValueError("reference_videos must be an ordered list of 1–3 video paths.")
        if any(not isinstance(p, (str, Path)) or not str(p).strip() for p in reference_videos):
            raise ValueError("Each reference video needs a nonempty file path.")
        videos = tuple(str(Path(p).expanduser().resolve()) for p in reference_videos)
        from .media import probe_reference
        for path in videos:
            probe_reference(path, "videos")
    keyframes = []
    for value in (first_frame, last_frame):
        if value is None:
            keyframes.append(None)
            continue
        if not isinstance(value, (str, Path)) or not str(value).strip():
            raise ValueError("A first or last frame needs a local still-image path.")
        from PIL import Image
        path = Path(value).expanduser().resolve()
        with Image.open(path) as image:
            if getattr(image, "n_frames", 1) != 1:
                raise ValueError("Keyframes must be still images.")
            image.verify()
        keyframes.append(str(path))
    has_keyframes = any(keyframes)
    if has_keyframes and (references or videos):
        raise ValueError("First/last frames and Ref2VA references use different model tasks.")
    inferred = "fl2va" if has_keyframes else "ref2va" if references or videos else "t2va"
    if task is not None and task not in ("t2va", "fl2va", "ref2va"):
        raise ValueError("task must be t2va, fl2va or ref2va.")
    if task is not None and task != inferred:
        raise ValueError(f"task={task} does not match the supplied inputs ({inferred}).")
    if reference_resize not in ("legacy", "match"):
        raise ValueError("reference_resize must be legacy or match.")
    if reference_resize != "legacy" and not references:
        raise ValueError("reference_resize applies only to Ref2VA images.")
    if resolution is None:
        resolution = "576p" if references and not videos else "768p"
    canvases = {"768p": (1366, 768, 1376), "576p": (1024, 576, 1024)}
    if resolution not in canvases:
        raise ValueError("resolution must be '768p' or '576p'.")
    if isinstance(duration, bool):
        raise ValueError("duration must be a number of seconds.")
    try:
        seconds = Decimal(str(duration))
        frames = seconds * 24
        if not seconds.is_finite() or not Decimal(5) <= seconds <= Decimal(15):
            raise ValueError("duration must be between 5 and 15 seconds.")
        if abs(frames - frames.to_integral_value()) > Decimal("0.000001"):
            raise ValueError("duration must correspond to a whole frame at 24 fps.")
    except InvalidOperation as error:
        raise ValueError("duration must be a finite number.") from error
    if seed is None:
        seed = secrets.randbits(32)
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("seed must be an integer from 0 to 4294967295.")
    count = int(frames.to_integral_value())
    width, height, model_width = canvases[resolution]
    return GenerationRequest(prompt, preset, resolution, count / 24, seed,
                             width, height, count, model_width, height,
                             ((count - 5 + 16) // 17) * 17 + 5,
                             preset_version="ours-fl2va-vsa-v1.2" if has_keyframes else
                                 "ours-ref2va-video-v1" if videos else
                                 "ours-ref2va-match-v1" if references and reference_resize == "match" else
                                 "ours-ref2va-v1" if references else "ours-v1",
                             reference_images=references, task=inferred,
                             first_frame=keyframes[0], last_frame=keyframes[1],
                             reference_resize=reference_resize, reference_videos=videos)


def generate(prompt=None, *, prompt_file=None, preset="ours", resolution=None,
             duration=15, seed=None, output=None, model_dir=None, on_progress=None,
             diagnostics=False, timeout=7200, reference_images=None,
             task=None, first_frame=None, last_frame=None, reference_resize="legacy",
             reference_videos=None):
    """Generate a complete MP4 and metadata; Ctrl-C cancels the whole worker group.

    on_progress receives small dictionaries in the caller process. diagnostics
    additionally saves numerical arrays for migration/algorithm research.
    """
    request = resolve(prompt, prompt_file=prompt_file, preset=preset,
                      resolution=resolution, duration=duration, seed=seed,
                      reference_images=reference_images, task=task,
                      first_frame=first_frame, last_frame=last_frame,
                      reference_resize=reference_resize, reference_videos=reference_videos)
    from .process import run_generation

    return run_generation(request, output=output, model_dir=model_dir,
                          on_progress=on_progress, diagnostics=diagnostics,
                          timeout=timeout)
