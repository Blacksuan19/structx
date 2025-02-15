# structx

`structx` is a powerful Python library for extracting structured data from text
using Large Language Models (LLMs). It dynamically generates type-safe data
models and provides consistent, structured extraction with support for complex
nested data structures.

[![view - Documentation](https://img.shields.io/badge/PyPi-0.1.3-blue?style=for-the-badge)](https://pypi.org/project/structx "view package on PyPi")
&nbsp;&nbsp;&nbsp;
[![GitHub Actions](https://img.shields.io/badge/github%20actions-%232671E5.svg?style=for-the-badge&logo=githubactions&logoColor=white)](# "Build with github actions")

## Features

- 🔄 Dynamic model generation from natural language queries
- 🎯 Automatic schema inference and generation
- 📊 Support for complex nested data structures
- 🚀 Multi-threaded processing for large datasets
- ⚡ Async support
- 🔧 Configurable extraction using OmegaConf
- 📁 Support for multiple file formats (CSV, Excel, JSON, Parquet)
- 🏗️ Type-safe data models using Pydantic
- 🎮 Easy-to-use interface
- 🔌 Support for multiple LLM providers through litellm
- 🔄 Automatic retry mechanism with exponential backoff

## Installation

```bash
pip install structx
```

## Quick Start

```python
from structx import Extractor

# Example data
data = [
    {"description": "System check on 2024-01-15 detected high CPU usage (92%) on server-01. Alert triggered at 14:30."},
    {"description": "Database backup failure occurred on 2024-01-20 03:00. Root cause: insufficient storage space."}
]

# Initialize extractor using litellm
extractor = Extractor.from_litellm(
    model="gpt-4o-mini",  # or any other model supported by litellm
    api_key="your-api-key",
    max_retries=3,     # Maximum number of retry attempts
    min_wait=1,        # Minimum seconds to wait between retries
    max_wait=10        # Maximum seconds to wait between retries
    ...  # other parameters to litellm
)

# Extract as list of model instances
results_list, failed = extractor.extract(
    data=data,
    query="extract incident dates and their significance",
    return_df=False
)

print("\nResults as model instances:")
for result in results_list:
    print(result.model_dump_json(indent=2))


# Extract as DataFrame
# this will expand nested data structures into separate columns
results_df, failed = extractor.extract(
    data=data,
    query="extract incident dates and their significance"
    return_df=True
)

print("\nResults as DataFrame:")
print(results_df)
```

## Configuration

structx uses OmegaConf for flexible configuration management. Configure
extraction parameters using YAML:

```yaml
# config.yaml
analysis:
  temperature: 0.2
  top_p: 0.1
  max_tokens: 2000

refinement:
  temperature: 0.1
  top_p: 0.05
  max_tokens: 2000

extraction:
  temperature: 0.0
  top_p: 0.1
  max_tokens: 2000
```

Use the configuration:

```python
extractor = Extractor.from_litellm(
    model="gpt-4",
    api_key="your-api-key",
    config="config.yaml"
)

# Or use a dictionary
config = {
    "analysis": {
        "temperature": 0.2,
        "top_p": 0.1
    },
    # ... other settings
}
extractor = Extractor.from_litellm(
    model="gpt-4",
    api_key="your-api-key",
    config=config
)
```

## Advanced Usage

### Using Different LLM Providers

structx supports multiple LLM providers through litellm. You can easily switch
between providers by patching your own client with instructor or passing the
required parameters to litellm:

```python
import instructor
from openai import OpenAI, AzureOpenAI

# patch your own client with instructor
client = instructor.from_openai(AzureOpenAI)
extractor = Extractor(
    client=client,
    model_name="gpt-4o-mini",
)


# use litellm
extractor = Extractor.from_litellm(
    model="claude-2",
    api_key="your-anthropic-key"
)
```

for more information on how to use litellm, refer to the
[litellm documentation](https://docs.litellm.ai/docs/).

### Complex Data Structures

The library automatically handles nested data structures:

```python
results, failed = extractor.extract(
    data=data,
    query="""
    extract incident information including:
    - timestamp of incident
    - type of issue
    - metrics (if any) with their values
    - resolution steps taken
    """,
)

# Access structured data
for result in results:
    print(f"Incident Time: {result.timestamp}")
    for metric in result.metrics:
        print(f"- {metric.name}: {metric.value} {metric.unit}")
```

### Async Support

```python
async def process_data():
    results, failed = await extractor.extract_async(
        data=data,
        query="extract incident dates and their significance",
        return_df=False
    )
    return results, failed
```

### Preview Generated Schema

```python
# Get the schema without performing extraction
schema = extractor.get_schema(
    query="extract metrics and issues",
    sample_text="Your sample text here"
)
print(schema)
```

### Retry Configuration

structx includes an automatic retry mechanism with exponential backoff for
handling transient failures during extraction. You can configure retry behavior
when initializing the Extractor:

```python
# Default retry settings
extractor = Extractor.from_litellm(
    model="gpt-4",
    api_key="your-api-key"
)

# Custom retry settings
extractor = Extractor.from_litellm(
    model="gpt-4",
    api_key="your-api-key",
    max_retries=5,      # More retry attempts
    min_wait=2,         # Wait at least 2 seconds
    max_wait=30         # Maximum 30 seconds wait
)

# Disable retries
extractor = Extractor.from_litellm(
    model="gpt-4",
    api_key="your-api-key",
    max_retries=0       # Disables retry mechanism
)
```

The retry mechanism uses exponential backoff, meaning the wait time between
retries increases exponentially (but is capped at `max_wait`):

- First retry: `min_wait` seconds
- Second retry: `min_wait * 2` seconds
- Third retry: `min_wait * 4` seconds
- And so on, up to `max_wait`

#### Retry Parameters

| Parameter   | Type | Default | Description                             |
| ----------- | ---- | ------- | --------------------------------------- |
| max_retries | int  | 3       | Maximum number of retry attempts        |
| min_wait    | int  | 1       | Minimum seconds to wait between retries |
| max_wait    | int  | 10      | Maximum seconds to wait between retries |

## Requirements

- Python 3.8+
- instructor
- litellm
- pandas
- pydantic (v2+)
- omegaconf
- PyYAML
- tqdm
- tenacity (for retry mechanism)

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/structx.git
cd structx

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -e ".[dev]"
```

## Contributing

Contributions are welcome! Please read our
[Contributing Guidelines](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file
for details.
