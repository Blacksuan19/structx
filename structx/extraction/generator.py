from typing import Dict, FrozenSet, List, Optional, Set, Tuple, Type, get_args

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, create_model

from structx.core.exceptions import ModelGenerationError
from structx.core.models import ExtractionRequest, ModelField
from structx.core.type_system import normalize_type_expression, resolve_type_expression
from structx.utils.helpers import handle_errors


class ModelGenerator:
    """Factory for generating dynamic Pydantic models."""

    @staticmethod
    def _nested_field_type(field: ModelField, nested_model: Type[BaseModel]) -> type:
        expression = normalize_type_expression(field.type)
        is_optional = expression.startswith("Optional[")
        if is_optional:
            expression = expression[len("Optional[") : -1]

        if expression.startswith("List["):
            field_type = List[nested_model]
        elif expression.startswith("Set["):
            field_type = Set[nested_model]
        elif expression.startswith("FrozenSet["):
            field_type = FrozenSet[nested_model]
        elif expression.startswith("Tuple["):
            field_type = Tuple[nested_model]
        else:
            field_type = nested_model
        return Optional[field_type] if is_optional else field_type

    @staticmethod
    def _field_annotation(field: ModelField, field_type: type) -> type:
        type_is_nullable = type(None) in get_args(field_type)
        if field.nullable and not type_is_nullable:
            return Optional[field_type]
        return field_type

    @classmethod
    def _create_nested_model(
        cls,
        field_name: str,
        field_description: str,
        nested_fields: List[ModelField],
        parent_name: str = "",
        frozen: bool = False,
    ) -> Type[BaseModel]:
        """Create a nested Pydantic model"""
        logger.debug(f"\nCreating nested model: {field_name}")
        logger.debug(f"Parent name: {parent_name}")

        field_definitions: Dict[str, tuple[type, Field]] = {}

        for field in nested_fields:
            if field.nested_fields:
                nested_expression = normalize_type_expression(field.type)
                nested_model = cls._create_nested_model(
                    field_name=field.name,
                    field_description=field.description,
                    nested_fields=field.nested_fields,
                    parent_name=field_name,
                    frozen=(
                        "Set[" in nested_expression or "FrozenSet[" in nested_expression
                    ),
                )
                field_type = cls._nested_field_type(field, nested_model)
            else:
                field_type = resolve_type_expression(field.type)

            field_definitions[field.name] = (
                cls._field_annotation(field, field_type),
                Field(
                    default=... if field.required else None,
                    description=field.description,
                    **(field.validation or {}),
                ),
            )

        model_name = f"{parent_name}{field_name}" if parent_name else field_name

        # Create the model using Pydantic v2 style
        model_options = (
            {"__config__": ConfigDict(frozen=True)}
            if frozen
            else {"__base__": BaseModel}
        )
        model = create_model(model_name, **model_options, **field_definitions)

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
        logger.debug("Starting model generation from extraction request")
        logger.debug(f"Model name: {request.model_name}")
        logger.debug(f"Description: {request.model_description}")
        logger.debug("Fields:")
        for field in request.fields:
            logger.debug(f"- {field.name}: {field.type}")
            if field.nested_fields:
                logger.debug(
                    f"  With nested fields: {[f.name for f in field.nested_fields]}"
                )

        # Create the model
        model = cls._create_nested_model(
            field_name=request.model_name,
            field_description=request.model_description,
            nested_fields=request.fields,
        )

        logger.debug("Model generation completed")

        return model
