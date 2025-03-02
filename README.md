# structx

`structx` is a powerful Python library for extracting structured data from text
using Large Language Models (LLMs). It dynamically generates type-safe data
models and provides consistent, structured extraction with support for complex
nested data structures.

[![view - Documentation](https://img.shields.io/badge/PyPi-0.2.1-blue?style=for-the-badge)](https://pypi.org/project/structx "view package on PyPi")
&nbsp;&nbsp;&nbsp;
[![GitHub Actions](https://img.shields.io/badge/github%20actions-%232671E5.svg?style=for-the-badge&logo=githubactions&logoColor=white)](# "Build with github actions")

## Features

- 🔄 Dynamic model generation from natural language queries
- 🎯 Automatic schema inference and generation
- 📊 Support for complex nested data structures
- 🚀 Multi-threaded processing for large datasets
- ⚡ Async support
- 🔧 Configurable extraction using OmegaConf
- 📁 Support for multiple file formats (CSV, Excel, JSON, Parquet, PDF, TXT, and
  more)
- 📄 Support for unstructured text and document processing
- 🏗️ Type-safe data models using Pydantic
- 🎮 Easy-to-use interface
- 🔌 Support for multiple LLM providers through litellm
- 🔄 Automatic retry mechanism with exponential backoff

## Installation

```bash
pip install structx
```

For PDF support:

```bash
pip install structx[pdf]
```

For DOCX support:

```bash
pip install structx[docx]
```

For all document formats:

```bash
pip install structx[docs]
```

## Quick Start

```python
from structx import Extractor

# Initialize extractor using litellm
extractor = Extractor.from_litellm(
    model="gpt-4o-mini",  # or any other model supported by litellm
    api_key="your-api-key",
    max_retries=3,     # Maximum number of retry attempts
    min_wait=1,        # Minimum seconds to wait between retries
    max_wait=10        # Maximum seconds to wait between retries
)

# Extract from structured data
data = [
    {"description": "System check on 2024-01-15 detected high CPU usage (92%) on server-01. Alert triggered at 14:30."},
    {"description": "Database backup failure occurred on 2024-01-20 03:00. Root cause: insufficient storage space."}
]

# Extract data and get ExtractionResult object
result = extractor.extract(
    data=data,
    query="extract incident dates and their significance",
    return_df=False
)

# ExtractionResult contains extracted data, failed rows, and the generated model
print(f"Extraction successful: {result.success_count} items extracted")
print(f"Success rate: {result.success_rate:.1f}%")

# Access extracted data (list of model instances)
for item in result.data:
    print(f"Date: {item.incident_date}")
    print(f"Significance: {item.significance}")

# Access the generated model
print(f"Generated model: {result.model.__name__}")
print(result.model_json_schema())

# Extract from files
file_result = extractor.extract(
    data="logs.csv",
    query="extract incident dates and their significance"
    return_df=True
)

# Access as DataFrame
print(file_result.data.head())
```

Example output:

```json
Extraction successful: 2 items extracted
Success rate: 100.0%
Date: 2024-01-15
Significance: High CPU usage (92%) on server-01, alert triggered at 14:30
Date: 2024-01-20 03:00
Significance: Database backup failure due to insufficient storage space
Generated model: IncidentExtraction
{
  "title": "IncidentExtraction",
  "type": "object",
  "properties": {
    "incident_date": {
      "title": "Incident Date",
      "type": "string",
      "description": "Date when the incident occurred"
    },
    "significance": {
      "title": "Significance",
      "type": "string",
      "description": "Description of the incident and its significance"
    }
  }
}
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

### Unstructured Text Support

structx supports extracting structured data from various unstructured sources:

```python
# From a PDF file
result = extractor.extract(
    data="document.pdf",
    query="extract all dates and events",
    chunk_size=2000,  # Size of text chunks
    overlap=200       # Overlap between chunks
)

# From a Word document
result = extractor.extract(
    data="report.docx",
    query="extract key findings and recommendations"
)

# From raw text
text = """
System check on 2024-01-15 detected high CPU usage (92%) on server-01.
Database backup failure occurred on 2024-01-20 03:00.
"""
result = extractor.extract(
    data=text,
    query="extract incident dates and their significance"
)

print(f"Extracted {result.success_count} items with {result.failure_count} failures")
print(f"Success rate: {result.success_rate:.1f}%")
```

The library automatically:

1. Detects file types and processes accordingly
2. Chunks large documents for better processing
3. Maintains source information in the results

#### Chunking Parameters

| Parameter  | Type | Default | Description                    |
| ---------- | ---- | ------- | ------------------------------ |
| chunk_size | int  | 1000    | Size of text chunks            |
| overlap    | int  | 100     | Overlap between chunks         |
| encoding   | str  | 'utf-8' | Text encoding for file reading |

### Using your own Data Models

structx generates Pydantic data models for structured data extraction. However,
you can also use your own data models:

```python
from pydantic import BaseModel
from typing import List

class Metric(BaseModel):
    name: str
    value: float
    unit: str

class Incident(BaseModel):
    timestamp: str
    issue_type: str
    metrics: List[Metric]
    resolution: str

# Extract using custom data model
result = extractor.extract(
    data="incident_report.txt",
    query="extract incident information including timestamps, issues, and metrics",
    model=Incident
)

# Access structured data
for item in result.data:
    print(f"Incident Time: {item.timestamp}")
    print(f"Issue Type: {item.issue_type}")
    for metric in item.metrics:
        print(f"- {metric.name}: {metric.value} {metric.unit}")
    print(f"Resolution: {item.resolution}")

# Reuse the model for another extraction
new_result = extractor.extract(
    data="another_report.txt",
    query="extract incident information",
    model=result.model  # Reuse the model from previous extraction
)
```

### Using Different LLM Providers

structx supports multiple LLM providers through litellm. You can easily switch
between providers by patching your own client with instructor or passing the
required parameters to litellm:

```python
import instructor
from openai import OpenAI, AzureOpenAI
import os

# patch your own client with instructor
client = instructor.from_openai(AzureOpenAI())
extractor = Extractor(
    client=client,
    model_name="gpt-4o-mini",
)


# use litellm
os.environ["ANTHROPIC_API_KEY"] = "your-anthropic-key"
extractor = Extractor.from_litellm(
    model="claude-3-5-sonnet",
)
```

for more information on how to use litellm, refer to the
[litellm documentation](https://docs.litellm.ai/docs/).

### Multiple Query Processing

structx allows processing multiple queries on the same data in a single call
using the `extract_queries` method. This is useful when you need to extract
different types of information from the same text without having it all on the
same model:

```python
# Define multiple queries
queries = [
    "extract all dates and their significance",
    "extract technical issues and their severity",
    "extract metrics and their values"
]

# Process all queries on the same data
results = extractor.extract_queries(
    data="incident_report.txt",
    queries=queries,
    return_df=True,
    expand_nested=True
)

# Access results by query
for query, result in results.items():
    print(f"\nResults for query: {query}")
    print(f"Extracted {result.success_count} items")
    print(f"Failed {result.failure_count} items")
    print(result.data.head())

    # Access the model for this query
    print(f"Model: {result.model.__name__}")
```

Example output:

```bash
Results for query: extract all dates and their significance
Extracted 5 items
Failed 0 items
   incident_date                                      significance
0    2024-01-15  High CPU usage (92%) on server-01, alert at 14:30
1    2024-01-20  Database backup failure due to insufficient space
Model: DateExtractionModel

Results for query: extract technical issues and their severity
Extracted 5 items
Failed 0 items
            issue_type severity                               description
0       CPU Overload     High  CPU usage at 92%, exceeding safe threshold
1  Backup Failure   Critical  Database backup failed due to storage issue
Model: IssueExtractionModel
```

This approach is more efficient than making separate calls for each query since
the data is loaded only once. The return value is a dictionary where:

- Keys are the original queries
- Values are the extraction results (ExtractionResult objects)

You can use all the same options as with the regular `extract` method,
including:

- Processing different data types (files, DataFrames, raw text)
- Returning DataFrames or model instances
- Expanding nested structures
- Configuring chunking parameters

### Preview Generated Schema

structx supports previewing the generated schema model without performing
extraction. This is useful for inspecting the model structure and field
information:

```python
# Get the schema model without performing extraction
ModelClass = extractor.get_schema(
    query="extract incident dates and their significance",
    sample_text="System check on 2024-01-15 detected high CPU usage (92%) on server-01."
)

# Print the JSON schema
print(ModelClass.model_json_schema(indent=2))

# Explore field information
for field_name, field in ModelClass.model_fields.items():
    print(f"Field: {field_name}")
    print(f"  Type: {field.annotation}")
    print(f"  Description: {field.description}")

# Create an instance manually
instance = ModelClass(
    incident_date="2024-02-15",
    significance="Example manually created instance"
)
print(instance.model_dump_json(indent=2))

# Use the model for extraction
result = extractor.extract(
    data="incident_report.txt",
    query="extract incident dates and their significance",
    model=ModelClass
)
```

This allows you to:

1. Inspect the model structure
2. Create instances manually
3. Use the model for validation
4. Access field metadata
5. Use the model for extraction later on

### Async Support

structx supports asynchronous workflows using Python's `asyncio` library. For
each of the extraction methods, you can use the `_async` version to perform the
extraction asynchronously:

```python
import asyncio

async def process_data():
    # async extraction
    result = await extractor.extract_async(
        data=data,
        query="extract incident dates and their significance",
        return_df=False
    )

    print(f"Extracted {result.success_count} items")

    # async extraction with multiple queries
    query_results = await extractor.extract_queries_async(
        data="incident_report.txt",
        queries=queries,
        return_df=True,
        expand_nested=True
    )

    # async schema generation
    ModelClass = await extractor.get_schema_async(
        query="extract incident dates and their significance",
        sample_text="System check on 2024-01-15 detected high CPU usage (92%) on server-01."
    )

    return result, query_results, ModelClass

# Run the async function
result, query_results, ModelClass = asyncio.run(process_data())
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

## Supported File Formats

| Format  | Extension             | Requirements                |
| ------- | --------------------- | --------------------------- |
| CSV     | .csv                  | Built-in                    |
| Excel   | .xlsx, .xls           | Built-in                    |
| JSON    | .json                 | Built-in                    |
| Parquet | .parquet              | Built-in                    |
| Feather | .feather              | Built-in                    |
| Text    | .txt, .md, .log, etc. | Built-in                    |
| PDF     | .pdf                  | `pip install structx[pdf]`  |
| Word    | .docx, .doc           | `pip install structx[docx]` |

## Requirements

- Python 3.8+
- instructor
- litellm
- pandas
- pydantic (v2+)
- omegaconf
- tqdm
- tenacity (for retry mechanism)

Optional dependencies:

- pypdf (for PDF support)
- python-docx (for DOCX support)

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
pip install -e ".[dev,docs]"
```

## Contributing

Contributions are welcome! Please read our
[Contributing Guidelines](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file
for details.
