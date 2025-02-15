import json
from functools import wraps
from typing import Any, Callable, Dict, Type

from loguru import logger
from pydantic import BaseModel

from structx.core.exceptions import ExtractionError


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
        log_args: Whether to log function arguments
        log_result: Whether to log function result
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


def log_model_schema(model: BaseModel) -> None:
    """
    Log Pydantic model schema

    Args:
        model: Pydantic model
    """
    try:

        schema = model.model_json_schema()
        model_name = model.__class__.__name__
        logger.debug(f"{model_name} schema: {json.dumps(schema, indent=2)}")
    except Exception as e:
        model_name = model.__class__.__name__
        logger.warning(f"Error logging {model_name} schema: {e}")


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
