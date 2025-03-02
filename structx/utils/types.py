from typing import Any, Dict, ParamSpec, TypeVar

from pydantic import BaseModel

ResponseType = TypeVar("ResponseType")

DictStrAny = Dict[str, Any]

# Type variables for parameters and return type
T = TypeVar("T", bound=BaseModel)
R = TypeVar("R")
P = ParamSpec("P")
