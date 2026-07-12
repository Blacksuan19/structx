# Input Contracts

Most users should pass supported data directly to `Extractor`. Integrations can
prepare input explicitly when they need to inspect normalized data or reuse one
document conversion across schema and extraction operations.

## PreparedInput

::: structx.core.input.PreparedInput
    options:
      show_bases: false
      heading_level: 3

## PdfRow

::: structx.core.input.PdfRow
    options:
      show_bases: false
      heading_level: 3

## Resource Ownership

`FileReader.read_file()` returns a `PreparedInput`. Existing PDFs are borrowed
and never deleted. Converted documents place generated PDFs in `owned_paths`.

One-shot `Extractor` methods clean those paths automatically. The public
preparation context managers keep prepared input open across schema and
extraction methods, then guarantee cleanup when the context exits:

```python
from structx import Extractor

with extractor.prepare_input(data="agreement.docx") as prepared:
    print(prepared.dataframe)
    print(prepared.pdf_rows[0].pdf_path)
    schema = extractor.get_schema(
        data=prepared,
        query="extract agreement terms",
    )
    result = extractor.extract(
        data=prepared,
        query="extract agreement terms",
        model=schema,
    )
```

Use `async with extractor.prepare_input_async(...)` when preparation may perform
blocking file parsing or document conversion. The prepared object can be
inspected for metering or status updates before any model-backed operation.
Lower-level callers can still use the idempotent `PreparedInput.close()` method
directly when a context manager is not suitable.

See [Supported Formats](../reference/supported-formats.md) for accepted public
input types and document conversion behavior.
