# Getting Started

This guide will help you get started with `structx` for structured data
extraction.

## Installation

!!! info "Package rename notice (PyPI)"
    The PyPI distribution has been renamed from `structx-llm` to `structx` (September 2025).

    - Imports are unchanged: `import structx`
    - Document processing lives in the optional `docs` extra
    - To upgrade:

        ```bash
        pip uninstall -y structx-llm
        pip install -U structx
        ```

    If you pinned `structx-llm` in requirements or lock files, replace it with `structx`.
    Install `structx[docs]` for non-PDF document conversion.

Install the package:

```bash
pip install structx
```

For converting non-PDF documents and images to multimodal PDF input:

```bash
pip install "structx[docs]"
```

### What You Get

- **Structured Data**: CSV, JSON, Excel, Parquet, and Feather through pandas
- **Existing PDFs**: Direct Instructor multimodal passthrough in the base install
- **Other Documents**: Optional Docling and WeasyPrint conversion through
  `structx[docs]`
  - Document-to-PDF conversion for supported non-PDF formats
  - OCR-free visual interpretation by the selected multimodal model

## Basic Usage

### Initialize the Extractor

```python
from structx import Extractor

# Using litellm (supports multiple providers)
extractor = Extractor.from_litellm(
    model="openai/gpt-4o",  # or another LiteLLM model identifier
    api_key="your-api-key"
)

# Or with a custom client
import instructor
from openai import AzureOpenAI

client = instructor.patch(AzureOpenAI(
    api_key="your-api-key",
    api_version="2024-02-15-preview",
    azure_endpoint="your-endpoint"
))

extractor = Extractor(
    client=client,
    model_name="your-model-deployment"
)
```

## API Requirements

**Important**: All extractor methods require **keyword arguments**. You cannot
use positional arguments.

```python
# ✅ Correct - using keyword arguments
result = extractor.extract(data="file.pdf", query="extract information")

# ❌ Incorrect - using positional arguments
result = extractor.extract("file.pdf", "extract information")  # This will fail
```

This applies to all methods:

- `prepare_input(*, data, ...)`
- `prepare_input_async(*, data, ...)`
- `extract(*, data, query, ...)`
- `extract_async(*, data, query, ...)`
- `extract_queries(*, data, queries, ...)`
- `get_schema(*, data, query, ...)`
- `refine_data_model(*, model, refinement_instructions, ...)`

### Extract Structured Data

```python
# From a file (automatically detects format and uses optimal processing)
# Process a PDF invoice
result = extractor.extract(
    data="scripts/example_input/S0305SampleInvoice.pdf",         # Unstructured: multimodal PDF processing
    query="extract invoice number, total amount, and line items"
)

# Process a DOCX contract
result = extractor.extract(
    data="scripts/example_input/free-consultancy-agreement.docx", # Unstructured: converted to PDF then multimodal
    query="extract the parties, effective date, and payment terms"
)
```

!!! note "Document dependencies"
    Existing PDFs and raw strings work with the base installation. Install
    `structx[docs]` for non-PDF document paths such as DOCX, PPTX, HTML, or
    images that must be converted through Docling and WeasyPrint.

### Access Results

```python
# Check extraction statistics
print(f"Successful rows: {result.success_count}")
print(f"Failed rows: {result.failure_count}")
print(f"Success rate: {result.success_rate:.1f}%")

# Access as list of model instances
for item in result.data:
    print(item.model_dump_json(indent=2))

# Or convert to DataFrame
import pandas as pd
df = pd.DataFrame([item.model_dump() for item in result.data])
print(df)

# Access the generated model
print(f"Model: {result.model.__name__}")
print(result.model.model_json_schema())

# Inspect row provenance, status, and row-specific usage
for row in result.rows:
    print(row.source_index, row.status, row.usage.total_tokens)
```

See [Working with Results](guides/working-with-results.md) for status meanings,
row provenance, multiple items per row, counters, and DataFrame behavior.

### Check Token Usage

`structx` automatically tracks token usage for all operations, helping you
monitor costs:

```python
# Check token usage
usage = result.usage
print(f"Total tokens used: {usage.total_tokens}")

# See usage breakdown by step
for step, calls in usage.steps.items():
    print(step.value, [call.total_tokens for call in calls])
```

### Configure Extraction

```python
# With a YAML file
extractor = Extractor.from_litellm(
    model="openai/gpt-5.5",
    api_key="your-api-key",
    config="config.yaml"
)

# With a dictionary
config = {
    "planning": {
        "reasoning_effort": "low"
    },
    "extraction": {
        "reasoning_effort": "medium",
        "max_completion_tokens": 16000
    }
}

extractor = Extractor.from_litellm(
    model="openai/gpt-5.5",
    api_key="your-api-key",
    config=config
)

# With retry settings
extractor = Extractor.from_litellm(
    model="openai/gpt-4o",
    api_key="your-api-key",
    max_retries=5,      # Five retries after the initial attempt
    min_wait=2,         # Minimum seconds between retries
    max_wait=30         # Maximum seconds between retries
)
```

Structx does not set sampling controls or token limits by default. Values under
each step are passed to LiteLLM and the selected provider, so only configure
parameters supported by your model.

## Next Steps

- Learn about [Basic Extraction](guides/basic-extraction.md) techniques
- Understand [Extraction Results](guides/working-with-results.md), row status,
  provenance, and per-row usage
- Explore [Custom Models](guides/custom-models.md) for specific extraction needs
- Learn about the [Retry Mechanism](guides/retry-mechanism.md) for handling
  transient errors
- See how to [Refine Data Models](guides/model-refinement.md) with natural
  language instructions
- Learn how to handle [Unstructured Text](guides/unstructured-text.md) like PDFs
  and documents
- Check out the [API Reference](api/extractor.md) for detailed documentation
- Explore [Token Usage Tracking](guides/token-tracking.md) for monitoring costs
- Discover [Async Operations](guides/async-operations.md) for better performance
- Understand [Multiple Queries](guides/multiple-queries.md) for complex
  extraction scenarios
