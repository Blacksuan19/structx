"""Canonical type handling for dynamically generated extraction models."""

import ast
import re
from datetime import date, datetime, time
from decimal import Decimal
from typing import (
    Any,
    Dict,
    FrozenSet,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    Type,
    get_origin,
)
from uuid import UUID


class TypeExpressionError(ValueError):
    """Raised when a model field contains an unsupported type expression."""


_ALIASES = {
    "any": "Any",
    "array": "List",
    "bool": "bool",
    "boolean": "bool",
    "booleans": "bool",
    "date": "date",
    "date-time": "datetime",
    "datetime": "datetime",
    "decimal": "Decimal",
    "dict": "Dict",
    "dictionary": "Dict",
    "float": "float",
    "frozen_set": "FrozenSet",
    "frozenset": "FrozenSet",
    "int": "int",
    "integer": "int",
    "integers": "int",
    "list": "List",
    "map": "Dict",
    "none": "None",
    "nonetype": "None",
    "null": "None",
    "number": "float",
    "numbers": "float",
    "numeric": "float",
    "object": "Dict",
    "optional": "Optional",
    "set": "Set",
    "str": "str",
    "string": "str",
    "strings": "str",
    "time": "time",
    "tuple": "Tuple",
    "uuid": "UUID",
}

CANONICAL_SCALAR_TYPES = (
    "Any",
    "bool",
    "date",
    "datetime",
    "Decimal",
    "float",
    "int",
    "str",
    "time",
    "UUID",
)

CANONICAL_CONTAINER_TYPES = ("List", "Set", "Dict", "FrozenSet", "Tuple")

SUPPORTED_FIELD_CONSTRAINTS = frozenset(
    {
        "alias",
        "deprecated",
        "examples",
        "exclude",
        "frozen",
        "ge",
        "gt",
        "json_schema_extra",
        "le",
        "lt",
        "max_length",
        "min_length",
        "multiple_of",
        "pattern",
        "repr",
        "strict",
        "title",
    }
)

_PRIMITIVES = set(CANONICAL_SCALAR_TYPES)

_RUNTIME_TYPES: Dict[str, Type[Any]] = {
    "Any": Any,
    "bool": bool,
    "date": date,
    "datetime": datetime,
    "Decimal": Decimal,
    "float": float,
    "int": int,
    "str": str,
    "time": time,
    "UUID": UUID,
}

_RUNTIME_TYPE_NAMES = {
    runtime_type: name for name, runtime_type in _RUNTIME_TYPES.items()
}

_CONTAINER_ORIGIN_NAMES = {
    list: "List",
    set: "Set",
    dict: "Dict",
    frozenset: "FrozenSet",
    tuple: "Tuple",
}

_LEGACY_TYPES = {
    "EmailStr": ("str", {}),
    "pydantic.EmailStr": ("str", {}),
    "PositiveInt": ("int", {"gt": 0}),
    "NegativeInt": ("int", {"lt": 0}),
    "PositiveFloat": ("float", {"gt": 0.0}),
    "NegativeFloat": ("float", {"lt": 0.0}),
    "conint": ("int", {}),
    "confloat": ("float", {}),
    "constr": ("str", {}),
    "conlist": ("List[Any]", {}),
    "conset": ("Set[Any]", {}),
    "confrozenset": ("FrozenSet[Any]", {}),
}

_VALIDATION_ALIASES = {
    "regex": "pattern",
    "min_items": "min_length",
    "max_items": "max_length",
}


def _split_top_level(value: str, delimiter: str) -> List[str]:
    parts: List[str] = []
    start = 0
    depth = 0
    for index, character in enumerate(value):
        if character in "[<(":
            depth += 1
        elif character in "]>)":
            depth -= 1
            if depth < 0:
                raise TypeExpressionError(f"Unbalanced type expression: {value!r}")
        elif character == delimiter and depth == 0:
            parts.append(value[start:index].strip())
            start = index + 1
    if depth != 0:
        raise TypeExpressionError(f"Unbalanced type expression: {value!r}")
    parts.append(value[start:].strip())
    return [part for part in parts if part]


