# Getting Started

This guide will help you get started with `structx` for structured data
extraction.

## Installation

Install the core package:

```bash
pip install structx-llm
```

For additional document format support:

```bash
# For PDF support
pip install structx-llm[pdf]

# For DOCX support
pip install structx-llm[docx]

# For all document formats
pip install structx-llm[docs]
```

## Basic Usage

### Initialize the Extractor

```python
from structx import Extractor

# Using litellm (supports multiple providers)
extractor = Extractor.from_litellm(
    model="gpt-4o-mini",  # or any other model supported by litellm
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

### Extract Structured Data

```python
# From a DataFrame
import pandas as pd

df = pd.DataFrame({
    "description": [
        "System check on 2024-01-15 detected high CPU usage (92%) on server-01.",
        "Database backup failure occurred on 2024-01-20 03:00."
    ]
})

result = extractor.extract(
    data=df,
    query="extract incident dates and affected systems"
)

# From a file
result = extractor.extract(
    data="logs.csv",
    query="extract incident dates and affected systems"
)

# From raw text
text = """
System check on 2024-01-15 detected high CPU usage (92%) on server-01.
Database backup failure occurred on 2024-01-20 03:00.
"""

result = extractor.extract(
    data=text,
    query="extract incident dates and affected systems"
)
```

### Access Results

```python
# Check extraction statistics
print(f"Extracted {result.success_count} items")
print(f"Failed {result.failure_count} items")
print(f"Success rate: {result.success_rate:.1f}%")

# Access as list of model instances
for item in result.data:
    print(f"Date: {item.incident_date}")
    print(f"System: {item.affected_system}")

# Or convert to DataFrame
import pandas as pd
df = pd.DataFrame([item.model_dump() for item in result.data])
print(df)

# Access the generated model
print(f"Model: {result.model.__name__}")
print(result.model.model_json_schema())
```

### Check Token Usage

`structx` automatically tracks token usage for all operations, helping you
monitor costs:

```python
# Check token usage
usage = result.get_token_usage()
print(f"Total tokens used: {usage.total_tokens}")

# See usage breakdown by step
for step in usage.steps:
    print(f"{step.name}: {step.tokens} tokens")
```

### Configure Extraction

```python
# With a YAML file
extractor = Extractor.from_litellm(
    model="gpt-4o-mini",
    api_key="your-api-key",
    config="config.yaml"
)

# With a dictionary
config = {
    "refinement": {
        "temperature": 0.1,
        "top_p": 0.05
    },
    "extraction": {
        "temperature": 0.0,
        "top_p": 0.1
    }
}

extractor = Extractor.from_litellm(
    model="gpt-4o-mini",
    api_key="your-api-key",
    config=config
)

# With retry settings
extractor = Extractor.from_litellm(
    model="gpt-4o-mini",
    api_key="your-api-key",
    max_retries=5,      # Maximum retry attempts
    min_wait=2,         # Minimum seconds between retries
    max_wait=30         # Maximum seconds between retries
)
```

## Next Steps

- Learn about [Basic Extraction](guides/basic-extraction.md) techniques
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
