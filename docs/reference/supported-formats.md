# Supported Formats

`structx` supports structured file formats in the base install and optional
multimodal document processing through the `docs` extra.

## Structured Data Formats

These formats are processed directly as structured data without conversion:

| Format  | Extension   | Description                         | Processing Method        |
| ------- | ----------- | ----------------------------------- | ------------------------ |
| CSV     | .csv        | Comma-separated values              | Direct pandas processing |
| Excel   | .xlsx, .xls | Microsoft Excel spreadsheets        | Direct pandas processing |
| JSON    | .json       | JavaScript Object Notation          | Direct pandas processing |
| Parquet | .parquet    | Columnar storage format             | Direct pandas processing |
| Feather | .feather    | Fast on-disk format for data frames | Direct pandas processing |

## Unstructured Document Formats

Install `structx[docs]` to use the multimodal document pipeline:

| Format | Extension                               | Processing Method                  | Dependencies |
| ------ | --------------------------------------- | ---------------------------------- | ------------ |
| PDF    | .pdf                                    | PDF → Multimodal                   | `structx[docs]` |
| Word   | .docx, .doc                             | Docling → HTML → PDF → Multimodal  | `structx[docs]` |
| PowerPoint | .pptx, .ppt                         | Docling → HTML → PDF → Multimodal  | `structx[docs]` |
| Text   | .txt, .md, .py, .html, .xml, .log, .rst | Docling → HTML → PDF → Multimodal  | `structx[docs]` |

### Advanced Processing Features

- **Multimodal PDF Processing**: Native instructor vision support for PDFs
- **PDF Passthrough**: Existing PDFs are sent directly to multimodal extraction
- **Intelligent Conversion**: Automatic document-to-PDF conversion with styling for supported non-PDF formats
- **Structure Preservation**: Maintains tables, formatting, and layout
- **Context Awareness**: Full document context without chunking limitations

## Processing Examples

### Structured Data

```python
# CSV files - direct pandas processing
result = extractor.extract(
    data="sales_data.csv",
    query="extract top performing products and their revenue"
)

# Excel files with specific sheet
result = extractor.extract(
    data="financial_report.xlsx",
    query="extract quarterly revenue figures",
    file_options={"sheet_name": "Q4 Results"}
)

# JSON data
result = extractor.extract(
    data="api_logs.json",
    query="extract error events and response times"
)
```

### Unstructured Documents (Multimodal Processing)

```python
# PDF documents - passed directly to multimodal extraction
result = extractor.extract(
    data="contract.pdf",
    query="extract parties, dates, and payment terms"
)

# DOCX documents - converted via the Docling pipeline
result = extractor.extract(
    data="project_proposal.docx",
    query="extract deliverables, timeline, and budget"
)

# Text files - converted via the Docling pipeline
result = extractor.extract(
    data="meeting_notes.txt",
    query="extract action items and responsible parties"
)

# Markdown files - converted via the Docling pipeline
result = extractor.extract(
    data="README.md",
    query="extract installation steps and requirements"
)

# Code files - converted via the Docling pipeline
result = extractor.extract(
    data="main.py",
    query="extract function definitions and their purposes"
)
```

## Input Data Types

`structx` can extract data from various input formats:

### 1. File Paths

```python
result = extractor.extract(
    data="path/to/file.csv",
    query="extract key information"
)
```

### 2. DataFrames

```python
import pandas as pd

df = pd.DataFrame({"text": ["Sample text 1", "Sample text 2"]})

result = extractor.extract(
    data=df,
    query="extract key information"
)
```

### 3. Lists of Dictionaries

```python
data = [
    {"text": "Sample text 1"},
    {"text": "Sample text 2"}
]

result = extractor.extract(
    data=data,
    query="extract key information"
)
```

### 4. Raw Text

```python
text = """
Sample text with information to extract.
More text with additional information.
"""

result = extractor.extract(
    data=text,
    query="extract key information"
)
```

## File Reading Options

### CSV Options

```python
result = extractor.extract(
    data="data.csv",
    query="extract key information",
    file_options={
        "delimiter": ";",      # Custom delimiter
        "encoding": "latin1",  # Custom encoding
        "skiprows": 1          # Skip header row
    }
)
```

### Excel Options

```python
result = extractor.extract(
    data="data.xlsx",
    query="extract key information",
    file_options={
        "sheet_name": "Sheet2",  # Specific sheet
        "skiprows": 3            # Skip header rows
    }
)
```

## Output Types

`structx` can return data in different formats:

1. **Model Instances** (default):

   ```python
   result = extractor.extract(
       data=df,
       query="extract key information",
       return_df=False  # Default
   )

   # Access as list of model instances
   for item in result.data:
       print(item.field_name)
   ```

2. **DataFrame**:

   ```python
   result = extractor.extract(
       data=df,
       query="extract key information",
       return_df=True
   )

   # Access as DataFrame
   print(result.data.head())
   ```

## Nested Data Handling

For nested data structures, you can choose to flatten them:

```python
result = extractor.extract(
    data=df,
    query="extract key information",
    return_df=True,
    expand_nested=True  # Flatten nested structures
)
```
