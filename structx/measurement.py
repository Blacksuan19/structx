"""Standalone document measurement.

This module estimates how much content a PDF contains. It exists for callers
that need page and text-length estimates *before* extraction, such as usage
quoting in a hosted product.

It is deliberately independent of the extraction pipeline:

- Extraction never calls this module.
- Measuring a document never rewrites, converts, or replaces the input file.
- OCR here is local image-to-text recognition, never a model request.

Example:
    ```python
    from structx.measurement import DocumentMeasurer

    measurer = DocumentMeasurer(ocr_mode="auto")
    measurement = measurer.measure("invoice.pdf")
    print(measurement.page_count, measurement.character_count, measurement.status)
    ```
"""

import threading
from dataclasses import dataclass, field
from math import ceil, sqrt
from pathlib import Path
from typing import Any, Callable, Optional, Tuple, Union

from structx.core.exceptions import ConfigurationError, FileError
from structx.utils.measurement_ocr import (
    OcrEngineUnavailableError,
    create_default_ocr_reader,
)

ESTIMATOR_REVISION = "1"
"""Revision of the counting algorithm.

This identifies how counts were produced. It is not a promise that optional OCR
models or their versions are frozen.
"""

OCR_MODES: Tuple[str, ...] = ("never", "auto", "always")

MEASUREMENT_BYTES_LIMIT = 50 * 1024 * 1024
MEASUREMENT_PAGE_LIMIT = 500
MEASUREMENT_RENDER_DPI = 150.0
MEASUREMENT_RENDER_PIXEL_LIMIT = 12_000_000

# PDFium is not thread-safe, so all measurement work through this module is
# serialized. Run heavy OCR workloads in separate processes instead.
_PDFIUM_LOCK = threading.Lock()

_PDF_POINTS_PER_INCH = 72.0
_RENDER_SCALE_ATTEMPTS = 8
_RENDER_SCALE_MARGIN = 0.999


@dataclass(frozen=True)
class PageMeasurement:
    """Measured content of one page.

    Attributes:
        page_number: One-based page position in the source document.
        character_count: Unicode code points observed on the page.
        method: How the count was produced: ``native``, ``ocr``, or ``none``.
        status: ``complete`` when the page was measured, ``partial`` when the
            count is known to be incomplete or unavailable.
        error_code: Stable reason for a partial page, otherwise ``None``.
    """

    page_number: int
    character_count: int
    method: str
    status: str
    error_code: Optional[str] = None


@dataclass(frozen=True)
class DocumentMeasurement:
    """Measured content of one document.

    Attributes:
        pages: Page measurements in source order.
        ocr_mode: OCR mode used for this measurement.
        estimator_revision: Revision of the counting algorithm.
    """

    pages: Tuple[PageMeasurement, ...] = field(default_factory=tuple)
    ocr_mode: str = "never"
    estimator_revision: str = ESTIMATOR_REVISION

    @property
    def page_count(self) -> int:
        """Number of pages in the measured document."""
        return len(self.pages)

    @property
    def character_count(self) -> int:
        """Total characters observed across measured pages."""
        return sum(page.character_count for page in self.pages)

    @property
    def status(self) -> str:
        """``complete`` only when every page of a non-empty document was measured."""
        if not self.pages:
            return "partial"
        if all(page.status == "complete" for page in self.pages):
            return "complete"
        return "partial"

    @property
    def error_codes(self) -> Tuple[str, ...]:
        """Distinct partial-page reasons, in first-seen order."""
        codes: list = []
        for page in self.pages:
            if page.error_code and page.error_code not in codes:
                codes.append(page.error_code)
        return tuple(codes)


def _positive_int(value: Any, name: str) -> int:
    """Validate a positive integer setting."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ConfigurationError(f"{name} must be a positive integer")
    return value


def _positive_real(value: Any, name: str) -> float:
    """Validate a positive finite numeric setting."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a positive number")
    number = float(value)
    if number <= 0 or number != number or number in (float("inf"), float("-inf")):
        raise ConfigurationError(f"{name} must be a positive finite number")
    return number


