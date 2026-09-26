"""H3 Apple: image references and a prompt to synchronized video and audio."""

from .api import DownloadApprovalRequired, GenerationRequest, GenerationResult, generate, resolve

__version__ = "0.5.1.dev2"
__all__ = ["generate", "resolve", "GenerationRequest", "GenerationResult", "DownloadApprovalRequired"]
