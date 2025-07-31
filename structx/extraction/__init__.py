"""
Extraction module for structured data extraction.

This module provides a well-organized architecture for extracting structured data
from various sources using LLMs with dynamic model generation.

Structure:
- core/: Core LLM operations and utilities
- processors/: Data processing and model operations
- engines/: Extraction engines for different strategies
- extractor.py: Main orchestrator class
- generator.py: Dynamic model generation
- result_manager.py: Result management utilities
"""

# Core components
from .core import LLMCore, ModelUtils

# Engines
from .engines import ExtractionEngine
from .extractor import Extractor
from .generator import ModelGenerator

# Processors
from .processors import ContentAnalyzer, DataProcessor, ModelOperations
from .result_manager import ResultManager

__all__ = [
    "Extractor",
    "ModelGenerator",
    "ResultManager",
    "LLMCore",
    "ModelUtils",
    "ContentAnalyzer",
    "DataProcessor",
    "ModelOperations",
    "ExtractionEngine",
]
