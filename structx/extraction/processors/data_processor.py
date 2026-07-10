"""
Data preparation and batch processing for extractions.
"""

import asyncio
import threading
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, List, Union

import pandas as pd
from tqdm import tqdm

from structx.core.exceptions import ExtractionError
from structx.utils.file_reader import FileReader
from structx.utils.helpers import handle_errors


class DataProcessor:
    """
    Handles data preparation and batch processing for extractions.
    """

    def __init__(self, max_threads: int = 10, batch_size: int = 100):
        """
        Initialize data processor.

        Args:
            max_threads: Maximum number of concurrent threads
            batch_size: Size of batches for processing
        """
        self.max_threads = max_threads
        self.batch_size = batch_size

    @handle_errors(error_message="Data preparation failed", error_type=ExtractionError)
    def prepare_data(
        self, data: Union[str, Path, pd.DataFrame, List[Dict[str, str]]], **kwargs: Any
    ) -> pd.DataFrame:
        """
        Convert input data to DataFrame.

        Args:
            data: Input data (file path, DataFrame, list of dicts, or raw text)
            **kwargs: Additional options for file reading

        Returns:
            DataFrame with data
        """
        if isinstance(data, pd.DataFrame):
            df = data
        elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
            df = pd.DataFrame(data)
        elif isinstance(data, (str, Path)) and Path(str(data)).exists():
            df = FileReader.read_file(data, **kwargs)
        elif isinstance(data, str):
            # Raw text processing using unified multimodal PDF pipeline
            import tempfile

            # Create a temporary text file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            ) as temp_file:
                temp_file.write(data)
                temp_path = temp_file.name

            df = FileReader.read_file(temp_path, **kwargs)
            df.loc[:, "source"] = temp_path  # Set source to temp file path

        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

        # Ensure text column exists
        if "text" not in df.columns and len(df.columns) == 1:
            df["text"] = df[df.columns[0]]

        return df

    def process_batch(
        self,
        batch: pd.DataFrame,
        worker_fn: Callable,
        target_columns: List[str],
    ) -> None:
        """
        Process a batch of data using threads.

        Args:
            batch: Batch of data to process
            worker_fn: Worker function to execute
            target_columns: Target columns for processing
        """
        semaphore = threading.Semaphore(self.max_threads)
        threads = []

        with tqdm(total=len(batch), desc=f"Processing batch", unit="row") as pbar:
            # Create and start threads for batch
            for idx, row in batch.iterrows():
                # Check if this is a multimodal PDF row
                if (
                    "multimodal" in row
                    and row["multimodal"]
                    and row.get("file_type") == "pdf"
                ):
                    row_data = {
                        "pdf_path": row["pdf_path"],
                        "multimodal": True,
                        "file_type": "pdf",
                        "source": row.get("source", ""),
                    }
                else:
                    # Regular text processing
                    row_data = row[target_columns].to_markdown()

                thread = threading.Thread(
                    target=worker_fn,
                    args=(row_data, idx, semaphore, pbar),
                )
                thread.start()
                threads.append(thread)

            # Wait for batch threads to complete
            for thread in threads:
                thread.join()

    def process_in_batches(
        self,
        df: pd.DataFrame,
        worker_fn: Callable,
        target_columns: List[str],
    ) -> None:
        """
        Process DataFrame in batches.

        Args:
            df: DataFrame to process
            worker_fn: Worker function to execute
            target_columns: Target columns for processing
        """
        # Process in batches
        for batch_start in range(0, len(df), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(df))
            batch = df.iloc[batch_start:batch_end]
            self.process_batch(batch, worker_fn, target_columns)

    async def run_async(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Run a function asynchronously in a thread pool.

        Args:
            func: Function to run
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function
        """
        # Use functools.partial to create a callable with all arguments
        wrapped_func = partial(func, *args, **kwargs)

        try:
            # Try to get the running loop
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Since we created a new loop, we need to run and close it
            try:
                return await loop.run_in_executor(None, wrapped_func)
            finally:
                loop.close()
        else:
            # We got an existing loop, just use it
            return await loop.run_in_executor(None, wrapped_func)
