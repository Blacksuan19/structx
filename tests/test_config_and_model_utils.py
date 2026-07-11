from typing import Literal

from pydantic import BaseModel, Field

from structx.core.config import ExtractionConfig, StepConfig
from structx.extraction.core.model_utils import ModelUtils


class IncidentModel(BaseModel):
    """Incident record."""

    severity: Literal["low", "high"] = Field(description="Incident severity")
    summary: str = Field(description="Short incident summary")
    count: int


def test_step_config_has_no_implicit_model_parameters():
    assert StepConfig().model_dump() == {}


def test_step_config_preserves_provider_specific_parameters():
    assert StepConfig(
        reasoning_effort="low",
        max_completion_tokens=16_000,
    ).model_dump() == {
        "reasoning_effort": "low",
        "max_completion_tokens": 16_000,
    }


def test_extraction_config_only_returns_explicit_parameters():
    config = ExtractionConfig(
        config={
            "planning": {"reasoning_effort": "low"},
            "extraction": {"max_completion_tokens": 16_000},
        }
    )

    assert config.planning == {"reasoning_effort": "low"}
    assert config.extraction == {"max_completion_tokens": 16_000}


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

    assert any(
        "severity" in item and "Possible values" in item for item in characteristics
    )
    assert requirements["summary"] == "string"
    assert description == "Incident record."
