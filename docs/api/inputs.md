# Input Contracts

Most users should pass supported data directly to `Extractor`. The contracts on
this page are useful for integrations that call the lower-level file and input
processors.

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

`Extractor` and the `InputProcessor.prepared()` context manager clean those
paths automatically. A direct `FileReader` caller must perform cleanup:

```python
from structx.extraction.processors.input_processor import InputProcessor
from structx.utils.file_reader import FileReader

prepared = FileReader.read_file("agreement.docx")
try:
    print(prepared.dataframe)
    print(prepared.pdf_rows[0].pdf_path)
finally:
    InputProcessor.cleanup(prepared)
```

See [Supported Formats](../reference/supported-formats.md) for accepted public
input types and document conversion behavior.
