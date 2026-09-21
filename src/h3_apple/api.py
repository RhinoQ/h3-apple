"""One public generation path: ordered still references and a complete prompt."""

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
import secrets


@dataclass(frozen=True)
class GenerationRequest:
    prompt: str
    reference_images: tuple[str, ...]
    resolution: str
    duration: float
    seed: int
    width: int
    height: int
    num_frames: int
    model_width: int
    model_height: int
    model_num_frames: int
    recipe: str = "ref2va-i8-sol-sage-v1"
    fps: int = 24
    audio_sample_rate: int = 32000
    audio_channels: int = 2
    num_steps: int = 4

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class GenerationResult:
    video_path: Path
    metadata_path: Path
    elapsed_seconds: float
    seed: int


def resolve(prompt=None, *, prompt_file=None, reference_images=None,
            resolution="576p", duration=15, seed=None, aspect_ratio="16:9"):
    """Validate inputs and resolve geometry without loading model weights."""
    if (prompt is None) == (prompt_file is None):
        raise ValueError("Provide exactly one of prompt or prompt_file.")
    if prompt_file is not None:
        prompt = Path(prompt_file).expanduser().read_text(encoding="utf-8")
    if not isinstance(prompt, str) or not prompt.strip() or "\x00" in prompt:
        raise ValueError("prompt must be nonempty text without NUL characters.")
    if not isinstance(reference_images, (list, tuple)) or not 1 <= len(reference_images) <= 9:
        raise ValueError("Provide an ordered list of 1–9 reference images.")
    if any(not isinstance(p, (str, Path)) or not str(p).strip() for p in reference_images):
        raise ValueError("Each reference image needs a nonempty file path.")
    references = tuple(str(Path(p).expanduser().resolve()) for p in reference_images)
    from PIL import Image, ImageOps
    from .image_inputs import reference_image_size
    for path in references:
        with Image.open(path) as image:
            if getattr(image, "n_frames", 1) != 1:
                raise ValueError("Reference inputs must be still images.")
            reference_image_size(*ImageOps.exif_transpose(image).size, 1024 * 576)
        with Image.open(path) as image:
            image.verify()
    canvases = {"576p": (1024, 576, 1024), "768p": (1366, 768, 1376)}
    if resolution not in canvases:
        raise ValueError("resolution must be '576p' or '768p'.")
    if aspect_ratio not in ("16:9", "9:16"):
        raise ValueError("aspect_ratio must be '16:9' or '9:16'.")
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
    model_height = height
    if aspect_ratio == "9:16":
        width, height, model_width, model_height = height, width, height, model_width
    return GenerationRequest(prompt, references, resolution, count / 24, seed,
                             width, height, count, model_width, model_height,
                             ((count - 5 + 16) // 17) * 17 + 5)


def generate(prompt=None, *, prompt_file=None, reference_images=None,
             resolution="576p", duration=15, seed=None, aspect_ratio="16:9",
             output=None, model_dir=None, on_progress=None, diagnostics=False,
             timeout=7200):
    """Generate an MP4 with stereo audio and a run record in an isolated worker."""
    request = resolve(prompt, prompt_file=prompt_file, reference_images=reference_images,
                      resolution=resolution, duration=duration, seed=seed,
                      aspect_ratio=aspect_ratio)
    from .process import run_generation
    return run_generation(request, output=output, model_dir=model_dir,
                          on_progress=on_progress, diagnostics=diagnostics, timeout=timeout)
