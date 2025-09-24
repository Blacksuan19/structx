# structx-llm (DEPRECATED)

**This package is deprecated and has been renamed to
[`structx`](https://pypi.org/project/structx).**

All future releases and support are under the new name. Installing `structx-llm`
will automatically install `structx` as a dependency.

**Migration:**

- Update your requirements to use `structx` instead of `structx-llm`
- For extras, use `structx[docs]`, `structx[pdf]`, `structx[docx]`

```bash
pip uninstall -y structx-llm
pip install -U structx
```

Advanced structured data extraction from any document using LLMs with multimodal
support.

[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue.svg?style=for-the-badge)](https://structx.blacksuan19.dev "Documentation")
[![PyPI](https://img.shields.io/badge/PyPi-0.4.9-blue?style=for-the-badge)](https://pypi.org/project/structx-llm "Package")
[![GitHub Actions](https://img.shields.io/badge/github%20actions-%232671E5.svg?style=for-the-badge&logo=githubactions&logoColor=white)](# "Build with GitHub Actions")

`structx` is a powerful Python library for extracting structured data from any
document or text using Large Language Models (LLMs). It features an innovative
multimodal PDF processing pipeline that converts any document to PDF and uses
instructor's vision capabilities for superior extraction quality.

## ✨ Key Features

### 🎯 **Advanced Document Processing**

- **� Multimodal PDF Pipeline**: Converts any document (TXT, DOCX, etc.) to PDF
  for optimal extraction
- **🖼️ Vision-Enabled Extraction**: Native instructor multimodal support for
  PDFs and images
- **🔄 Smart Format Detection**: Automatic processing mode selection for best
  results
- **📊 Universal File Support**: CSV, Excel, JSON, Parquet, PDF, DOCX, TXT,
  Markdown, and more

### 🚀 **Intelligent Data Extraction**

- **🔄 Dynamic Model Generation**: Create type-safe Pydantic models from natural
  language queries
- **🎯 Automatic Schema Inference**: Intelligent schema generation and
  refinement
- **📊 Complex Data Structures**: Support for nested and hierarchical data
- **🔄 Natural Language Refinement**: Improve models with conversational
  instructions

### ⚡ **Performance & Reliability**

- **🚀 High-Performance Processing**: Multi-threaded and async operations
- **🔄 Robust Error Handling**: Automatic retry mechanism with exponential
  backoff
- **📈 Token Usage Tracking**: Detailed step-by-step metrics for cost monitoring
- **� Flexible Configuration**: Configurable extraction using OmegaConf
- **🔌 Multiple LLM Providers**: Support through litellm integration

## Installation

```bash
# Core package with basic extraction capabilities
pip install structx-llm
```

### 📄 Enhanced Document Processing (Recommended)

For the best experience with all document types including advanced multimodal
PDF processing:

```bash
# Complete document processing support
pip install structx-llm[docs]

# Individual components
pip install structx-llm[pdf]   # PDF processing with multimodal support
pip install structx-llm[docx]  # Advanced DOCX conversion via docling
```

### 🔧 What Each Extra Provides

- **`[docs]`**: Complete multimodal document processing pipeline
  - PDF conversion from any document type
  - Instructor multimodal vision support
  - Advanced DOCX processing via docling
  - Enhanced extraction quality
- **`[pdf]`**: PDF-specific processing

  - Multimodal PDF support via instructor
  - PDF generation capabilities
  - Basic PDF text extraction fallback

- **`[docx]`**: Advanced DOCX support
  - Document conversion via docling
  - Structure preservation
  - Markdown-based processing pipeline

## Quick Start

### Basic Text Extraction

```python
from structx import Extractor

# Initialize extractor
extractor = Extractor.from_litellm(
    model="gpt-4o",
    api_key="your-api-key",
    max_retries=3,      # Automatically retry on transient errors
    min_wait=1,         # Start with 1 second wait
    max_wait=10         # Maximum 10 seconds between retries
)

# Extract from text
result = extractor.extract(
    data="System check on 2024-01-15 detected high CPU usage (92%) on server-01.",
    query="extract incident date and details"
)

# Access results
print(f"Extracted {result.success_count} items")
print(result.data[0].model_dump_json(indent=2))
```

### 📄 Document Processing with Multimodal Support

```python
# Process a PDF invoice directly with vision capabilities
result = extractor.extract(
    data="scripts/example_input/S0305SampleInvoice.pdf",      # Direct multimodal processing
    query="extract the invoice number, total amount, and line items"
)

# Convert a DOCX contract and process with multimodal support
result = extractor.extract(
    data="scripts/example_input/free-consultancy-agreement.docx", # Auto-converted to PDF -> multimodal
    query="extract parties, effective date, and payment terms"
)
```

### 📊 Token Usage Monitoring

```python
# Check token usage for cost monitoring
usage = result.get_token_usage()
if usage:
    print(f"Total tokens: {usage.total_tokens}")
    print(f"By step: {[(s.name, s.tokens) for s in usage.steps]}")
```

## 🚀 Why Multimodal PDF Processing?

The innovative multimodal approach provides significant advantages over
traditional text-based extraction:

- **📄 Context Preservation**: Full document layout and structure are maintained
- **🎯 Higher Accuracy**: Vision models can interpret tables, charts, and
  complex layouts
- **🔄 No Chunking Issues**: Eliminates problems with information split across
  chunks
- **📊 Universal Format**: Any document type becomes processable through PDF
  conversion
- **🖼️ Visual Understanding**: Handles documents with visual elements,
  formatting, and structure

## 📚 Documentation

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

## 📁 Supported File Formats

### 📊 Structured Data (Direct Processing)

- **CSV**: Comma-separated values with custom delimiters
- **Excel**: .xlsx/.xls with sheet selection and custom options
- **JSON**: JavaScript Object Notation with nested support
- **Parquet**: Columnar storage format for large datasets
- **Feather**: Fast binary format for data frames

### 📄 Unstructured Documents (Multimodal Pipeline)

| Format   | Extensions                                    | Processing Method                     | Quality    |
| -------- | --------------------------------------------- | ------------------------------------- | ---------- |
| **PDF**  | `.pdf`                                        | Direct multimodal processing          | ⭐⭐⭐⭐⭐ |
| **Word** | `.docx`, `.doc`                               | Docling → Markdown → PDF → Multimodal | ⭐⭐⭐⭐⭐ |
| **Text** | `.txt`, `.md`, `.py`, `.log`, `.xml`, `.html` | Styled PDF → Multimodal               | ⭐⭐⭐⭐   |

### 🔄 Processing Modes

- **Multimodal PDF** (default): Best quality, preserves layout and context
- **Simple Text**: Fallback mode with chunking for memory-constrained
  environments
- **Simple PDF**: Basic PDF text extraction without vision capabilities

## Contributing

Contributions are welcome! Please read our
[Contributing Guidelines](https://structx.blacksuan19.dev/contributing) for
details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file
for details.
