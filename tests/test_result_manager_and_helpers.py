import pandas as pd
from pydantic import BaseModel

from structx.core.models import ExtractionResult, RowResult
from structx.extraction.result_manager import ResultCollector
from structx.utils.helpers import flatten_extracted_data
from structx.utils.usage import ExtractorUsage


class NestedItem(BaseModel):
    name: str
    details: dict
    tags: list[str]


def test_flatten_extracted_data_handles_nested_dicts_and_lists():
    flattened = flatten_extracted_data(
        {
            "name": "incident",
            "details": {"date": "2026-01-01"},
            "tags": ["a", "b"],
            "events": [{"time": "one"}, {"time": "two"}],
        }
    )

    assert flattened == {
        "name": "incident",
        "details_date": "2026-01-01",
        "tags": '["a", "b"]',
        "events_0_time": "one",
        "events_1_time": "two",
    }


def test_result_collector_initializes_and_updates_dataframe():
    df = pd.DataFrame({"source": ["row"]})
    collector = ResultCollector(
        source=df,
        model=NestedItem,
        return_df=True,
        expand_nested=True,
    )

    collector.record(
        RowResult(
            position=0,
            source_index=0,
            input_data="row",
            items=[
                NestedItem(
                    name="incident",
                    details={"date": "2026-01-01"},
                    tags=["a"],
                )
            ],
        )
    )
    result = collector.build(ExtractorUsage())

    assert result.data.loc[0, "name"] == "incident"
    assert result.data.loc[0, "details_date"] == "2026-01-01"
    assert result.data.loc[0, "extraction_status"] == "Success"


def test_result_collector_records_failed_rows():
    collector = ResultCollector(
        source=pd.DataFrame({"source": ["row"]}),
        model=NestedItem,
        return_df=True,
        expand_nested=False,
    )
    collector.record(
        RowResult(
            position=0,
            source_index="source-row",
            input_data="bad row",
            items=[],
            error="boom",
        )
    )
    result = collector.build(ExtractorUsage())

    assert result.failed.iloc[0]["index"] == "source-row"
    assert result.failed.iloc[0]["text"] == "bad row"
    assert result.failed.iloc[0]["error"] == "boom"
    assert result.data.loc[0, "extraction_status"] == "Failed: boom"


def test_result_collector_updates_duplicate_index_labels_by_position():
    collector = ResultCollector(
        source=pd.DataFrame(
            {"source": ["first", "second"]},
            index=["duplicate", "duplicate"],
        ),
        model=NestedItem,
        return_df=True,
        expand_nested=False,
    )
    collector.record(
        RowResult(
            position=1,
            source_index="duplicate",
            input_data="second",
            items=[NestedItem(name="second", details={}, tags=[])],
        )
    )
    result_df = collector.build(ExtractorUsage()).data

    assert result_df.iloc[0]["extraction_status"] is None
    assert result_df.iloc[1]["name"] == "second"
    assert result_df.iloc[1]["extraction_status"] == "Success"


def test_result_collector_does_not_copy_source_for_list_results():
    collector = ResultCollector(
        source=pd.DataFrame({"source": ["row"]}),
        model=NestedItem,
        return_df=False,
        expand_nested=False,
    )
    collector.record(
        RowResult(
            position=0,
            source_index=0,
            input_data="row",
            items=[NestedItem(name="item", details={}, tags=[])],
        )
    )

    result = collector.build(ExtractorUsage())

    assert collector.result_df is None
    assert result.data == [NestedItem(name="item", details={}, tags=[])]


def test_extraction_result_counts_successful_input_rows():
    data = pd.DataFrame(
        {
            "name": ["ok", None],
            "extraction_status": ["Success", "Failed: boom"],
        }
    )
    result = ExtractionResult(
        data=data,
        rows=[
            RowResult(position=0, source_index=0, input_data="ok", items=[]),
            RowResult(
                position=1,
                source_index=1,
                input_data="bad",
                items=[],
                error="boom",
            ),
        ],
        model=NestedItem,
    )

    assert result.success_count == 1
    assert result.extracted_count == 2
    assert result.failure_count == 1
    assert result.success_rate == 50.0


def test_result_exposes_per_row_usage_and_empty_status():
    row_usage = ExtractorUsage()
    row = RowResult(
        position=0,
        source_index="source-row",
        input_data="row",
        items=[],
        usage=row_usage,
    )
    result = ExtractionResult(data=[], rows=[row], model=NestedItem)

    assert result.rows[0].usage is row_usage
    assert result.rows[0].status == "empty"
    assert result.empty_count == 1
