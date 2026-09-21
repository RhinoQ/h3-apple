"""H3 Apple: image references and a prompt to synchronized video and audio."""

from .api import GenerationRequest, GenerationResult, generate, resolve

__version__ = "0.4.0"
__all__ = ["generate", "resolve", "GenerationRequest", "GenerationResult"]
