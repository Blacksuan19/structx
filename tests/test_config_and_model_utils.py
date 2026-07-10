from typing import Literal

import pytest
from pydantic import BaseModel, Field, ValidationError

from structx.core.config import ExtractionConfig, StepConfig
from structx.extraction.core.model_utils import ModelUtils


class IncidentModel(BaseModel):
    """Incident record."""

    severity: Literal["low", "high"] = Field(description="Incident severity")
    summary: str = Field(description="Short incident summary")
    count: int


def test_step_config_merges_defaults_with_overrides():
    assert StepConfig(temperature=0.7).model_dump() == {
        "temperature": 0.7,
        "top_p": 0.1,
        "max_tokens": 2000,
    }


def test_step_config_validates_ranges():
    with pytest.raises(ValidationError):
        StepConfig(temperature=2.0)


def test_extraction_config_merges_nested_overrides():
    config = ExtractionConfig(
        config={
            "extraction": {"temperature": 0.3},
            "analysis": {"max_tokens": 123},
        }
    )

    assert config.extraction["temperature"] == 0.3
    assert config.extraction["max_tokens"] == 8192
    assert config.analysis["max_tokens"] == 123


def test_model_utils_extracts_schema_info_and_enum_values():
    schema_info = ModelUtils.extract_model_schema_info(IncidentModel)

    assert "- severity" in schema_info
    assert "Possible values: low, high" in schema_info
    assert "Short incident summary" in schema_info


def test_model_utils_creates_context_for_document_model():
    context = ModelUtils.create_model_context(IncidentModel, "document")

    assert "Model fields and descriptions" in context
    assert "from the document" in context


def test_model_utils_extracts_characteristics_requirements_and_description():
    characteristics = ModelUtils.extract_field_characteristics(IncidentModel)
    requirements = ModelUtils.extract_structural_requirements(IncidentModel)
    description = ModelUtils.get_model_description(IncidentModel)

    assert any("severity" in item and "Possible values" in item for item in characteristics)
    assert requirements["summary"] == "string"
    assert description == "Incident record."
