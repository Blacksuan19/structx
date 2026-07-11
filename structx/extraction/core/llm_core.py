"""
Core LLM operations and query processing.
"""

import logging
import threading
import time
from typing import Dict, List, Mapping, Optional, Type

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
from structx.utils.helpers import handle_errors
from structx.utils.types import ResponseType
from structx.utils.usage import ExtractionStep, ExtractorUsage


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
        planning_model_name: Optional[str] = None,
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
            planning_model_name: Optional model for non-extraction planning steps
        """
        self.client = client
        self.model_name = model_name
        self.config = config
        self.max_retries = max_retries
        self.min_wait = min_wait
        self.max_wait = max_wait
        self.planning_model_name = planning_model_name or model_name
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
        started_at = time.perf_counter()
        model_name = (
            self.model_name
            if step == ExtractionStep.EXTRACTION
            else self.planning_model_name
        )
        try:
            result, completion = self.client.chat.completions.create_with_completion(
                model=model_name,
                response_model=response_model,
                messages=messages,
                **config,
            )
        except Exception:
            elapsed = time.perf_counter() - started_at
            logger.error(
                f"LLM step {step.value} with {model_name} failed after {elapsed:.2f}s"
            )
            raise

        elapsed = time.perf_counter() - started_at
        logger.info(
            f"LLM step {step.value} with {model_name} completed in {elapsed:.2f}s"
        )

        usage = (
            completion.get("usage")
            if isinstance(completion, Mapping)
            else getattr(completion, "usage", None)
        )

        # Add to usage tracking if available (thread-safe)
        if usage is not None:
            with self.usage_lock:
                self.usage.add_step_usage(step, usage)
            total_tokens = getattr(usage, "total_tokens", 0)
            logger.debug(f"Step {step.value}: {total_tokens} tokens used")

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
