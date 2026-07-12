from pathlib import Path

import pandas as pd
import pytest

from structx.core.exceptions import FileError
from structx.core.input import PdfRow, PreparedInput
from structx.extraction.processors.batch_processor import BatchProcessor
from structx.extraction.processors.input_processor import InputProcessor
from structx.utils.file_reader import FileReader


def test_prepare_data_returns_dataframe_unchanged():
    source_df = pd.DataFrame({"message": ["hello"]})

    result = InputProcessor().prepare(source_df)

    assert result.dataframe is source_df


def test_prepare_data_converts_list_of_dicts_to_dataframe():
    result = InputProcessor().prepare([{"message": "hello"}, {"message": "world"}])

    assert result.dataframe["message"].tolist() == ["hello", "world"]


def test_prepare_data_preserves_single_column_dataframe_schema():
    result = InputProcessor().prepare(pd.DataFrame({"message": ["hello"]}))

    assert result.dataframe.columns.tolist() == ["message"]


def test_prepare_data_normalizes_non_string_column_names():
    source_df = pd.DataFrame({1: ["hello"], "message": ["world"]})

    result = InputProcessor().prepare(source_df)

    assert result.dataframe.columns.tolist() == ["1", "message"]
    assert source_df.columns.tolist() == [1, "message"]


def test_prepare_data_rejects_duplicate_column_names():
    source_df = pd.DataFrame([["hello", "world"]], columns=["text", "text"])

    with pytest.raises(ValueError, match="Column names must be unique"):
        InputProcessor().prepare(source_df)


def test_prepare_data_reads_existing_file(monkeypatch, tmp_path):
    source_path = tmp_path / "notes.txt"
    source_path.write_text("hello", encoding="utf-8")

    def fake_read_file(path, **kwargs):
        assert path == source_path
        assert kwargs == {"file_options": {"encoding": "utf-8"}}
        return PreparedInput(
            dataframe=pd.DataFrame({"source": [str(source_path)]}),
            pdf_rows={0: PdfRow(pdf_path=Path("/tmp/fake.pdf"), source=source_path)},
        )

    monkeypatch.setattr(FileReader, "read_file", fake_read_file)

    result = InputProcessor().prepare(
        source_path,
        file_options={"encoding": "utf-8"},
    )

    assert result.pdf_rows[0].pdf_path == Path("/tmp/fake.pdf")


def test_prepare_data_keeps_raw_text_in_memory(monkeypatch):
    monkeypatch.setattr(
        FileReader,
        "read_file",
        lambda *args, **kwargs: pytest.fail("raw text should not use FileReader"),
    )
    result = InputProcessor().prepare("raw incident text")

    assert result.dataframe.to_dict(orient="records") == [{"text": "raw incident text"}]
    assert result.owned_paths == []


@pytest.mark.parametrize("data", ["", "   ", [], pd.DataFrame()])
def test_prepare_data_rejects_empty_input(data):
    with pytest.raises(ValueError, match="Input .* is empty"):
        InputProcessor().prepare(data)


@pytest.mark.parametrize(
    "missing_path",
    [
        "/tmp/structx-missing-document.docx",
        "/tmp/structx-missing.unknown",
        Path("/tmp/structx-missing.pdf"),
    ],
)
def test_prepare_data_rejects_missing_file_paths(missing_path):
    with pytest.raises(FileError, match="File not found"):
        InputProcessor().prepare(missing_path)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"max_threads": 0}, "max_threads"),
        ({"batch_size": 0}, "batch_size"),
    ],
)
def test_batch_processor_rejects_invalid_runtime_settings(kwargs, message):
    with pytest.raises(ValueError, match=message):
        BatchProcessor(**kwargs)


def test_process_in_batches_passes_tabular_rows_as_markdown():
    seen = []

    def worker(row_data, row_position, row_label):
        seen.append((row_position, row_label, row_data))

    df = pd.DataFrame({"message": ["hello", "world"]})

    BatchProcessor(max_threads=1, batch_size=1).map_rows(
        PreparedInput(dataframe=df),
        worker,
        ["message"],
    )

    assert [(position, label) for position, label, _ in seen] == [(0, 0), (1, 1)]
    assert "hello" in seen[0][2]
    assert "world" in seen[1][2]


def test_process_batch_passes_pdf_rows_as_typed_payloads(tmp_path):
    seen = []

    def worker(row_data, row_position, row_label):
        seen.append((row_position, row_label, row_data))

    source = tmp_path / "doc.md"
    pdf = tmp_path / "doc.pdf"
    prepared_input = PreparedInput(
        dataframe=pd.DataFrame({"source": [str(source)]}),
        pdf_rows={0: PdfRow(pdf_path=pdf, source=source)},
    )

    BatchProcessor(max_threads=1).map_rows(prepared_input, worker, ["source"])

    assert seen == [(0, 0, PdfRow(pdf_path=pdf, source=source))]


def test_cleanup_data_removes_all_owned_temporary_paths(tmp_path):
    paths = [tmp_path / "source.txt", tmp_path / "rendered.pdf"]
    for path in paths:
        path.write_text("temporary", encoding="utf-8")
    prepared_input = PreparedInput(
        dataframe=pd.DataFrame({"source": [str(paths[0])]}),
        owned_paths=paths.copy(),
    )

    InputProcessor.cleanup(prepared_input)

    assert all(not path.exists() for path in paths)
    assert prepared_input.owned_paths == []
    assert prepared_input.closed


def test_explicitly_prepared_input_is_reused_without_automatic_cleanup(tmp_path):
    owned_path = tmp_path / "rendered.pdf"
    owned_path.write_text("temporary", encoding="utf-8")
    prepared_input = PreparedInput(
        dataframe=pd.DataFrame({"source": ["document.docx"]}),
        owned_paths=[owned_path],
    )
    processor = InputProcessor()

    with processor.prepared(prepared_input) as reused:
        assert reused is prepared_input

    assert owned_path.exists()
    assert not prepared_input.closed

    prepared_input.close()
    prepared_input.close()

    assert not owned_path.exists()
    assert prepared_input.closed
    with pytest.raises(RuntimeError, match="closed"):
        processor.prepare(prepared_input)
