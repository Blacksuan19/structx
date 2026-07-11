# Exceptions

Public `Extractor` methods generally wrap operation-level failures in
`ExtractionError`. Lower-level APIs retain more specific exceptions. Pydantic
model validation continues to raise `pydantic.ValidationError`.

::: structx.core.exceptions.StructXError
    options:
      show_bases: true
      heading_level: 2

::: structx.core.exceptions.ConfigurationError
    options:
      show_bases: true
      heading_level: 2

::: structx.core.exceptions.ExtractionError
    options:
      show_bases: true
      heading_level: 2

::: structx.core.exceptions.ModelGenerationError
    options:
      show_bases: true
      heading_level: 2

::: structx.core.exceptions.FileError
    options:
      show_bases: true
      heading_level: 2

See [Error Handling](../reference/error-handling.md) for failure boundaries and
row-level error handling.
