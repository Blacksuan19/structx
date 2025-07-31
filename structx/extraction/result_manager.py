"""
Result management for extraction operations.
"""

from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
from loguru import logger
from pydantic import BaseModel

from structx.utils.helpers import flatten_extracted_data


class ResultManager:
    """
    Manages extraction results, errors, and statistics.
    """

    @staticmethod
    def initialize_results(
        df: pd.DataFrame, extraction_model: type[BaseModel]
    ) -> tuple[pd.DataFrame, List[Any], List[Dict]]:
        """
        Initialize result containers.

        Args:
            df: Original DataFrame
            extraction_model: Pydantic model for extraction

        Returns:
            Tuple of (result_df, result_list, failed_rows)
        """
        result_df = df.copy()
        result_list = []
        failed_rows = []

        # Initialize extraction columns
        for field_name in extraction_model.model_fields:
            result_df[field_name] = None
        result_df["extraction_status"] = None

        return result_df, result_list, failed_rows

    @staticmethod
    def update_dataframe(
        result_df: pd.DataFrame,
        items: List[BaseModel],
        row_idx: int,
        expand_nested: bool,
    ) -> None:
        """
        Update DataFrame with extracted items.

        Args:
            result_df: DataFrame to update
            items: Extracted model instances
            row_idx: Row index to update
            expand_nested: Whether to flatten nested structures
        """
        for i, item in enumerate(items):
            # Flatten if needed
            item_data = (
                flatten_extracted_data(item.model_dump())
                if expand_nested
                else item.model_dump()
            )

            # For multiple items, append index to field names
            if i > 0:
                item_data = {f"{k}_{i}": v for k, v in item_data.items()}

            # Update result dataframe
            for field_name, value in item_data.items():
                result_df.at[row_idx, field_name] = value

        result_df.at[row_idx, "extraction_status"] = "Success"

    @staticmethod
    def handle_extraction_error(
        result_df: pd.DataFrame,
        failed_rows: List[Dict],
        row_idx: int,
        row_text: str,
        error: Exception,
    ) -> None:
        """
        Handle and log extraction errors.

        Args:
            result_df: DataFrame to update with error status
            failed_rows: List to append failed row information
            row_idx: Row index that failed
            row_text: Text that failed to extract
            error: Exception that occurred
        """
        failed_rows.append(
            {
                "index": row_idx,
                "text": row_text,
                "error": str(error),
                "timestamp": datetime.now().isoformat(),
            }
        )
        result_df.at[row_idx, "extraction_status"] = f"Failed: {str(error)}"

    @staticmethod
    def log_extraction_stats(total_rows: int, failed_rows: List[Dict]) -> None:
        """
        Log extraction statistics.

        Args:
            total_rows: Total number of rows processed
            failed_rows: List of failed rows
        """
        success_count = total_rows - len(failed_rows)
        logger.info("\nExtraction Statistics:")
        logger.info(f"Total rows: {total_rows}")
        logger.info(
            f"Successfully processed: {success_count} "
            f"({success_count/total_rows*100:.2f}%)"
        )
        logger.info(
            f"Failed: {len(failed_rows)} " f"({len(failed_rows)/total_rows*100:.2f}%)"
        )
