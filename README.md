# structx

Advanced structured data extraction from any document using LLMs with multimodal
support.

[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue.svg?style=for-the-badge)](https://structx.aolabs.dev "Documentation")
[![PyPI](https://img.shields.io/badge/PyPi-0.5.1-blue?style=for-the-badge)](https://pypi.org/project/structx "Package")
[![GitHub Actions](https://img.shields.io/badge/github%20actions-%232671E5.svg?style=for-the-badge&logo=githubactions&logoColor=white)](# "Build with GitHub Actions")

`structx` is a powerful Python library for extracting structured data from text,
tables, and documents using Large Language Models (LLMs). With the optional
`docs` extra, it provides a multimodal PDF pipeline that passes PDFs directly to
vision-capable models and converts other document formats to PDF first.

## 🔔 Package rename notice (PyPI)

The PyPI distribution has been renamed from `structx-llm` to `structx`
(September 2025).

- Imports are unchanged: continue using `import structx`
- Document processing now lives in the optional `docs` extra
- Please update your environments and requirement files to use the new name

Upgrade commands:

```bash
pip uninstall -y structx-llm
pip install -U structx
```

If you previously pinned `structx-llm` in requirements or lock files, replace it
with `structx`. For document/PDF processing, install `structx[docs]`.

## ✨ Key Features

### 🎯 **Advanced Document Processing**

- **� Multimodal PDF Pipeline**: Passes PDFs directly to vision-capable models
  and converts supported non-PDF documents to PDF
- **🖼️ Vision-Enabled Extraction**: Native instructor multimodal support for
  PDFs and images
- **🔄 Smart Format Detection**: Automatic processing mode selection for best
  results
- **📊 Flexible File Support**: CSV, Excel, JSON, Parquet in the base install,
  with PDF, DOCX, TXT, Markdown, and more via `structx[docs]`

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
pip install structx
```

For document and multimodal PDF support:

```bash
pip install "structx[docs]"
```

### 🔧 What The Package Provides

- Structured readers for CSV, Excel, JSON, Parquet, and Feather
- Instructor multimodal vision support
- Optional Docling document parsing with CPU-only PyTorch resolution for uv on Linux
- Optional WeasyPrint PDF rendering for non-PDF document formats

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

Install `structx[docs]` before using non-PDF document formats. Existing PDFs can
be passed directly through the multimodal path.

```python
# Process a PDF invoice through the multimodal pipeline
result = extractor.extract(
    data="scripts/example_input/S0305SampleInvoice.pdf",
    query="extract the invoice number, total amount, and line items"
)

# Convert a DOCX contract and process with multimodal support
result = extractor.extract(
    data="scripts/example_input/free-consultancy-agreement.docx",
    query="extract parties, effective date, and payment terms"
)
```

### 📊 Token Usage Monitoring

```python
# Check token usage for cost monitoring
usage = result.usage
if usage:
    print(f"Total tokens: {usage.total_tokens}")
    for step, calls in usage.steps.items():
        print(step.value, [call.total_tokens for call in calls])
```

## 🚀 Why Multimodal PDF Processing?

The innovative multimodal approach provides significant advantages over
traditional text-based extraction:

- **📄 Context Preservation**: Full document layout and structure are maintained
- **🎯 Higher Accuracy**: Vision models can interpret tables, charts, and
  complex layouts
- **🔄 No Chunking Issues**: Eliminates problems with information split across
  chunks
- **📊 Universal Format**: Existing PDFs are passed through directly; supported
  non-PDF documents become processable through PDF conversion
- **🖼️ Visual Understanding**: Handles documents with visual elements,
  formatting, and structure

## 📚 Documentation

For comprehensive documentation, examples, and guides, visit our
[documentation site](https://structx.aolabs.dev).

- [Getting Started](https://structx.aolabs.dev/getting-started)
- [Basic Extraction](https://structx.aolabs.dev/guides/basic-extraction)
- [Unstructured Text Processing](https://structx.aolabs.dev/guides/unstructured-text)
- [Async Operations](https://structx.aolabs.dev/guides/async-operations)
- [Multiple Queries](https://structx.aolabs.dev/guides/multiple-queries)
- [Custom Models](https://structx.aolabs.dev/guides/custom-models)
- [Token Usage Tracking](https://structx.aolabs.dev/guides/token-tracking)
- [API Reference](https://structx.aolabs.dev/api/extractor)

## Examples

Check out our [example gallery](https://structx.aolabs.dev/examples) for
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
| **PDF**  | `.pdf`                                        | PDF → Multimodal                      | ⭐⭐⭐⭐⭐ |
| **Word** | `.docx`, `.doc`                               | Docling → HTML → PDF → Multimodal     | ⭐⭐⭐⭐⭐ |
| **PowerPoint** | `.pptx`, `.ppt`                       | Docling → HTML → PDF → Multimodal     | ⭐⭐⭐⭐   |
| **Text** | `.txt`, `.md`, `.py`, `.log`, `.xml`, `.html` | Docling → HTML → PDF → Multimodal     | ⭐⭐⭐⭐   |

### 🔄 Processing Pipeline

- **PDF passthrough**: Existing PDFs are sent directly to multimodal extraction
- **Docling parsing**: Reads non-PDF document-like inputs into a structured document model
- **WeasyPrint rendering**: Converts Docling HTML to a temporary PDF for non-PDF inputs
- **Multimodal extraction**: Sends the rendered PDF to instructor's multimodal API

## Contributing

Contributions are welcome! Please read our
[Contributing Guidelines](https://structx.aolabs.dev/contributing) for
details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file
for details.