def _generic_parts(value: str) -> Optional[tuple[str, List[str]]]:
    positions = [
        position for position in (value.find("["), value.find("<")) if position >= 0
    ]
    if not positions:
        return None

    opening_index = min(positions)
    opening = value[opening_index]
    closing = "]" if opening == "[" else ">"
    if not value.endswith(closing):
        raise TypeExpressionError(f"Malformed generic type: {value!r}")

    base = value[:opening_index].strip()
    parameters = _split_top_level(value[opening_index + 1 : -1], ",")
    return base, parameters


def _canonical_name(value: str) -> str:
    name = value.strip()
    canonical = _ALIASES.get(name.lower(), name)
    if canonical in _PRIMITIVES or canonical in {
        "Dict",
        "FrozenSet",
        "List",
        "None",
        "Optional",
        "Set",
        "Tuple",
    }:
        return canonical
    raise TypeExpressionError(f"Unsupported model field type: {value!r}")


def _legacy_type_definition(value: str) -> tuple[str, Dict[str, Any]]:
    """Convert supported Pydantic v1 type names without evaluating code."""
    expression = value.strip()
    if expression in _LEGACY_TYPES:
        canonical, constraints = _LEGACY_TYPES[expression]
        return canonical, constraints.copy()

    try:
        parsed = ast.parse(expression, mode="eval").body
    except SyntaxError:
        return expression, {}

    if not isinstance(parsed, ast.Call) or not isinstance(parsed.func, ast.Name):
        return expression, {}
    if parsed.func.id not in _LEGACY_TYPES:
        return expression, {}

    canonical, constraints = _LEGACY_TYPES[parsed.func.id]
    constraints = constraints.copy()

    if parsed.func.id in {"conlist", "conset", "confrozenset"} and parsed.args:
        item_expression = ast.unparse(parsed.args[0])
        collection = {
            "conlist": "List",
            "conset": "Set",
            "confrozenset": "FrozenSet",
        }[parsed.func.id]
        canonical = f"{collection}[{normalize_type_expression(item_expression)}]"

    for keyword in parsed.keywords:
        if keyword.arg is None:
            continue
        try:
            constraints[keyword.arg] = ast.literal_eval(keyword.value)
        except (ValueError, TypeError):
            continue

    return canonical, constraints


