"""
Core extraction engine with different processing strategies.
"""

from typing import Any, Dict, List, Type, Union

from loguru import logger
from pydantic import BaseModel, Field, create_model

from structx.core.exceptions import ExtractionError
from structx.core.models import ExtractionGuide, QueryRefinement
from structx.extraction.core.llm_core import LLMCore
from structx.extraction.core.model_utils import ModelUtils
from structx.utils.helpers import handle_errors
from structx.utils.prompts import extraction_system_prompt, extraction_template
from structx.utils.usage import ExtractionStep


class ExtractionEngine:
    """
    Core extraction engine with different processing strategies.
    """

    def __init__(self, llm_core: LLMCore):
        """
        Initialize extraction engine.

        Args:
            llm_core: LLM core for completions
        """
        self.llm_core = llm_core

    @handle_errors(error_message="Text extraction failed", error_type=ExtractionError)
    def extract_with_model(
        self,
        text: str,
        extraction_model: Type[BaseModel],
        refined_query: QueryRefinement,
        guide: ExtractionGuide,
        is_custom_model: bool = False,
    ) -> List[BaseModel]:
        """
        Extract data with enforced structure with retries and usage tracking.

        Args:
            text: Text to extract from
            extraction_model: Pydantic model for extraction
            refined_query: Refined query with details
            guide: Extraction guide with patterns
            is_custom_model: Whether this is a user-provided model

        Returns:
            List of extracted model instances
        """
        # Create a container model to wrap the list items
        # this is necessary to be able to track token usage, when passing an iterable data model
        # result._raw_response does not exist making usage calculations not possible
        container_name = f"{extraction_model.__name__}Container"
        container_model = create_model(
            container_name,
            __base__=BaseModel,
            items=(
                List[extraction_model],
                Field(description=f"List of {extraction_model.__name__} items"),
            ),
        )

        # Get model context for custom models
        extra_context = ""
        if is_custom_model:
            extra_context = ModelUtils.create_model_context(extraction_model, "text")

        # Use _perform_llm_completion with the container model
        container = self.llm_core.complete_with_retry(
            messages=[
                {"role": "system", "content": extraction_system_prompt},
                {
                    "role": "user",
                    "content": extraction_template.substitute(
                        query=refined_query.refined_query,
                        patterns=guide.structural_patterns,
                        rules=(
                            guide.relationship_rules + [extra_context]
                            if extra_context
                            else guide.relationship_rules
                        ),
                        text=text,
                    ),
                },
            ],
            response_model=container_model,
            config=self.llm_core.config.extraction,
            step=ExtractionStep.EXTRACTION,
        )

        # Return just the items
        return container.items

    @handle_errors(error_message="PDF extraction failed", error_type=ExtractionError)
    def extract_with_multimodal_pdf(
        self,
        pdf_path: str,
        extraction_model: Type[BaseModel],
        refined_query: QueryRefinement,
        guide: ExtractionGuide,
        is_custom_model: bool = False,
    ) -> List[BaseModel]:
        """
        Extract data from PDF using instructor's multimodal support.

        Args:
            pdf_path: Path to PDF file
            extraction_model: Pydantic model for extraction
            refined_query: Refined query with details
            guide: Extraction guide with patterns
            is_custom_model: Whether this is a user-provided model

        Returns:
            List of extracted model instances
        """
        try:
            from instructor.multimodal import PDF
        except ImportError:
            raise ImportError(
                "instructor multimodal support is required for PDF processing. "
                "Install it with: pip install instructor[multimodal]"
            )

        # For multimodal PDF, we need a single wrapper model, not a container with multiple items
        # This is because instructor's multimodal support expects a single response, not multiple tool calls
        wrapper_name = f"{extraction_model.__name__}List"
        wrapper_model = create_model(
            wrapper_name,
            __base__=BaseModel,
            items=(
                List[extraction_model],
                Field(
                    description=f"List of extracted {extraction_model.__name__} items from the document"
                ),
            ),
        )

        # Get model context for custom models
        extra_context = ""
        if is_custom_model:
            extra_context = ModelUtils.create_model_context(
                extraction_model, "document"
            )

        content = [
            f"Extract structured information from this PDF document following these guidelines:\n\n"
            f"Query: {refined_query.refined_query}\n"
            f"Patterns: {guide.structural_patterns}\n"
            f"Rules: {guide.relationship_rules + [extra_context] if extra_context else guide.relationship_rules}\n\n",
            PDF.from_path(pdf_path),
        ]

        logger.info(
            f"Extracting from PDF: {pdf_path} with query: {refined_query.refined_query}"
        )

        result = self.llm_core.complete_with_retry(
            response_model=wrapper_model,
            messages=[
                {"role": "system", "content": extraction_system_prompt},
                {
                    "role": "user",
                    "content": content,
                },
            ],
            step=ExtractionStep.EXTRACTION,
            config=self.llm_core.config.extraction,
        )
        logger.info(f"Completed extraction for PDF: {pdf_path}")
        return result.items

    def extract_from_row_data(
        self,
        row_data: Union[str, Dict[str, Any]],
        extraction_model: Type[BaseModel],
        refined_query: QueryRefinement,
        guide: ExtractionGuide,
        is_custom_model: bool = False,
    ) -> List[BaseModel]:
        """
        Extract data from row data (either text or multimodal).

        Args:
            row_data: Row data to extract from
            extraction_model: Pydantic model for extraction
            refined_query: Refined query with details
            guide: Extraction guide with patterns
            is_custom_model: Whether this is a user-provided model

        Returns:
            List of extracted model instances
        """
        # Check if this is a multimodal PDF row
        if (
            isinstance(row_data, dict)
            and row_data.get("multimodal")
            and row_data.get("file_type") == "pdf"
        ):
            pdf_path = row_data.get("pdf_path")
            return self.extract_with_multimodal_pdf(
                pdf_path=pdf_path,
                extraction_model=extraction_model,
                refined_query=refined_query,
                guide=guide,
                is_custom_model=is_custom_model,
            )
        else:
            # Handle regular text extraction
            row_text = row_data if isinstance(row_data, str) else str(row_data)
            return self.extract_with_model(
                text=row_text,
                extraction_model=extraction_model,
                refined_query=refined_query,
                guide=guide,
                is_custom_model=is_custom_model,
            )
