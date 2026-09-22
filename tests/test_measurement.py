import sys
import types
from pathlib import Path

import pytest

from structx.core.exceptions import ConfigurationError, FileError
from structx.measurement import DocumentMeasurer, DocumentMeasurement
from structx.utils.measurement_ocr import (
    OcrEngineUnavailableError,
    RapidOcrReader,
    create_default_ocr_reader,
)

pdfium = pytest.importorskip(
    "pypdfium2", reason="optional measurement dependencies are not installed"
)


def build_pdf(path: Path, page_texts, page_size=(612, 792)) -> Path:
    """Write a small PDF where ``None`` produces a page with no text layer."""
    width, height = page_size
    objects = {}
    page_ids = [4 + index * 2 for index in range(len(page_texts))]

    objects[1] = "<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_texts)} >>"
    objects[3] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    for page_id, text in zip(page_ids, page_texts):
        content_id = page_id + 1
        page = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] "
            "/Resources << /Font << /F1 3 0 R >> >>"
        )
        if text is None:
            objects[page_id] = page + " >>"
            objects[content_id] = "<< /Length 0 >>\nstream\n\nendstream"
            continue
        stream = f"BT /F1 24 Tf 72 700 Td ({text}) Tj ET"
        objects[page_id] = page + f" /Contents {content_id} 0 R >>"
        objects[content_id] = (
            f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream"
        )

    body = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for object_id in sorted(objects):
        offsets[object_id] = len(body)
        body += f"{object_id} 0 obj\n{objects[object_id]}\nendobj\n".encode("latin-1")

    xref_offset = len(body)
    highest_id = max(objects)
    body += f"xref\n0 {highest_id + 1}\n".encode("latin-1")
    body += b"0000000000 65535 f \n"
    for object_id in range(1, highest_id + 1):
        offset = offsets.get(object_id, 0)
        body += f"{offset:010d} 00000 n \n".encode("latin-1")
    body += (
        f"trailer\n<< /Size {highest_id + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("latin-1")

    path.write_bytes(bytes(body))
    return path


class RecordingReader:
    """Test double that records how often OCR ran and what it received."""

    def __init__(self, text="recognized text", error=None):
        self.text = text
        self.error = error
        self.calls = []

    def __call__(self, image):
        self.calls.append(image)
        if self.error is not None:
            raise self.error
        return self.text


@pytest.fixture
def native_pdf(tmp_path) -> Path:
    return build_pdf(tmp_path / "native.pdf", ["Hello measurement"])


@pytest.fixture
def blank_pdf(tmp_path) -> Path:
    return build_pdf(tmp_path / "blank.pdf", [None])


@pytest.fixture
def mixed_pdf(tmp_path) -> Path:
    return build_pdf(tmp_path / "mixed.pdf", ["Invoice total 42", None])


def test_native_pages_are_measured_without_ocr(native_pdf):
    reader = RecordingReader()
    measurement = DocumentMeasurer(ocr_mode="auto", ocr_reader=reader).measure(
        native_pdf
    )

    assert measurement.page_count == 1
    assert measurement.status == "complete"
    assert measurement.error_codes == ()
    assert measurement.estimator_revision == "1"
    page = measurement.pages[0]
    assert page.page_number == 1
    assert page.method == "native"
    assert page.character_count == len("Hello measurement")
    assert reader.calls == []


def test_page_without_text_layer_is_partial_when_ocr_is_disabled(blank_pdf):
    measurement = DocumentMeasurer().measure(blank_pdf)

    page = measurement.pages[0]
    assert (page.method, page.status, page.error_code) == (
        "none",
        "partial",
        "ocr_skipped",
    )
    assert page.character_count == 0
    assert measurement.status == "partial"
    assert measurement.character_count == 0


def test_auto_mode_measures_pages_without_text_through_ocr(blank_pdf):
    reader = RecordingReader(text="scanned words")
    measurement = DocumentMeasurer(ocr_mode="auto", ocr_reader=reader).measure(
        blank_pdf
    )

    page = measurement.pages[0]
    assert (page.method, page.status, page.error_code) == ("ocr", "complete", None)
    assert page.character_count == len("scanned words")
    assert len(reader.calls) == 1


def test_successful_ocr_reporting_no_text_is_a_complete_zero_count(blank_pdf):
    measurement = DocumentMeasurer(
        ocr_mode="auto", ocr_reader=RecordingReader(text="")
    ).measure(blank_pdf)

    page = measurement.pages[0]
    assert (page.method, page.status, page.character_count) == ("ocr", "complete", 0)
    assert measurement.status == "complete"


def test_always_mode_replaces_native_text_instead_of_adding_to_it(native_pdf):
    reader = RecordingReader(text="ocr only")
    measurement = DocumentMeasurer(ocr_mode="always", ocr_reader=reader).measure(
        native_pdf
    )

    page = measurement.pages[0]
    assert (page.method, page.status) == ("ocr", "complete")
    assert page.character_count == len("ocr only")
    assert len(reader.calls) == 1


def test_failed_ocr_keeps_the_native_estimate_and_reports_partial(native_pdf):
    reader = RecordingReader(error=RuntimeError("engine crashed"))
    measurement = DocumentMeasurer(ocr_mode="always", ocr_reader=reader).measure(
        native_pdf
    )

    page = measurement.pages[0]
    assert (page.method, page.status, page.error_code) == (
        "native",
        "partial",
        "ocr_failed",
    )
    assert page.character_count == len("Hello measurement")
    assert measurement.status == "partial"


def test_unavailable_ocr_engine_is_reported_without_a_fake_count(blank_pdf):
    reader = RecordingReader(error=OcrEngineUnavailableError("missing engine"))
    measurement = DocumentMeasurer(ocr_mode="auto", ocr_reader=reader).measure(
        blank_pdf
    )

    page = measurement.pages[0]
    assert (page.method, page.status, page.error_code) == (
        "none",
        "partial",
        "ocr_unavailable",
    )
    assert page.character_count == 0


def test_document_totals_aggregate_measured_and_unmeasured_pages(mixed_pdf):
    measurement = DocumentMeasurer().measure(mixed_pdf)

    assert [page.page_number for page in measurement.pages] == [1, 2]
    assert [page.method for page in measurement.pages] == ["native", "none"]
    assert measurement.character_count == len("Invoice total 42")
    assert measurement.status == "partial"
    assert measurement.error_codes == ("ocr_skipped",)


def test_one_reader_serves_every_page_and_document(mixed_pdf, blank_pdf):
    reader = RecordingReader()
    measurer = DocumentMeasurer(ocr_mode="always", ocr_reader=reader)

    measurer.measure(mixed_pdf)
    measurer.measure(blank_pdf)

    assert len(reader.calls) == 3


def test_rendered_pages_stay_within_the_pixel_budget(native_pdf):
    reader = RecordingReader()
    DocumentMeasurer(
        ocr_mode="always", ocr_reader=reader, max_render_pixels=20_000
    ).measure(native_pdf)

    height, width = reader.calls[0].shape[:2]
    assert 0 < height * width <= 20_000

    full_reader = RecordingReader()
    DocumentMeasurer(ocr_mode="always", ocr_reader=full_reader).measure(native_pdf)
    full_height, full_width = full_reader.calls[0].shape[:2]
    assert full_height * full_width > height * width


def test_repeated_measurements_are_deterministic(mixed_pdf):
    measurer = DocumentMeasurer()
    first = measurer.measure(mixed_pdf)
    second = measurer.measure(mixed_pdf)

    assert first == second
    assert first is not second


def test_measurement_never_modifies_the_input_file(native_pdf):
    original = native_pdf.read_bytes()
    DocumentMeasurer(ocr_mode="always", ocr_reader=RecordingReader()).measure(
        native_pdf
    )

    assert native_pdf.read_bytes() == original


def test_extraction_input_preparation_is_unaffected_by_measurement(native_pdf):
    from structx.utils.file_reader import FileReader

    before = FileReader.read_file(native_pdf)
    DocumentMeasurer(ocr_mode="always", ocr_reader=RecordingReader()).measure(
        native_pdf
    )
    after = FileReader.read_file(native_pdf)

    assert before.pdf_rows[0].pdf_path == native_pdf
    assert after.pdf_rows[0].pdf_path == native_pdf
    assert before.planning_sample == after.planning_sample
    assert after.owned_paths == []


@pytest.mark.parametrize(
    "factory",
    [
        lambda: DocumentMeasurer(ocr_mode="sometimes"),
        lambda: DocumentMeasurer(ocr_reader="not callable"),
        lambda: DocumentMeasurer(max_pages=0),
        lambda: DocumentMeasurer(max_pages=True),
        lambda: DocumentMeasurer(max_input_bytes=-1),
        lambda: DocumentMeasurer(render_dpi=0),
        lambda: DocumentMeasurer(render_dpi=float("inf")),
        lambda: DocumentMeasurer(max_render_pixels=0),
    ],
)
def test_invalid_settings_are_rejected(factory):
    with pytest.raises(ConfigurationError):
        factory()


def test_missing_file_is_rejected(tmp_path):
    with pytest.raises(FileError, match="File not found"):
        DocumentMeasurer().measure(tmp_path / "absent.pdf")


def test_directory_input_is_rejected(tmp_path):
    with pytest.raises(FileError, match="Path is not a file"):
        DocumentMeasurer().measure(tmp_path)


def test_empty_file_is_rejected(tmp_path):
    empty = tmp_path / "empty.pdf"
    empty.write_bytes(b"")
    with pytest.raises(FileError, match="File is empty"):
        DocumentMeasurer().measure(empty)


def test_non_pdf_input_is_rejected(tmp_path):
    csv_path = tmp_path / "rows.csv"
    csv_path.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(FileError, match="PDF input only"):
        DocumentMeasurer().measure(csv_path)


def test_file_without_pdf_header_is_rejected(tmp_path):
    fake = tmp_path / "fake.pdf"
    fake.write_bytes(b"not a pdf at all")
    with pytest.raises(FileError, match="Invalid PDF file"):
        DocumentMeasurer().measure(fake)


def test_oversized_input_is_rejected(native_pdf):
    with pytest.raises(FileError, match="byte measurement limit"):
        DocumentMeasurer(max_input_bytes=16).measure(native_pdf)


def test_page_limit_is_reported_instead_of_truncating_coverage(mixed_pdf):
    with pytest.raises(FileError, match="page measurement limit"):
        DocumentMeasurer(max_pages=1).measure(mixed_pdf)


def test_unreadable_pdf_is_reported_as_a_file_error(tmp_path):
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"%PDF-1.4\nnot really a document\n%%EOF\n")
    with pytest.raises(FileError):
        DocumentMeasurer().measure(broken)


