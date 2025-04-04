# structx

Type-safe structured data extraction from text using LLMs.

[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue.svg?style=for-the-badge)](https://structx.blacksuan19.dev "Documentation")
[![PyPI](https://img.shields.io/badge/PyPi-0.2.22-blue?style=for-the-badge)](https://pypi.org/project/structx-llm "Package")
[![GitHub Actions](https://img.shields.io/badge/github%20actions-%232671E5.svg?style=for-the-badge&logo=githubactions&logoColor=white)](# "Build with GitHub Actions")

`structx` is a powerful Python library for extracting structured data from text
using Large Language Models (LLMs). It dynamically generates type-safe data
models and provides consistent, structured extraction with support for complex
nested data structures.

## Features

- 🔄 Dynamic model generation from natural language queries
- 🎯 Automatic schema inference and generation
- 📊 Support for complex nested data structures
- 🔄 Model refinement with natural language instructions
- 📈 Token usage tracking with detailed step-by-step metrics
- 📄 Support for unstructured text and document processing
- 🚀 Multi-threaded processing with async support
- 🔌 Support for multiple LLM providers through litellm
- 🔄 Automatic retry mechanism with exponential backoff

## Installation

```bash
pip install structx-llm
```

### For document processing support

```bash
pip install structx-llm[docs]
```

## Quick Start

```python
from structx import Extractor

# Initialize extractor
extractor = Extractor.from_litellm(
    model="gpt-4o-mini",
    api_key="your-api-key"
)

# Extract structured data
result = extractor.extract(
    data="System check on 2024-01-15 detected high CPU usage (92%) on server-01.",
    query="extract incident date and details"
)

# Access results
print(f"Extracted {result.success_count} items")
print(result.data[0].model_dump_json(indent=2))

# Check token usage
usage = result.get_token_usage()
if usage:
    print(f"Total tokens: {usage.total_tokens}")
    print(f"By step: {[(s.name, s.tokens) for s in usage.steps]}")
```

## Documentation

For comprehensive documentation, examples, and guides, visit our
[documentation site](https://structx.blacksuan19.dev).

- [Getting Started](https://structx.blacksuan19.dev/getting-started)
- [Basic Extraction](https://structx.blacksuan19.dev/guides/basic-extraction)
- [Unstructured Text Processing](https://structx.blacksuan19.dev/guides/unstructured-text)
- [Async Operations](https://structx.blacksuan19.dev/guides/async-operations)
- [Multiple Queries](https://structx.blacksuan19.dev/guides/multiple-queries)
- [Custom Models](https://structx.blacksuan19.dev/guides/custom-models)
- [Token Usage Tracking](https://structx.blacksuan19.dev/guides/token-tracking)
- [API Reference](https://structx.blacksuan19.dev/api/extractor)

## Examples

Check out our [example gallery](https://structx.blacksuan19.dev/examples) for
real-world use cases,

## Supported File Formats

- Structured: CSV, Excel, JSON, Parquet, Feather
- Unstructured: TXT, PDF, DOCX, Markdown, and more

## Contributing

Contributions are welcome! Please read our
[Contributing Guidelines](https://structx.blacksuan19.dev/contributing) for
details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file
for details.
