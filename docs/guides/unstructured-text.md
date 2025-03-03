# Unstructured Text

`structx` supports extracting structured data from various unstructured text
sources, including PDF documents, text files, and raw text.

## Supported File Formats

| Format  | Extension             | Requirements                    |
| ------- | --------------------- | ------------------------------- |
| CSV     | .csv                  | Built-in                        |
| Excel   | .xlsx, .xls           | Built-in                        |
| JSON    | .json                 | Built-in                        |
| Parquet | .parquet              | Built-in                        |
| Feather | .feather              | Built-in                        |
| Text    | .txt, .md, .log, etc. | Built-in                        |
| PDF     | .pdf                  | `pip install structx-llm[pdf]`  |
| Word    | .docx, .doc           | `pip install structx-llm[docx]` |

## Working with Text Files

```python
# Extract from a text file
result = extractor.extract(
    data="document.txt",
    query="extract key information"
)
```

## Working with PDF Documents

First, install the PDF dependencies:

```bash
pip install structx-llm[pdf]
```

Then extract data from PDF files:

```python
result = extractor.extract(
    data="document.pdf",
    query="extract key information"
)
```

## Working with Word Documents

First, install the DOCX dependencies:

```bash
pip install structx-llm[docx]
```

Then extract data from Word files:

```python
result = extractor.extract(
    data="document.docx",
    query="extract key information"
)
```

## Working with Raw Text

```python
text = """
System check on 2024-01-15 detected high CPU usage (92%) on server-01.
Database backup failure occurred on 2024-01-20 03:00.
"""

result = extractor.extract(
    data=text,
    query="extract incident dates and affected systems"
)
```

## Text Chunking

For large documents, `structx` automatically chunks the text to ensure effective
processing. You can control the chunking behavior with these parameters:

```python
result = extractor.extract(
    data="large_document.pdf",
    query="extract key information",
    chunk_size=2000,  # Size of text chunks
    overlap=200       # Overlap between chunks
)
```

### Chunking Parameters

| Parameter  | Type | Default | Description                    |
| ---------- | ---- | ------- | ------------------------------ |
| chunk_size | int  | 1000    | Size of text chunks            |
| overlap    | int  | 100     | Overlap between chunks         |
| encoding   | str  | 'utf-8' | Text encoding for file reading |

## Handling Multi-Page Documents

For PDF documents, `structx` processes each page and maintains page information:

```python
result = extractor.extract(
    data="multi_page.pdf",
    query="extract key information"
)

# Access page information (if return_df=True)
if 'page' in result.data.columns:
    page_counts = result.data['page'].value_counts()
    print("Extractions by page:", page_counts)
```

## Best Practices

1. **Be Specific in Queries**: For unstructured text, specific queries yield
   better results
2. **Adjust Chunk Size**: For very dense or sparse text, adjust the chunk size
   accordingly
3. **Use Appropriate Overlap**: Ensure context is maintained between chunks
4. **Check Failed Extractions**: Unstructured text may have more failures due to
   format variations

## Next Steps

- Learn about [Multiple Queries](multiple-queries.md) for extracting different
  types of information
- Explore [Async Operations](async-operations.md) for processing large documents
  efficiently
- See the [API Reference](../api/extractor.md) for all available options
