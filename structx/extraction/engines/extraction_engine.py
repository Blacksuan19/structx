"""
Core extraction engine with different processing strategies.
"""

from functools import lru_cache
from typing import Any, Dict, List, Optional, Type

from instructor.processing.multimodal import PDF
from loguru import logger
from pydantic import BaseModel, Field, create_model

from structx.core.input import PdfRow, RowPayload
from structx.extraction.core.llm_core import LLMCore
from structx.utils.prompts import extraction_system_prompt, extraction_template
from structx.utils.usage import ExtractionStep, ExtractorUsage


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

    @staticmethod
    @lru_cache(maxsize=128)
    def _container_model(extraction_model: Type[BaseModel]) -> Type[BaseModel]:
        return create_model(
            f"{extraction_model.__name__}Container",
            __base__=BaseModel,
            items=(
                List[extraction_model],
                Field(description=f"List of {extraction_model.__name__} items"),
            ),
        )

    @classmethod
    def _text_messages(
        cls,
        text: str,
        extraction_model: Type[BaseModel],
        instructions: str,
    ) -> List[Dict[str, Any]]:
        return [
            {"role": "system", "content": extraction_system_prompt},
            {
                "role": "user",
                "content": extraction_template.substitute(
                    instructions=instructions,
                    text=text,
                ),
            },
        ]

    @classmethod
    def _pdf_messages(
        cls,
        pdf_path: str,
        extraction_model: Type[BaseModel],
        instructions: str,
    ) -> List[Dict[str, Any]]:
        content = [
            f"Extract structured information from this PDF.\n\n{instructions}\n\n",
            PDF.from_path(pdf_path),
        ]
        return [
            {"role": "system", "content": extraction_system_prompt},
            {"role": "user", "content": content},
        ]

    def extract_with_model(
        self,
        text: str,
        extraction_model: Type[BaseModel],
        instructions: str,
        usage: Optional[ExtractorUsage] = None,
    ) -> List[BaseModel]:
        """
        Extract data with enforced structure with retries and usage tracking.

        Args:
            text: Text to extract from
            extraction_model: Pydantic model for extraction
            instructions: Explicit extraction instructions

        Returns:
            List of extracted model instances
        """
        container_model = self._container_model(extraction_model)

        container = self.llm_core.complete(
            messages=self._text_messages(
                text,
                extraction_model,
                instructions,
            ),
            response_model=container_model,
            step=ExtractionStep.EXTRACTION,
            usage=usage,
        )

        # Return just the items
        return container.items

    async def extract_with_model_async(
        self,
        text: str,
        extraction_model: Type[BaseModel],
        instructions: str,
        usage: Optional[ExtractorUsage] = None,
    ) -> List[BaseModel]:
        container = await self.llm_core.complete_async(
            messages=self._text_messages(
                text,
                extraction_model,
                instructions,
            ),
            response_model=self._container_model(extraction_model),
            step=ExtractionStep.EXTRACTION,
            usage=usage,
        )
        return container.items

    def extract_with_multimodal_pdf(
        self,
        pdf_path: str,
        extraction_model: Type[BaseModel],
        instructions: str,
        usage: Optional[ExtractorUsage] = None,
    ) -> List[BaseModel]:
        """
        Extract data from PDF using instructor's multimodal support.

        Args:
            pdf_path: Path to PDF file
            extraction_model: Pydantic model for extraction
            instructions: Explicit extraction instructions

        Returns:
            List of extracted model instances
        """
        wrapper_model = self._container_model(extraction_model)

        logger.debug(f"Extracting from PDF: {pdf_path}")

        result = self.llm_core.complete(
            response_model=wrapper_model,
            messages=self._pdf_messages(
                pdf_path,
                extraction_model,
                instructions,
            ),
            step=ExtractionStep.EXTRACTION,
            usage=usage,
        )
        logger.debug(f"Completed extraction for PDF: {pdf_path}")
        return result.items

    async def extract_with_multimodal_pdf_async(
        self,
        pdf_path: str,
        extraction_model: Type[BaseModel],
        instructions: str,
        usage: Optional[ExtractorUsage] = None,
    ) -> List[BaseModel]:
        result = await self.llm_core.complete_async(
            response_model=self._container_model(extraction_model),
            messages=self._pdf_messages(
                pdf_path,
                extraction_model,
                instructions,
            ),
            step=ExtractionStep.EXTRACTION,
            usage=usage,
        )
        return result.items

    def extract_from_row_data(
        self,
        row_data: RowPayload,
        extraction_model: Type[BaseModel],
        instructions: str,
        usage: Optional[ExtractorUsage] = None,
    ) -> List[BaseModel]:
        """
        Extract data from row data (either text or multimodal).

        Args:
            row_data: Row data to extract from
            extraction_model: Pydantic model for extraction
            instructions: Explicit extraction instructions

        Returns:
            List of extracted model instances
        """
        if isinstance(row_data, PdfRow):
            return self.extract_with_multimodal_pdf(
                pdf_path=str(row_data.pdf_path),
                extraction_model=extraction_model,
                instructions=instructions,
                usage=usage,
            )
        else:
            # Handle regular text extraction
            return self.extract_with_model(
                text=row_data,
                extraction_model=extraction_model,
                instructions=instructions,
                usage=usage,
            )

    async def extract_from_row_data_async(
        self,
        row_data: RowPayload,
        extraction_model: Type[BaseModel],
        instructions: str,
        usage: Optional[ExtractorUsage] = None,
    ) -> List[BaseModel]:
        """Asynchronously extract one independent row."""
        if isinstance(row_data, PdfRow):
            return await self.extract_with_multimodal_pdf_async(
                pdf_path=str(row_data.pdf_path),
                extraction_model=extraction_model,
                instructions=instructions,
                usage=usage,
            )
        return await self.extract_with_model_async(
            text=row_data,
            extraction_model=extraction_model,
            instructions=instructions,
            usage=usage,
        )
