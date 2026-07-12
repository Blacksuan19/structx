"""Portable schema definitions and UI-facing type capabilities."""

from __future__ import annotations

from types import UnionType
from typing import (
    Annotated,
    Any,
    Dict,
    List,
    Mapping,
    Optional,
    Type,
    Union,
    get_args,
    get_origin,
)

from pydantic import BaseModel, ConfigDict, Field
from pydantic_core import PydanticUndefined, to_jsonable_python

from structx.core.exceptions import ModelGenerationError
from structx.core.models import ExtractionRequest, ModelField
from structx.core.type_system import (
    CANONICAL_CONTAINER_TYPES,
    CANONICAL_SCALAR_TYPES,
    SUPPORTED_FIELD_CONSTRAINTS,
    canonical_container_name,
    canonical_scalar_name,
)
from structx.extraction.generator import ModelGenerator


class ScalarTypeCapability(BaseModel):
    """One canonical scalar type available to schema builders."""

    model_config = ConfigDict(frozen=True)

    id: str
    label: str
    constraints: List[str] = Field(default_factory=list)
    advanced: bool = False


class ContainerTypeCapability(BaseModel):
    """One canonical container and the item shapes supported by StructX."""

    model_config = ConfigDict(frozen=True)

    id: str
    label: str
    description: str
    allowed_item_kinds: List[str]
    ordered: bool
    unique: bool
    advanced: bool = False


class TypeModifierCapabilities(BaseModel):
    """Presence and nullability controls kept separate from value types."""

    model_config = ConfigDict(frozen=True)

    required: bool = True
    nullable: bool = True
    default: bool = True