def test_missing_pdf_backend_is_reported_as_configuration_error(monkeypatch, tmp_path):
    from structx import measurement

    target = tmp_path / "input.pdf"
    build_pdf(target, ["text"])
    monkeypatch.delitem(sys.modules, "pypdfium2", raising=False)
    monkeypatch.setattr("builtins.__import__", _import_failing_on("pypdfium2"))

    with pytest.raises(ConfigurationError, match="structx\\[measurement\\]"):
        measurement.DocumentMeasurer().measure(target)


def test_empty_measurement_reports_partial_status():
    assert DocumentMeasurement().status == "partial"
    assert DocumentMeasurement().page_count == 0


def install_fake_rapidocr(monkeypatch, texts=("first line", "second line"), error=None):
    calls = {}

    class FakeResult:
        txts = tuple(texts) if texts is not None else None

    class FakeRapidOCR:
        def __init__(self, **kwargs):
            calls["init"] = calls.get("init", 0) + 1
            calls["kwargs"] = kwargs
            if error is not None:
                raise error

        def __call__(self, image):
            calls["images"] = calls.get("images", []) + [image]
            return FakeResult()

    module = types.ModuleType("rapidocr")
    module.RapidOCR = FakeRapidOCR
    monkeypatch.setitem(sys.modules, "rapidocr", module)
    return calls


