import asyncio
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from structx.core.exceptions import ExtractionError
from structx.extraction.extractor import Extractor


class AsyncRecord(BaseModel):
    """One independently extracted row."""

    value: str


class TrackingAsyncCompletions:
    def __init__(self):
        self.active = 0
        self.max_active = 0

    async def create_with_completion(self, **kwargs):
        text = str(kwargs["messages"][1]["content"])
        marker = next(value for value in ("row-0", "row-1", "row-2") if value in text)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep({"row-0": 0.03, "row-1": 0.01, "row-2": 0.02}[marker])
            if marker == "row-1":
                raise ValueError("row failed")
            result = kwargs["response_model"](items=[AsyncRecord(value=marker)])
            completion = SimpleNamespace(
                usage={
                    "prompt_tokens": 10,
                    "completion_tokens": 2,
                    "total_tokens": 12,
                }
            )
            return result, completion
        finally:
            self.active -= 1


def test_extract_async_uses_bounded_concurrency_and_stable_row_mapping():
    completions = TrackingAsyncCompletions()
    extractor = Extractor(
        client=SimpleNamespace(),
        async_client=SimpleNamespace(chat=SimpleNamespace(completions=completions)),
        model_name="provider/model",
        max_threads=2,
        max_retries=0,
    )

    result = asyncio.run(
        extractor.extract_async(
            data=[{"text": "row-0"}, {"text": "row-1"}, {"text": "row-2"}],
            query="extract value",
            model=AsyncRecord,
        )
    )

    assert [item.value for item in result.data] == ["row-0", "row-2"]
    assert result.failed.iloc[0]["index"] == 1
    assert "row failed" in result.failed.iloc[0]["error"]
    assert result.success_count == 2
    assert completions.max_active == 2
    assert len(result.usage.get_step("extraction")) == 2
    assert result.rows[0].usage.total_tokens == 12
    assert result.rows[1].usage.total_tokens == 0
    assert result.rows[2].usage.total_tokens == 12


def test_extract_async_requires_an_async_client_for_provider_calls():
    extractor = Extractor(
        client=SimpleNamespace(),
        model_name="provider/model",
        max_retries=0,
    )

    with pytest.raises(ExtractionError, match="requires an async Instructor client"):
        asyncio.run(
            extractor.extract_async(
                data=[{"text": "row-0"}],
                query="extract value",
                model=AsyncRecord,
            )
        )
