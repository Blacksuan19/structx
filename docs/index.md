# structx

<div class="grid cards" markdown>

- :material-text-box-search-outline: **Structured Data Extraction**

  Extract structured data from unstructured text using LLMs

- :material-code-json: **Dynamic Model Generation**

  Automatically generate type-safe Pydantic models

- :material-file-document-multiple: **Multiple File Formats**

  Support for CSV, Excel, JSON, PDF, TXT, and more

- :material-lightning-bolt: **Async Support**

  Asynchronous operations for high-throughput processing

</div>

## Overview

`structx` is a powerful Python library that extracts structured data from text
using Large Language Models (LLMs). It dynamically generates type-safe data
models and provides consistent, structured extraction with support for complex
nested data structures.

Whether you're analyzing incident reports, processing documents, or extracting
metrics from unstructured text, `structx` provides a simple, consistent
interface with powerful capabilities.

## Key Features

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

## Quick Example

```python
from structx import Extractor

# Initialize extractor
extractor = Extractor.from_litellm(
    model="gpt-4o-mini",
    api_key="your-api-key"
)

# Extract structured data
result = extractor.extract(
    data="incident_report.txt",
    query="extract incident dates, affected systems, and resolution steps"
)

# Access the extracted data
print(f"Extracted {result.success_count} items")
for item in result.data:
    print(f"Date: {item.incident_date}")
    print(f"System: {item.affected_system}")
    print(f"Resolution: {item.resolution_steps}")
```

## License

This project is licensed under the MIT License - see the
[LICENSE](https://github.com/yourusername/structx/blob/main/LICENSE) file for
details.