def test_default_reader_does_not_import_the_engine_until_used(monkeypatch):
    monkeypatch.delitem(sys.modules, "rapidocr", raising=False)
    create_default_ocr_reader()

    assert "rapidocr" not in sys.modules


def test_default_reader_joins_recognized_lines(monkeypatch):
    calls = install_fake_rapidocr(monkeypatch)
    reader = create_default_ocr_reader()

    assert reader("first image") == "first line\nsecond line"
    assert reader("second image") == "first line\nsecond line"
    assert calls["init"] == 1
    assert len(calls["images"]) == 2


def test_default_reader_returns_empty_text_when_nothing_is_recognized(monkeypatch):
    install_fake_rapidocr(monkeypatch, texts=None)

    assert create_default_ocr_reader()("image") == ""


def test_default_reader_forwards_engine_parameters(monkeypatch):
    calls = install_fake_rapidocr(monkeypatch)
    RapidOcrReader(params={"Rec.model_type": "tiny"})("image")

    assert calls["kwargs"] == {"params": {"Rec.model_type": "tiny"}}


def test_default_reader_reports_unavailable_engine(monkeypatch):
    monkeypatch.delitem(sys.modules, "rapidocr", raising=False)
    monkeypatch.setattr(
        "builtins.__import__",
        _import_failing_on("rapidocr"),
    )

    with pytest.raises(OcrEngineUnavailableError, match="measurement-ocr"):
        create_default_ocr_reader()("image")