def _normalize_validation(
    validation: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    raw_validation = dict(validation or {})
    normalized: Dict[str, Any] = {}

    for key, value in raw_validation.items():
        if key in SUPPORTED_FIELD_CONSTRAINTS:
            normalized[key] = value

    for source_key, target_key in _VALIDATION_ALIASES.items():
        if source_key in raw_validation and target_key not in normalized:
            normalized[target_key] = raw_validation[source_key]

    if "allow_mutation" in raw_validation and "frozen" not in normalized:
        normalized["frozen"] = not bool(raw_validation["allow_mutation"])

    pattern = normalized.get("pattern")
    if pattern is not None:
        try:
            re.compile(pattern)
        except (re.error, TypeError):
            normalized.pop("pattern", None)

    return normalized


def normalize_field_definition(
    type_expression: str,
    validation: Optional[Mapping[str, Any]] = None,
) -> tuple[str, Dict[str, Any]]:
    """Canonicalize one model field's type and Pydantic constraints."""
    legacy_type, implied_constraints = _legacy_type_definition(type_expression)
    normalized_validation = _normalize_validation(
        {**implied_constraints, **dict(validation or {})}
    )
    return normalize_type_expression(legacy_type), normalized_validation


def canonical_scalar_name(annotation: Any) -> Optional[str]:
    """Return the canonical name for a supported runtime scalar type."""
    return _RUNTIME_TYPE_NAMES.get(annotation)


def canonical_container_name(annotation: Any) -> Optional[str]:
    """Return the canonical name for a supported container annotation."""
    return _CONTAINER_ORIGIN_NAMES.get(get_origin(annotation) or annotation)


def normalize_type_expression(value: str) -> str:
    """Normalize common JSON, TypeScript, and Python type syntax."""
    if not isinstance(value, str) or not value.strip():
        raise TypeExpressionError("Model field type must be a non-empty string")

    expression = value.strip().strip("`").replace("typing.", "")

    lowered_expression = expression.lower()
    if lowered_expression.startswith(("array of ", "list of ")):
        prefix = (
            "array of " if lowered_expression.startswith("array of ") else "list of "
        )
        expression = f"List[{expression[len(prefix):].strip()}]"
    elif expression.endswith("[]"):
        expression = f"List[{expression[:-2]}]"

    union_parts = _split_top_level(expression, "|")
    if len(union_parts) > 1:
        null_names = {"none", "nonetype", "null"}
        nullable = any(part.lower() in null_names for part in union_parts)
        non_null = [
            normalize_type_expression(part)
            for part in union_parts
            if part.lower() not in null_names
        ]
        if len(non_null) != 1 or not nullable:
            raise TypeExpressionError(
                f"Only nullable unions are supported, received {value!r}"
            )
        inner = non_null[0]
        return inner if inner.startswith("Optional[") else f"Optional[{inner}]"

    generic = _generic_parts(expression)
    if generic:
        raw_base, raw_parameters = generic
        if raw_base.lower() == "union":
            null_names = {"none", "nonetype", "null"}
            non_null = [
                parameter
                for parameter in raw_parameters
                if parameter.lower() not in null_names
            ]
            if len(non_null) != 1 or len(non_null) == len(raw_parameters):
                raise TypeExpressionError(
                    f"Only nullable unions are supported, received {value!r}"
                )
            return f"Optional[{normalize_type_expression(non_null[0])}]"
        base = _canonical_name(raw_base)
        parameters = [normalize_type_expression(item) for item in raw_parameters]

        if base in {"List", "Set", "FrozenSet", "Optional"}:
            if len(parameters) != 1:
                raise TypeExpressionError(f"{base} requires one type parameter")
            return f"{base}[{parameters[0]}]"
        if base == "Dict":
            if len(parameters) == 1:
                parameters.insert(0, "str")
            if len(parameters) != 2:
                raise TypeExpressionError("Dict requires key and value types")
            return f"Dict[{parameters[0]}, {parameters[1]}]"
        if base == "Tuple":
            if not parameters:
                raise TypeExpressionError("Tuple requires at least one type parameter")
            return f"Tuple[{', '.join(parameters)}]"
        raise TypeExpressionError(f"{base} cannot be used as a generic type")

    canonical = _canonical_name(expression)
    if canonical == "List":
        return "List[Any]"
    if canonical == "Dict":
        return "Dict[str, Any]"
    if canonical in {"Set", "FrozenSet"}:
        return f"{canonical}[Any]"
    if canonical == "Tuple":
        return "Tuple[Any]"
    if canonical in {"Optional", "None"}:
        raise TypeExpressionError(f"Incomplete model field type: {value!r}")
    return canonical


def resolve_type_expression(value: str) -> Type[Any]:
    """Resolve a canonical type expression without eval or forward references."""
    expression = normalize_type_expression(value)
    if expression in _RUNTIME_TYPES:
        return _RUNTIME_TYPES[expression]

    generic = _generic_parts(expression)
    if not generic:
        raise TypeExpressionError(f"Unsupported canonical type: {expression!r}")

    base, parameters = generic
    resolved = [resolve_type_expression(parameter) for parameter in parameters]
    if base == "List":
        return List[resolved[0]]
    if base == "Set":
        return Set[resolved[0]]
    if base == "FrozenSet":
        return FrozenSet[resolved[0]]
    if base == "Optional":
        return Optional[resolved[0]]
    if base == "Dict":
        return Dict[resolved[0], resolved[1]]
    if base == "Tuple":
        return Tuple[tuple(resolved)]
    raise TypeExpressionError(f"Unsupported generic type: {expression!r}")


def is_collection_type(value: str) -> bool:
    """Return whether the outer non-optional type is a collection."""
    expression = normalize_type_expression(value)
    if expression.startswith("Optional["):
        generic = _generic_parts(expression)
        if generic:
            expression = generic[1][0]
    return expression.startswith(("List[", "Set[", "FrozenSet[", "Tuple["))
