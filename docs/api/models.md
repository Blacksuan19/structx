# Models

These are the core models used in `structx` for data extraction and results.

## ExtractionResult

::: structx.core.models.ExtractionResult
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

## Other Models

::: structx.core.models
    options:
      show_bases: false
      heading_level: 3
