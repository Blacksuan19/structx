from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ExtractionStep(Enum):
    """
    Enumeration of extraction process steps.

    Represents the different steps in the extraction pipeline where token usage is tracked.
    """

    ANALYSIS = "analysis"
    REFINEMENT = "refinement"
    SCHEMA_GENERATION = "schema_generation"
    EXTRACTION = "extraction"


class TokenDetails(BaseModel):
    """
    Details about token usage with advanced metrics.

    Stores specialized token metrics such as reasoning (thinking) tokens,
    audio tokens, and cached tokens when available from the LLM provider.
    """

    audio_tokens: int = 0
    reasoning_tokens: int = 0
    cached_tokens: int = 0


class StepUsage(BaseModel):
    """
    Token usage information for a single step in the extraction process.

    Contains detailed token usage statistics for one step, including both prompt and
    completion tokens, along with any provider-specific token details.
    """

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    step: ExtractionStep
    completion_tokens_details: Optional[TokenDetails] = None
    prompt_tokens_details: Optional[TokenDetails] = None

    @classmethod
    def from_completion(
        cls, completion: Any, step: ExtractionStep
    ) -> Optional["StepUsage"]:
        """
        Create StepUsage from completion object.

        Args:
            completion: LLM completion response object
            step: Which extraction step this usage belongs to

        Returns:
            StepUsage object or None if no usage data is available
        """
        if not completion or not hasattr(completion, "usage"):
            return None

        usage = completion.usage
        usage_data = {
            "prompt_tokens": getattr(usage, "prompt_tokens", 0),
            "completion_tokens": getattr(usage, "completion_tokens", 0),
            "total_tokens": getattr(usage, "total_tokens", 0),
            "step": step,
        }

        # Add token details if available
        if hasattr(usage, "completion_tokens_details"):
            details = usage.completion_tokens_details
            usage_data["completion_tokens_details"] = TokenDetails(
                audio_tokens=getattr(details, "audio_tokens", 0),
                reasoning_tokens=getattr(details, "reasoning_tokens", 0),
            )

        if hasattr(usage, "prompt_tokens_details"):
            details = usage.prompt_tokens_details
            usage_data["prompt_tokens_details"] = TokenDetails(
                audio_tokens=getattr(details, "audio_tokens", 0),
                cached_tokens=getattr(details, "cached_tokens", 0),
            )

        return cls(**usage_data)


class StepSummary(BaseModel):
    """
    Token usage summary for a single step.

    Provides a simple summary of token consumption for a specific step
    of the extraction process.

    Attributes:
        tokens: Number of tokens used in this step
        name: Name of the step (analysis, refinement, etc.)
    """

    tokens: int
    name: str


class ExtractionSummary(BaseModel):
    """
    Token usage summary for extraction steps.

    Extends StepSummary with additional details about individual extraction steps.

    Attributes:
        tokens: Number of tokens used across all extraction steps
        name: Always "extraction"
        steps: Detailed breakdown of individual extraction calls
    """

    tokens: int
    name: str = "extraction"
    steps: List[StepSummary] = []


class UsageSummary(BaseModel):
    """
    Overall token usage summary across all extraction steps.

    Provides a complete view of token usage throughout the extraction process,
    including totals and per-step breakdowns.

    Attributes:
        total_tokens: Total tokens used across all steps
        prompt_tokens: Total tokens used in prompts
        completion_tokens: Total tokens generated in completions
        thinking_tokens: Total thinking/reasoning tokens (if available)
        cached_tokens: Total cached tokens (if available)
        steps: List of per-step usage summaries
    """

    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    thinking_tokens: Optional[int] = None
    cached_tokens: Optional[int] = None
    steps: List[Union[StepSummary, ExtractionSummary]]

    def get_step(
        self, step_name: str
    ) -> Optional[Union[StepSummary, ExtractionSummary]]:
        """
        Get a step summary by its name.

        Args:
            step_name: Name of the step to retrieve

        Returns:
            Step summary or None if not found
        """
        for step in self.steps:
            if step.name == step_name:
                return step
        return None


