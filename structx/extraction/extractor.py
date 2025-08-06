"""
Refactored main extractor class - now acts as an orchestrator with better organization.
"""

import copy
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

import pandas as pd
from instructor import Instructor
from loguru import logger
from pydantic import BaseModel

from structx.core.config import ExtractionConfig
from structx.core.exceptions import ConfigurationError, ExtractionError
from structx.core.models import ExtractionResult
from structx.extraction.core.llm_core import LLMCore
from structx.extraction.engines.extraction_engine import ExtractionEngine
from structx.extraction.processors.data_content import ContentAnalyzer, DataProcessor
from structx.extraction.processors.model_operations import ModelOperations
from structx.extraction.result_manager import ResultManager
from structx.utils.helpers import handle_errors


class Extractor:
    """
    Main class for structured data extraction - now acts as an orchestrator.

    This class coordinates the various specialized components to perform
    structured data extraction from different types of sources.

    Args:
        client: Instructor-patched client
        model_name: Name of the model to use
        config: Configuration for extraction steps
        max_threads: Maximum number of concurrent threads
        batch_size: Size of batches for processing
        max_retries: Maximum number of retries for extraction
        min_wait: Minimum seconds to wait between retries
        max_wait: Maximum seconds to wait between retries
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
        """Initialize extractor."""
        self.model_name = model_name

        # Setup configuration
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

        # Initialize core components
        self.llm_core = LLMCore(
            client=client,
            model_name=model_name,
            config=self.config,
            max_retries=max_retries,
            min_wait=min_wait,
            max_wait=max_wait,
        )

        # Initialize specialized processors
        self.model_operations = ModelOperations(self.llm_core)
        self.extraction_engine = ExtractionEngine(self.llm_core)
        self.data_processor = DataProcessor(max_threads, batch_size)
        self.result_manager = ResultManager()
        self.content_analyzer = ContentAnalyzer()

        logger.info(f"Initialized Extractor with configuration: {self.config.conf}")

    def _initialize_extraction(
        self, df: pd.DataFrame, query: str, generate_model: bool = True
    ) -> tuple[Any, Any, Optional[Type[BaseModel]]]:
        """Initialize the extraction process by refining query and generating models if needed."""
        # Refine query
        refined_query = self.llm_core.refine_query(query)
        logger.info(f"Refined Query: {refined_query.refined_query}")

        # Generate guide
        guide = self.llm_core.generate_extraction_guide(
            refined_query, df.columns.tolist()
        )
        logger.info(f"Target Columns: {guide.target_columns}")

        if not generate_model:
            return refined_query, guide, None

        # Get sample text for schema generation
        # Check if this is file-based extraction (contains pdf_path or source columns)
        is_file_based = "pdf_path" in df.columns or "source" in df.columns

        if is_file_based:
            # For file-based extractions, extract actual content samples
            sample_text = self.content_analyzer.extract_content_sample_for_schema(df)
            # Add context about the content type
            content_context = self.content_analyzer.detect_content_type_and_context(df)
            sample_text = f"Content type: {content_context}\n\n{sample_text}"
        else:
            # For traditional tabular data, use the existing approach
            sample_text = df[guide.target_columns].iloc[0]

        # Generate model
        schema_request = self.model_operations.generate_extraction_schema(
            sample_text, refined_query, guide
        )
        extraction_model = self.model_operations.create_model_from_schema(
            schema_request
        )

        return refined_query, guide, extraction_model

    def _create_extraction_worker(
        self,
        extraction_model: Type[BaseModel],
        refined_query: Any,
        guide: Any,
        result_df: pd.DataFrame,
        result_list: List[Any],
        failed_rows: List[Dict],
        return_df: bool,
        expand_nested: bool,
        is_custom_model: bool = False,
    ):
        """Create a worker function for threaded extraction."""

        def extract_worker(
            row_data: Union[str, Dict],
            row_idx: int,
            semaphore: threading.Semaphore,
            pbar,
        ):
            with semaphore:
                try:
                    items = self.extraction_engine.extract_from_row_data(
                        row_data=row_data,
                        extraction_model=extraction_model,
                        refined_query=refined_query,
                        guide=guide,
                        is_custom_model=is_custom_model,
                    )

                    if return_df:
                        self.result_manager.update_dataframe(
                            result_df, items, row_idx, expand_nested
                        )
                    else:
                        result_list.extend(items)

                except Exception as e:
                    row_text = row_data if isinstance(row_data, str) else str(row_data)
                    self.result_manager.handle_extraction_error(
                        result_df, failed_rows, row_idx, row_text, e
                    )
                finally:
                    pbar.update(1)

        return extract_worker

    @handle_errors(error_message="Data processing failed", error_type=ExtractionError)
    def _process_data(
        self,
        df: pd.DataFrame,
        query: str,
        return_df: bool,
        expand_nested: bool = False,
        extraction_model: Optional[Type[BaseModel]] = None,
    ) -> ExtractionResult:
        """Process DataFrame with extraction."""
        # Reset usage tracking
        self.llm_core.reset_usage()

        # Initialize extraction
        if extraction_model:
            # When a custom model is provided, generate refinement and guide from the model
            # instead of from the query to avoid conflicts
            refined_query, guide = self.model_operations.generate_from_custom_model(
                model=extraction_model, query=query, data_columns=df.columns.tolist()
            )
            ExtractionModel = extraction_model
        else:
            refined_query, guide, ExtractionModel = self._initialize_extraction(
                df, query, generate_model=True
            )

        # Initialize results
        result_df, result_list, failed_rows = self.result_manager.initialize_results(
            df, ExtractionModel
        )

        # Create worker function - pass is_custom_model flag when using a provided model
        worker_fn = self._create_extraction_worker(
            extraction_model=ExtractionModel,
            refined_query=refined_query,
            guide=guide,
            result_df=result_df,
            result_list=result_list,
            failed_rows=failed_rows,
            return_df=return_df,
            expand_nested=expand_nested,
            is_custom_model=extraction_model is not None,
        )

        # Process in batches
        self.data_processor.process_in_batches(df, worker_fn, guide.target_columns)

        # Log statistics
        self.result_manager.log_extraction_stats(len(df), failed_rows)

        # Create a deep copy of usage for the result
        result_usage = copy.deepcopy(self.llm_core.get_usage())

        # Reset the extractor's usage for the next operation
        self.llm_core.reset_usage()

        # Return results
        return ExtractionResult(
            data=result_df if return_df else result_list,
            failed=pd.DataFrame(failed_rows),
            model=ExtractionModel,
            usage=result_usage,
        )

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
        df = self.data_processor.prepare_data(data, **kwargs)
        return self._process_data(df, query, return_df, expand_nested, model)

    async def extract_async(
        self,
        *,
        data: Union[str, Path, pd.DataFrame, List[Dict[str, str]]],
        query: str,
        return_df: bool = False,
        expand_nested: bool = False,
        **kwargs: Any,
    ) -> ExtractionResult:
        """
        Asynchronous version of `extract`.

        Args:
            data: Input data (file path, DataFrame, list of dicts, or raw text)
            query: Natural language query
            return_df: Whether to return DataFrame
            expand_nested: Whether to flatten nested structures
            **kwargs: Additional options for file reading

        Returns:
            ExtractionResult containing extracted data, failed rows, and the model
        """
        return await self.data_processor.run_async(
            self.extract, data, query, None, return_df, expand_nested, **kwargs
        )

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
        *,
        data: Union[str, Path, pd.DataFrame, List[Dict[str, str]]],
        queries: List[str],
        return_df: bool = False,
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
        return await self.data_processor.run_async(
            self.extract_queries, data, queries, return_df, expand_nested, **kwargs
        )

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
        if isinstance(data, str) and not Path(data).exists():
            sample_text = data
            columns = ["text"]
        else:
            df = self.data_processor.prepare_data(data, **kwargs)
            is_file_based = "pdf_path" in df.columns or "source" in df.columns
            columns = df.columns.tolist()

            if is_file_based:
                sample_text = self.content_analyzer.extract_content_sample_for_schema(
                    df
                )
                content_context = self.content_analyzer.detect_content_type_and_context(
                    df
                )
                sample_text = f"Content type: {content_context}\n\n{sample_text}"
            else:
                # For traditional tabular data, create a representative sample
                sample_text = "\n".join(df.head().to_string(index=False).splitlines())

        # Refine query
        refined_query = self.llm_core.refine_query(query)

        # Generate guide
        guide = self.llm_core.generate_extraction_guide(refined_query, columns)

        # Generate schema
        schema_request = self.model_operations.generate_extraction_schema(
            sample_text, refined_query, guide
        )

        # Create model
        extraction_model = self.model_operations.create_model_from_schema(
            schema_request
        )

        # Create a deep copy of usage for the model
        model_usage = copy.deepcopy(self.llm_core.get_usage())

        # Reset the extractor's usage for the next operation
        self.llm_core.reset_usage()

        # Add usage to model
        extraction_model.usage = model_usage

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
        return await self.data_processor.run_async(
            self.get_schema, query, data, **kwargs
        )

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

        refined_model = self.model_operations.refine_existing_model(
            model, refinement_instructions, model_name
        )

        # Create a deep copy of usage for the model
        model_usage = copy.deepcopy(self.llm_core.get_usage())

        # Reset the extractor's usage for the next operation
        self.llm_core.reset_usage()

        # Add usage to model
        refined_model.usage = model_usage

        return refined_model

    @classmethod
    def from_litellm(
        cls,
        *,
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
        Create Extractor instance using litellm.

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

        # drop unnecessary parameters
        litellm.drop_params = True

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