def _normalized(text: str) -> str:
    """Normalize line endings so counts do not depend on the source platform."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _import_pdfium():
    """Import the optional PDF backend used for measurement."""
    try:
        import pypdfium2
    except Exception as error:  # pragma: no cover - import environment
        raise ConfigurationError(
            "Document measurement requires pypdfium2. " "Install structx[measurement]."
        ) from error
    return pypdfium2


class DocumentMeasurer:
    """Estimate page and character counts for PDF documents.

    The measurer is reusable: one instance can measure many documents and
    reuses a single OCR reader when OCR is enabled. Measurement is synchronous
    and serialized internally.

    Attributes:
        ocr_mode: ``never`` (default) uses embedded text only. ``auto`` also
            runs OCR for pages with no usable embedded text. ``always`` reads
            every page with OCR instead of its embedded text.
        max_pages: Largest document accepted, in pages.
        max_input_bytes: Largest input accepted, in bytes.
        render_dpi: Resolution used when rendering a page for OCR.
        max_render_pixels: Upper bound on rendered pixels per page. Larger
            pages are rendered at a reduced scale rather than skipped.
    """

    def __init__(
        self,
        *,
        ocr_mode: str = "never",
        ocr_reader: Optional[Callable[[Any], str]] = None,
        max_pages: int = MEASUREMENT_PAGE_LIMIT,
        max_input_bytes: int = MEASUREMENT_BYTES_LIMIT,
        render_dpi: float = MEASUREMENT_RENDER_DPI,
        max_render_pixels: int = MEASUREMENT_RENDER_PIXEL_LIMIT,
    ) -> None:
        if ocr_mode not in OCR_MODES:
            raise ConfigurationError(f"ocr_mode must be one of {', '.join(OCR_MODES)}")
        if ocr_reader is not None and not callable(ocr_reader):
            raise ConfigurationError("ocr_reader must be callable")

        self.ocr_mode = ocr_mode
        self.max_pages = _positive_int(max_pages, "max_pages")
        self.max_input_bytes = _positive_int(max_input_bytes, "max_input_bytes")
        self.render_dpi = _positive_real(render_dpi, "render_dpi")
        self.max_render_pixels = _positive_int(max_render_pixels, "max_render_pixels")
        self._ocr_reader = ocr_reader

    def measure(self, file_path: Union[str, Path]) -> DocumentMeasurement:
        """Measure one PDF document.

        Args:
            file_path: Path to an existing PDF file.

        Returns:
            Page and character estimates with per-page completeness.

        Raises:
            FileError: If the file is missing, empty, not a readable PDF, or
                exceeds the configured size or page limits.
            ConfigurationError: If the optional PDF backend is unavailable.
        """
        path = self._validated_path(file_path)
        pdfium = _import_pdfium()
        with _PDFIUM_LOCK:
            pages = self._measure_pages(pdfium, path)
        return DocumentMeasurement(
            pages=tuple(pages),
            ocr_mode=self.ocr_mode,
            estimator_revision=ESTIMATOR_REVISION,
        )

    def _validated_path(self, file_path: Union[str, Path]) -> Path:
        """Reject inputs this API cannot measure before opening them."""
        path = Path(file_path)
        if not path.exists():
            raise FileError(f"File not found: {path}")
        if not path.is_file():
            raise FileError(f"Path is not a file: {path}")

        size = path.stat().st_size
        if size == 0:
            raise FileError(f"File is empty: {path}")
        if size > self.max_input_bytes:
            raise FileError(
                f"File exceeds the {self.max_input_bytes} byte measurement limit: "
                f"{path}"
            )
        if path.suffix.lower() != ".pdf":
            raise FileError(
                f"Document measurement supports PDF input only: {path.suffix}"
            )

        with path.open("rb") as pdf_file:
            header = pdf_file.read(1024)
        if b"%PDF-" not in header:
            raise FileError(f"Invalid PDF file: {path}")
        return path

    def _measure_pages(self, pdfium: Any, path: Path) -> list:
        """Open the document once and measure every page in order."""
        try:
            document = pdfium.PdfDocument(path)
        except Exception as error:
            raise FileError(f"Could not open PDF for measurement: {path}") from error

        try:
            if _is_encrypted(pdfium, document):
                raise FileError(f"Encrypted PDFs cannot be measured: {path}")

            page_count = len(document)
            if page_count < 1:
                raise FileError(f"The PDF contains no pages: {path}")
            if page_count > self.max_pages:
                raise FileError(
                    f"PDF exceeds the {self.max_pages} page measurement limit: {path}"
                )
            return [self._measure_page(document, index) for index in range(page_count)]
        finally:
            document.close()

    def _measure_page(self, document: Any, index: int) -> PageMeasurement:
        """Measure one page without letting a page failure end the document."""
        page_number = index + 1
        try:
            page = document[index]
        except Exception:
            return PageMeasurement(
                page_number, 0, "none", "partial", "page_load_failed"
            )

        try:
            native_text, native_failed = _native_text(page)

            if self.ocr_mode == "always":
                return self._ocr_page(page, page_number, native_text, native_failed)

            if native_failed:
                if self.ocr_mode == "auto":
                    return self._ocr_page(page, page_number, "", True)
                return PageMeasurement(
                    page_number, 0, "none", "partial", "native_text_failed"
                )

            if native_text.strip():
                return PageMeasurement(
                    page_number, len(native_text), "native", "complete"
                )

            if self.ocr_mode == "auto":
                return self._ocr_page(page, page_number, "", False)

            # Without OCR, an empty text layer cannot be distinguished from a
            # scanned page, so the page is reported as incomplete.
            return PageMeasurement(page_number, 0, "none", "partial", "ocr_skipped")
        finally:
            page.close()

    def _ocr_page(
        self,
        page: Any,
        page_number: int,
        native_text: str,
        native_failed: bool,
    ) -> PageMeasurement:
        """Measure a page with OCR, falling back to any usable native count."""
        text, error_code = self._recognized_text(page)
        if error_code is None:
            return PageMeasurement(page_number, len(text), "ocr", "complete")
        if not native_failed and native_text.strip():
            return PageMeasurement(
                page_number, len(native_text), "native", "partial", error_code
            )
        return PageMeasurement(page_number, 0, "none", "partial", error_code)

    def _recognized_text(self, page: Any) -> Tuple[str, Optional[str]]:
        """Render one page and recognize its text, reporting bounded failures."""
        reader = self._resolve_reader()
        if reader is None:
            return "", "ocr_unavailable"

        try:
            image = self._rendered_image(page)
        except Exception:
            return "", "page_render_failed"

        try:
            text = reader(image)
        except OcrEngineUnavailableError:
            return "", "ocr_unavailable"
        except Exception:
            return "", "ocr_failed"

        if not isinstance(text, str):
            return "", "ocr_failed"
        return _normalized(text), None

    def _resolve_reader(self) -> Optional[Callable[[Any], str]]:
        """Return the configured reader, creating the built-in one on demand."""
        if self._ocr_reader is None:
            self._ocr_reader = create_default_ocr_reader()
        return self._ocr_reader

    def _rendered_image(self, page: Any) -> Any:
        """Render a page to pixels within the configured pixel budget."""
        bitmap = page.render(scale=self._render_scale(page))
        try:
            return bitmap.to_numpy()
        finally:
            bitmap.close()

    def _render_scale(self, page: Any) -> float:
        """Scale a page to the requested DPI without exceeding the pixel limit.

        The rendered bitmap uses whole pixels, so the scale is reduced until the
        rounded-up dimensions also fit the budget.
        """
        width, height = page.get_size()
        if width <= 0 or height <= 0:
            raise ValueError("Page has no renderable area")

        scale = self.render_dpi / _PDF_POINTS_PER_INCH
        for _ in range(_RENDER_SCALE_ATTEMPTS):
            pixels = ceil(width * scale) * ceil(height * scale)
            if pixels <= self.max_render_pixels:
                break
            scale *= sqrt(self.max_render_pixels / pixels) * _RENDER_SCALE_MARGIN
        else:
            raise ValueError("Page cannot be rendered within the pixel limit")

        if width * scale < 1 or height * scale < 1:
            raise ValueError("Page cannot be rendered within the pixel limit")
        return scale


def _is_encrypted(pdfium: Any, document: Any) -> bool:
    """Detect encrypted documents, including empty-password encryption."""
    security_revision = getattr(pdfium.raw, "FPDF_GetSecurityHandlerRevision", None)
    if security_revision is None:  # pragma: no cover - backend without the symbol
        return False
    try:
        return security_revision(document) >= 0
    except Exception:  # pragma: no cover - defensive backend guard
        return False


def _native_text(page: Any) -> Tuple[str, bool]:
    """Read a page's embedded text layer.

    Returns:
        The normalized text and a flag indicating that reading it failed.
    """
    try:
        text_page = page.get_textpage()
    except Exception:
        return "", True

    try:
        return _normalized(text_page.get_text_bounded()), False
    except Exception:
        return "", True
    finally:
        text_page.close()
