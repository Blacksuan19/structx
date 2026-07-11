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
