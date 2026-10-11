"""H3 Apple: image references and a prompt to synchronized video and audio."""

from .api import DownloadApprovalRequired, GenerationRequest, GenerationResult, generate, resolve

from .upscale import upscale, UpscaleResult

__version__ = "0.8.1"
__all__ = ["generate", "resolve", "upscale", "GenerationRequest", "GenerationResult", "UpscaleResult", "DownloadApprovalRequired"]
