"""
Core LLM operations and query processing.
"""

import logging
import threading
from typing import Dict, List, Type

from instructor import Instructor
from loguru import logger
from tenacity import (
    after_log,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from structx.core.config import DictStrAny, ExtractionConfig
from structx.core.exceptions import ExtractionError
from structx.core.models import ExtractionGuide, QueryRefinement
from structx.utils.helpers import handle_errors
from structx.utils.prompts import (
    guide_system_prompt,
    guide_template,
    query_refinement_system_prompt,
    query_refinement_template,
)
from structx.utils.types import ResponseType
from structx.utils.usage import ExtractionStep, ExtractorUsage, StepUsage


class LLMCore:
    """
    Core LLM operations with retry logic, usage tracking, and query processing.
    """

    def __init__(
        self,
        client: Instructor,
        model_name: str,
        config: ExtractionConfig,
        max_retries: int = 3,
        min_wait: int = 1,
        max_wait: int = 10,
    ):
        """
        Initialize LLM core.

        Args:
            client: Instructor-patched client
            model_name: Name of the model to use
            config: Extraction configuration
            max_retries: Maximum number of retries for extraction
            min_wait: Minimum seconds to wait between retries
            max_wait: Maximum seconds to wait between retries
        """
        self.client = client
        self.model_name = model_name
        self.config = config
        self.max_retries = max_retries
        self.min_wait = min_wait
        self.max_wait = max_wait
        self.usage_lock = threading.Lock()
        self.usage = ExtractorUsage()

    def reset_usage(self) -> None:
        """Reset usage tracking."""
        with self.usage_lock:
            self.usage = ExtractorUsage()

    def get_usage(self) -> ExtractorUsage:
        """Get current usage statistics."""
        with self.usage_lock:
            return self.usage

    def _create_retry_decorator(self):
        """Create retry decorator with instance parameters."""
        return retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(
                multiplier=self.min_wait, min=self.min_wait, max=self.max_wait
            ),
            retry=retry_if_exception_type(ExtractionError),
            before_sleep=before_sleep_log(logger, logging.DEBUG),
            after=after_log(logger, logging.DEBUG),
        )

    @handle_errors(error_message="LLM completion failed", error_type=ExtractionError)
    def complete(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[ResponseType],
        config: DictStrAny,
        step: ExtractionStep,
    ) -> ResponseType:
        """
        Perform LLM completion and track token usage.

        Args:
            messages: Messages for the completion
            response_model: Pydantic model for response
            config: Configuration for the completion
            step: Step being performed for usage tracking

        Returns:
            Completion result
        """
        result, completion = self.client.chat.completions.create_with_completion(
            model=self.model_name,
            response_model=response_model,
            messages=messages,
            **config,
        )

        usage = StepUsage.from_completion(completion, step)

        # Add to usage tracking if available (thread-safe)
        if usage:
            with self.usage_lock:
                self.usage.add_step_usage(usage)
            logger.debug(f"Step {step.value}: {usage.total_tokens} tokens used")

        return result

    def complete_with_retry(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[ResponseType],
        config: DictStrAny,
        step: ExtractionStep,
    ) -> ResponseType:
        """
        Perform LLM completion with retry logic.

        Args:
            messages: Messages for the completion
            response_model: Pydantic model for response
            config: Configuration for the completion
            step: Step being performed for usage tracking

        Returns:
            Completion result
        """
        retry_decorator = self._create_retry_decorator()

        @retry_decorator
        def _complete():
            return self.complete(messages, response_model, config, step)

        return _complete()

    @handle_errors(error_message="Query refinement failed", error_type=ExtractionError)
    def refine_query(self, query: str) -> QueryRefinement:
        """
        Refine and expand query with structural requirements.

        Args:
            query: Original query string

        Returns:
            Refined query with additional details
        """
        return self.complete(
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

    @handle_errors(error_message="Guide generation failed", error_type=ExtractionError)
    def generate_extraction_guide(
        self, refined_query: QueryRefinement, data_columns: List[str]
    ) -> ExtractionGuide:
        """
        Generate extraction guide based on refined query.

        Args:
            refined_query: Refined query with details
            data_columns: Available data columns

        Returns:
            Extraction guide with patterns and rules
        """
        return self.complete(
            messages=[
                {"role": "system", "content": guide_system_prompt},
                {
                    "role": "user",
                    "content": guide_template.substitute(
                        data_characteristics=refined_query.data_characteristics,
                        available_columns=data_columns,
                    ),
                },
            ],
            response_model=ExtractionGuide,
            config=self.config.refinement,
            step=ExtractionStep.GUIDE,
        )
