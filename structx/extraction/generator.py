from typing import Dict, List, Optional, Type

from loguru import logger
from pydantic import BaseModel, Field, create_model
from pydantic._internal._model_construction import ModelMetaclass

from structx.core.exceptions import ModelGenerationError
from structx.core.models import ExtractionRequest, ModelField
from structx.utils.constants import SAFE_TYPES, TYPE_ALIASES
from structx.utils.helpers import handle_errors


class ModelGenerator(ModelMetaclass):
    """Metaclass for generating dynamic Pydantic models"""

    _model_registry = {}  # Class variable to store created models

    @classmethod
    def _register_model(cls, model_name: str, model: Type[BaseModel]):
        """Register a created model for reference"""
        cls._model_registry[model_name] = model

    @classmethod
    def _get_registered_model(cls, model_name: str) -> Optional[Type[BaseModel]]:
        """Get a registered model by name"""
        return cls._model_registry.get(model_name)

    @classmethod
    @handle_errors(error_message="Error parsing generic type", error_type=ValueError)
    def _parse_generic_type(cls, type_str: str) -> Type:
        """Parse and validate generic type strings"""
        base_type = type_str[: type_str.index("[")] if "[" in type_str else type_str

        # Check if it's a generic type constructor
        if base_type not in SAFE_TYPES:
            raise ValueError(f"Unsupported base type: {base_type}")

        if "[" not in type_str:
            return SAFE_TYPES[base_type]

        params_str = type_str[type_str.index("[") + 1 : type_str.rindex("]")]

        if base_type == "Dict":
            key_type_str, value_type_str = params_str.split(",", 1)
            key_type = cls._evaluate_type(key_type_str.strip())
            value_type = cls._evaluate_type(value_type_str.strip())
            return Dict[key_type, value_type]

        elif base_type in ("List", "Optional"):
            inner_type = cls._evaluate_type(params_str.strip())
            return SAFE_TYPES[base_type][inner_type]

        raise ValueError(f"Unsupported generic type: {type_str}")

    @classmethod
    def _normalize_type(cls, type_str: str) -> str:
        """Normalize type strings to Python types"""
        # Remove any whitespace
        type_str = type_str.strip()

        # Check if it's a basic type alias
        if type_str.lower() in TYPE_ALIASES:
            return TYPE_ALIASES[type_str.lower()]

        # Handle generic types (List[], Dict[], etc.)
        if "[" in type_str and "]" in type_str:
            base_type = type_str[: type_str.index("[")]
            params = type_str[type_str.index("[") + 1 : type_str.rindex("]")]

            # Normalize base type
            if base_type.lower() in TYPE_ALIASES:
                base_type = TYPE_ALIASES[base_type.lower()]

            # Recursively normalize parameter types
            param_types = [cls._normalize_type(p.strip()) for p in params.split(",")]
            return f"{base_type}[{', '.join(param_types)}]"

        return type_str

    @classmethod
    @handle_errors(
        error_message="Error evaluating type",
        error_type=ValueError,
        default_return=str,
    )
    def _evaluate_type(cls, type_str: str) -> Type:
        """Safely evaluate type string"""
        # Normalize the type string first
        normalized_type = cls._normalize_type(type_str)
        logger.debug(f"Normalized type '{type_str}' to '{normalized_type}'")

        # Check if it's a base type
        if normalized_type in SAFE_TYPES:
            return SAFE_TYPES[normalized_type]

        # Check if it's a registered model
        if normalized_type in cls._model_registry:
            return cls._get_registered_model(normalized_type)

        # Check if it's a generic type
        if any(
            normalized_type.startswith(f"{t}[") for t in ("List", "Dict", "Optional")
        ):
            return cls._parse_generic_type(normalized_type)

        # If it's not a generic type and not registered, it might be a model
        # that hasn't been created yet
        logger.info(
            f"Type '{normalized_type}' not found in registry, will be created later"
        )
        return normalized_type

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

        # First create any nested models needed
        nested_models = {}
        for field in nested_fields:
            if field.nested_fields:
                nested_model = cls._create_nested_model(
                    field_name=field.name,
                    field_description=field.description,
                    nested_fields=field.nested_fields,
                    parent_name=field_name,
                )
                nested_models[field.name] = nested_model
                cls._register_model(field.name, nested_model)

        field_definitions: Dict[str, tuple[type, Field]] = {}

        for field in nested_fields:
            # Get base type
            if field.name in nested_models:
                field_type = nested_models[field.name]
            else:
                normalized_type = cls._normalize_type(field.type)
                field_type = cls._evaluate_type(normalized_type)

            # Handle List types
            if isinstance(field.type, str) and (
                field.type.startswith("List[")
                or field.type.startswith("array[")
                or field.type == "array"
            ):
                if field.nested_fields:
                    # Create model for list items
                    item_model = cls._create_nested_model(
                        field_name=f"{field.name}Item",
                        field_description=field.description,
                        nested_fields=field.nested_fields,
                        parent_name=field_name,
                    )
                    field_type = List[item_model]
                else:
                    field_type = List[field_type]

            field_definitions[field.name] = (
                Optional[field_type],
                Field(
                    default=None,
                    description=field.description,
                    **field.validation or {},
                ),
            )

        model_name = f"{parent_name}{field_name}" if parent_name else field_name

        # Create the model using Pydantic v2 style
        model = create_model(model_name, __base__=BaseModel, **field_definitions)

        # Add description as model docstring
        model.__doc__ = field_description

        # Register the model
        cls._register_model(model_name, model)

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

        # Reset model registry
        cls._model_registry = {}
        logger.debug("Reset model registry")

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
