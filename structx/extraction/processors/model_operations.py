"""
Model operations including schema generation and custom model processing.
"""

import json
from typing import Any, List, Optional, Tuple, Type

from instructor.processing.multimodal import PDF
from loguru import logger
from pydantic import BaseModel

from structx.core.models import ExtractionPlan, ExtractionRequest
from structx.extraction.core.llm_core import LLMCore
from structx.extraction.generator import ModelGenerator
from structx.utils.prompts import (
    extraction_plan_system_prompt,
    extraction_plan_template,
    refinement_system_prompt,
    refinement_template,
)
from structx.utils.usage import ExtractionStep, ExtractorUsage


class ModelOperations:
    """
    Handles all model-related operations including schema generation and custom model processing.
    """

    def __init__(self, llm_core: LLMCore):
        """
        Initialize model operations.

        Args:
            llm_core: LLM core for completions
        """
        self.llm_core = llm_core

    @staticmethod
    def _validate_target_columns(
        target_columns: List[str], data_columns: List[str]
    ) -> List[str]:
        available_columns = set(data_columns)
        validated = [column for column in target_columns if column in available_columns]
        return validated or data_columns

    def generate_extraction_plan(
        self,
        query: str,
        sample_text: str,
        data_columns: List[str],
        usage: ExtractorUsage,
        pdf_path: Optional[str] = None,
    ) -> ExtractionPlan:
        """Generate instructions, target columns, and schema in one model call."""
        messages = self._plan_messages(query, sample_text, data_columns, pdf_path)
        plan = self.llm_core.complete(
            messages=messages,
            response_model=ExtractionPlan,
            step=ExtractionStep.SCHEMA_GENERATION,
            usage=usage,
        )
        return self._finalize_plan(plan, data_columns)

    async def generate_extraction_plan_async(
        self,
        query: str,
        sample_text: str,
        data_columns: List[str],
        usage: ExtractorUsage,
        pdf_path: Optional[str] = None,
    ) -> ExtractionPlan:
        """Asynchronously generate instructions, target columns, and schema."""
        messages = self._plan_messages(query, sample_text, data_columns, pdf_path)
        plan = await self.llm_core.complete_async(
            messages=messages,
            response_model=ExtractionPlan,
            step=ExtractionStep.SCHEMA_GENERATION,
            usage=usage,
        )
        return self._finalize_plan(plan, data_columns)

    @staticmethod
    def _plan_messages(
        query: str,
        sample_text: str,
        data_columns: List[str],
        pdf_path: Optional[str],
    ) -> List[dict[str, Any]]:
        prompt = extraction_plan_template.substitute(
            query=query,
            available_columns=data_columns,
            sample_text=sample_text or "See the attached PDF document.",
        )
        user_content: Any = [prompt, PDF.from_path(pdf_path)] if pdf_path else prompt
        return [
            {"role": "system", "content": extraction_plan_system_prompt},
            {"role": "user", "content": user_content},
        ]

    @classmethod
    def _finalize_plan(
        cls, plan: ExtractionPlan, data_columns: List[str]
    ) -> ExtractionPlan:
        plan.target_columns = cls._validate_target_columns(
            plan.target_columns, data_columns
        )
        return plan

    def create_model_from_schema(
        self, schema_request: ExtractionRequest
    ) -> Type[BaseModel]:
        """
        Create Pydantic model from extraction request.

        Args:
            schema_request: Request containing model schema

        Returns:
            Generated Pydantic model class
        """
        extraction_model = ModelGenerator.from_extraction_request(schema_request)
        logger.debug("Generated Model Schema:")
        logger.debug(json.dumps(extraction_model.model_json_schema(), indent=2))
        return extraction_model

    def refine_existing_model(
        self,
        model: Type[BaseModel],
        instructions: str,
        usage: ExtractorUsage,
        model_name: Optional[str] = None,
    ) -> Type[BaseModel]:
        """
        Refine an existing data model based on natural language instructions.

        Args:
            model: Existing Pydantic model to refine
            instructions: Natural language instructions for refinement
            model_name: Optional name for the refined model

        Returns:
            A new refined Pydantic model
        """
        # Default model name if not provided
        if model_name is None:
            model_name = f"Refined{model.__name__}"

        extraction_request = self.llm_core.complete(
            response_model=ExtractionRequest,
            messages=self._refinement_messages(model, instructions),
            step=ExtractionStep.SCHEMA_GENERATION,
            usage=usage,
        )
        return self._create_refined_model(extraction_request, model_name)

    async def refine_existing_model_async(
        self,
        model: Type[BaseModel],
        instructions: str,
        usage: ExtractorUsage,
        model_name: Optional[str] = None,
    ) -> Type[BaseModel]:
        """Asynchronously refine an existing model."""
        model_name = model_name or f"Refined{model.__name__}"
        extraction_request = await self.llm_core.complete_async(
            response_model=ExtractionRequest,
            messages=self._refinement_messages(model, instructions),
            step=ExtractionStep.SCHEMA_GENERATION,
            usage=usage,
        )
        return self._create_refined_model(extraction_request, model_name)

    @staticmethod
    def _refinement_messages(
        model: Type[BaseModel], instructions: str
    ) -> List[dict[str, Any]]:
        model_schema = json.dumps(model.model_json_schema(), indent=2)
        return [
            {"role": "system", "content": refinement_system_prompt},
            {
                "role": "user",
                "content": refinement_template.substitute(
                    model_schema=model_schema,
                    instructions=instructions,
                ),
            },
        ]

    @staticmethod
    def _create_refined_model(
        extraction_request: ExtractionRequest, model_name: str
    ) -> Type[BaseModel]:
        extraction_request.model_name = model_name
        return ModelGenerator.from_extraction_request(extraction_request)

    def generate_from_custom_model(
        self,
        model: Type[BaseModel],
        query: str,
        data_columns: List[str],
    ) -> Tuple[str, List[str]]:
        """
        Generate deterministic instructions for a provided custom model.

        Args:
            model: The provided custom model
            query: The original query (used as context)
            data_columns: Available columns in the dataset

        Returns:
            Extraction instructions and columns to include
        """
        instructions = (
            f"{query}\n\nPopulate the supplied {model.__name__} model exactly. "
            "Use only evidence present in the input and leave nullable fields null "
            "when the source does not support a value."
        )
        logger.debug(f"Using all input columns for custom model {model.__name__}")
        return instructions, data_columns