class TypeCapabilities(BaseModel):
    """Versioned canonical type catalog for external schema builders."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1"
    scalars: List[ScalarTypeCapability]
    containers: List[ContainerTypeCapability]
    modifiers: TypeModifierCapabilities = Field(
        default_factory=TypeModifierCapabilities
    )


_STRING_CONSTRAINTS = ["min_length", "max_length", "pattern", "strict"]
_NUMBER_CONSTRAINTS = ["gt", "ge", "lt", "le", "multiple_of", "strict"]
_SCALAR_METADATA = {
    "str": ("Text", _STRING_CONSTRAINTS, False),
    "int": ("Integer", _NUMBER_CONSTRAINTS, False),
    "float": ("Number", _NUMBER_CONSTRAINTS, False),
    "Decimal": ("Decimal", _NUMBER_CONSTRAINTS, False),
    "bool": ("Boolean", ["strict"], False),
    "date": ("Date", ["strict"], False),
    "datetime": ("Date and time", ["strict"], False),
    "time": ("Time", ["strict"], False),
    "UUID": ("UUID", ["strict"], False),
    "Any": ("Any value", [], True),
}

_CONTAINER_METADATA = {
    "List": {
        "label": "List",
        "description": "Ordered values that may contain duplicates",
        "allowed_item_kinds": ["scalar", "object", "container"],
        "ordered": True,
        "unique": False,
    },
    "Set": {
        "label": "Set",
        "description": "Unique values without a stable order",
        "allowed_item_kinds": ["hashable_scalar", "object"],
        "ordered": False,
        "unique": True,
    },
    "Dict": {
        "label": "Map",
        "description": "Text keys mapped to values",
        "allowed_item_kinds": ["scalar", "container"],
        "ordered": False,
        "unique": True,
        "advanced": True,
    },
    "FrozenSet": {
        "label": "Frozen set",
        "description": "Immutable unique values without a stable order",
        "allowed_item_kinds": ["hashable_scalar", "object"],
        "ordered": False,
        "unique": True,
        "advanced": True,
    },
    "Tuple": {
        "label": "Tuple",
        "description": "Fixed-position values",
        "allowed_item_kinds": ["scalar", "object"],
        "ordered": True,
        "unique": False,
        "advanced": True,
    },
}

_TYPE_CAPABILITIES = TypeCapabilities(
    scalars=[
        ScalarTypeCapability(
            id=type_id,
            label=_SCALAR_METADATA[type_id][0],
            constraints=_SCALAR_METADATA[type_id][1],
            advanced=_SCALAR_METADATA[type_id][2],
        )
        for type_id in CANONICAL_SCALAR_TYPES
    ],
    containers=[
        ContainerTypeCapability(id=type_id, **_CONTAINER_METADATA[type_id])
        for type_id in CANONICAL_CONTAINER_TYPES
    ],
)


def get_type_capabilities() -> TypeCapabilities:
    """Return the canonical, alias-free type catalog for schema-builder UIs."""
    return _TYPE_CAPABILITIES.model_copy(deep=True)


def _unsupported(message: str) -> ModelGenerationError:
    return ModelGenerationError(message)


def _model_has_custom_behavior(model: Type[BaseModel]) -> bool:
    decorators = getattr(model, "__pydantic_decorators__", None)
    if decorators is not None:
        collections = (
            "validators",
            "field_validators",
            "root_validators",
            "field_serializers",
            "model_serializers",
            "model_validators",
            "computed_fields",
        )
        if any(getattr(decorators, name, {}) for name in collections):
            return True
    return bool(getattr(model, "model_computed_fields", {}))


def _unwrap_annotated(annotation: Any) -> Any:
    if get_origin(annotation) is Annotated:
        return get_args(annotation)[0]
    return annotation


def _unwrap_nullable(annotation: Any) -> tuple[Any, bool]:
    annotation = _unwrap_annotated(annotation)
    origin = get_origin(annotation)
    if origin not in {Union, UnionType}:
        return annotation, False

    arguments = get_args(annotation)
    non_null = [argument for argument in arguments if argument is not type(None)]
    if len(non_null) != len(arguments) - 1 or len(non_null) != 1:
        raise _unsupported(
            f"Only a single type combined with None is supported, received {annotation!r}"
        )
    return _unwrap_annotated(non_null[0]), True


def _model_fields(
    model: Type[BaseModel], seen: set[Type[BaseModel]]
) -> List[ModelField]:
    if model in seen:
        raise _unsupported(
            f"Recursive model definitions are not supported: {model.__name__}"
        )
    if _model_has_custom_behavior(model):
        raise _unsupported(
            f"Custom validators, serializers, and computed fields cannot be serialized: {model.__name__}"
        )

    seen.add(model)
    try:
        return [
            _field_from_pydantic(name, field, seen)
            for name, field in model.model_fields.items()
        ]
    finally:
        seen.remove(model)


def _annotation_definition(
    annotation: Any, seen: set[Type[BaseModel]]
) -> tuple[str, Optional[List[ModelField]], bool]:
    annotation, nullable = _unwrap_nullable(annotation)
    scalar = canonical_scalar_name(annotation)
    if scalar is not None:
        return scalar, None, nullable

    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return "Dict[str, Any]", _model_fields(annotation, seen), nullable

    container = canonical_container_name(annotation)
    if container is None:
        raise _unsupported(f"Unsupported Pydantic field type: {annotation!r}")

    arguments = get_args(annotation)
    if container in {"List", "Set", "FrozenSet"}:
        if len(arguments) != 1:
            raise _unsupported(f"{container} requires one item type")
        item_type, nested_fields, item_nullable = _annotation_definition(
            arguments[0], seen
        )
        if item_nullable:
            item_type = f"Optional[{item_type}]"
        expression = f"{container}[{item_type}]"
    elif container == "Dict":
        if len(arguments) != 2:
            raise _unsupported("Dict requires key and value types")
        key_type, key_nested, key_nullable = _annotation_definition(arguments[0], seen)
        value_type, value_nested, value_nullable = _annotation_definition(
            arguments[1], seen
        )
        if key_nested or value_nested or key_nullable:
            raise _unsupported(
                "Nested models and nullable keys inside Dict are not supported"
            )
        if value_nullable:
            value_type = f"Optional[{value_type}]"
        expression = f"Dict[{key_type}, {value_type}]"
        nested_fields = None
    else:
        if not arguments or Ellipsis in arguments:
            raise _unsupported("Tuple requires explicit fixed-position item types")
        item_definitions = [
            _annotation_definition(argument, seen) for argument in arguments
        ]
        nested = [definition for definition in item_definitions if definition[1]]
        if len(nested) > 1 or (nested and len(arguments) > 1):
            raise _unsupported(
                "Tuple cannot contain a nested model alongside other item types"
            )
        item_types = [
            f"Optional[{item_type}]" if item_nullable else item_type
            for item_type, _, item_nullable in item_definitions
        ]
        expression = f"Tuple[{', '.join(item_types)}]"
        nested_fields = nested[0][1] if nested else None

    if nullable:
        expression = f"Optional[{expression}]"
    return expression, nested_fields, nullable


def _field_validation(field: Any) -> Dict[str, Any]:
    validation: Dict[str, Any] = {}
    for key in SUPPORTED_FIELD_CONSTRAINTS:
        value = getattr(field, key, None)
        if key == "repr" and value is True:
            continue
        if value is not None and not callable(value):
            validation[key] = to_jsonable_python(value)

    for metadata in field.metadata:
        for key in SUPPORTED_FIELD_CONSTRAINTS:
            value = getattr(metadata, key, None)
            if value is not None and not callable(value):
                validation[key] = to_jsonable_python(value)
    return validation


def _field_from_pydantic(
    name: str, field: Any, seen: set[Type[BaseModel]]
) -> ModelField:
    if field.default_factory is not None:
        raise _unsupported(f"Default factories cannot be serialized for field {name!r}")

    field_type, nested_fields, nullable = _annotation_definition(field.annotation, seen)
    required = field.is_required()
    has_default = not required and field.default is not PydanticUndefined
    default = to_jsonable_python(field.default) if has_default else None
    if has_default and default is None:
        nullable = True

    return ModelField(
        name=name,
        type=field_type,
        description=field.description or "",
        validation=_field_validation(field),
        nested_fields=nested_fields,
        required=required,
        nullable=nullable,
        has_default=has_default,
        default=default,
    )


def model_to_extraction_request(
    model: Type[BaseModel],
    *,
    model_name: Optional[str] = None,
    model_description: Optional[str] = None,
) -> ExtractionRequest:
    """Convert a declarative Pydantic model into a portable definition."""
    if not isinstance(model, type) or not issubclass(model, BaseModel):
        raise TypeError("model must be a Pydantic BaseModel class")

    stored_definition = getattr(model, "__structx_definition__", None)
    if isinstance(stored_definition, ExtractionRequest):
        updates = {}
        if model_name is not None:
            updates["model_name"] = model_name
        if model_description is not None:
            updates["model_description"] = model_description
        return stored_definition.model_copy(deep=True, update=updates)

    description = model_description
    if description is None:
        description = (model.__dict__.get("__doc__") or "").strip()
    return ExtractionRequest(
        model_name=model_name or model.__name__,
        model_description=description,
        fields=_model_fields(model, set()),
    )


def model_from_extraction_request(
    request: ExtractionRequest | Mapping[str, Any],
) -> Type[BaseModel]:
    """Create a runtime Pydantic model from a portable definition or JSON data."""
    definition = (
        request
        if isinstance(request, ExtractionRequest)
        else ExtractionRequest.model_validate(request)
    )
    return ModelGenerator.from_extraction_request(definition)
