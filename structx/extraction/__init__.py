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

from .extractor import Extractor
from .generator import ModelGenerator

__all__ = [
    "Extractor",
    "ModelGenerator",
]
