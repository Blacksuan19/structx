"""Opt-in tests against the endpoint configured in the local environment."""

import asyncio
import json
from decimal import Decimal

import pytest
from pydantic import BaseModel

from structx import Extractor


class LiveInvoice(BaseModel):
    invoice_number: str
    total_amount: Decimal


@pytest.mark.live
def test_live_dynamic_schema_and_text_extraction(live_llm_config):
    extractor = Extractor.from_litellm(
        model=live_llm_config.model,
        api_key=live_llm_config.api_key,
        api_base=live_llm_config.api_base,
        max_threads=1,
        max_retries=1,
    )

    result = extractor.extract(
        data=[{"text": "Invoice INV-42 is due on 2026-08-15 for USD 125.50."}],
        query="extract the invoice number, due date, and total amount",
    )

    assert result.success_count == 1
    assert len(result.data) == 1
    serialized = json.dumps(result.data[0].model_dump(mode="json"))
    assert "INV-42" in serialized
    assert "2026-08-15" in serialized
    assert "125.5" in serialized
    assert result.usage.get_step("schema_generation")
    assert result.usage.get_step("extraction")
    assert result.usage.total_tokens > 0


@pytest.mark.live
def test_live_async_rows_with_custom_model(live_llm_config):
    extractor = Extractor.from_litellm(
        model=live_llm_config.model,
        api_key=live_llm_config.api_key,
        api_base=live_llm_config.api_base,
        max_threads=3,
        max_retries=1,
    )
    rows = [
        {"text": "Invoice A-1 totals USD 10.00."},
        {"text": "Invoice B-2 totals USD 20.00."},
        {"text": "Invoice C-3 totals USD 30.00."},
    ]

    result = asyncio.run(
        extractor.extract_async(
            data=rows,
            query="extract the invoice number and total amount",
            model=LiveInvoice,
        )
    )

    assert [item.invoice_number for item in result.data] == ["A-1", "B-2", "C-3"]
    assert [item.total_amount for item in result.data] == [
        Decimal("10.00"),
        Decimal("20.00"),
        Decimal("30.00"),
    ]
    assert result.usage.get_step("schema_generation") == []
    assert len(result.usage.get_step("extraction")) == 3
