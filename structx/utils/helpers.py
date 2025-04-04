import functools
import json
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, Type

from loguru import logger

from structx.core.exceptions import ExtractionError
from structx.core.models import ExtractionRequest, ModelField
from structx.utils.types import P, R


def handle_errors(
    error_message: str,
    error_type: Type[Exception] = ExtractionError,
    default_return: Any = None,
):
    """
    Decorator for consistent error handling and logging

    Args:
        error_message: Base message for the error
        error_type: Type of exception to raise
        default_return: Default return value if an error occurs
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Call the function
                return func(*args, **kwargs)

            except Exception as e:
                logger.error(
                    f"{error_message}: {str(e)}\n" f"Function: {func.__name__}"
                )

                if default_return is not None:
                    return default_return

                raise error_type(f"{error_message}: {str(e)}") from e

        return wrapper

    return decorator


def flatten_extracted_data(data: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    """
    Flatten nested structures for DataFrame storage

    Args:
        data: Nested dictionary of extracted data
        prefix: Prefix for nested keys
    """
    flattened = {}

    for key, value in data.items():
        new_key = f"{prefix}_{key}" if prefix else key

        if isinstance(value, dict):
            nested = flatten_extracted_data(value, new_key)
            flattened.update(nested)
        elif isinstance(value, list):
            if value and isinstance(value[0], dict):
                for i, item in enumerate(value):
                    nested = flatten_extracted_data(item, f"{new_key}_{i}")
                    flattened.update(nested)
            else:
                flattened[new_key] = json.dumps(value)
        else:
            flattened[new_key] = value

    return flattened


def async_wrapper(sync_method: Callable[P, R]) -> Callable[P, Awaitable[R]]:
    """
    Decorator to create async versions of sync methods with shared docstrings

    Args:
        sync_method: The synchronous method to wrap

    Returns:
        Async version of the method with preserved signature
    """
    method_name = sync_method.__name__

    @functools.wraps(sync_method)
    async def async_method(*args: P.args, **kwargs: P.kwargs) -> R:
        """Asynchronous wrapper"""
        self = args[0]  # The first argument is 'self'
        # Use _run_async from the instance
        return await self._run_async(sync_method, *args, **kwargs)

    # Add a note that this is an async version
    if sync_method.__doc__:
        async_method.__doc__ = (
            f"Asynchronous version of `{method_name}`.\n\n{sync_method.__doc__}"
        )
    else:
        async_method.__doc__ = f"Asynchronous version of `{method_name}`."

    # Rename the method
    async_method.__name__ = f"{method_name}_async"
    async_method.__qualname__ = f"{sync_method.__qualname__}_async"

    return async_method


def convert_pydantic_v1_to_v2(request: ExtractionRequest) -> ExtractionRequest:
    """
    Comprehensively convert Pydantic v1 syntax to v2 syntax in an extraction request

    Args:
        request: The extraction request potentially containing v1 syntax

    Returns:
        Updated extraction request with v2 syntax
    """

    def convert_field(field: ModelField) -> ModelField:
        """Convert a single field from v1 to v2 syntax"""
        # Create a copy of the validation dict
        validation = field.validation.copy() if field.validation else {}

        # Field validation conversions
        v1_to_v2_mappings = {
            # String validations
            "regex": "pattern",
            "min_items": "min_length",
            "max_items": "max_length",
            "anystr_strip_whitespace": "strip_whitespace",
            "anystr_lower": "to_lower",
            "anystr_upper": "to_upper",
            # Numeric validations
            "gt": "gt",  # Same in v2, but included for completeness
            "ge": "ge",  # Same in v2, but included for completeness
            "lt": "lt",  # Same in v2, but included for completeness
            "le": "le",  # Same in v2, but included for completeness
            "multiple_of": "multiple_of",  # Same in v2, but included for completeness
            # Collection validations
            "min_items": "min_length",
            "max_items": "max_length",
            "unique_items": "unique_items",  # Same in v2, but included for completeness
            # Other validations
            "const": "frozen",
            "allow_mutation": "frozen",  # Inverse logic: !allow_mutation = frozen
        }

        # Apply mappings
        for v1_key, v2_key in v1_to_v2_mappings.items():
            if v1_key in validation:
                # Special case for allow_mutation which has inverse logic
                if v1_key == "allow_mutation":
                    validation[v2_key] = not validation.pop(v1_key)
                else:
                    validation[v2_key] = validation.pop(v1_key)

        # Handle special cases and complex conversions

        # Convert type strings from v1 to v2 format
        field_type = field.type

        # Handle EmailStr which moved from pydantic.EmailStr to pydantic.EmailStr
        if field_type == "EmailStr" or field_type == "pydantic.EmailStr":
            field_type = "EmailStr"
            # Add import hint in validation for model generator
            validation["_import_"] = "from pydantic import EmailStr"

        # Handle PositiveInt, NegativeInt, etc. which were removed in v2
        type_conversions = {
            "PositiveInt": "int",
            "NegativeInt": "int",
            "PositiveFloat": "float",
            "NegativeFloat": "float",
            "conint": "int",
            "confloat": "float",
            "constr": "str",
            "conlist": "List",
            "conset": "Set",
            "confrozenset": "FrozenSet",
        }

        for old_type, new_type in type_conversions.items():
            if old_type in field_type:
                field_type = new_type
                # Add appropriate constraints based on the original type
                if old_type == "PositiveInt":
                    validation["gt"] = 0
                elif old_type == "NegativeInt":
                    validation["lt"] = 0
                elif old_type == "PositiveFloat":
                    validation["gt"] = 0.0
                elif old_type == "NegativeFloat":
                    validation["lt"] = 0.0

        # Process nested fields if present
        nested_fields = None
        if hasattr(field, "nested_fields") and field.nested_fields:
            nested_fields = [
                convert_field(nested_field) for nested_field in field.nested_fields
            ]

        # Create updated field with converted validation
        return ModelField(
            name=field.name,
            type=field_type,
            description=field.description,
            validation=validation,
            nested_fields=nested_fields,
        )

    # Convert all fields
    updated_fields = [convert_field(field) for field in request.fields]

    # Create updated request
    return ExtractionRequest(
        model_name=request.model_name,
        model_description=request.model_description,
        fields=updated_fields,
    )


def sanitize_regex_patterns(
    extraction_request: "ExtractionRequest",
) -> "ExtractionRequest":
    """
    Sanitize regex patterns in field validations to make them compatible with Pydantic V2

    Args:
        extraction_request: The extraction request to sanitize

    Returns:
        Sanitized extraction request
    """

    def fix_field_validation(field):
        # Fix regex patterns in validation dict
        if field.validation:
            # For pattern/regex fields, sanitize the pattern
            for pattern_key in ["pattern", "regex"]:
                if pattern_key in field.validation:
                    try:
                        # Just test if the pattern compiles - if it does, leave it alone
                        import re

                        re.compile(field.validation[pattern_key])
                    except re.error:
                        # If pattern doesn't compile, we'll use a simpler approach:
                        # Remove the pattern validation entirely rather than trying to fix it
                        logger.warning(
                            f"Removing invalid regex pattern: {field.validation[pattern_key]}"
                        )
                        del field.validation[pattern_key]

        # Process nested fields recursively
        if field.nested_fields:
            for nested_field in field.nested_fields:
                fix_field_validation(nested_field)

    # Process all fields
    for field in extraction_request.fields:
        fix_field_validation(field)

    return extraction_request
