"""
Data and content processing for extractions.
"""

import asyncio
import threading
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, List, Union

import pandas as pd
from loguru import logger
from tqdm import tqdm

from structx.core.exceptions import ExtractionError
from structx.utils.file_reader import FileReader
from structx.utils.helpers import handle_errors


class ContentAnalyzer:
    """
    Analyzes content types and extracts samples for schema generation.
    """

    @staticmethod
    def detect_content_type_and_context(df: pd.DataFrame) -> str:
        """
        Detect content type and provide context for better model generation.

        Args:
            df: DataFrame to analyze

        Returns:
            String describing the content type and context
        """
        # Check if this is file-based extraction
        is_file_based = "pdf_path" in df.columns or "source" in df.columns

        if not is_file_based:
            return "tabular data with structured columns"

        # Analyze file types and provide context
        file_types = set()
        file_examples = []

        for idx, row in df.iterrows():
            if idx >= 5:  # Limit analysis to first 5 files
                break

            if "pdf_path" in row and pd.notna(row["pdf_path"]):
                file_types.add("PDF")
                file_examples.append(Path(row["pdf_path"]).name)
            elif "source" in row and pd.notna(row["source"]):
                source_path = Path(row["source"])
                ext = source_path.suffix.lower()
                if ext in [".pdf"]:
                    file_types.add("PDF")
                elif ext in [".docx", ".doc"]:
                    file_types.add("Word document")
                elif ext in [".txt", ".md"]:
                    file_types.add("Text document")
                else:
                    file_types.add(f"{ext} file")
                file_examples.append(source_path.name)

        context_info = f"document(s) of type: {', '.join(file_types)}"
        if file_examples:
            context_info += f". Examples: {', '.join(file_examples[:3])}"
            if len(file_examples) > 3:
                context_info += f" and {len(file_examples) - 3} more"

        return context_info

    @staticmethod
    def extract_content_sample_for_schema(
        df: pd.DataFrame, max_chars: int = 2000
    ) -> str:
        """
        Extract content samples from files to inform schema generation.

        Args:
            df: DataFrame containing file information
            max_chars: Maximum characters per sample

        Returns:
            String containing sample content for schema generation
        """
        samples = []

        for idx, row in df.iterrows():
            if idx >= 3:  # Limit to first 3 files for sampling
                break

            try:
                # Check if this is a file-based row
                if "pdf_path" in row and pd.notna(row["pdf_path"]):
                    # For PDF files, extract text sample using pypdf
                    try:
                        import pypdf

                        with open(row["pdf_path"], "rb") as file:
                            reader = pypdf.PdfReader(file)
                            text = ""
                            # Extract from first few pages
                            for page_num in range(min(3, len(reader.pages))):
                                text += reader.pages[page_num].extract_text()
                                if len(text) > max_chars:
                                    break
                            samples.append(text[:max_chars])
                    except Exception as e:
                        logger.warning(
                            f"Could not extract PDF sample from {row['pdf_path']}: {e}"
                        )
                        # Fallback: use filename and basic info
                        samples.append(f"PDF file: {Path(row['pdf_path']).name}")

                elif "source" in row and pd.notna(row["source"]):
                    # For other file types, try to read content
                    source_path = Path(row["source"])
                    if source_path.exists():
                        try:
                            if source_path.suffix.lower() in [".txt", ".md"]:
                                with open(source_path, "r", encoding="utf-8") as f:
                                    content = f.read()[:max_chars]
                                    samples.append(content)
                            else:
                                # For other file types, use filename
                                samples.append(f"File: {source_path.name}")
                        except Exception as e:
                            logger.warning(
                                f"Could not read sample from {source_path}: {e}"
                            )
                            samples.append(f"File: {source_path.name}")
                else:
                    # This is likely traditional tabular data
                    # Convert row data to string representation
                    row_text = " | ".join(
                        [f"{col}: {val}" for col, val in row.items() if pd.notna(val)]
                    )
                    samples.append(row_text[:max_chars])

            except Exception as e:
                logger.warning(f"Error extracting sample from row {idx}: {e}")
                continue

        if not samples:
            # Fallback: return a generic sample based on available columns
            return f"Data with columns: {', '.join(df.columns.tolist())}"

        return "\n\n---SAMPLE SEPARATOR---\n\n".join(samples)

    @staticmethod
    def suggest_column_mappings(
        model_properties: Dict[str, any],
        data_columns: List[str],
        field_descriptions: Dict[str, Dict[str, any]],
    ) -> Dict[str, List[str]]:
        """
        Create intelligent mapping suggestions between model fields and data columns.

        Args:
            model_properties: Properties from the model schema
            data_columns: Available column names in the dataset
            field_descriptions: Descriptions and types for model fields

        Returns:
            Dictionary mapping model field names to potential column names
        """
        mapping_suggestions = {}

        for field_name in model_properties.keys():
            potential_columns = []

            # Find columns that might match this field based on name similarity
            field_terms = set(field_name.lower().replace("_", " ").split())
            field_description = (
                field_descriptions.get(field_name, {}).get("description", "").lower()
            )
            field_desc_terms = set(
                field_description.replace(",", " ").replace(".", " ").split()
            )

            for column in data_columns:
                col_terms = set(column.lower().replace("_", " ").split())

                # Check for direct matches or substring matches
                if (
                    field_name.lower() in column.lower()
                    or column.lower() in field_name.lower()
                    or any(term in column.lower() for term in field_terms)
                    or any(term in column.lower() for term in field_desc_terms)
                ):
                    potential_columns.append(column)

            # If no matches found through name/description similarity, suggest all columns
            # as the field might be extracted from any text column
            if not potential_columns:
                # Add text columns or if not found, just add all columns
                text_columns = [
                    col
                    for col in data_columns
                    if "text" in col.lower() or "description" in col.lower()
                ]
                potential_columns = text_columns if text_columns else data_columns

            mapping_suggestions[field_name] = potential_columns

        return mapping_suggestions


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

            df = FileReader.read_file(temp_path, mode="multimodal_pdf", **kwargs)
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
