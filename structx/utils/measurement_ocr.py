"""Optional OCR adapter for standalone document measurement.

This module is only imported by :mod:`structx.measurement`. Extraction never
loads it, and importing this module does not import an OCR engine: the engine
is created on first use so that ``rapidocr`` stays an optional dependency.
"""

import threading
from typing import Any, Callable, Dict, Optional

from structx.core.exceptions import StructXError


class OcrEngineUnavailableError(StructXError):
    """Raised when an OCR engine is requested but cannot be created."""

    pass


def _joined_text(result: Any) -> str:
    """Join recognized text lines from a RapidOCR result."""
    lines = getattr(result, "txts", None)
    if not lines:
        return ""
    return "\n".join(str(line) for line in lines)


class RapidOcrReader:
    """Callable adapter that turns rendered page pixels into recognized text.

    The engine is created lazily on the first page that needs OCR and then
    reused for every later page measured through the same reader. Calls are
    serialized because a single engine instance is not guaranteed to be
    thread-safe.

    Attributes:
        engine_params: Parameters forwarded to ``RapidOCR`` on creation.
    """

    def __init__(self, **engine_params: Any) -> None:
        self.engine_params: Dict[str, Any] = dict(engine_params)
        self._engine: Optional[Any] = None
        self._lock = threading.Lock()

    def _ensure_engine(self) -> Any:
        """Create the RapidOCR engine once, or report that it is unavailable."""
        if self._engine is not None:
            return self._engine
        try:
            from rapidocr import RapidOCR
        except Exception as error:  # pragma: no cover - import environment
            raise OcrEngineUnavailableError(
                "RapidOCR is not installed. Install structx[measurement-ocr] "
                "or pass an ocr_reader to DocumentMeasurer."
            ) from error
        try:
            self._engine = (
                RapidOCR(**self.engine_params) if self.engine_params else RapidOCR()
            )
        except Exception as error:
            raise OcrEngineUnavailableError(
                f"Could not initialize RapidOCR: {error}"
            ) from error
        return self._engine

    def __call__(self, image: Any) -> str:
        """Recognize text in one rendered page image.

        Args:
            image: Rendered page pixels as an RGB array.

        Returns:
            Recognized text, or an empty string when nothing was recognized.

        Raises:
            OcrEngineUnavailableError: If the OCR engine cannot be created.
        """
        engine = self._ensure_engine()
        with self._lock:
            return _joined_text(engine(image))


def create_default_ocr_reader(**engine_params: Any) -> Callable[[Any], str]:
    """Create the built-in RapidOCR reader without initializing the engine.

    Args:
        **engine_params: Optional parameters forwarded to ``RapidOCR``.

    Returns:
        A callable that accepts rendered page pixels and returns text.
    """
    return RapidOcrReader(**engine_params)