def test_default_reader_reports_engine_initialization_failure(monkeypatch):
    install_fake_rapidocr(monkeypatch, error=RuntimeError("no models"))

    with pytest.raises(OcrEngineUnavailableError, match="Could not initialize"):
        create_default_ocr_reader()("image")


def _import_failing_on(missing_name):
    import builtins

    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == missing_name:
            raise ImportError(f"no {missing_name}")
        return original_import(name, *args, **kwargs)

    return guarded_import


@pytest.mark.integration
def test_real_ocr_measures_a_rasterized_page(tmp_path, native_pdf):
    scanned = tmp_path / "scanned.pdf"
    _rasterize(native_pdf, scanned)

    without_ocr = DocumentMeasurer().measure(scanned)
    assert without_ocr.pages[0].error_code == "ocr_skipped"

    with_ocr = DocumentMeasurer(ocr_mode="auto").measure(scanned)
    page = with_ocr.pages[0]
    assert (page.method, page.status) == ("ocr", "complete")
    assert page.character_count > 0


def _rasterize(source: Path, target: Path) -> None:
    """Render a PDF's pages into an image-only PDF for OCR testing."""
    source_document = pdfium.PdfDocument(source)
    target_document = pdfium.PdfDocument.new()
    try:
        for index in range(len(source_document)):
            page = source_document[index]
            width, height = page.get_size()
            bitmap = page.render(scale=200 / 72)
            image = pdfium.PdfImage.new(target_document)
            image.set_bitmap(bitmap)
            image.set_matrix(pdfium.PdfMatrix().scale(width, height))
            new_page = target_document.new_page(width, height)
            new_page.insert_obj(image)
            new_page.gen_content()
            bitmap.close()
            page.close()
        target_document.save(target)
    finally:
        target_document.close()
        source_document.close()
