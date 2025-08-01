# Error Handling

`structx` provides comprehensive error handling for extraction processes.

## Error Types

### ExtractionError

The base exception for extraction errors:

```python
try:
    result = extractor.extract(
        data=df,
        query="extract key information"
    )
except ExtractionError as e:
    print(f"Extraction failed: {e}")
```

### ConfigurationError

Raised when there's an issue with the configuration:

```python
try:
    extractor = Extractor.from_litellm(
        model="gpt-4o",
        api_key="your-api-key",
        config="invalid_config.yaml"
    )
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

### ValidationError

Raised when there's a validation issue with the extracted data:

```python
try:
    result = extractor.extract(
        data=df,
        query="extract key information"
    )
except ValidationError as e:
    print(f"Validation error: {e}")
```

### ModelGenerationError

Raised when there's an issue generating the extraction model:

```python
try:
    model = extractor.get_schema(
        query="extract key information",
        sample_text="Sample text"
    )
except ModelGenerationError as e:
    print(f"Model generation error: {e}")
```

### FileError

Raised when there's an issue with file operations:

```python
try:
    result = extractor.extract(
        data="nonexistent_file.pdf",
        query="extract key information"
    )
except FileError as e:
    print(f"File error: {e}")
```

## Handling Failed Extractions

Even when the overall extraction succeeds, individual items may fail. These are
collected in the `failed` DataFrame:

```python
result = extractor.extract(
    data=df,
    query="extract key information"
)

if result.failure_count > 0:
    print(f"Failed extractions: {result.failure_count}")
    print(result.failed)
```

## Retry Mechanism

`structx` includes an automatic retry mechanism for handling transient failures:

```python
extractor = Extractor.from_litellm(
    model="gpt-4o",
    api_key="your-api-key",
    max_retries=5,      # Maximum number of retry attempts
    min_wait=2,         # Minimum seconds to wait between retries
    max_wait=30         # Maximum seconds to wait between retries
)
```

The retry mechanism uses exponential backoff, meaning the wait time between
retries increases exponentially (but is capped at `max_wait`).

## Logging

`structx` uses [loguru](https://github.com/Delgan/loguru) for logging. You can
configure the logging level:

```python
from loguru import logger

# Set logging level
logger.remove()
logger.add(sys.stderr, level="INFO")  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

For detailed debugging:

```python
logger.remove()
logger.add(sys.stderr, level="DEBUG")
```

## Best Practices

1. **Always Check Failures**: Always check `result.failure_count` and
   `result.failed` for failed extractions
2. **Use Try/Except**: Wrap extraction calls in try/except blocks
3. **Configure Retries**: Adjust retry settings based on your API stability
4. **Log Errors**: Enable appropriate logging levels for debugging
5. **Validate Results**: Validate extracted data before using it
