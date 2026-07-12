"""
structx: Structured data extraction using LLMs
"""

from structx.core.config import ExtractionConfig, StepConfig
from structx.core.models import (
    ExtractionPlan,
    ExtractionRequest,
    ExtractionResult,
    ModelField,
    RowResult,
)
from structx.extraction.extractor import Extractor
from structx.schema import (
    ContainerTypeCapability,
    ScalarTypeCapability,
    TypeCapabilities,
    TypeModifierCapabilities,
    get_type_capabilities,
    model_from_extraction_request,
    model_to_extraction_request,
)

__version__ = "0.6.2"
__all__ = [
    "Extractor",
    "ExtractionConfig",
    "StepConfig",
    "ModelField",
    "ExtractionPlan",
    "ExtractionRequest",
    "ExtractionResult",
    "RowResult",
    "ScalarTypeCapability",
    "ContainerTypeCapability",
    "TypeModifierCapabilities",
    "TypeCapabilities",
    "get_type_capabilities",
    "model_to_extraction_request",
    "model_from_extraction_request",
]
