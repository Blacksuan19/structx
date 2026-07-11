"""Public orchestration for structured extraction operations."""

import asyncio
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

import pandas as pd
from instructor import AsyncInstructor, Instructor
from loguru import logger
from pydantic import BaseModel

from structx.core.config import ExtractionConfig
from structx.core.exceptions import ConfigurationError, ExtractionError
from structx.core.input import PreparedInput, RowPayload
from structx.core.models import ExtractionResult, RowResult
from structx.extraction.core.llm_core import LLMCore
from structx.extraction.engines.extraction_engine import ExtractionEngine
from structx.extraction.processors.batch_processor import BatchProcessor
from structx.extraction.processors.content_analyzer import ContentAnalyzer
from structx.extraction.processors.input_processor import InputProcessor
from structx.extraction.processors.model_operations import ModelOperations
from structx.extraction.result_manager import ResultCollector
from structx.utils.helpers import handle_errors
from structx.utils.usage import ExtractorUsage


@dataclass(frozen=True)
class ExtractionStrategy:
    """The model and instructions needed to process prepared rows."""

    model: Type[BaseModel]
    instructions: str
    target_columns: List[str]


class Extractor:
    """Coordinate input preparation, model planning, extraction, and results.

    Args:
        client: Instructor-patched client
        model_name: Name of the model to use
        config: Configuration for extraction steps
        max_threads: Maximum concurrent row requests
        batch_size: Rows scheduled in each processing batch
        max_retries: Maximum number of retries for extraction
        min_wait: Minimum seconds to wait between retries
        max_wait: Maximum seconds to wait between retries
        planning_model: Optional model for instruction and schema generation
        async_client: Optional async Instructor client for async methods
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
        planning_model: Optional[str] = None,
        async_client: Optional[AsyncInstructor] = None,
    ):
        """Initialize extractor."""
        if (
            not isinstance(max_threads, int)
            or isinstance(max_threads, bool)
            or max_threads < 1
        ):
            raise ConfigurationError("max_threads must be a positive integer")
        if (
            not isinstance(batch_size, int)
            or isinstance(batch_size, bool)
            or batch_size < 1
        ):
            raise ConfigurationError("batch_size must be a positive integer")
        if (
            not isinstance(max_retries, int)
            or isinstance(max_retries, bool)
            or max_retries < 0
        ):
            raise ConfigurationError("max_retries must be a non-negative integer")
        if min_wait < 0 or max_wait < min_wait:
            raise ConfigurationError(
                "wait settings must satisfy 0 <= min_wait <= max_wait"
            )

        self.model_name = model_name

        # Setup configuration
        if config is None:
            self.config = ExtractionConfig()
        elif isinstance(config, dict):
            self.config = ExtractionConfig(**config)
        elif isinstance(config, (str, Path)):
            self.config = ExtractionConfig.from_yaml(config)
        elif isinstance(config, ExtractionConfig):
            self.config = config
        else:
            raise ConfigurationError("Invalid configuration type")

        # Initialize core components
        self.llm_core = LLMCore(
            client=client,
            async_client=async_client,
            model_name=model_name,
            config=self.config,
            max_retries=max_retries,
            min_wait=min_wait,
            max_wait=max_wait,
            planning_model_name=planning_model,
        )

        # Initialize specialized processors
        self.model_operations = ModelOperations(self.llm_core)
        self.extraction_engine = ExtractionEngine(self.llm_core)
        self.input_processor = InputProcessor()
        self.batch_processor = BatchProcessor(max_threads, batch_size)
        self.content_analyzer = ContentAnalyzer()

        logger.debug(f"Initialized Extractor with configuration: {self.config}")

    @staticmethod
    def _validate_query(query: str) -> str:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        return query.strip()

    @classmethod
    def _validate_queries(cls, queries: List[str]) -> List[str]:
        if not isinstance(queries, list) or not queries:
            raise ValueError("queries must be a non-empty list")
        validated = [cls._validate_query(query) for query in queries]
        if len(set(validated)) != len(validated):
            raise ValueError("queries must not contain duplicates")
        return validated

    def _build_strategy(
        self,
        prepared_input: PreparedInput,
        query: str,
        usage: ExtractorUsage,
        model: Optional[Type[BaseModel]],
    ) -> ExtractionStrategy:
        """Build deterministic or model-generated instructions for one operation."""
        if model is not None:
            instructions, target_columns = (
                self.model_operations.generate_from_custom_model(
                    model=model,
                    query=query,
                    data_columns=prepared_input.dataframe.columns.tolist(),
                )
            )
            return ExtractionStrategy(model, instructions, target_columns)

        sample_text = self._create_schema_sample(prepared_input)
        pdf_path = self._planning_pdf_path(prepared_input)
        plan = self.model_operations.generate_extraction_plan(
            query=query,
            sample_text=sample_text,
            data_columns=prepared_input.dataframe.columns.tolist(),
            usage=usage,
            pdf_path=pdf_path,
        )
        logger.debug(f"Extraction Instructions: {plan.instructions}")
        logger.debug(f"Target Columns: {plan.target_columns}")

        extraction_model = self.model_operations.create_model_from_schema(
            plan.extraction_schema
        )
        return ExtractionStrategy(
            extraction_model,
            plan.instructions,
            plan.target_columns,
        )

    async def _build_strategy_async(
        self,
        prepared_input: PreparedInput,
        query: str,
        usage: ExtractorUsage,
        model: Optional[Type[BaseModel]],
    ) -> ExtractionStrategy:
        """Asynchronously build the strategy when model planning is required."""
        if model is not None:
            instructions, target_columns = (
                self.model_operations.generate_from_custom_model(
                    model=model,
                    query=query,
                    data_columns=prepared_input.dataframe.columns.tolist(),
                )
            )
            return ExtractionStrategy(model, instructions, target_columns)

        plan = await self.model_operations.generate_extraction_plan_async(
            query=query,
            sample_text=await asyncio.to_thread(
                self._create_schema_sample, prepared_input
            ),
            data_columns=prepared_input.dataframe.columns.tolist(),
            usage=usage,
            pdf_path=self._planning_pdf_path(prepared_input),
        )
        extraction_model = self.model_operations.create_model_from_schema(
            plan.extraction_schema
        )
        return ExtractionStrategy(
            extraction_model,
            plan.instructions,
            plan.target_columns,
        )

    def _create_schema_sample(self, prepared_input: PreparedInput) -> str:
        """Create one representative sample for extraction planning."""
        df = prepared_input.dataframe
        if prepared_input.pdf_rows:
            sample_text = prepared_input.planning_sample or ""
            content_context = self.content_analyzer.detect_content_type_and_context(
                prepared_input
            )
            return f"Content type: {content_context}\n\n{sample_text}"
        return "\n".join(df.head().to_string(index=False).splitlines())

    @staticmethod
    def _planning_pdf_path(prepared_input: PreparedInput) -> Optional[str]:
        """Attach a PDF to planning only when no text sample is available."""
        if prepared_input.planning_sample or not prepared_input.pdf_rows:
            return None
        first_pdf = prepared_input.pdf_rows[min(prepared_input.pdf_rows)]
        return str(first_pdf.pdf_path)

    def _create_extraction_worker(
        self,
        strategy: ExtractionStrategy,
    ):
        """Create a worker function for synchronous row extraction."""

        def extract_worker(
            row_data: RowPayload,
            row_position: int,
            row_label: Any,
        ):
            try:
                row_usage = ExtractorUsage()
                items = self.extraction_engine.extract_from_row_data(
                    row_data=row_data,
                    extraction_model=strategy.model,
                    instructions=strategy.instructions,
                    usage=row_usage,
                )
                return RowResult(
                    position=row_position,
                    source_index=row_label,
                    input_data=row_data,
                    items=items,
                    usage=row_usage,
                )
            except Exception as error:
                return RowResult(
                    position=row_position,
                    source_index=row_label,
                    input_data=row_data,
                    items=[],
                    usage=row_usage,
                    error=str(error),
                )

        return extract_worker

    def _create_async_extraction_worker(
        self,
        strategy: ExtractionStrategy,
    ):
        """Create an async worker that preserves row identity on success or failure."""

        async def extract_worker(
            row_data: RowPayload,
            row_position: int,
            row_label: Any,
        ) -> RowResult:
            try:
                row_usage = ExtractorUsage()
                items = await self.extraction_engine.extract_from_row_data_async(
                    row_data=row_data,
                    extraction_model=strategy.model,
                    instructions=strategy.instructions,
                    usage=row_usage,
                )
                return RowResult(
                    position=row_position,
                    source_index=row_label,
                    input_data=row_data,
                    items=items,
                    usage=row_usage,
                )
            except Exception as error:
                return RowResult(
                    position=row_position,
                    source_index=row_label,
                    input_data=row_data,
                    items=[],
                    usage=row_usage,
                    error=str(error),
                )

        return extract_worker

    def _process_data(
        self,
        prepared_input: PreparedInput,
        query: str,
        return_df: bool,
        expand_nested: bool = False,
        extraction_model: Optional[Type[BaseModel]] = None,
    ) -> ExtractionResult:
        """Process DataFrame with extraction."""
        operation_usage = ExtractorUsage()
        strategy = self._build_strategy(
            prepared_input, query, operation_usage, extraction_model
        )

        results = ResultCollector(
            source=prepared_input.dataframe,
            model=strategy.model,
            return_df=return_df,
            expand_nested=expand_nested,
        )

        worker_fn = self._create_extraction_worker(strategy=strategy)

        # Process in batches
        outcomes = self.batch_processor.map_rows(
            prepared_input, worker_fn, strategy.target_columns
        )
        for outcome in outcomes:
            operation_usage.merge(outcome.usage)
            results.record(outcome)
        return results.build(operation_usage)

    async def _process_data_async(
        self,
        prepared_input: PreparedInput,
        query: str,
        return_df: bool,
        expand_nested: bool = False,
        extraction_model: Optional[Type[BaseModel]] = None,
    ) -> ExtractionResult:
        """Plan once, then asynchronously process independent rows."""
        if self.llm_core.async_client is None:
            raise ConfigurationError(
                "Async extraction requires an async Instructor client"
            )
        operation_usage = ExtractorUsage()
        strategy = await self._build_strategy_async(
            prepared_input, query, operation_usage, extraction_model
        )
        results = ResultCollector(
            source=prepared_input.dataframe,
            model=strategy.model,
            return_df=return_df,
            expand_nested=expand_nested,
        )
        outcomes = await self.batch_processor.map_rows_async(
            prepared_input,
            self._create_async_extraction_worker(strategy),
            strategy.target_columns,
        )
        for outcome in outcomes:
            operation_usage.merge(outcome.usage)
            results.record(outcome)
        return results.build(operation_usage)

    @handle_errors(error_message="Extraction failed", error_type=ExtractionError)
    def extract(
        self,
        *,
        data: Union[str, Path, pd.DataFrame, List[Dict[str, str]]],
        query: str,
        model: Optional[Type[BaseModel]] = None,
        return_df: bool = False,
        expand_nested: bool = False,
        **kwargs: Any,
    ) -> ExtractionResult:
        """
        Extract structured data from text.

        Args:
            data: Input data (file path, DataFrame, list of dicts, or raw text)
            query: Natural language query
            model: Optional pre-generated Pydantic model class (if None, a model will be generated)
            return_df: Whether to return DataFrame
            expand_nested: Whether to flatten nested structures
            **kwargs: Additional options for file reading

        Returns:
            Extraction result with extracted data, failed rows, and model (if requested)
        """
        query = self._validate_query(query)
        with self.input_processor.prepared(data, **kwargs) as prepared_input:
            return self._process_data(
                prepared_input, query, return_df, expand_nested, model
            )

    async def extract_async(
        self,
        *,
        data: Union[str, Path, pd.DataFrame, List[Dict[str, str]]],
        query: str,
        model: Optional[Type[BaseModel]] = None,
        return_df: bool = False,
        expand_nested: bool = False,
        **kwargs: Any,
    ) -> ExtractionResult:
        """
        Asynchronous version of `extract`.

        Args:
            data: Input data (file path, DataFrame, list of dicts, or raw text)
            query: Natural language query
            model: Optional pre-generated Pydantic model class
            return_df: Whether to return DataFrame
            expand_nested: Whether to flatten nested structures
            **kwargs: Additional options for file reading

        Returns:
            ExtractionResult containing extracted data, failed rows, and the model
        """
        try:
            query = self._validate_query(query)
            async with self.input_processor.prepared_async(
                data, **kwargs
            ) as prepared_input:
                return await self._process_data_async(
                    prepared_input, query, return_df, expand_nested, model
                )
        except Exception as error:
            raise ExtractionError(f"Async extraction failed: {error}") from error

    @handle_errors(error_message="Batch extraction failed", error_type=ExtractionError)
    def extract_queries(
        self,
        *,
        data: Union[str, Path, pd.DataFrame, List[Dict[str, str]]],
        queries: List[str],
        return_df: bool = True,
        expand_nested: bool = False,
        **kwargs: Any,
    ) -> Dict[str, ExtractionResult]:
        """
        Process multiple queries on the same data.

        Args:
            data: Input data (file path, DataFrame, list of dicts, or raw text)
            queries: List of queries to process
            return_df: Whether to return DataFrame
            expand_nested: Whether to flatten nested structures
            **kwargs: Additional options for file reading

        Returns:
            Dictionary mapping queries to their results (extracted data and failed extractions)
        """
        queries = self._validate_queries(queries)
        with self.input_processor.prepared(data, **kwargs) as prepared_input:
            results = {}
            for query in queries:
                logger.debug(f"Processing query: {query}")
                results[query] = self._process_data(
                    prepared_input=prepared_input,
                    query=query,
                    return_df=return_df,
                    expand_nested=expand_nested,
                )
            return results

    async def extract_queries_async(
        self,
        *,
        data: Union[str, Path, pd.DataFrame, List[Dict[str, str]]],
        queries: List[str],
        return_df: bool = True,
        expand_nested: bool = False,
        **kwargs: Any,
    ) -> Dict[str, ExtractionResult]:
        """
        Asynchronous version of `extract_queries`.

        Args:
            data: Input data
            queries: List of queries
            return_df: Whether to return DataFrame
            expand_nested: Whether to flatten nested structures
            **kwargs: Additional options

        Returns:
            Dictionary mapping queries to ExtractionResult objects
        """
        try:
            queries = self._validate_queries(queries)
            async with self.input_processor.prepared_async(
                data, **kwargs
            ) as prepared_input:
                results = {}
                for query in queries:
                    results[query] = await self._process_data_async(
                        prepared_input=prepared_input,
                        query=query,
                        return_df=return_df,
                        expand_nested=expand_nested,
                    )
                return results
        except Exception as error:
            raise ExtractionError(f"Async batch extraction failed: {error}") from error

    @handle_errors(error_message="Schema generation failed", error_type=ExtractionError)
    def get_schema(
        self,
        *,
        data: Union[str, Path, pd.DataFrame, List[Dict[str, str]]],
        query: str,
        **kwargs: Any,
    ) -> Type[BaseModel]:
        """
        Get extraction model without performing extraction.

        Args:
            query: Natural language query
            data: Input data (file path, DataFrame, list of dicts, or raw text)
            **kwargs: Additional options for file reading

        Returns:
            Pydantic model for extraction with `.usage` attribute for token tracking
        """
        query = self._validate_query(query)
        with self.input_processor.prepared(data, **kwargs) as prepared_input:
            sample_text = self._create_schema_sample(prepared_input)
            columns = prepared_input.dataframe.columns.tolist()

            operation_usage = ExtractorUsage()
            pdf_path = self._planning_pdf_path(prepared_input)
            plan = self.model_operations.generate_extraction_plan(
                query=query,
                sample_text=sample_text,
                data_columns=columns,
                usage=operation_usage,
                pdf_path=pdf_path,
            )

            extraction_model = self.model_operations.create_model_from_schema(
                plan.extraction_schema
            )
            extraction_model.usage = operation_usage
            return extraction_model

    async def get_schema_async(
        self,
        *,
        data: Union[str, Path, pd.DataFrame, List[Dict[str, str]]],
        query: str,
        **kwargs: Any,
    ) -> Type[BaseModel]:
        """
        Asynchronous version of `get_schema`.

        Args:
            query: Natural language query
            data: Input data (file path, DataFrame, list of dicts, or raw text)
            **kwargs: Additional options for file reading

        Returns:
            Dynamically generated Pydantic model class
        """
        try:
            query = self._validate_query(query)
            async with self.input_processor.prepared_async(
                data, **kwargs
            ) as prepared_input:
                usage = ExtractorUsage()
                plan = await self.model_operations.generate_extraction_plan_async(
                    query=query,
                    sample_text=await asyncio.to_thread(
                        self._create_schema_sample, prepared_input
                    ),
                    data_columns=prepared_input.dataframe.columns.tolist(),
                    usage=usage,
                    pdf_path=self._planning_pdf_path(prepared_input),
                )
                model = self.model_operations.create_model_from_schema(
                    plan.extraction_schema
                )
                model.usage = usage
                return model
        except Exception as error:
            raise ExtractionError(f"Async schema generation failed: {error}") from error

    @handle_errors(error_message="Model refinement failed", error_type=ExtractionError)
    def refine_data_model(
        self,
        *,
        model: Type[BaseModel],
        refinement_instructions: str,
        model_name: Optional[str] = None,
    ) -> Type[BaseModel]:
        """
        Refine an existing data model based on natural language instructions.

        Args:
            model: Existing Pydantic model to refine
            refinement_instructions: Natural language instructions for refinement
            model_name: Optional name for the refined model (defaults to original name with 'Refined' prefix)

        Returns:
            A new refined Pydantic model with `.usage` attribute for token tracking
        """
        # Default model name if not provided
        if model_name is None:
            model_name = f"Refined{model.__name__}"

        operation_usage = ExtractorUsage()
        refined_model = self.model_operations.refine_existing_model(
            model=model,
            instructions=refinement_instructions,
            model_name=model_name,
            usage=operation_usage,
        )

        # Add usage to model
        refined_model.usage = operation_usage

        return refined_model

    async def refine_data_model_async(
        self,
        *,
        model: Type[BaseModel],
        refinement_instructions: str,
        model_name: Optional[str] = None,
    ) -> Type[BaseModel]:
        """Asynchronously refine an existing data model."""
        try:
            usage = ExtractorUsage()
            refined_model = await self.model_operations.refine_existing_model_async(
                model=model,
                instructions=refinement_instructions,
                model_name=model_name,
                usage=usage,
            )
            refined_model.usage = usage
            return refined_model
        except Exception as error:
            raise ExtractionError(f"Async model refinement failed: {error}") from error

    @classmethod
    def from_litellm(
        cls,
        *,
        model: str,
        api_key: Optional[str] = None,
        config: Optional[Union[Dict, str, Path, ExtractionConfig]] = None,
        max_threads: int = 10,
        batch_size: int = 100,
        max_retries: int = 3,
        min_wait: int = 1,
        max_wait: int = 10,
        planning_model: Optional[str] = None,
        **litellm_kwargs: Any,
    ) -> "Extractor":
        """
        Create Extractor instance using litellm.

        Args:
            model: Model identifier (e.g., "gpt-4", "claude-2", "azure/gpt-4")
            api_key: API key for the model provider
            config: Per-step completion parameters passed to the model provider
            max_threads: Maximum concurrent row requests
            batch_size: Rows scheduled in each processing batch
            max_retries: Maximum number of retries for extraction
            min_wait: Minimum seconds to wait between retries
            max_wait: Maximum seconds to wait between retries
            planning_model: Optional model for instruction and schema generation
            **litellm_kwargs: Additional kwargs for litellm (e.g., api_base, organization)
        """
        import instructor
        from litellm import acompletion, completion

        completion_options = {**litellm_kwargs, "drop_params": True}
        if api_key:
            completion_options["api_key"] = api_key

        # Bind provider settings to this client instead of mutating LiteLLM globals.
        completion_with_filtered_params = partial(completion, **completion_options)
        client = instructor.from_litellm(completion_with_filtered_params)
        async_completion = partial(acompletion, **completion_options)
        async_client = instructor.from_litellm(async_completion, async_client=True)

        return cls(
            client=client,
            async_client=async_client,
            model_name=model,
            config=config,
            max_threads=max_threads,
            batch_size=batch_size,
            max_retries=max_retries,
            min_wait=min_wait,
            max_wait=max_wait,
            planning_model=planning_model,
        )
