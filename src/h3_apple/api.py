"""One public generation path: ordered still references and a complete prompt."""

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
import secrets


class DownloadApprovalRequired(RuntimeError):
    """A first-run download exceeds 20 GB and needs explicit consent."""

    def __init__(self, plan):
        self.download_bytes = plan["download_bytes"]
        self.additional_disk_bytes = plan["additional_disk_bytes"]
        super().__init__(
            f"First-time model setup needs {self.download_bytes / 10**9:.2f} GB of downloads "
            f"and {self.additional_disk_bytes / 10**9:.2f} GB of additional disk space. "
            "Confirm with --allow-large-download on the command line, or "
            "allow_large_download=True in generate()."
        )


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
    recipe: str = "ref2va-premerged-i8-sol-sage-v2"
    fps: int = 24
    audio_sample_rate: int = 32000
    audio_channels: int = 2
    num_steps: int = 4
    mode: str = "SOL"
    x2: bool = True
    attention: str | None = None
    quality: str | None = None
    upscale: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class GenerationResult:
    video_path: Path
    metadata_path: Path
    elapsed_seconds: float
    seed: int
    native_video_path: Path | None = None


_QUALITIES = {
    "fast": dict(mode="SOL", resolution="544p", x2=True, attention=None, upscale=False),
    "medium": dict(mode="VSA", resolution="768p", x2=False, attention="vsa", upscale=False),
    "high": dict(mode="VSA", resolution="768p", x2=False, attention="dense", upscale=True),
}


def _configuration(quality, *, mode, resolution, x2, attention, upscale):
    """Resolve a named quality or preserve the existing advanced settings."""
    for name, value in (("x2", x2), ("upscale", upscale)):
        if value is not None and type(value) is not bool:
            raise ValueError(f"{name} must be a boolean.")
    if quality is not None:
        if not isinstance(quality, str) or quality not in _QUALITIES:
            raise ValueError("quality must be 'fast', 'medium' or 'high'.")
        chosen = _QUALITIES[quality]
        supplied = dict(mode=mode, resolution=resolution, x2=x2, attention=attention, upscale=upscale)
        for name, value in supplied.items():
            if value is not None and value != chosen[name]:
                raise ValueError(f"quality='{quality}' requires {name}={chosen[name]!r}; "
                                 f"omit {name} or omit quality to use advanced settings.")
        return chosen
    upscale = False if upscale is None else upscale
    return dict(mode="SOL" if mode is None else mode,
                resolution=("768p" if upscale else "544p") if resolution is None else resolution,
                x2=not upscale if x2 is None else x2, attention=attention, upscale=upscale)


def resolve(prompt=None, *, prompt_file=None, reference_images=None,
            quality=None, resolution=None, duration=5, seed=None, aspect_ratio="16:9",
            mode=None, x2=None, attention=None, upscale=None):
    """Validate inputs and resolve generation and restoration without loading models."""
    settings = _configuration(quality, mode=mode, resolution=resolution, x2=x2,
                              attention=attention, upscale=upscale)
    mode, resolution, x2, attention, upscale = (settings[key] for key in
                                               ("mode", "resolution", "x2", "attention", "upscale"))
    if mode not in ("SOL", "VSA"):
        raise ValueError("mode must be 'SOL' or 'VSA'.")
    if attention is not None and (mode != "VSA" or attention not in ("vsa", "dense")):
        raise ValueError("attention requires mode='VSA' and must be 'vsa' or 'dense'.")
    attention = (attention or "vsa") if mode == "VSA" else None
    if upscale and (x2 or resolution not in ("576p", "768p")):
        raise ValueError("generate(upscale=True) uses native 576p or 768p. Omit resolution and x2 "
                         "for automatic settings, or generate X2 video first and call upscale() separately.")
    if attention == "dense" and (resolution != "768p" or x2):
        raise ValueError("Dense attention requires native 768p (resolution='768p', x2=False).")
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
    canvases = {"544p": (960, 544, 960), "576p": (1024, 576, 1024), "768p": (1366, 768, 1376)}
    if resolution not in canvases:
        raise ValueError("resolution must be '544p', '576p' or '768p'.")
    if resolution == "544p" and not x2:
        raise ValueError("544p sampling requires x2=True (CLI: --x2).")
    if resolution == "768p" and x2:
        raise ValueError("X2 supports only 544p or 576p sampling. For 768p, set x2=False (CLI: --no-x2).")
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
    if x2:
        width, height = width * 2, height * 2
    return GenerationRequest(prompt, references, resolution, count / 24, seed,
                             width, height, count, model_width, model_height,
                             ((count - 5 + 16) // 17) * 17 + 5, mode=mode, x2=x2,
                             attention=attention, quality=quality, upscale=upscale,
                             recipe=("ref2va-premerged-i8-sol-sage-v2" if mode == "SOL" else
                                     "ref2va-w8a8-dense-bf16-v1" if attention == "dense" else
                                     "ref2va-w8a8-vsa-int8qk-v1"))


def generate(prompt=None, *, prompt_file=None, reference_images=None,
             quality=None, resolution=None, duration=5, seed=None, aspect_ratio="16:9", mode=None,
             attention=None, x2=None, x2_model_dir=None, upscale=None, upscale_model_dir=None,
             upscale_timeout=14400,
             output=None, model_dir=None, on_progress=None, diagnostics=False,
             timeout=7200, allow_large_download=False):
    """Prepare H3 if needed, then generate an MP4 with stereo audio.

    Model downloads over 20 GB raise DownloadApprovalRequired unless explicitly
    allowed. Importing this module and resolving inputs never download anything.
    """
    request = resolve(prompt, prompt_file=prompt_file, reference_images=reference_images,
                      quality=quality, resolution=resolution, duration=duration, seed=seed,
                      aspect_ratio=aspect_ratio, mode=mode, attention=attention, x2=x2, upscale=upscale)
    if request.upscale and x2_model_dir is not None:
        raise ValueError("x2_model_dir cannot be used with upscale.")
    if not request.upscale and upscale_model_dir is not None:
        raise ValueError("upscale_model_dir requires upscale=True.")
    if request.upscale:
        from .workflow import generate_upscaled
        return generate_upscaled(request, output=output, model_dir=model_dir,
            on_progress=on_progress, diagnostics=diagnostics, timeout=timeout,
            allow_large_download=allow_large_download, upscale_model_dir=upscale_model_dir,
            upscale_timeout=upscale_timeout)
    from .process import run_generation
    return run_generation(request, output=output, model_dir=model_dir,
                          on_progress=on_progress, diagnostics=diagnostics, timeout=timeout,
                          allow_large_download=allow_large_download, x2_model_dir=x2_model_dir)
