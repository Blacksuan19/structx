from datetime import date, datetime, time
from typing import Any, Dict, List, Optional

TYPE_ALIASES = {
    "string": "str",
    "integer": "int",
    "numeric": "float",
    "number": "float",
    "boolean": "bool",
    "array": "List",
    "object": "dict",
}

SAFE_TYPES = {
    # Python built-ins
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    # Common types
    "datetime": datetime,
    "date": date,
    "time": time,
    # Generic type constructors
    "List": List,
    "Dict": Dict,
    "Optional": Optional,
    "Any": Any,
}
