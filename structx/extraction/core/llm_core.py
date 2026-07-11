"""
Core LLM operations and query processing.
"""

import logging
import time
from typing import Any, Dict, List, Mapping, Optional, Type

from instructor import AsyncInstructor, Instructor
from loguru import logger
from tenacity import (
    after_log,
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from structx.core.config import ExtractionConfig
from structx.core.exceptions import ConfigurationError, ExtractionError
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
        async_client: Optional[AsyncInstructor] = None,
        max_retries: int = 3,
        min_wait: int = 1,
        max_wait: int = 10,
        planning_model_name: Optional[str] = None,
    ):
        """
        Initialize LLM core.

        Args:
            client: Instructor-patched client
            async_client: Optional Instructor-patched asynchronous client
            model_name: Name of the model to use
            config: Extraction configuration
            max_retries: Maximum number of retries for extraction
            min_wait: Minimum seconds to wait between retries
            max_wait: Maximum seconds to wait between retries
            planning_model_name: Optional model for non-extraction planning steps
        """
        if (
            not isinstance(max_retries, int)
            or isinstance(max_retries, bool)
            or max_retries < 0
        ):
            raise ValueError("max_retries must be a non-negative integer")
        if min_wait < 0 or max_wait < min_wait:
            raise ValueError("wait settings must satisfy 0 <= min_wait <= max_wait")

        self.client = client
        self.async_client = async_client
        self.model_name = model_name
        self.config = config
        self.max_retries = max_retries
        self.min_wait = min_wait
        self.max_wait = max_wait
        self.planning_model_name = planning_model_name or model_name

    def _create_retry_decorator(self):
        """Create retry decorator with instance parameters."""
        return retry(
            stop=stop_after_attempt(self.max_retries + 1),
            wait=wait_exponential(
                multiplier=self.min_wait, min=self.min_wait, max=self.max_wait
            ),
            retry=retry_if_exception(self._is_retryable_error),
            before_sleep=before_sleep_log(logger, logging.DEBUG),
            after=after_log(logger, logging.DEBUG),
            reraise=True,
        )

    def _request_settings(self, step: ExtractionStep) -> tuple[str, Dict[str, Any]]:
        if step == ExtractionStep.EXTRACTION:
            return self.model_name, self.config.for_step("extraction")
        return self.planning_model_name, self.config.for_step("planning")

    @staticmethod
    def _completion_usage(completion: Any) -> Any:
        return (
            completion.get("usage")
            if isinstance(completion, Mapping)
            else getattr(completion, "usage", None)
        )

    @staticmethod
    def _record_usage(
        tracker: Optional[ExtractorUsage], step: ExtractionStep, completion: Any
    ) -> None:
        completion_usage = LLMCore._completion_usage(completion)
        if tracker is not None and completion_usage is not None:
            tracker.add_step_usage(step, completion_usage)

    @staticmethod
    def _is_retryable_error(error: BaseException) -> bool:
        """Return whether an exception chain represents a transient failure."""
        from litellm.exceptions import (
            APIConnectionError,
            BadGatewayError,
            InternalServerError,
            RateLimitError,
            ServiceUnavailableError,
            Timeout,
        )

        transient_errors = (
            APIConnectionError,
            BadGatewayError,
            InternalServerError,
            RateLimitError,
            ServiceUnavailableError,
            Timeout,
        )
        current: Optional[BaseException] = error
        while current is not None:
            if isinstance(current, transient_errors):
                return True
            status_code = getattr(current, "status_code", None)
            if status_code in {408, 429} or (
                isinstance(status_code, int) and status_code >= 500
            ):
                return True
            current = current.__cause__ or current.__context__
        return False

    def _complete_once(
        self,
        messages: List[Dict[str, Any]],
        response_model: Type[ResponseType],
        step: ExtractionStep,
        usage: Optional[ExtractorUsage] = None,
    ) -> ResponseType:
        """Perform one provider call and record successful usage."""
        started_at = time.perf_counter()
        model_name, completion_config = self._request_settings(step)
        try:
            result, completion = self.client.chat.completions.create_with_completion(
                model=model_name,
                response_model=response_model,
                messages=messages,
                **completion_config,
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

        self._record_usage(usage, step, completion)

        return result

    async def _complete_once_async(
        self,
        messages: List[Dict[str, Any]],
        response_model: Type[ResponseType],
        step: ExtractionStep,
        usage: Optional[ExtractorUsage] = None,
    ) -> ResponseType:
        """Perform one asynchronous provider call and record successful usage."""
        if self.async_client is None:
            raise ConfigurationError(
                "Async extraction requires an async Instructor client"
            )

        started_at = time.perf_counter()
        model_name, completion_config = self._request_settings(step)
        try:
            result, completion = (
                await self.async_client.chat.completions.create_with_completion(
                    model=model_name,
                    response_model=response_model,
                    messages=messages,
                    **completion_config,
                )
            )
        except Exception:
            elapsed = time.perf_counter() - started_at
            logger.error(
                f"Async LLM step {step.value} with {model_name} failed after "
                f"{elapsed:.2f}s"
            )
            raise

        elapsed = time.perf_counter() - started_at
        logger.info(
            f"Async LLM step {step.value} with {model_name} completed in "
            f"{elapsed:.2f}s"
        )
        self._record_usage(usage, step, completion)
        return result

    @handle_errors(error_message="LLM completion failed", error_type=ExtractionError)
    def complete(
        self,
        messages: List[Dict[str, Any]],
        response_model: Type[ResponseType],
        step: ExtractionStep,
        usage: Optional[ExtractorUsage] = None,
    ) -> ResponseType:
        """Perform a model-routed completion with transient-error retries."""
        retry_decorator = self._create_retry_decorator()

        @retry_decorator
        def _complete():
            return self._complete_once(messages, response_model, step, usage)

        return _complete()

    async def complete_async(
        self,
        messages: List[Dict[str, Any]],
        response_model: Type[ResponseType],
        step: ExtractionStep,
        usage: Optional[ExtractorUsage] = None,
    ) -> ResponseType:
        """Perform an asynchronous completion with transient-error retries."""
        retry_decorator = self._create_retry_decorator()

        @retry_decorator
        async def _complete():
            return await self._complete_once_async(
                messages, response_model, step, usage
            )

        try:
            return await _complete()
        except Exception as error:
            raise ExtractionError(f"LLM completion failed: {error}") from error
