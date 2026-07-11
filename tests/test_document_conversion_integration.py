from pathlib import Path

import pytest

from structx.utils.file_reader import FileReader

pytest.importorskip(
    "docling.document_converter",
    reason="optional document dependencies are not installed",
)
pytest.importorskip(
    "weasyprint",
    reason="optional document dependencies are not installed",
)


def assert_pdf_output(pdf_path: Path):
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0
    assert pdf_path.read_bytes().startswith(b"%PDF")


@pytest.mark.integration
def test_sample_docx_converts_to_real_pdf(sample_docx_path):
    prepared_input = FileReader.read_file(sample_docx_path)
    pdf_path = prepared_input.pdf_rows[0].pdf_path

    assert prepared_input.dataframe.loc[0, "source"] == str(sample_docx_path)
    assert "consultancy agreement" in prepared_input.planning_sample.lower()
    assert_pdf_output(pdf_path)


@pytest.mark.integration
def test_sample_pdf_is_passed_through_for_multimodal_input(sample_pdf_path):
    prepared_input = FileReader.read_file(sample_pdf_path)
    pdf_path = prepared_input.pdf_rows[0].pdf_path

    assert prepared_input.dataframe.loc[0, "source"] == str(sample_pdf_path)
    assert pdf_path == sample_pdf_path
    assert_pdf_output(pdf_path)


@pytest.mark.integration
def test_real_docling_text_sampling_for_example_documents(
    sample_docx_path,
):
    docx_sample = FileReader.extract_text_sample(sample_docx_path, max_chars=300)

    assert "consultancy agreement" in docx_sample.lower()
