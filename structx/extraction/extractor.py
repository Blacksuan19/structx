import asyncio
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union

import pandas as pd
from instructor import Instructor
from loguru import logger
from pydantic import BaseModel
from tenacity import (
    after_log,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tqdm import tqdm

from structx.core.config import DictStrAny, ExtractionConfig
from structx.core.exceptions import ConfigurationError, ExtractionError
from structx.core.models import (
    ExtractionGuide,
    ExtractionRequest,
    QueryAnalysis,
    QueryRefinement,
)
from structx.extraction.generator import ModelGenerator
from structx.utils.file_reader import FileReader
from structx.utils.helpers import flatten_extracted_data, handle_errors
from structx.utils.prompts import *  # noqa: F401 sue me


class Extractor:
    """
    Main class for structured data extraction

    Args:
        client (Instructor): Instructor-patched Azure OpenAI client
        model_name (str): Name of the model to use
        config (Optional[Union[Dict, str, Path, ExtractionConfig]]): Configuration for extraction steps
        max_threads (int): Maximum number of concurrent threads
        batch_size (int): Size of batches for processing
        max_retries (int): Maximum number of retries for extraction
        min_wait (int): Minimum seconds to wait between retries
        max_wait (int): Maximum seconds to wait between retries
    """

    def __init__(
        self,
        client: Instructor,
        model_name: str,
        config: Optional[Union[Dict, str, Path, ExtractionConfig]] = None,
        max_threads: int = 10,
        batch_size: int = 100,
        max_retries: int = 3,  # Add retry configuration
        min_wait: int = 1,  # Minimum seconds to wait between retries
        max_wait: int = 10,  # Maximum seconds to wait between retries
    ):
        """Initialize extractor"""
        self.client = client
        self.model_name = model_name
        self.max_threads = max_threads
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.min_wait = min_wait
        self.max_wait = max_wait

        if not config:
            self.config = ExtractionConfig()
        elif isinstance(config, (dict, str, Path)):
            self.config = ExtractionConfig(
                config=config if isinstance(config, dict) else None,
                config_path=config if isinstance(config, (str, Path)) else None,
            )
        elif isinstance(config, ExtractionConfig):
            self.config = config
        else:
            raise ConfigurationError("Invalid configuration type")

        logger.info(f"Initialized Extractor with configuration: {self.config.conf}")

    def _perform_llm_completion(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[BaseModel],
        config: DictStrAny,
    ) -> Dict:
        """
        Perform completion with the given model and prompt

        Args:
            messages: List of messages for the completion
            response_model: Pydantic model for response
            config: Configuration for the completion
        """
        return self.client.chat.completions.create(
            model=self.model_name,
            response_model=response_model,
            messages=messages,
            **config,
        )

    @handle_errors(error_message="Query analysis failed", error_type=ExtractionError)
    def _analyze_query(self, query: str, available_columns: List[str]) -> QueryAnalysis:
        """
        Analyze query to determine target column and extraction purpose

        Args:
            query: Natural language query
            available_columns: List of available column names
        """
        return self._perform_llm_completion(
            messages=[
                {"role": "system", "content": query_analysis_system_prompt},
                {
                    "role": "user",
                    "content": query_analysis_template.substitute(
                        query=query, available_columns=", ".join(available_columns)
                    ),
                },
            ],
            response_model=QueryAnalysis,
            config=self.config.analysis,
        )

    @handle_errors(error_message="Query refinement failed", error_type=ExtractionError)
    def _refine_query(self, query: str) -> QueryRefinement:
        """
        Refine and expand query with structural requirements

        Args:
            query: Original query to refine
        """

        return self._perform_llm_completion(
            messages=[
                {"role": "system", "content": query_refinement_system_prompt},
                {
                    "role": "user",
                    "content": query_refinement_template.substitute(query=query),
                },
            ],
            response_model=QueryRefinement,
            config=self.config.refinement,
        )

    @handle_errors(error_message="Schema generation failed", error_type=ExtractionError)
    def _generate_extraction_schema(
        self, sample_text: str, refined_query: QueryRefinement, guide: ExtractionGuide
    ) -> ExtractionRequest:
        """Generate schema with enforced structure"""

        return self._perform_llm_completion(
            messages=[
                {"role": "system", "content": schema_system_prompt},
                {
                    "role": "user",
                    "content": schema_template.substitute(
                        refined_query=refined_query.refined_query,
                        data_characteristics=refined_query.data_characteristics,
                        structural_requirements=refined_query.structural_requirements,
                        organization_principles=guide.organization_principles,
                        sample_text=sample_text,
                    ),
                },
            ],
            response_model=ExtractionRequest,
            config=self.config.refinement,
        )

    def _generate_extraction_guide(
        self, refined_query: QueryRefinement
    ) -> ExtractionGuide:
        """Generate extraction guide based on refined query"""

        return self._perform_llm_completion(
            messages=[
                {"role": "system", "content": guide_system_prompt},
                {
                    "role": "user",
                    "content": guide_template.substitute(
                        data_characteristics=refined_query.data_characteristics
                    ),
                },
            ],
            response_model=ExtractionGuide,
            config=self.config.refinement,
        )

    def create_retry_decorator(self):
        """Create retry decorator with instance parameters"""
        return retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(
                multiplier=self.min_wait, min=self.min_wait, max=self.max_wait
            ),
            retry=retry_if_exception_type(ExtractionError),
            before_sleep=before_sleep_log(logger, logging.DEBUG),
            after=after_log(logger, logging.DEBUG),
        )

    @handle_errors(
        "Data extraction failed after all retries", error_type=ExtractionError
    )
    def _extract_with_model(
        self,
        text: str,
        extraction_model: Type[BaseModel],
        refined_query: QueryRefinement,
        guide: ExtractionGuide,
    ) -> List[BaseModel]:
        """Extract data with enforced structure with retries"""
        # Apply retry decorator dynamically
        retry_decorator = self.create_retry_decorator()
        extract_with_retry = retry_decorator(self._extract_without_retry)
        return extract_with_retry(text, extraction_model, refined_query, guide)

    def _extract_without_retry(
        self,
        text: str,
        extraction_model: Type[BaseModel],
        refined_query: QueryRefinement,
        guide: ExtractionGuide,
    ) -> BaseModel:
        """
        Extract structured data from text using a Pydantic model

        Args:
            text (str): Text to extract data from
            extraction_model (Type[BaseModel]): Pydantic model for data extraction
            refined_query (QueryRefinement): Refined query object
            guide (ExtractionGuide): Extraction guide object
        """

        result = self._perform_llm_completion(
            messages=[
                {"role": "system", "content": extraction_system_prompt},
                {
                    "role": "user",
                    "content": extraction_template.substitute(
                        query=refined_query.refined_query,
                        patterns=guide.structural_patterns,
                        rules=guide.relationship_rules,
                        text=text,
                    ),
                },
            ],
            response_model=Iterable[extraction_model],
            config=self.config.extraction,
        )

        # Validate result
        validated = [extraction_model.model_validate(item) for item in result]
        return validated

    @handle_errors(
        error_message="Failed to initialize extraction", error_type=ExtractionError
    )
    def _initialize_extraction(
        self, df: pd.DataFrame, query: str
    ) -> Tuple[QueryAnalysis, QueryRefinement, ExtractionGuide, Type[BaseModel]]:
        """Initialize the extraction process by analyzing query and generating models"""
        # Analyze query
        query_analysis = self._analyze_query(
            query, available_columns=df.columns.tolist()
        )
        logger.info(f"Target Column: {query_analysis.target_column}")
        logger.info(f"Extraction Purpose: {query_analysis.extraction_purpose}")

        # Refine query
        refined_query = self._refine_query(query)
        logger.info(f"Refined Query: {refined_query.refined_query}")

        # Get sample text and generate guide
        sample_text = df[query_analysis.target_column].iloc[0]
        guide = self._generate_extraction_guide(refined_query)

        # Generate model
        schema_request = self._generate_extraction_schema(
            sample_text, refined_query, guide
        )
        ExtractionModel = ModelGenerator.from_extraction_request(schema_request)
        logger.info("Generated Model Schema:")
        logger.info(json.dumps(ExtractionModel.model_json_schema(), indent=2))

        return query_analysis, refined_query, guide, ExtractionModel

    def _initialize_results(
        self, df: pd.DataFrame, extraction_model: Type[BaseModel]
    ) -> Tuple[pd.DataFrame, List[Any], List[Dict]]:
        """Initialize result containers"""
        result_df = df.copy()
        result_list = []
        failed_rows = []

        # Initialize extraction columns
        for field_name in extraction_model.__fields__:
            result_df[field_name] = None
        result_df["extraction_status"] = None

        return result_df, result_list, failed_rows

    def _create_extraction_worker(
        self,
        extraction_model: Type[BaseModel],
        refined_query: QueryRefinement,
        guide: ExtractionGuide,
        result_df: pd.DataFrame,
        result_list: List[Any],
        failed_rows: List[Dict],
        return_df: bool,
        expand_nested: bool,
    ):
        """Create a worker function for threaded extraction"""

        def extract_worker(
            row_text: str,
            row_idx: int,
            semaphore: threading.Semaphore,
            pbar: tqdm,
        ):
            with semaphore:
                try:
                    items = self._extract_with_model(
                        text=row_text,
                        extraction_model=extraction_model,
                        refined_query=refined_query,
                        guide=guide,
                    )

                    if return_df:
                        self._update_dataframe(result_df, items, row_idx, expand_nested)
                    else:
                        result_list.extend(items)

                except Exception as e:
                    self._handle_extraction_error(
                        result_df, failed_rows, row_idx, row_text, e
                    )
                finally:
                    pbar.update(1)

        return extract_worker

    def _update_dataframe(
        self,
        result_df: pd.DataFrame,
        items: List[BaseModel],
        row_idx: int,
        expand_nested: bool,
    ) -> None:
        """Update DataFrame with extracted items"""
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

    def _handle_extraction_error(
        self,
        result_df: pd.DataFrame,
        failed_rows: List[Dict],
        row_idx: int,
        row_text: str,
        error: Exception,
    ) -> None:
        """Handle and log extraction errors"""
        failed_rows.append(
            {
                "index": row_idx,
                "text": row_text,
                "error": str(error),
                "timestamp": datetime.now().isoformat(),
            }
        )
        result_df.at[row_idx, "extraction_status"] = f"Failed: {str(error)}"

    def _process_batch(
        self,
        batch: pd.DataFrame,
        worker_fn: Callable,
        target_column: str,
    ) -> None:
        """Process a batch of data using threads"""
        semaphore = threading.Semaphore(self.max_threads)
        threads = []

        with tqdm(
            total=len(batch),
            desc=f"Processing batch",
            unit="row",
        ) as pbar:
            # Create and start threads for batch
            for idx, row in batch.iterrows():
                thread = threading.Thread(
                    target=worker_fn,
                    args=(row[target_column], idx, semaphore, pbar),
                )
                thread.start()
                threads.append(thread)

            # Wait for batch threads to complete
            for thread in threads:
                thread.join()

    def _log_extraction_stats(self, total_rows: int, failed_rows: List[Dict]) -> None:
        """Log extraction statistics"""
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

    @handle_errors(error_message="Data processing failed", error_type=ExtractionError)
    def _process_data(
        self, df: pd.DataFrame, query: str, return_df: bool, expand_nested: bool = False
    ) -> Tuple[Union[pd.DataFrame, List[BaseModel]], pd.DataFrame]:
        """Process DataFrame with extraction"""
        # Initialize extraction
        query_analysis, refined_query, guide, ExtractionModel = (
            self._initialize_extraction(df, query)
        )

        # Initialize results
        result_df, result_list, failed_rows = self._initialize_results(
            df, ExtractionModel
        )

        # Create worker function
        worker_fn = self._create_extraction_worker(
            extraction_model=ExtractionModel,
            refined_query=refined_query,
            guide=guide,
            result_df=result_df,
            result_list=result_list,
            failed_rows=failed_rows,
            return_df=return_df,
            expand_nested=expand_nested,
        )

        # Process in batches
        for batch_start in range(0, len(df), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(df))
            batch = df.iloc[batch_start:batch_end]
            self._process_batch(batch, worker_fn, query_analysis.target_column)

        # Log statistics
        self._log_extraction_stats(len(df), failed_rows)

        # Return results
        failed_df = pd.DataFrame(failed_rows)
        return (result_df if return_df else result_list), failed_df

    @handle_errors(error_message="Batch extraction failed", error_type=ExtractionError)
    def extract(
        self,
        data: Union[str, Path, pd.DataFrame],
        query: str,
        return_df: bool = False,
        expand_nested: bool = False,
        file_kwargs: Optional[Dict] = None,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Extract structured data from file or DataFrame

        Args:
            data: Path to input file or pandas DataFrame
            query: Natural language query describing what to extract
            return_df: Whether to return the extracted DataFrame or a list of dictionaries (default: False)
            expand_nested: Whether to expand nested structures in the result (default: False, only for `return_df=True`)
            file_kwargs: Optional kwargs for file reading (used only if data is a path)

        Returns:
            Tuple containing:
                - DataFrame with extracted data
                - DataFrame with failed extractions
        """
        # Handle input data
        if isinstance(data, pd.DataFrame):
            df = data
        else:
            file_kwargs = file_kwargs or {}
            df = FileReader.read_file(data, **file_kwargs)

        # Process data
        return self._process_data(df, query, return_df, expand_nested)

    async def extract_async(
        self,
        data: Union[str, Path, pd.DataFrame],
        query: str,
        return_df: bool = False,
        expand_nested: bool = False,
        file_kwargs: Optional[Dict] = None,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Asynchronously extract structured data from file or DataFrame

        Args:
            data: Path to input file or pandas DataFrame
            query: Natural language query describing what to extract
            return_df: Whether to return the extracted DataFrame or a list of dictionaries (default: False)
            expand_nested: Whether to expand nested structures in the result (default: False, only for `return_df=True`)
            file_kwargs: Optional kwargs for file reading (used only if data is a path)

        Returns:
            Tuple containing:
                - DataFrame with extracted data
                - DataFrame with failed extractions
        """
        try:
            # Handle input data
            if isinstance(data, pd.DataFrame):
                df = data
            else:
                file_kwargs = file_kwargs or {}
                df = await asyncio.to_thread(FileReader.read_file, data, **file_kwargs)

            # Process data in thread pool
            return await asyncio.to_thread(
                self._process_data, df, query, return_df, expand_nested
            )

        except Exception as e:
            raise ExtractionError(f"Async extraction failed: {str(e)}")

    @handle_errors(error_message="Schema generation failed", error_type=ExtractionError)
    def get_schema(self, query: str, sample_text: str) -> str:
        """
        Get JSON schema for extraction model without performing extraction

        Args:
            query: Natural language query
            sample_text: Sample text for context

        Returns:
            JSON schema of the generated model
        """
        # Refine query
        refined_query = self._refine_query(query)

        guide = self._generate_extraction_guide(refined_query)

        # Generate schema
        schema_request = self._generate_extraction_schema(
            sample_text, refined_query, guide
        )

        # Create model
        ExtractionModel = ModelGenerator.from_extraction_request(schema_request)

        # Return schema
        return json.dumps(ExtractionModel.model_json_schema(), indent=2)

    @handle_errors(error_message="Batch extraction failed", error_type=ExtractionError)
    def extract_batch(
        self,
        data: Union[str, Path, pd.DataFrame],
        queries: List[str],
        file_kwargs: Optional[Dict] = None,
    ) -> Dict[str, Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Process multiple queries on the same data

        Args:
            data: Path to input file or pandas DataFrame
            queries: List of queries to process
            file_kwargs: Optional kwargs for file reading (used only if data is a path)

        Returns:
            Dictionary mapping queries to their results
        """
        results = {}

        for query in queries:
            logger.info(f"\nProcessing query: {query}")
            result_df, failed_df = self.extract(data, query, file_kwargs)
            results[query] = (result_df, failed_df)

        return results

    @classmethod
    def from_litellm(
        cls,
        model: str,
        api_key: Optional[str] = None,
        config: Optional[Union[Dict, str]] = None,
        max_threads: int = 10,
        batch_size: int = 100,
        max_retries: int = 3,
        min_wait: int = 1,
        max_wait: int = 10,
        **litellm_kwargs: Any,
    ) -> "Extractor":
        """
        Create Extractor instance using litellm

        Args:
            model: Model identifier (e.g., "gpt-4", "claude-2", "azure/gpt-4")
            api_key: API key for the model provider
            config: Extraction configuration
            max_threads: Maximum number of concurrent threads
            batch_size: Size of processing batches
            **litellm_kwargs: Additional kwargs for litellm (e.g., api_base, organization)
        """
        import instructor
        import litellm
        from litellm import completion

        # Set up litellm
        if api_key:
            litellm.api_key = api_key

        # Set additional litellm configs
        for key, value in litellm_kwargs.items():
            setattr(litellm, key, value)

        # Create patched client
        client = instructor.from_litellm(completion)

        return cls(
            client=client,
            model_name=model,
            config=config,
            max_threads=max_threads,
            batch_size=batch_size,
            max_retries=max_retries,
            min_wait=min_wait,
            max_wait=max_wait,
        )
