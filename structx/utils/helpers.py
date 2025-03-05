import functools
import json
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, ParamSpec, Type, TypeVar

from loguru import logger
from pydantic import BaseModel

from structx.core.exceptions import ExtractionError
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
