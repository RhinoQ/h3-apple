"""H3 Apple: image references and a prompt to synchronized video and audio."""

from .api import DownloadApprovalRequired, GenerationRequest, GenerationResult, generate, resolve
from .faces.api import EnhancementResult, enhance_faces

__version__ = "0.6.0"
__all__ = ["generate", "resolve", "GenerationRequest", "GenerationResult", "DownloadApprovalRequired", "enhance_faces", "EnhancementResult"]
