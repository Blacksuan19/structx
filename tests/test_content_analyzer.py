import pandas as pd

from structx.extraction.processors.content_analyzer import ContentAnalyzer
from structx.utils.file_reader import FileReader


def test_detect_content_type_for_tabular_data():
    df = pd.DataFrame({"id": [1], "message": ["hello"]})

    assert (
        ContentAnalyzer.detect_content_type_and_context(df)
        == "tabular data with structured columns"
    )


def test_detect_content_type_for_file_sources(sample_docx_path, tmp_path):
    txt_path = tmp_path / "notes.txt"
    txt_path.write_text("notes", encoding="utf-8")

    df = pd.DataFrame({"source": [str(sample_docx_path), str(txt_path)]})

    context = ContentAnalyzer.detect_content_type_and_context(df)

    assert "Word document" in context
    assert "Text document" in context
    assert "free-consultancy-agreement.docx" in context
    assert "notes.txt" in context


def test_extract_content_sample_for_schema_uses_file_reader(
    monkeypatch, sample_pdf_path
):
    def fake_extract_text_sample(path, max_chars=2000):
        assert path == sample_pdf_path
        assert max_chars == 7
        return "sample text"

    monkeypatch.setattr(FileReader, "extract_text_sample", fake_extract_text_sample)
    df = pd.DataFrame({"source": [str(sample_pdf_path)]})

    assert (
        ContentAnalyzer.extract_content_sample_for_schema(df, max_chars=7)
        == "sample text"
    )


def test_extract_content_sample_for_schema_handles_tabular_rows():
    df = pd.DataFrame({"id": [1], "message": ["hello"], "empty": [None]})

    sample = ContentAnalyzer.extract_content_sample_for_schema(df)

    assert sample == "id: 1 | message: hello"


def test_extract_content_sample_for_schema_uses_cached_conversion():
    df = pd.DataFrame({"source": ["document.docx"]})
    df.attrs["content_sample"] = "already parsed"

    assert ContentAnalyzer.extract_content_sample_for_schema(df) == "already parsed"


def test_extract_content_sample_for_schema_limits_to_three_rows():
    df = pd.DataFrame({"message": ["one", "two", "three", "four"]})

    sample = ContentAnalyzer.extract_content_sample_for_schema(df)

    assert "message: one" in sample
    assert "message: three" in sample
    assert "message: four" not in sample


def test_suggest_column_mappings_uses_names_descriptions_and_text_fallback():
    model_properties = {
        "incident_date": {},
        "summary": {},
        "owner": {},
    }
    data_columns = ["Incident Date", "description_text", "assignee"]
    field_descriptions = {
        "summary": {"description": "short description of the incident"},
        "owner": {"description": "responsible person"},
    }

    suggestions = ContentAnalyzer.suggest_column_mappings(
        model_properties,
        data_columns,
        field_descriptions,
    )

    assert suggestions["incident_date"] == ["Incident Date"]
    assert "description_text" in suggestions["summary"]
    assert suggestions["owner"] == ["description_text"]
