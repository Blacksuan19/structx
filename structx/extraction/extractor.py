import asyncio
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

import pandas as pd
from instructor import Instructor
from loguru import logger
from pydantic import BaseModel, Field, create_model
from tenacity import (
    after_log,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tqdm import tqdm
from zmq import has

from structx.core.config import DictStrAny, ExtractionConfig
from structx.core.exceptions import ConfigurationError, ExtractionError
from structx.core.models import (
    ExtractionGuide,
    ExtractionRequest,
    ExtractionResult,
    QueryAnalysis,
    QueryRefinement,
)
from structx.extraction.generator import ModelGenerator
from structx.utils.file_reader import FileReader
from structx.utils.helpers import (
    convert_pydantic_v1_to_v2,
    flatten_extracted_data,
    handle_errors,
    sanitize_regex_patterns,
)
from structx.utils.prompts import *  # noqa
from structx.utils.types import ResponseType
from structx.utils.usage import ExtractionStep, ExtractorUsage, StepUsage


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
        max_retries: int = 3,
        min_wait: int = 1,
        max_wait: int = 10,
    ):
        """Initialize extractor"""
        self.client = client
        self.model_name = model_name
        self.max_threads = max_threads
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.min_wait = min_wait
        self.max_wait = max_wait
        self.usage_lock = threading.Lock()
        self.usage = ExtractorUsage()

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

    @handle_errors(error_message="LLM completion failed", error_type=ExtractionError)
    def _perform_llm_completion(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[ResponseType],
        config: DictStrAny,
        step: ExtractionStep,
    ) -> ResponseType:
        """Perform LLM completion and track token usage"""
        # Use create_with_completion as shown in Instructor docs
        result, completion = self.client.chat.completions.create_with_completion(
            model=self.model_name,
            response_model=response_model,
            messages=messages,
            **config,
        )

        # Create usage object
        usage = StepUsage.from_completion(completion, step)

        # Add to usage tracking if available (thread-safe)
        if usage:
            with self.usage_lock:
                self.usage.add_step_usage(usage)
            logger.debug(f"Step {step.value}: {usage.total_tokens} tokens used")

        return result

    @handle_errors(error_message="Query analysis failed", error_type=ExtractionError)
    def _analyze_query(self, query: str, available_columns: List[str]) -> QueryAnalysis:
        """Analyze query to determine target column and extraction purpose"""
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
            step=ExtractionStep.ANALYSIS,
        )

    @handle_errors(error_message="Query refinement failed", error_type=ExtractionError)
    def _refine_query(self, query: str) -> QueryRefinement:
        """Refine and expand query with structural requirements"""

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
            step=ExtractionStep.REFINEMENT,
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
            step=ExtractionStep.SCHEMA_GENERATION,
        )

    @handle_errors(error_message="Guide generation failed", error_type=ExtractionError)
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
            step=ExtractionStep.REFINEMENT,
        )

    def _create_retry_decorator(self):
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

    def _extract_without_retry(
        self,
        text: str,
        extraction_model: Type[BaseModel],
        refined_query: QueryRefinement,
        guide: ExtractionGuide,
    ) -> List[BaseModel]:
        """Extract structured data with usage tracking"""
        messages = [
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
        ]

        # Use create directly, not create_with_completion for extraction
        # This returns a properly structured response for iterable models

        class ResponseContainer(BaseModel):
            """Container for the response"""

            response: List[BaseModel]

        response = self.client.chat.completions.create_iterable(
            model=self.model_name,
            response_model=extraction_model,
            messages=messages,
            **self.config.extraction,
        )

        response = list(response)

        print("Response:", response)
        print(f"{dir(response[0])=}")

        # check if any of the items in the response has the _raw_response attribute
        # we neeed to check item by item because the response is an iterable
        if hasattr(response, "_raw_response"):
            completion = response._raw_response
            # Track usage
            usage = StepUsage.from_completion(completion, ExtractionStep.EXTRACTION)
            if usage:
                with self.usage_lock:
                    self.usage.add_step_usage(usage)

        # Return validated items
        return [extraction_model.model_validate(item) for item in response]

    def _extract_with_model(
        self,
        text: str,
        extraction_model: Type[BaseModel],
        refined_query: QueryRefinement,
        guide: ExtractionGuide,
    ) -> List[BaseModel]:
        """Extract data with enforced structure with retries and usage tracking"""
        # Create a container model to wrap the list items
        container_name = f"{extraction_model.__name__}Container"
        container_model = create_model(
            container_name,
            __base__=BaseModel,
            items=(
                List[extraction_model],
                Field(description=f"List of {extraction_model.__name__} items"),
            ),
        )

        # Apply retry decorator
        retry_decorator = self._create_retry_decorator()

        @retry_decorator
        def extract_with_retry():
            # Use _perform_llm_completion with the container model
            container = self._perform_llm_completion(
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
                response_model=container_model,
                config=self.config.extraction,
                step=ExtractionStep.EXTRACTION,
            )

            # Return just the items
            return container.items

        # Execute with retry
        return extract_with_retry()

    @handle_errors(
        error_message="Failed to initialize extraction", error_type=ExtractionError
    )
    def _initialize_extraction(
        self, df: pd.DataFrame, query: str, generate_model: bool = True
    ) -> Tuple[
        QueryAnalysis,
        QueryRefinement,
        ExtractionGuide,
        Optional[Type[BaseModel]],
    ]:
        """Initialize the extraction process by analyzing query and generating models if needed"""
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

        if not generate_model:
            return query_analysis, refined_query, guide

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
        for field_name in extraction_model.model_fields:
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

        with tqdm(total=len(batch), desc=f"Processing batch", unit="row") as pbar:
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
        self,
        df: pd.DataFrame,
        query: str,
        return_df: bool,
        expand_nested: bool = False,
        extraction_model: Optional[Type[BaseModel]] = None,
    ) -> ExtractionResult:
        """Process DataFrame with extraction"""
        # Reset usage tracking
        self.usage = ExtractorUsage()

        # Initialize extraction
        if extraction_model:
            query_analysis, refined_query, guide = self._initialize_extraction(
                df, query, generate_model=False
            )
            ExtractionModel = extraction_model
        else:
            query_analysis, refined_query, guide, ExtractionModel = (
                self._initialize_extraction(df, query, generate_model=True)
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
        return ExtractionResult(
            data=result_df if return_df else result_list,
            failed=pd.DataFrame(failed_rows),
            model=ExtractionModel,
            usage=self.usage,
        )

    def _prepare_data(
        self, data: Union[str, Path, pd.DataFrame, List[Dict[str, str]]], **kwargs: Any
    ) -> pd.DataFrame:
        """
        Convert input data to DataFrame

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
            # Raw text
            chunk_size = kwargs.get("chunk_size", 1000)
            overlap = kwargs.get("overlap", 100)
            chunks = []
            for i in range(0, len(data), chunk_size - overlap):
                chunks.append(data[i : i + chunk_size])

            df = pd.DataFrame(
                {"text": chunks, "chunk_id": range(len(chunks)), "source": "raw_text"}
            )
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

        # Ensure text column exists
        if "text" not in df.columns and len(df.columns) == 1:
            df["text"] = df[df.columns[0]]

        return df

    async def _run_async(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Run a function asynchronously in a thread pool

        Args:
            func: Function to run
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function
        """
        # Use functools.partial to create a callable with all arguments
        from functools import partial

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

    @handle_errors(error_message="Extraction failed", error_type=ExtractionError)
    def extract(
        self,
        data: Union[str, Path, pd.DataFrame, List[Dict[str, str]]],
        query: str,
        model: Optional[Type[BaseModel]] = None,
        return_df: bool = False,
        expand_nested: bool = False,
        **kwargs: Any,
    ) -> ExtractionResult:
        """
        Extract structured data from text

        Args:
            data: Input data (file path, DataFrame, list of dicts, or raw text)
            query: Natural language query
            model: Optional pre-generated Pydantic model class (if None, a model will be generated)
            return_df: Whether to return DataFrame
            expand_nested: Whether to flatten nested structures
            **kwargs: Additional options for file reading
                - chunk_size: Size of text chunks (for unstructured text)
                - overlap: Overlap between chunks (for unstructured text)
                - encoding: Text encoding (for unstructured text)

        Returns:
            Extraction result with extracted data, failed rows, and model (if requested)
        """
        df = self._prepare_data(data, **kwargs)
        return self._process_data(df, query, return_df, expand_nested, model)

    async def extract_async(
        self,
        data: Union[str, Path, pd.DataFrame, List[Dict[str, str]]],
        query: str,
        return_df: bool = False,
        expand_nested: bool = False,
        **kwargs: Any,
    ) -> ExtractionResult:
        """
        Asynchronous version of `extract`.

        Extract structured data from text

        Args:
            data: Input data (file path, DataFrame, list of dicts, or raw text)
            query: Natural language query
            return_df: Whether to return DataFrame
            expand_nested: Whether to flatten nested structures
            **kwargs: Additional options for file reading

        Returns:
            ExtractionResult containing extracted data, failed rows, and the model
        """

    @handle_errors(error_message="Batch extraction failed", error_type=ExtractionError)
    def extract_queries(
        self,
        data: Union[str, Path, pd.DataFrame, List[Dict[str, str]]],
        queries: List[str],
        return_df: bool = True,
        expand_nested: bool = False,
        **kwargs: Any,
    ) -> Dict[str, ExtractionResult]:
        """
        Process multiple queries on the same data

        Args:
            data: Input data (file path, DataFrame, list of dicts, or raw text)
            queries: List of queries to process
            return_df: Whether to return DataFrame
            expand_nested: Whether to flatten nested structures
            **kwargs: Additional options for file reading
                - chunk_size: Size of text chunks (for unstructured text)
                - overlap: Overlap between chunks (for unstructured text)
                - encoding: Text encoding (for unstructured text)

        Returns:
            Dictionary mapping queries to their results (extracted data and failed extractions)
        """
        results = {}

        for query in queries:
            logger.info(f"\nProcessing query: {query}")
            result = self.extract(
                data=data,
                query=query,
                return_df=return_df,
                expand_nested=expand_nested,
                **kwargs,
            )
            results[query] = result

        return results

    async def extract_queries_async(
        self,
        data: Union[str, Path, pd.DataFrame, List[Dict[str, str]]],
        queries: List[str],
        return_df: bool = False,
        expand_nested: bool = False,
        **kwargs: Any,
    ) -> Dict[str, ExtractionResult]:
        """
        Asynchronous version of `extract_queries`.

        Extract structured data using multiple queries

        Args:
            data: Input data
            queries: List of queries
            return_df: Whether to return DataFrame
            expand_nested: Whether to flatten nested structures
            **kwargs: Additional options

        Returns:
            Dictionary mapping queries to ExtractionResult objects
        """

    @handle_errors(error_message="Schema generation failed", error_type=ExtractionError)
    def get_schema(self, query: str, sample_text: str) -> Type[BaseModel]:
        """
        Get extraction model without performing extraction

        Args:
            query: Natural language query
            sample_text: Sample text for context

        Returns:
            Pydantic model for extraction with `.usage` attribute for token tracking
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

        ExtractionModel.usage = self.usage
        # Return schema
        return ExtractionModel

    async def get_schema_async(self, query: str, sample_text: str) -> Type[BaseModel]:
        """
        Asynchronous version of `get_schema`.

        Get the dynamically generated model for extraction

        Args:
            query: Natural language query
            sample_text: Sample text for context

        Returns:
            Dynamically generated Pydantic model class
        """

    def refine_data_model(
        self,
        model: Type[BaseModel],
        instructions: str,
        model_name: Optional[str] = None,
    ) -> Type[BaseModel]:
        """
        Refine an existing data model based on natural language instructions

        Args:
            model: Existing Pydantic model to refine
            instructions: Natural language instructions for refinement
            model_name: Optional name for the refined model (defaults to original name with 'Refined' prefix)

        Returns:
            A new refined Pydantic model with `.usage` attribute for token tracking
        """

        # Default model name if not provided
        if model_name is None:
            model_name = f"Refined{model.__name__}"

        # Get the schema of the existing model
        model_schema = model.model_json_schema()
        model_schema_str = json.dumps(model_schema, indent=2)

        # Generate schema for the refined model directly
        extraction_request = self._perform_llm_completion(
            response_model=ExtractionRequest,
            messages=[
                {
                    "role": "system",
                    "content": """You are a data model refinement specialist.
                Analyze the existing model and the refinement instructions to create
                a new model that incorporates the requested changes.""",
                },
                {
                    "role": "user",
                    "content": f"""
                Refine the following data model according to these instructions:
                
                EXISTING MODEL SCHEMA:
                ```json
                {model_schema_str}
                ```
            REFINEMENT INSTRUCTIONS:
            {instructions}
            
            Create a new model schema that:
            1. Keeps fields from the original model that shouldn't change
            2. Modifies fields as specified in the instructions
            3. Adds new fields as specified in the instructions
            4. Removes fields as specified in the instructions
            
            Important: Use Pydantic v2 syntax:
            - Use `pattern` instead of `regex` for string patterns
            - Use `model_config` instead of `Config` class
            - Use `Field` with validation parameters instead of validators where possible
            
            Include a clear description of the model and each field.
        """,
                },
            ],
            config=self.config.refinement,
            step=ExtractionStep.SCHEMA_GENERATION,
        )

        # Set the model name if specified
        if model_name:
            extraction_request.model_name = model_name

        # Sanitize regex patterns to prevent validation errors
        sanitized_request = sanitize_regex_patterns(extraction_request)

        # Convert from v1 to v2 if needed and generate model
        converted_request = convert_pydantic_v1_to_v2(sanitized_request)
        refined_model = ModelGenerator.from_extraction_request(converted_request)

        # Add usage tracking to the generated model
        refined_model.usage = self.usage

        return refined_model

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
            max_retries: Maximum number of retries for extraction
            min_wait: Minimum seconds to wait between retries
            max_wait: Maximum seconds to wait between retries
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


# add async versions of extraction methods
from structx.utils.helpers import async_wrapper

Extractor.extract_async = async_wrapper(Extractor.extract)
Extractor.extract_queries_async = async_wrapper(Extractor.extract_queries)
Extractor.get_schema_async = async_wrapper(Extractor.get_schema)
