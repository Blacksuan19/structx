# Supported Formats

`structx` supports a comprehensive variety of file formats for data extraction,
with advanced unstructured document processing capabilities.

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

These formats use the advanced multimodal PDF processing pipeline:

| Format | Extension                               | Processing Method                     | Dependencies          |
| ------ | --------------------------------------- | ------------------------------------- | --------------------- |
| PDF    | .pdf                                    | Direct multimodal processing          | Built-in (instructor) |
| Word   | .docx, .doc                             | Docling → Markdown → PDF → Multimodal | `structx-llm[docs]`   |
| Text   | .txt, .md, .py, .html, .xml, .log, .rst | Markdown → PDF → Multimodal           | `structx-llm[docs]`   |

### Advanced Processing Features

- **Multimodal PDF Processing**: Native instructor vision support for PDFs
- **Intelligent Conversion**: Automatic document-to-PDF conversion with styling
- **Structure Preservation**: Maintains tables, formatting, and layout
- **Context Awareness**: Full document context without chunking limitations
- **Fallback Support**: Automatic fallback to text processing if needed

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
# PDF documents - direct multimodal processing
result = extractor.extract(
    data="contract.pdf",
    query="extract parties, dates, and payment terms"
)

# DOCX documents - converted via docling pipeline
result = extractor.extract(
    data="project_proposal.docx",
    query="extract deliverables, timeline, and budget"
)

# Text files - converted to styled PDF
result = extractor.extract(
    data="meeting_notes.txt",
    query="extract action items and responsible parties"
)

# Markdown files - enhanced PDF conversion
result = extractor.extract(
    data="README.md",
    query="extract installation steps and requirements"
)

# Code files - syntax highlighted PDF
result = extractor.extract(
    data="main.py",
    query="extract function definitions and their purposes"
)
```

### Processing Mode Options

```python
# Default: multimodal PDF processing (recommended)
result = extractor.extract(
    data="document.docx",
    query="extract information"
    # mode="multimodal_pdf" is default
)

# Alternative: simple text processing
result = extractor.extract(
    data="document.txt",
    query="extract information",
    mode="simple_text",
    chunk_size=1500,
    chunk_overlap=200
)

# Alternative: simple PDF processing
result = extractor.extract(
    data="document.pdf",
    query="extract information",
    mode="simple_pdf"
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

### Document Processing Options

```python
result = extractor.extract(
    data="document.pdf",
    query="extract key information",
    mode="multimodal_pdf",    # Default mode (recommended)
    chunk_size=2000,          # Only used in fallback simple modes
    chunk_overlap=200         # Only used in fallback simple modes
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
