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


PARALLEL_ENGINE_PARAMS: Dict[str, Any] = {
    "params": {"EngineConfig.onnxruntime.intra_op_num_threads": 1}
}
"""Engine parameters used when several reader threads run at once.

ONNX Runtime already spreads a single recognition call across CPU cores, so
parallel workers only help when each engine is limited to one inference thread.
This applies to the built-in onnxruntime engine; pass explicit engine parameters
for other backends.
"""


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


class ThreadLocalRapidOcrReader:
    """Reader that gives every worker thread its own OCR engine.

    ``RapidOCR`` updates instance state on each call, so one engine cannot be
    shared across threads. This reader creates an engine per thread instead,
    which is what makes page-level parallel OCR safe.

    Attributes:
        engine_params: Parameters forwarded to ``RapidOCR`` on creation.
    """

    def __init__(self, **engine_params: Any) -> None:
        self.engine_params: Dict[str, Any] = dict(engine_params)
        self._local = threading.local()

    def __call__(self, image: Any) -> str:
        """Recognize text using this thread's engine, creating it on demand."""
        reader = getattr(self._local, "reader", None)
        if reader is None:
            reader = RapidOcrReader(**self.engine_params)
            self._local.reader = reader
        return reader(image)


def create_default_ocr_reader(
    *, workers: int = 1, **engine_params: Any
) -> Callable[[Any], str]:
    """Create the built-in RapidOCR reader without initializing the engine.

    Args:
        workers: Number of threads that may call the reader at once. Values
            above one create one engine per thread and, unless the caller
            overrides engine parameters, limit each engine to a single
            inference thread so workers do not oversubscribe the CPU.
        **engine_params: Optional parameters forwarded to ``RapidOCR``.

    Returns:
        A callable that accepts rendered page pixels and returns text.
    """
    if workers <= 1:
        return RapidOcrReader(**engine_params)
    if not engine_params:
        engine_params = dict(PARALLEL_ENGINE_PARAMS)
    return ThreadLocalRapidOcrReader(**engine_params)
