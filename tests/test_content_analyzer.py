import pandas as pd

from structx.core.input import PdfRow, PreparedInput
from structx.extraction.processors.content_analyzer import ContentAnalyzer


def test_detect_content_type_for_tabular_data():
    prepared_input = PreparedInput(
        dataframe=pd.DataFrame({"id": [1], "message": ["hello"]})
    )

    assert (
        ContentAnalyzer.detect_content_type_and_context(prepared_input)
        == "tabular data with structured columns"
    )


def test_detect_content_type_for_explicit_document_payloads(sample_docx_path, tmp_path):
    txt_path = tmp_path / "notes.txt"
    prepared_input = PreparedInput(
        dataframe=pd.DataFrame({"source": [str(sample_docx_path), str(txt_path)]}),
        pdf_rows={
            0: PdfRow(tmp_path / "first.pdf", sample_docx_path),
            1: PdfRow(tmp_path / "second.pdf", txt_path),
        },
    )

    context = ContentAnalyzer.detect_content_type_and_context(prepared_input)

    assert "docx" in context
    assert "txt" in context
    assert sample_docx_path.name in context
    assert "notes.txt" in context
