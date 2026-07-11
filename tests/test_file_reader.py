import sys
import types

import pandas as pd
import pytest

from structx.core.exceptions import FileError
from structx.utils.file_reader import FileReader


def install_fake_document_modules(monkeypatch, text="sample text", html="<h1>Doc</h1>"):
    calls = {}

    class FakeDocument:
        def export_to_html(self):
            return html

        def export_to_text(self):
            return text

    class FakeResult:
        document = FakeDocument()

    class FakePipelineOptions:
        def __init__(self):
            self.do_ocr = True
            self.do_table_structure = True

    class FakeFormatOption:
        def __init__(self, *, pipeline_options):
            self.pipeline_options = pipeline_options

    class FakeInputFormat:
        IMAGE = "image"

    class FakeDocumentConverter:
        def __init__(self, **kwargs):
            calls["converter_kwargs"] = kwargs

        def convert(self, path):
            calls["converted_path"] = path
            return FakeResult()

    class FakeHTML:
        def __init__(self, *, string, base_url=None):
            calls["html"] = string
            calls["base_url"] = base_url

        def write_pdf(self, path):
            calls["pdf_path"] = path
            with open(path, "wb") as pdf_file:
                pdf_file.write(b"%PDF-1.4 fake")

    docling_module = types.ModuleType("docling")
    datamodel_module = types.ModuleType("docling.datamodel")
    base_models_module = types.ModuleType("docling.datamodel.base_models")
    base_models_module.InputFormat = FakeInputFormat
    pipeline_options_module = types.ModuleType("docling.datamodel.pipeline_options")
    pipeline_options_module.PdfPipelineOptions = FakePipelineOptions
    converter_module = types.ModuleType("docling.document_converter")
    converter_module.DocumentConverter = FakeDocumentConverter
    converter_module.ImageFormatOption = FakeFormatOption
    weasyprint_module = types.ModuleType("weasyprint")
    weasyprint_module.HTML = FakeHTML

    monkeypatch.setitem(sys.modules, "docling", docling_module)
    monkeypatch.setitem(sys.modules, "docling.datamodel", datamodel_module)
    monkeypatch.setitem(
        sys.modules, "docling.datamodel.base_models", base_models_module
    )
    monkeypatch.setitem(
        sys.modules,
        "docling.datamodel.pipeline_options",
        pipeline_options_module,
    )
    monkeypatch.setitem(sys.modules, "docling.document_converter", converter_module)
    monkeypatch.setitem(sys.modules, "weasyprint", weasyprint_module)

    return calls


def test_read_structured_csv_uses_pandas_reader(tmp_path):
    csv_path = tmp_path / "incidents.csv"
    csv_path.write_text("id,message\n1,hello\n2,world\n", encoding="utf-8")

    df = FileReader.read_file(csv_path)

    assert list(df.columns) == ["id", "message"]
    assert df["message"].tolist() == ["hello", "world"]


def test_read_document_file_converts_to_multimodal_pdf(monkeypatch, sample_docx_path):
    calls = install_fake_document_modules(monkeypatch)

    df = FileReader.read_file(sample_docx_path)

    assert df.to_dict(orient="records")[0]["source"] == str(sample_docx_path)
    assert df.to_dict(orient="records")[0]["multimodal"] is True
    assert df.to_dict(orient="records")[0]["file_type"] == "pdf"
    assert calls["converted_path"] == str(sample_docx_path)
    assert calls["html"] == "<h1>Doc</h1>"
    assert calls["base_url"] == str(sample_docx_path.parent)
    assert calls["pdf_path"] == df.loc[0, "pdf_path"]
    assert df.attrs["content_sample"] == "sample text"
    format_options = calls["converter_kwargs"]["format_options"]
    assert format_options["image"].pipeline_options.do_ocr is False
    assert format_options["image"].pipeline_options.do_table_structure is False


def test_empty_document_is_rejected_before_conversion(monkeypatch, tmp_path):
    calls = install_fake_document_modules(monkeypatch)
    empty_document = tmp_path / "empty.docx"
    empty_document.touch()

    with pytest.raises(FileError, match="File is empty"):
        FileReader.read_file(empty_document)

    assert "converted_path" not in calls


def test_invalid_pdf_is_rejected(tmp_path):
    invalid_pdf = tmp_path / "invalid.pdf"
    invalid_pdf.write_text("not a pdf", encoding="utf-8")

    with pytest.raises(FileError, match="Invalid PDF"):
        FileReader.read_file(invalid_pdf)


def test_read_sample_pdf_passes_existing_pdf_through(sample_pdf_path):
    df = FileReader.read_file(sample_pdf_path)

    record = df.to_dict(orient="records")[0]
    assert record["source"] == str(sample_pdf_path)
    assert record["pdf_path"] == str(sample_pdf_path)
    assert record["file_type"] == "pdf"


def test_extract_text_sample_uses_docling(monkeypatch, sample_docx_path):
    install_fake_document_modules(monkeypatch, text="abcdef")

    assert FileReader.extract_text_sample(sample_docx_path, max_chars=3) == "abc"


def test_extract_text_sample_returns_empty_for_pdf_without_docling(sample_pdf_path):
    assert FileReader.extract_text_sample(sample_pdf_path, max_chars=3) == ""


def test_get_file_type_classifies_structured_document_and_unknown(
    sample_docx_path,
    sample_pdf_path,
):
    assert FileReader.get_file_type("data.csv") == "structured"
    assert FileReader.get_file_type(sample_docx_path) == "document"
    assert FileReader.get_file_type(sample_pdf_path) == "document"
    assert FileReader.get_file_type("slides.ppt") == "document"
    assert FileReader.get_file_type("archive.zip") == "unknown"


def test_read_file_forwards_file_options_to_structured_reader(tmp_path):
    csv_path = tmp_path / "semi.csv"
    csv_path.write_text("id;message\n1;hello\n", encoding="utf-8")

    df = FileReader.read_file(csv_path, file_options={"sep": ";"})

    assert df.to_dict(orient="records") == [{"id": 1, "message": "hello"}]
