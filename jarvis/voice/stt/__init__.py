"""
Speech-to-text provider sub-package.

Use ``create_stt()`` to get the right provider by name.
"""

from typing import Any, Dict

from ...core.logger import get_logger
from ..base import STTProvider

logger = get_logger(__name__)

WHISPER_PROVIDER = "faster-whisper"

# Constructor kwargs only one provider understands. ``create_stt`` is handed
# the union of both so it can still build the Vosk fallback after a
# faster-whisper request turns out unusable.
_VOSK_ONLY = ("model_path",)
_WHISPER_ONLY = ("model_size", "model_dir")


def _kwargs_for(provider: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    drop = _VOSK_ONLY if provider == WHISPER_PROVIDER else _WHISPER_ONLY
    return {k: v for k, v in kwargs.items() if k not in drop}


def create_stt(provider: str = "vosk", **kwargs) -> STTProvider:
    """Create an STT provider instance.

    Args:
        provider: ``"vosk"`` (default) or ``"faster-whisper"``.
        **kwargs: Passed through to the provider constructor
                  (model_path, model_size, model_dir, sample_rate, etc.).

    Returns:
        An initialised STTProvider. A ``faster-whisper`` request whose package
        or model is unavailable degrades to Vosk once, logged, rather than
        leaving the daemon with no voice input at all (Project-JARVIS#138).

    Raises:
        ValueError: If the provider name is unknown.
    """
    if provider == WHISPER_PROVIDER:
        from .whisper_stt import INSTALL_HINT, WhisperSTT

        stt = WhisperSTT(**_kwargs_for(WHISPER_PROVIDER, kwargs))
        if stt.is_available() and stt.ensure_model():
            return stt
        logger.error(
            "faster-whisper STT unavailable (package or model missing), "
            f"falling back to Vosk. {INSTALL_HINT}"
        )
        provider = "vosk"

    if provider == "vosk":
        from .vosk_stt import VoskSTT

        return VoskSTT(**_kwargs_for("vosk", kwargs))
    raise ValueError(
        f"Unknown STT provider: '{provider}'. Available: vosk, {WHISPER_PROVIDER}"
    )


__all__ = ["STTProvider", "create_stt"]
