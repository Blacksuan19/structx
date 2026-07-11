import json
from functools import wraps
from typing import Any, Dict, Type

from loguru import logger

from structx.core.exceptions import ExtractionError
from structx.utils.types import P, R


def handle_errors(
    error_message: str,
    error_type: Type[Exception] = ExtractionError,
    default_return: Any = None,
):
    """Wrap errors with a consistent Structx exception and log message."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as error:
                logger.error(
                    f"{error_message}: {str(error)}\nFunction: {func.__name__}"
                )
                if default_return is not None:
                    return default_return
                raise error_type(f"{error_message}: {str(error)}") from error

        return wrapper

    return decorator


def flatten_extracted_data(data: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    """Flatten nested extracted data for DataFrame storage."""
    flattened = {}

    for key, value in data.items():
        new_key = f"{prefix}_{key}" if prefix else key

        if isinstance(value, dict):
            flattened.update(flatten_extracted_data(value, new_key))
        elif isinstance(value, list):
            if value and isinstance(value[0], dict):
                for index, item in enumerate(value):
                    flattened.update(flatten_extracted_data(item, f"{new_key}_{index}"))
            else:
                flattened[new_key] = json.dumps(value)
        else:
            flattened[new_key] = value

    return flattened
