from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, Optional, Type, Union

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

from structx.core.input import RowPayload
from structx.core.type_system import normalize_field_definition
from structx.utils.types import T
from structx.utils.usage import ExtractorUsage


class ModelField(BaseModel):
    """Definition of a field in the extraction model"""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Name of the field")
    type: str = Field(
        description=(
            "Canonical Python type for the field, such as str, int, float, bool, "
            "date, datetime, List[str], Dict[str, Any], or Optional[List[str]]"
        )
    )
    description: str = Field(description="Description of what this field represents")
    validation: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional validation rules"
    )
    nested_fields: Optional[List["ModelField"]] = Field(
        default=None, description="Fields for nested models"
    )
    required: bool = Field(
        default=False, description="Whether the generated field must be present"
    )
    nullable: bool = Field(
        default=True, description="Whether the generated field may be null"
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_definition(cls, value: Any) -> Any:
        if not isinstance(value, dict) or "type" not in value:
            return value

        normalized = value.copy()
        field_type, validation = normalize_field_definition(
            normalized["type"], normalized.get("validation")
        )
        normalized["type"] = field_type
        normalized["validation"] = validation
        if normalized.get("nullable") is False and field_type.startswith("Optional["):
            normalized["type"] = field_type[len("Optional[") : -1]
        return normalized

    @model_validator(mode="after")
    def validate_presence_semantics(self) -> "ModelField":
        if not self.required and not self.nullable:
            raise ValueError("A non-required field must be nullable")
        return self


class ExtractionRequest(BaseModel):
    """Request for model generation"""

    model_name: str = Field(description="Name for generated model")
    model_description: str = Field(description="Description of model purpose")
    fields: List[ModelField] = Field(description="Fields to extract")


class ExtractionPlan(BaseModel):
    """A complete extraction plan generated in one model call."""

    instructions: str = Field(description="Explicit extraction instructions")
    target_columns: List[str] = Field(description="Input columns needed for extraction")
    extraction_schema: ExtractionRequest = Field(alias="schema")


@dataclass(frozen=True)
class RowResult(Generic[T]):
    """Extraction outcome, provenance, and usage for one input row.

    Attributes:
        position: Zero-based input position, unique even when DataFrame index
            labels are duplicated.
        source_index: Original DataFrame index label.
        input_data: Exact text or PDF payload sent for this row.
        items: Zero or more validated model instances returned for the row.
        usage: Provider usage recorded by this row's extraction request. It does
            not include operation-level schema planning.
        error: Error text for a failed row, otherwise ``None``.
    """

    position: int
    source_index: Any
    input_data: RowPayload
    items: List[T]
    usage: ExtractorUsage = field(default_factory=ExtractorUsage)
    error: Optional[str] = None

    @property
    def status(self) -> str:
        """Return ``success``, ``empty``, or ``failed`` for this row."""
        if self.error is not None:
            return "failed"
        return "success" if self.items else "empty"


@dataclass
class ExtractionResult(Generic[T]):
    """
    Container for extraction results.

    Attributes:
        data: Extracted data (DataFrame or list of model instances)
        rows: Row-level outcomes with provenance and usage
        model: Generated or provided model class
        usage: Token usage information across all extraction steps

    ``data`` is the convenient flattened output. ``rows`` is the canonical
    mapping back to each input row and preserves empty results, failures, and
    row-specific usage.
    """

    data: Union[pd.DataFrame, List[T]]
    rows: List[RowResult[T]]
    model: Type[T]
    usage: ExtractorUsage = field(default_factory=ExtractorUsage)

    @property
    def failed(self) -> pd.DataFrame:
        """Failed row details as a compatibility-friendly DataFrame view."""
        return pd.DataFrame.from_records(
            [
                {
                    "index": row.source_index,
                    "text": str(row.input_data),
                    "error": row.error,
                }
                for row in self.rows
                if row.error is not None
            ],
            columns=["index", "text", "error"],
        )

    @property
    def attempted_count(self) -> int:
        """Number of input rows submitted for extraction."""
        return len(self.rows)

    @property
    def success_count(self) -> int:
        """Number of input rows extracted successfully."""
        return sum(row.error is None for row in self.rows)

    @property
    def empty_count(self) -> int:
        """Number of successful input rows that produced no model instances."""
        return sum(row.status == "empty" for row in self.rows)

    @property
    def extracted_count(self) -> int:
        """Number of extracted model instances or result rows returned."""
        return len(self.data)

    @property
    def failure_count(self) -> int:
        """Number of input rows that failed extraction."""
        return len(self.failed)

    @property
    def success_rate(self) -> float:
        """Percentage of attempted rows that did not fail."""
        total = self.attempted_count
        return (self.success_count / total * 100) if total > 0 else 0

    def __repr__(self) -> str:
        """String representation"""
        return (
            f"ExtractionResult(success={self.success_count}, "
            f"failed={self.failure_count}, "
            f"model={self.model.__name__})"
        )

    def __str__(self):
        return self.__repr__()


# Rebuild the model to ensure nested fields are properly defined
ModelField.model_rebuild()
