import json
import os
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Dict, List

from structx import Extractor
from structx.core.models import ExtractionResult
from structx.utils.usage import UsageSummary


def print_section_header(title: str, description: str = None):
    """Print a section header with an optional description."""
    print(f"\n## {title}")
    if description:
        print(f"\n{description}")


def print_code_block(code_lines: List[str]):
    """Print code in a markdown code block."""
    print("\n```python")
    for line in code_lines:
        print(line)
    print("```")


def print_json(data: List[Dict]):
    """Print data as a JSON code block."""
    print("\n```json")
    print(json.dumps(data, indent=2, default=str))
    print("```")


def print_token_usage(usage: UsageSummary):
    """Print token usage information."""
    print("\n### Token Usage:")
    if usage:
        print(f"Total tokens used: {usage.total_tokens}")
        print("Tokens by step:")
        for step in usage.steps:
            print(f"- {step.name}: {step.tokens} tokens\n")


def print_extraction_results(results: ExtractionResult):
    """Print extraction results including stats, token usage, and data."""
    print("\n### Results:")
    print(
        f"\nExtracted {results.success_count} items with {results.success_rate:.1f}% success rate"
    )

    print_token_usage(results.usage.get_usage_summary())

    # Display results - either as markdown table or JSON
    if hasattr(results.data, "to_markdown"):
        print(results.data.to_markdown(index=False))
    else:
        print_json([item.model_dump() for item in results.data])


def run_extraction_example(
    extractor: Extractor,
    data_path: Path,
    title: str,
    description: str,
    query: str,
    code_lines: List[str],
) -> ExtractionResult:
    """Run and document an extraction example."""
    print_section_header(title, description)
    print_code_block(code_lines)

    results = extractor.extract(data_path, query)
    print_extraction_results(results)

    # For complex examples that benefit from showing the model schema
    if (
        title != "Example 3: Complex Nested Extraction"
    ):  # Only show for simpler examples
        print("\n<details>")
        print(f"<summary>Generated Model: `{results.model.__name__}`</summary>\n")
        print_json(results.model.model_json_schema())
        print("\n</details>")

    return results


def main():
    # Redirect stdout to capture output
    output = StringIO()
    sys.stdout = output

    # Start generating the README content
    print("# Examples")
    print(
        "\nThis document contains examples of using the structx library for structured data extraction from unstructured documents."
    )
    print(f"\n*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    # Setup section
    print_section_header("Setup")
    print_code_block(
        [
            "from structx import Extractor",
            "from pathlib import Path",
            "import os",
            "\n# Initialize the extractor",
            "extractor = Extractor.from_litellm(",
            '    model="gpt-4o",',
            '    api_key="your-api-key"',
            ")",
        ]
    )

    # Sample data section
    print_section_header(
        "Sample Documents",
        "The following examples use a legal document (consultancy agreement) and a receipt (invoice).",
    )

    consultancy_agreement_path = Path(
        "scripts/example_input/free-consultancy-agreement.docx"
    )
    invoice_path = Path("scripts/example_input/S0305SampleInvoice.pdf")

    print(f"1. Consultancy Agreement: `{consultancy_agreement_path}`")
    print(f"2. Invoice PDF: `{invoice_path}`")

    # Initialize extractor
    extractor = Extractor.from_litellm(
        model="gpt-4o",
        api_base=os.getenv("OPENAI_BASE_URL"),
    )

    # Example 1: Extract Key Terms from a Legal Document
    q1 = "summarize the main terms and conditions of this consultancy agreement, focusing on the key obligations, deliverables, and payment terms."
    run_extraction_example(
        extractor=extractor,
        data_path=consultancy_agreement_path,
        title="Example 1: Extracting Key Terms from a Legal Agreement",
        description="This example demonstrates extracting key information from a DOCX file containing a consultancy agreement.",
        query=q1,
        code_lines=[
            "# Define the path to the document",
            f'agreement_path = Path("{consultancy_agreement_path}")',
            "\n# Define the extraction query",
            f'query = "{q1}"',
            "result = extractor.extract(agreement_path, query)",
            "\n# Access the extraction results",
            'print(f"Extracted {result.success_count} items with {result.success_rate:.1f}% success rate")',
            "print(result.data)",
        ],
    )

    # Example 2: Extract Details from an Invoice PDF
    q2 = "this is an invoice for professional services rendered, extract the professional name, service description, hourly rate and total amount."
    run_extraction_example(
        extractor=extractor,
        data_path=invoice_path,
        title="Example 2: Extracting Details from an Invoice PDF",
        description="This example showcases extracting structured data from a PDF invoice, including line items.",
        query=q2,
        code_lines=[
            "# Define the path to the PDF",
            f'invoice_path = Path("{invoice_path}")',
            "\n# Define the extraction query",
            f'query = "{q2}"',
            "result = extractor.extract(invoice_path, query)",
        ],
    )

    # Example 3: Schema Generation for Legal Clauses
    print_section_header(
        "Example 3: Preview Generated Schema for Legal Clauses",
        "This example shows how to generate and inspect a schema for extracting specific clauses from a legal document without performing a full extraction.",
    )

    q3 = "extract the confidentiality clause, including the definition of confidential information and the duration of the obligation."
    print_code_block(
        [
            "# Generate schema for a specific legal clause",
            f'query = "{q3}"',
            f'agreement_path = Path("{consultancy_agreement_path}")',
            "DataModel = extractor.get_schema(query=query, data=agreement_path)",
            "\n# Print schema",
            "print(DataModel.model_json_schema())",
        ]
    )

    DataModel = extractor.get_schema(query=q3, data=consultancy_agreement_path)

    print("\n### Token Usage for Schema Generation Process:")

    usage: UsageSummary = DataModel.usage.get_usage_summary()
    print(f"Total tokens used: {usage.total_tokens}")

    print("\nBreakdown by step:")
    for step in usage.steps:
        print(f"- {step.name}: {step.tokens} tokens\n")

    print("\n<details>")
    print("<summary>Generated Schema</summary>\n")
    print_json(DataModel.model_json_schema())
    print("\n</details>")

    # Restore stdout
    sys.stdout = sys.__stdout__

    # Write the captured output to README.md
    Path("docs/examples.md").write_text(output.getvalue(), encoding="utf-8")
    print(f"examples.md has been generated successfully!")


if __name__ == "__main__":
    main()
