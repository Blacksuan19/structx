# Models

These are the core models used in `structx` for data extraction and results.

## RowResult

::: structx.core.models.RowResult
    options:
      show_bases: false
      heading_level: 3

## ExtractionResult

::: structx.core.models.ExtractionResult
    options:
      show_bases: false
      heading_level: 3

The distinction between flattened output and row provenance is covered in
[Working with Results](../guides/working-with-results.md).

## ModelField

::: structx.core.models.ModelField
    options:
      show_bases: false
      heading_level: 3

## Generated Field Types

`ModelField` normalizes model-generated type expressions before dynamic model
creation. Canonical expressions include:

- Scalars: `str`, `int`, `float`, `bool`, `date`, `datetime`, `time`,
  `Decimal`, `UUID`, and `Any`
- Collections: `List[T]`, `Dict[str, T]`, `Set[T]`, `FrozenSet[T]`, and
  `Tuple[...]`
- Nullable values: `Optional[T]`

Common JSON, TypeScript, and legacy Pydantic forms such as `string`,
`array<number>`, `string[]`, `T | null`, `PositiveInt`, and `conlist(...)` are
converted to canonical Python forms. Ambiguous unions and unknown types are
rejected instead of silently becoming strings.

Legacy validation names such as `regex`, `min_items`, and `max_items` are
normalized to their Pydantic v2 equivalents. Unsupported constraints and
invalid regular expressions are discarded before model creation.

## ExtractionRequest

::: structx.core.models.ExtractionRequest
    options:
      show_bases: false
      heading_level: 3

`ExtractionRequest` is the portable representation of a StructX model. It can
be serialized as JSON, stored outside the Python process, and converted back to
a runtime Pydantic model:

```python
from structx import (
    ExtractionRequest,
    model_from_extraction_request,
    model_to_extraction_request,
)

definition = model_to_extraction_request(Invoice)
stored = definition.model_dump(mode="json")

restored_definition = ExtractionRequest.model_validate(stored)
RestoredInvoice = model_from_extraction_request(restored_definition)
```

StructX-generated and refined models retain their original definition, so
`model_to_extraction_request()` returns that definition without reverse
engineering it. Custom Pydantic models are converted from their declarative
fields, nested models, supported constraints, required state, nullability, and
serializable defaults.

Custom validators, serializers, computed fields, recursive models, and default
factories cannot be represented as portable data and are rejected rather than
silently discarded.

## Type Capabilities

Use `get_type_capabilities()` to build schema editors without copying StructX's
private aliases or type parser:

```python
from structx import get_type_capabilities

capabilities = get_type_capabilities()
payload = capabilities.model_dump(mode="json")
```

The catalog contains canonical scalar and container identifiers, user-facing
labels, supported constraints, valid item kinds, and presence modifiers.
Aliases such as `string`, `integer`, and `array` remain accepted as input but
are never returned by the catalog or persisted by `ExtractionRequest`.

::: structx.schema.TypeCapabilities
    options:
      show_bases: false
      heading_level: 3

## Schema Conversion Functions

::: structx.schema.model_to_extraction_request
    options:
      show_bases: false
      heading_level: 3

::: structx.schema.model_from_extraction_request
    options:
      show_bases: false
      heading_level: 3

::: structx.schema.get_type_capabilities
    options:
      show_bases: false
      heading_level: 3

## ExtractionPlan

::: structx.core.models.ExtractionPlan
    options:
      show_bases: false
      heading_level: 3

`ExtractionPlan` is the validated result of dynamic planning. It combines the
instructions used for row extraction, selected input columns, and the generated
schema. Supplying a custom Pydantic model skips this planning request.

## ModelGenerator

::: structx.extraction.generator.ModelGenerator
    options:
      show_bases: false
      heading_level: 3

`ModelGenerator.from_extraction_request()` is the low-level path for turning an
`ExtractionRequest` into a runtime Pydantic model. Normal extraction performs
this step automatically.
