from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_serializer


class ExtractionStep(Enum):
    """A model-backed step in the extraction pipeline."""

    SCHEMA_GENERATION = "schema_generation"
    EXTRACTION = "extraction"


def _read_value(source: Any, *names: str) -> Any:
    if source is None:
        return None
    for name in names:
        if isinstance(source, Mapping):
            value = source.get(name)
        else:
            value = getattr(source, name, None)
        if value is not None:
            return value
    return None


def _token_count(source: Any, *names: str) -> int:
    value = _read_value(source, *names)
    return value if isinstance(value, int) else 0


def _optional_token_count(source: Any, *names: str) -> Optional[int]:
    value = _read_value(source, *names)
    return value if isinstance(value, int) else None


class ExtractorUsage(BaseModel):
    """Raw provider usage objects grouped by extraction step."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    steps: Dict[ExtractionStep, List[Any]] = Field(default_factory=dict)

    @field_serializer("steps")
    def serialize_steps(
        self, steps: Dict[ExtractionStep, List[Any]]
    ) -> Dict[str, List[Any]]:
        return {step.value: usages for step, usages in steps.items()}

    def add_step_usage(self, step: ExtractionStep, usage: Any) -> None:
        """Associate a provider usage object with a pipeline step."""
        if usage is not None:
            self.steps.setdefault(step, []).append(usage)

    def get_step(self, step: Union[ExtractionStep, str]) -> List[Any]:
        """Return the raw usage objects recorded for a pipeline step."""
        step = ExtractionStep(step) if isinstance(step, str) else step
        return self.steps.get(step, [])

    def _all_usages(self) -> Iterable[Any]:
        for usages in self.steps.values():
            yield from usages

    @staticmethod
    def _prompt_tokens(usage: Any) -> int:
        return _token_count(usage, "prompt_tokens", "input_tokens")

    @staticmethod
    def _completion_tokens(usage: Any) -> int:
        return _token_count(usage, "completion_tokens", "output_tokens")

    @classmethod
    def _total_tokens(cls, usage: Any) -> int:
        total = _optional_token_count(usage, "total_tokens")
        if total is not None:
            return total
        return cls._prompt_tokens(usage) + cls._completion_tokens(usage)

    @staticmethod
    def _reasoning_tokens(usage: Any) -> Optional[int]:
        details = _read_value(
            usage, "completion_tokens_details", "output_tokens_details"
        )
        nested = _optional_token_count(
            details, "reasoning_tokens", "thinking_tokens"
        )
        return nested if nested is not None else _optional_token_count(
            usage, "reasoning_tokens", "thinking_tokens"
        )

    @staticmethod
    def _cached_tokens(usage: Any) -> Optional[int]:
        details = _read_value(usage, "prompt_tokens_details", "input_tokens_details")
        nested = _optional_token_count(
            details,
            "cached_tokens",
            "cache_read_tokens",
            "cache_read_input_tokens",
        )
        return nested if nested is not None else _optional_token_count(
            usage,
            "cached_tokens",
            "cache_read_tokens",
            "cache_read_input_tokens",
        )

    @computed_field
    @property
    def total_tokens(self) -> int:
        return sum(self._total_tokens(usage) for usage in self._all_usages())

    @computed_field
    @property
    def prompt_tokens(self) -> int:
        return sum(self._prompt_tokens(usage) for usage in self._all_usages())

    @computed_field
    @property
    def completion_tokens(self) -> int:
        return sum(self._completion_tokens(usage) for usage in self._all_usages())

    @computed_field
    @property
    def thinking_tokens(self) -> Optional[int]:
        values = [
            value
            for usage in self._all_usages()
            if (value := self._reasoning_tokens(usage)) is not None
        ]
        return sum(values) if values else None

    @computed_field
    @property
    def cached_tokens(self) -> Optional[int]:
        values = [
            value
            for usage in self._all_usages()
            if (value := self._cached_tokens(usage)) is not None
        ]
        return sum(values) if values else None
