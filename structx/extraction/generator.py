from typing import Dict, List, Optional, Type

from loguru import logger
from pydantic import BaseModel, Field, create_model
from pydantic._internal._model_construction import ModelMetaclass

from structx.core.exceptions import ModelGenerationError
from structx.core.models import ExtractionRequest, ModelField
from structx.core.type_system import is_collection_type, resolve_type_expression
from structx.utils.helpers import handle_errors


class ModelGenerator(ModelMetaclass):
    """Metaclass for generating dynamic Pydantic models"""

    @classmethod
    @handle_errors(
        error_message="Error creating nested model", error_type=ModelGenerationError
    )
    def _create_nested_model(
        cls,
        field_name: str,
        field_description: str,
        nested_fields: List[ModelField],
        parent_name: str = "",
    ) -> Type[BaseModel]:
        """Create a nested Pydantic model"""
        logger.debug(f"\nCreating nested model: {field_name}")
        logger.debug(f"Parent name: {parent_name}")

        field_definitions: Dict[str, tuple[type, Field]] = {}

        for field in nested_fields:
            if field.nested_fields:
                nested_model = cls._create_nested_model(
                    field_name=field.name,
                    field_description=field.description,
                    nested_fields=field.nested_fields,
                    parent_name=field_name,
                )
                field_type = (
                    List[nested_model]
                    if is_collection_type(field.type)
                    else nested_model
                )
            else:
                field_type = resolve_type_expression(field.type)

            field_definitions[field.name] = (
                Optional[field_type],
                Field(
                    default=None,
                    description=field.description,
                    **(field.validation or {}),
                ),
            )

        model_name = f"{parent_name}{field_name}" if parent_name else field_name

        # Create the model using Pydantic v2 style
        model = create_model(model_name, __base__=BaseModel, **field_definitions)

        # Add description as model docstring
        model.__doc__ = field_description

        return model

    @classmethod
    @handle_errors(
        error_message="Error generating model from extraction request",
        error_type=ModelGenerationError,
    )
    def from_extraction_request(cls, request: ExtractionRequest) -> Type[BaseModel]:
        """Create a new model from extraction request"""
        logger.info("\nStarting model generation from extraction request")
        logger.info(f"Model name: {request.model_name}")
        logger.info(f"Description: {request.model_description}")
        logger.info("Fields:")
        for field in request.fields:
            logger.info(f"- {field.name}: {field.type}")
            if field.nested_fields:
                logger.info(
                    f"  With nested fields: {[f.name for f in field.nested_fields]}"
                )

        # Create the model
        model = cls._create_nested_model(
            field_name=request.model_name,
            field_description=request.model_description,
            nested_fields=request.fields,
        )

        logger.info("\nModel generation completed")

        return model


class DynamicModel(BaseModel, metaclass=ModelGenerator):
    """Base class for dynamically generated models"""

    pass
