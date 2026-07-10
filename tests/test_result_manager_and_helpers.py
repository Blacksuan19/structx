import pandas as pd
from pydantic import BaseModel

from structx.extraction.result_manager import ResultManager
from structx.utils.helpers import flatten_extracted_data


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


def test_result_manager_initializes_and_updates_dataframe():
    df = pd.DataFrame({"source": ["row"]})
    result_df, result_list, failed_rows = ResultManager.initialize_results(
        df,
        NestedItem,
    )

    assert result_list == []
    assert failed_rows == []
    assert "name" in result_df.columns
    assert "extraction_status" in result_df.columns

    ResultManager.update_dataframe(
        result_df,
        [
            NestedItem(
                name="incident",
                details={"date": "2026-01-01"},
                tags=["a"],
            )
        ],
        row_idx=0,
        expand_nested=True,
    )

    assert result_df.loc[0, "name"] == "incident"
    assert result_df.loc[0, "details_date"] == "2026-01-01"
    assert result_df.loc[0, "extraction_status"] == "Success"


def test_result_manager_records_failed_rows():
    result_df = pd.DataFrame({"source": ["row"], "extraction_status": [None]})
    failed_rows = []

    ResultManager.handle_extraction_error(
        result_df,
        failed_rows,
        row_idx=0,
        row_text="bad row",
        error=ValueError("boom"),
    )

    assert failed_rows[0]["index"] == 0
    assert failed_rows[0]["text"] == "bad row"
    assert failed_rows[0]["error"] == "boom"
    assert result_df.loc[0, "extraction_status"] == "Failed: boom"
