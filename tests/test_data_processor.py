import asyncio

import pandas as pd

from structx.extraction.processors.data_processor import DataProcessor
from structx.utils.file_reader import FileReader


def test_prepare_data_returns_dataframe_unchanged():
    source_df = pd.DataFrame({"message": ["hello"]})

    result = DataProcessor().prepare_data(source_df)

    assert result is source_df


def test_prepare_data_converts_list_of_dicts_to_dataframe():
    result = DataProcessor().prepare_data([{"message": "hello"}, {"message": "world"}])

    assert result["message"].tolist() == ["hello", "world"]


def test_prepare_data_adds_text_column_for_single_column_dataframe():
    result = DataProcessor().prepare_data(pd.DataFrame({"message": ["hello"]}))

    assert result["text"].tolist() == ["hello"]


def test_prepare_data_reads_existing_file(monkeypatch, tmp_path):
    source_path = tmp_path / "notes.txt"
    source_path.write_text("hello", encoding="utf-8")

    def fake_read_file(path, **kwargs):
        assert path == source_path
        assert kwargs == {"file_options": {"encoding": "utf-8"}}
        return pd.DataFrame({"pdf_path": ["/tmp/fake.pdf"], "multimodal": [True]})

    monkeypatch.setattr(FileReader, "read_file", fake_read_file)

    result = DataProcessor().prepare_data(
        source_path,
        file_options={"encoding": "utf-8"},
    )

    assert result.loc[0, "pdf_path"] == "/tmp/fake.pdf"


def test_prepare_data_writes_raw_text_to_temp_file(monkeypatch):
    captured = {}

    def fake_read_file(path, **kwargs):
        captured["path"] = path
        with open(path, encoding="utf-8") as temp_file:
            captured["content"] = temp_file.read()
        return pd.DataFrame(
            {
                "pdf_path": ["/tmp/fake.pdf"],
                "source": ["old-source"],
                "multimodal": [True],
                "file_type": ["pdf"],
            }
        )

    monkeypatch.setattr(FileReader, "read_file", fake_read_file)

    result = DataProcessor().prepare_data("raw incident text")

    assert captured["content"] == "raw incident text"
    assert result.loc[0, "source"] == captured["path"]


def test_process_in_batches_passes_tabular_rows_as_markdown():
    seen = []

    def worker(row_data, row_idx, semaphore, pbar):
        seen.append((row_idx, row_data))

    df = pd.DataFrame({"message": ["hello", "world"]})

    DataProcessor(max_threads=1, batch_size=1).process_in_batches(
        df,
        worker,
        ["message"],
    )

    assert [idx for idx, _ in seen] == [0, 1]
    assert "hello" in seen[0][1]
    assert "world" in seen[1][1]


def test_process_batch_passes_multimodal_rows_as_dicts():
    seen = []

    def worker(row_data, row_idx, semaphore, pbar):
        seen.append((row_idx, row_data))

    df = pd.DataFrame(
        {
            "pdf_path": ["/tmp/doc.pdf"],
            "multimodal": [True],
            "file_type": ["pdf"],
            "source": ["doc.md"],
        }
    )

    DataProcessor(max_threads=1).process_batch(df, worker, ["source"])

    assert seen == [
        (
            0,
            {
                "pdf_path": "/tmp/doc.pdf",
                "multimodal": True,
                "file_type": "pdf",
                "source": "doc.md",
            },
        )
    ]


def test_run_async_passes_args_and_kwargs():
    async def run():
        return await DataProcessor().run_async(
            lambda first, *, second: f"{first}-{second}",
            "one",
            second="two",
        )

    assert asyncio.run(run()) == "one-two"
