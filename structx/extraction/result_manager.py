"""Operation-scoped collection of row extraction results."""

from typing import List, Optional, Type

import pandas as pd
from loguru import logger
from pydantic import BaseModel

from structx.core.models import ExtractionResult, RowResult
from structx.utils.helpers import flatten_extracted_data
from structx.utils.usage import ExtractorUsage


class ResultCollector:
    """Own mutable result state for exactly one extraction operation."""

    def __init__(
        self,
        source: pd.DataFrame,
        model: Type[BaseModel],
        return_df: bool,
        expand_nested: bool,
    ) -> None:
        self.model = model
        self.return_df = return_df
        self.expand_nested = expand_nested
        self.total_rows = len(source)
        self.result_df: Optional[pd.DataFrame] = source.copy() if return_df else None
        self.items: List[BaseModel] = []
        self.rows: List[RowResult[BaseModel]] = []

        if self.result_df is not None:
            for field_name in model.model_fields:
                self.result_df[field_name] = None
            self.result_df["extraction_status"] = None

    def record(self, outcome: RowResult[BaseModel]) -> None:
        """Record one row outcome in its original input position."""
        self.rows.append(outcome)
        if outcome.error is not None:
            self._record_failure(outcome)
        elif self.return_df:
            self._record_dataframe_items(outcome)
        else:
            self.items.extend(outcome.items)

    def _record_dataframe_items(self, outcome: RowResult[BaseModel]) -> None:
        assert self.result_df is not None
        for item_index, item in enumerate(outcome.items):
            item_data = (
                flatten_extracted_data(item.model_dump())
                if self.expand_nested
                else item.model_dump()
            )
            if item_index > 0:
                item_data = {
                    f"{field_name}_{item_index}": value
                    for field_name, value in item_data.items()
                }

            for field_name, value in item_data.items():
                if field_name not in self.result_df.columns:
                    self.result_df[field_name] = None
                column_position = self.result_df.columns.get_loc(field_name)
                self.result_df.iat[outcome.position, column_position] = value

        status_position = self.result_df.columns.get_loc("extraction_status")
        self.result_df.iat[outcome.position, status_position] = (
            "Success" if outcome.items else "Empty"
        )

    def _record_failure(self, outcome: RowResult[BaseModel]) -> None:
        if self.result_df is not None:
            status_position = self.result_df.columns.get_loc("extraction_status")
            self.result_df.iat[outcome.position, status_position] = (
                f"Failed: {outcome.error}"
            )

    def build(self, usage: ExtractorUsage) -> ExtractionResult:
        """Finalize the public result and log row-level statistics."""
        failure_count = sum(row.error is not None for row in self.rows)
        success_count = self.total_rows - failure_count
        logger.info(
            "Extraction completed: {} succeeded, {} failed, {} total",
            success_count,
            failure_count,
            self.total_rows,
        )
        return ExtractionResult(
            data=self.result_df if self.return_df else self.items,
            rows=self.rows,
            model=self.model,
            usage=usage,
        )
