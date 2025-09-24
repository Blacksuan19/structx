"""
structx: Structured data extraction using LLMs
"""

from structx.core.config import ExtractionConfig, StepConfig
from structx.core.models import (
    ExtractionGuide,
    ExtractionRequest,
    ModelField,
    QueryRefinement,
)
from structx.extraction.extractor import Extractor

__version__ = "0.4.9"

# Deprecation warning for PyPI package rename
import warnings

warnings.warn(
    "The PyPI package 'structx-llm' has been renamed to 'structx'. "
    "Please update your requirements to use 'structx'.",
    category=DeprecationWarning,
    stacklevel=2,
)
__all__ = [
    "Extractor",
    "ExtractionConfig",
    "StepConfig",
    "ModelField",
    "QueryAnalysis",
    "QueryRefinement",
    "ExtractionGuide",
    "ExtractionRequest",
]
