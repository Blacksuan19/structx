"""
Model operations including schema generation and custom model processing.
"""

import json
from typing import List, Tuple, Type

from loguru import logger
from pydantic import BaseModel

from structx.core.exceptions import ExtractionError
from structx.core.models import (
    ExtractionGuide,
    ExtractionPlan,
    ExtractionRequest,
    QueryRefinement,
)
from structx.extraction.core.llm_core import LLMCore
from structx.extraction.core.model_utils import ModelUtils
from structx.extraction.generator import ModelGenerator
from structx.extraction.processors.content_analyzer import ContentAnalyzer
from structx.utils.helpers import handle_errors
from structx.utils.prompts import (
    custom_model_guide_template,
    extraction_plan_system_prompt,
    extraction_plan_template,
    refinement_system_prompt,
    refinement_template,
)
from structx.utils.usage import ExtractionStep


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

    @handle_errors(error_message="Plan generation failed", error_type=ExtractionError)
    def generate_extraction_plan(
        self, query: str, sample_text: str, data_columns: List[str]
    ) -> ExtractionPlan:
        """Generate refinement, guide, and schema in one model call."""
        plan = self.llm_core.complete(
            messages=[
                {"role": "system", "content": extraction_plan_system_prompt},
                {
                    "role": "user",
                    "content": extraction_plan_template.substitute(
                        query=query,
                        available_columns=data_columns,
                        sample_text=sample_text,
                    ),
                },
            ],
            response_model=ExtractionPlan,
            config=self.llm_core.config.planning,
            step=ExtractionStep.SCHEMA_GENERATION,
        )
        available_columns = set(data_columns)
        plan.guide.target_columns = [
            column
            for column in plan.guide.target_columns
            if column in available_columns
        ]
        if not plan.guide.target_columns:
            plan.guide.target_columns = data_columns
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
        logger.info("Generated Model Schema:")
        logger.info(json.dumps(extraction_model.model_json_schema(), indent=2))
        return extraction_model

    def refine_existing_model(
        self,
        model: Type[BaseModel],
        instructions: str,
        model_name: str = None,
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

        # Get the schema of the existing model
        model_schema = model.model_json_schema()
        model_schema_str = json.dumps(model_schema, indent=2)

        # Generate schema for the refined model directly
        extraction_request = self.llm_core.complete(
            response_model=ExtractionRequest,
            messages=[
                {
                    "role": "system",
                    "content": refinement_system_prompt,
                },
                {
                    "role": "user",
                    "content": refinement_template.substitute(
                        model_schema=model_schema_str,
                        instructions=instructions,
                    ),
                },
            ],
            config=self.llm_core.config.planning,
            step=ExtractionStep.SCHEMA_GENERATION,
        )

        # Set the model name if specified
        if model_name:
            extraction_request.model_name = model_name

        refined_model = ModelGenerator.from_extraction_request(extraction_request)

        return refined_model

    def generate_from_custom_model(
        self,
        model: Type[BaseModel],
        query: str,
        data_columns: List[str],
    ) -> Tuple[QueryRefinement, ExtractionGuide]:
        """
        Generate refinement and guide from a provided custom model.

        When a custom model is provided, we reverse engineer the refinement and guide
        to match the model structure, rather than generating them from the query.

        Args:
            model: The provided custom model
            query: The original query (used as context)
            data_columns: Available columns in the dataset

        Returns:
            Tuple of refined_query and extraction_guide
        """
        # Get model schema and description
        model_description = ModelUtils.get_model_description(model)
        model_schema = model.model_json_schema()
        model_properties = model_schema.get("properties", {})

        # Extract data characteristics from the model properties
        data_characteristics = ModelUtils.extract_field_characteristics(model)

        # Extract structure requirements
        structural_requirements = ModelUtils.extract_structural_requirements(model)

        # Create a simplified query refinement with explicit field mapping instructions
        model_fields = list(model_properties.keys())
        refined_query = QueryRefinement(
            refined_query=f"Extract {model_description} as specified in the provided model, filling all fields with relevant data from the appropriate columns. Original query: {query}",
            data_characteristics=data_characteristics,
            structural_requirements=structural_requirements,
        )

        # Create custom field-to-column mapping suggestions based on field names and data columns
        field_descriptions = {}
        for prop_name, prop_info in model_properties.items():
            field_descriptions[prop_name] = {
                "description": prop_info.get("description", ""),
                "type": prop_info.get("type", ""),
                "enum": prop_info.get("enum", []),
            }

        column_suggestions = ContentAnalyzer.suggest_column_mappings(
            model_properties, data_columns, field_descriptions
        )

        # Generate guide with enhanced column mapping
        guide_messages = [
            {"role": "system", "content": "You are an extraction guide generator."},
            {
                "role": "user",
                "content": custom_model_guide_template.substitute(
                    data_characteristics=data_characteristics,
                    available_columns=data_columns,
                    model_fields=model_fields,
                    column_suggestions=json.dumps(column_suggestions, indent=2),
                ),
            },
        ]

        guide = self.llm_core.complete(
            messages=guide_messages,
            response_model=ExtractionGuide,
            config=self.llm_core.config.planning,
            step=ExtractionStep.SCHEMA_GENERATION,
        )

        logger.info(f"Extraction Columns: {guide.target_columns}")
        logger.info(
            f"Generated refinement and guide from custom model: {model.__name__}"
        )

        return refined_query, guide
