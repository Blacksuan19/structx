from dataclasses import dataclass
from typing import Any, Dict, Generic, List, Optional, Type, Union

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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


class QueryRefinement(BaseModel):
    """Refined query with structural information"""

    refined_query: str = Field(description="Expanded query with structure requirements")
    data_characteristics: List[str] = Field(
        default_factory=list, description="Characteristics of data to extract"
    )
    structural_requirements: Dict[str, Any] = Field(
        default_factory=dict, description="Requirements for data structure"
    )

    @field_validator("data_characteristics", mode="before")
    @classmethod
    def default_data_characteristics(cls, value: Any) -> Any:
        return [] if value is None else value

    @field_validator("structural_requirements", mode="before")
    @classmethod
    def default_structural_requirements(cls, value: Any) -> Any:
        return {} if value is None else value


class ExtractionGuide(BaseModel):
    """Guide for structured extraction"""

    model_config = ConfigDict(extra="allow")

    target_columns: List[str] = Field(description="Columns to analyze")

    structural_patterns: Dict[str, str] = Field(
        default_factory=dict, description="Patterns for structuring data"
    )
    relationship_rules: List[str] = Field(
        default_factory=list, description="Rules for data relationships"
    )
    organization_principles: List[str] = Field(
        default_factory=list, description="Principles for data organization"
    )

    @field_validator("relationship_rules", "organization_principles", mode="before")
    @classmethod
    def default_list_fields(cls, value: Any) -> Any:
        return [] if value is None else value

    @field_validator("structural_patterns", mode="before")
    @classmethod
    def default_structural_patterns(cls, value: Any) -> Any:
        return {} if value is None else value


class ExtractionRequest(BaseModel):
    """Request for model generation"""

    model_name: str = Field(description="Name for generated model")
    model_description: str = Field(description="Description of model purpose")
    fields: List[ModelField] = Field(description="Fields to extract")


class ExtractionPlan(BaseModel):
    """A complete extraction plan generated in one model call."""

    refined_query: QueryRefinement
    guide: ExtractionGuide
    extraction_schema: ExtractionRequest = Field(alias="schema")


@dataclass
class ExtractionResult(Generic[T]):
    """
    Container for extraction results.

    Attributes:
        data: Extracted data (DataFrame or list of model instances)
        failed: DataFrame with failed extractions
        model: Generated or provided model class
        usage: Token usage information across all extraction steps
    """

    data: Union[pd.DataFrame, List[T]]
    failed: pd.DataFrame
    model: Type[T]
    usage: Optional[ExtractorUsage] = None

    @property
    def success_count(self) -> int:
        """Number of successful extractions"""
        if isinstance(self.data, pd.DataFrame):
            return len(self.data)
        return len(self.data)

    @property
    def failure_count(self) -> int:
        """Number of failed extractions"""
        return len(self.failed)

    @property
    def success_rate(self) -> float:
        """Success rate as a percentage"""
        total = self.success_count + self.failure_count
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
