# Error Handling

The public extraction methods normalize pipeline failures to
`ExtractionError`. Individual row failures are collected on the returned
`ExtractionResult` instead of aborting the complete batch.

## Public Extraction Errors

```python
from structx.core.exceptions import ExtractionError

try:
    result = extractor.extract(
        data="contract.pdf",
        query="extract parties and payment terms",
    )
except ExtractionError as error:
    print(f"Extraction failed: {error}")
```

Missing, empty, unsupported, or malformed file inputs fail during data
preparation and are surfaced through this same `ExtractionError` boundary.

## FileReader Errors

`FileReader.read_file()` is a lower-level utility. When called directly, it
raises `FileError` for invalid paths, empty files, unsupported extensions,
malformed PDFs, and conversion failures:

```python
from structx.core.exceptions import FileError
from structx.utils.file_reader import FileReader

try:
    frame = FileReader.read_file("missing.pdf")
except FileError as error:
    print(f"File error: {error}")
```

## Configuration Errors

`ConfigurationError` is raised when `Extractor` receives an unsupported
configuration object type. YAML loading and provider-specific parameter errors
may originate from OmegaConf or the selected provider instead.

```python
from structx.core.exceptions import ConfigurationError

try:
    extractor = Extractor(
        client=client,
        model_name="openai/gpt-4o",
        config=object(),
    )
except ConfigurationError as error:
    print(f"Configuration error: {error}")
```

## Failed Rows

Once batch extraction starts, failures for individual rows are recorded in the
`failed` DataFrame. Successful rows remain available in `data`:

```python
result = extractor.extract(
    data=df,
    query="extract key information",
)

if result.failure_count:
    print(result.failed[["index", "error", "timestamp"]])
```

Pydantic response-validation failures are normally represented here rather
than raised directly to the caller.

## Logging

Structx uses Loguru. Replace the default sink to control verbosity:

```python
import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, level="DEBUG")
```

## Recommendations

1. Catch `ExtractionError` around public extraction and schema operations.
2. Check `failure_count` and `failed` after every batch extraction.
3. Use `FileReader` directly only when you need file-level error distinctions.
4. Inspect provider errors before increasing extraction attempts.
5. Validate extracted values before using them in downstream systems.
