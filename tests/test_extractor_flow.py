from types import SimpleNamespace
from contextlib import contextmanager

import pandas as pd
import pytest

from structx.core.exceptions import ConfigurationError, ExtractionError
from structx.core.input import PreparedInput
from structx.extraction.extractor import Extractor


def _unused_client():
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace()))


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"max_threads": 0}, "max_threads"),
        ({"batch_size": 0}, "batch_size"),
        ({"max_retries": -1}, "max_retries"),
        ({"min_wait": 2, "max_wait": 1}, "wait settings"),
    ],
)
def test_extractor_rejects_invalid_runtime_settings(kwargs, message):
    with pytest.raises(ConfigurationError, match=message):
        Extractor(client=_unused_client(), model_name="provider/model", **kwargs)


def test_get_schema_rejects_a_missing_file_before_planning(tmp_path):
    extractor = Extractor(client=_unused_client(), model_name="provider/model")
    missing_path = tmp_path / "missing.docx"

    with pytest.raises(ExtractionError, match="File not found"):
        extractor.get_schema(
            data=str(missing_path),
            query="extract contract terms",
        )


@pytest.mark.parametrize("queries", [[], ["valid", "valid"], [" "]])
def test_extract_queries_rejects_invalid_queries_before_preparing_data(
    monkeypatch, queries
):
    extractor = Extractor(client=_unused_client(), model_name="provider/model")
    monkeypatch.setattr(
        extractor.input_processor,
        "prepare",
        lambda *args, **kwargs: pytest.fail("data should not be prepared"),
    )

    with pytest.raises(ExtractionError):
        extractor.extract_queries(data="raw text", queries=queries)


def test_extract_queries_prepares_and_cleans_data_once(monkeypatch):
    extractor = Extractor(client=_unused_client(), model_name="provider/model")
    df = pd.DataFrame({"text": ["agreement"]})
    calls = {"prepare": 0, "cleanup": 0, "process": []}

    @contextmanager
    def prepared(*args, **kwargs):
        calls["prepare"] += 1
        try:
            yield PreparedInput(dataframe=df)
        finally:
            calls["cleanup"] += 1

    def process(prepared_input, query, return_df, expand_nested):
        assert prepared_input.dataframe is df
        calls["process"].append(query)
        return query

    monkeypatch.setattr(extractor.input_processor, "prepared", prepared)
    monkeypatch.setattr(extractor, "_process_data", process)

    results = extractor.extract_queries(
        data="agreement",
        queries=["payment", "termination"],
    )

    assert results == {"payment": "payment", "termination": "termination"}
    assert calls == {
        "prepare": 1,
        "cleanup": 1,
        "process": ["payment", "termination"],
    }