class ExtractorUsage(BaseModel):
    """
    Aggregated token usage tracking across all extraction steps.

    Stores and manages token usage data for the entire extraction process,
    providing methods to calculate totals and generate summaries.
    """

    steps: Dict[ExtractionStep, Union[StepUsage, List[StepUsage]]] = Field(
        default_factory=dict
    )

    def add_step_usage(self, usage: Optional[StepUsage]):
        """Add usage information for a step"""
        if not usage:
            return

        if usage.step == ExtractionStep.EXTRACTION:
            # For extraction steps, collect as a list
            if ExtractionStep.EXTRACTION not in self.steps:
                self.steps[ExtractionStep.EXTRACTION] = []
            extraction_list = self.steps[ExtractionStep.EXTRACTION]
            if isinstance(extraction_list, list):
                extraction_list.append(usage)
        else:
            # For other steps, store a single usage
            self.steps[usage.step] = usage

    def _get_attribute_value(self, obj: Any, attr_path: str) -> Optional[int]:
        """Extract a nested attribute value from an object using a dot-notation path"""
        value = obj
        for attr in attr_path.split("."):
            if not hasattr(value, attr) or getattr(value, attr) is None:
                return None
            value = getattr(value, attr)
        return value if isinstance(value, int) else None

    def _get_token_sum(self, attr_path: str) -> int:
        """Get sum of tokens across steps for a specific attribute path"""
        total = 0

        # Process all steps
        for step_type in ExtractionStep:
            if step_type not in self.steps:
                continue

            step_data = self.steps[step_type]

            # Single step case
            if isinstance(step_data, StepUsage):
                value = self._get_attribute_value(step_data, attr_path)
                if value is not None:
                    total += value

            # Multiple extraction steps case
            elif isinstance(step_data, list):
                for item in step_data:
                    value = self._get_attribute_value(item, attr_path)
                    if value is not None:
                        total += value

        return total

    # Simple property accessors using _get_token_sum
    @property
    def total_tokens(self) -> int:
        """Total tokens across all steps"""
        return self._get_token_sum("total_tokens")

    @property
    def prompt_tokens(self) -> int:
        """Total prompt tokens"""
        return self._get_token_sum("prompt_tokens")

    @property
    def completion_tokens(self) -> int:
        """Total completion tokens"""
        return self._get_token_sum("completion_tokens")

    @property
    def thinking_tokens(self) -> int:
        """Total thinking tokens"""
        return self._get_token_sum("completion_tokens_details.reasoning_tokens")

    @property
    def cached_tokens(self) -> int:
        """Total cached tokens"""
        return self._get_token_sum("prompt_tokens_details.cached_tokens")

    def get_usage_summary(self, detailed: bool = False) -> UsageSummary:
        """Get structured token usage summary.

        Args:
            detailed: Whether to include detailed breakdown of extraction steps

        Returns:
            UsageSummary object with token usage information
        """
        # Create step summaries for standard steps
        step_summaries = []
        for step_type in [
            ExtractionStep.ANALYSIS,
            ExtractionStep.REFINEMENT,
            ExtractionStep.SCHEMA_GENERATION,
        ]:
            if step_type in self.steps and isinstance(self.steps[step_type], StepUsage):
                step_summaries.append(
                    StepSummary(
                        tokens=self.steps[step_type].total_tokens, name=step_type.value
                    )
                )
            else:
                step_summaries.append(StepSummary(tokens=0, name=step_type.value))

        # Create extraction summary
        extraction_summary = None
        if ExtractionStep.EXTRACTION in self.steps:
            extraction_steps = self.steps[ExtractionStep.EXTRACTION]
            if isinstance(extraction_steps, list):
                # Total tokens
                total_extraction_tokens = sum(
                    step.total_tokens for step in extraction_steps
                )

                # Individual step details if requested
                extraction_steps_summary = []
                if detailed:
                    extraction_steps_summary = [
                        StepSummary(tokens=step.total_tokens, name=f"extraction_{i}")
                        for i, step in enumerate(extraction_steps)
                    ]

                extraction_summary = ExtractionSummary(
                    tokens=total_extraction_tokens,
                    name=ExtractionStep.EXTRACTION.value,
                    steps=extraction_steps_summary,
                )

        if not extraction_summary:
            extraction_summary = ExtractionSummary(
                tokens=0, name=ExtractionStep.EXTRACTION.value
            )

        step_summaries.append(extraction_summary)

        # Create the complete summary
        summary = UsageSummary(
            total_tokens=self.total_tokens,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            steps=step_summaries,
        )

        # Add optional fields if they have values
        thinking_tokens = self.thinking_tokens
        if thinking_tokens > 0:
            summary.thinking_tokens = thinking_tokens

        cached_tokens = self.cached_tokens
        if cached_tokens > 0:
            summary.cached_tokens = cached_tokens

        return summary
