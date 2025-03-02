# Supported Formats

`structx` supports a variety of file formats for data extraction.

## Built-in Support

These formats are supported without additional dependencies:

| Format  | Extension             | Description                         |
| ------- | --------------------- | ----------------------------------- |
| CSV     | .csv                  | Comma-separated values              |
| Excel   | .xlsx, .xls           | Microsoft Excel spreadsheets        |
| JSON    | .json                 | JavaScript Object Notation          |
| Parquet | .parquet              | Columnar storage format             |
| Feather | .feather              | Fast on-disk format for data frames |
| Text    | .txt, .md, .log, etc. | Plain text files                    |

## Optional Dependencies

These formats require additional dependencies:

| Format | Extension   | Dependencies                |
| ------ | ----------- | --------------------------- |
| PDF    | .pdf        | `pip install structx[pdf]`  |
| Word   | .docx, .doc | `pip install structx[docx]` |

## Input Types

`structx` can extract data from:

1. **File Paths**:

   ```python
   result = extractor.extract(
       data="path/to/file.csv",
       query="extract key information"
   )
   ```

2. **DataFrames**:

   ```python
   import pandas as pd

   df = pd.DataFrame({"text": ["Sample text 1", "Sample text 2"]})

   result = extractor.extract(
       data=df,
       query="extract key information"
   )
   ```

3. **Lists of Dictionaries**:

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

4. **Raw Text**:

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

When reading files, you can provide additional options:

```python
result = extractor.extract(
    data="document.pdf",
    query="extract key information",
    chunk_size=2000,  # Size of text chunks
    overlap=200,      # Overlap between chunks
    encoding="utf-8"  # Text encoding
)
```

### CSV Options

```python
result = extractor.extract(
    data="data.csv",
    query="extract key information",
    delimiter=";",    # Custom delimiter
    encoding="latin1", # Custom encoding
    skiprows=1        # Skip header row
)
```

### Excel Options

```python
result = extractor.extract(
    data="data.xlsx",
    query="extract key information",
    sheet_name="Sheet2",  # Specific sheet
    skiprows=3            # Skip header rows
)
```

### PDF Options

```python
result = extractor.extract(
    data="document.pdf",
    query="extract key information",
    chunk_size=2000,  # Size of text chunks
    overlap=200       # Overlap between chunks
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
