from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelField(BaseModel):
    """Definition of a field in the extraction model"""

    name: str = Field(description="Name of the field")
    type: str = Field(description="Type of the field")
    description: str = Field(description="Description of what this field represents")
    validation: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional validation rules"
    )
    nested_fields: Optional[List["ModelField"]] = Field(
        default=None, description="Fields for nested models"
    )

    class Config:
        validate_assignment = True


class QueryAnalysis(BaseModel):
    """Result of query analysis"""

    target_column: str = Field(description="Column containing text to analyze")
    extraction_purpose: str = Field(description="Purpose of extraction")


class QueryRefinement(BaseModel):
    """Refined query with structural information"""

    refined_query: str = Field(description="Expanded query with structure requirements")
    data_characteristics: Optional[List[str]] = Field(
        description="Characteristics of data to extract"
    )
    structural_requirements: Optional[Dict[str, str]] = Field(
        description="Requirements for data structure"
    )


class ExtractionGuide(BaseModel):
    """Guide for structured extraction"""

    structural_patterns: Optional[Dict[str, str]] = Field(
        description="Patterns for structuring data"
    )
    relationship_rules: Optional[List[str]] = Field(
        description="Rules for data relationships"
    )
    organization_principles: Optional[List[str]] = Field(
        description="Principles for data organization"
    )

    class Config:
        extra = "allow"  # Allow extra fields to be flexible with LLM responses


class ExtractionRequest(BaseModel):
    """Request for model generation"""

    model_name: str = Field(description="Name for generated model")
    model_description: str = Field(description="Description of model purpose")
    fields: List[ModelField] = Field(description="Fields to extract")
    extraction_strategy: str = Field(description="Strategy for extraction")


# Rebuild the model to ensure nested fields are properly defined
ModelField.model_rebuild()
