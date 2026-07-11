# Supported Formats

Structx handles tabular inputs directly and routes document-like inputs through
its optional multimodal PDF pipeline.

## Structured Data

These extensions are dispatched to pandas readers:

| Format | Extensions | Reader |
| --- | --- | --- |
| CSV | `.csv` | `pandas.read_csv` |
| Excel | `.xlsx`, `.xls` | `pandas.read_excel` |
| JSON | `.json` | `pandas.read_json` |
| Parquet | `.parquet` | `pandas.read_parquet` |
| Feather | `.feather` | `pandas.read_feather` |

The base installation includes `openpyxl` for `.xlsx`. Legacy `.xls` files and
Parquet or Feather files may require an additional pandas-compatible engine,
such as `xlrd` or `pyarrow`.

Reader options can be passed through `file_options`:

```python
result = extractor.extract(
    data="financial_report.xlsx",
    query="extract quarterly revenue figures",
    file_options={"sheet_name": "Q4 Results", "skiprows": 2},
)
```

## Documents

Install the document extra before processing non-PDF document or image paths:

```bash
pip install "structx[docs]"
```

| Category | Extensions | Processing |
| --- | --- | --- |
| PDF | `.pdf` | Validated and passed directly to multimodal extraction |
| Word | `.doc`, `.docx` | Docling to HTML, then WeasyPrint to PDF |
| PowerPoint | `.ppt`, `.pptx` | Docling to HTML, then WeasyPrint to PDF |
| OpenDocument | `.odt`, `.ods`, `.odp` | Docling to HTML, then WeasyPrint to PDF |
| E-book | `.epub` | Docling to HTML, then WeasyPrint to PDF |
| Markup and text | `.md`, `.markdown`, `.adoc`, `.asciidoc`, `.tex`, `.html`, `.xhtml`, `.xml`, `.txt`, `.py`, `.log`, `.rst` | Docling to HTML, then WeasyPrint to PDF |
| Images | `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`, `.webp` | Docling image input to PDF |
| Captions | `.webvtt`, `.vtt` | Docling to HTML, then WeasyPrint to PDF |

Existing PDFs are not parsed by Docling. Non-PDF inputs are converted once;
the resulting text sample is reused for schema planning and the generated PDF
is sent to the extraction model. OCR and Docling table-structure analysis are
disabled, leaving visual interpretation to the multimodal model.

Existing PDFs and raw strings work with the base installation. PDF extraction
still requires the selected model and provider endpoint to accept multimodal
PDF input.

```python
# Existing PDF passthrough
pdf_result = extractor.extract(
    data="contract.pdf",
    query="extract parties, dates, and payment terms",
)

# Non-PDF document conversion
docx_result = extractor.extract(
    data="project_proposal.docx",
    query="extract deliverables, timeline, and budget",
)
```

## In-Memory Inputs

### DataFrames

```python
import pandas as pd

data = pd.DataFrame({"text": ["Incident at 09:30", "Resolved at 10:15"]})
result = extractor.extract(data=data, query="extract incident timestamps")
```

### Lists of Dictionaries

```python
data = [{"text": "Invoice A totals $100"}, {"text": "Invoice B totals $250"}]
result = extractor.extract(data=data, query="extract invoice name and total")
```

### Raw Strings

Non-empty strings that do not look like paths are processed directly in memory
and do not require `structx[docs]`:

```python
result = extractor.extract(
    data="Incident 42 occurred at 09:30 and affected the billing service.",
    query="extract incident number, time, and affected service",
)
```

## Input Validation

Structx rejects missing paths, directories, empty files, empty DataFrames or
lists, malformed PDFs, and unsupported extensions before model planning begins.
Strings with a supported extension, an absolute path, or a relative-path prefix
such as `./` or `../` are treated as paths rather than raw text.

Low-level `FileReader.read_file()` calls return a
[`PreparedInput`](../api/inputs.md#preparedinput). Converted documents include
temporary PDFs that direct callers must clean up; `Extractor` handles this
automatically.

## Output Types

By default, `result.data` is a list of Pydantic model instances. Set
`return_df=True` for a DataFrame, and combine it with `expand_nested=True` to
flatten nested extracted objects:

```python
result = extractor.extract(
    data=data,
    query="extract incident dates and affected systems",
    return_df=True,
    expand_nested=True,
)
```
