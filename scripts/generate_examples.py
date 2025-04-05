import json
import os
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Dict, List

import pandas as pd

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

    print_token_usage(results.get_token_usage())

    # Display results - either as markdown table or JSON
    if hasattr(results.data, "to_markdown"):
        print(results.data.to_markdown(index=False))
    else:
        print_json([item.model_dump() for item in results.data])


def run_extraction_example(
    extractor: Extractor,
    df: pd.DataFrame,
    title: str,
    description: str,
    query: str,
    code_lines: List[str],
) -> ExtractionResult:
    """Run and document an extraction example."""
    print_section_header(title, description)
    print_code_block(code_lines)

    results = extractor.extract(df, query)
    print_extraction_results(results)

    # For complex examples that benefit from showing the model schema
    if (
        title != "Example 3: Complex Nested Extraction"
    ):  # Only show for simpler examples
        print("\n### Generated Model:")
        print(f"\nModel name: `{results.model.__name__}`")
        print_json(results.model.model_json_schema())

    return results


def main():
    # Redirect stdout to capture output
    output = StringIO()
    sys.stdout = output

    # Start generating the README content
    print("# Examples")
    print(
        "\nThis document contains examples of using the structx library for structured data extraction."
    )
    print(f"\n*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    # Setup section
    print_section_header("Setup")
    print_code_block(
        [
            "from structx import Extractor",
            "import pandas as pd",
            "import os",
            "\n# Initialize the extractor",
            "extractor = Extractor.from_litellm(",
            '    model="gpt-4o-mini",',
            '    api_key="your-api-key"',
            ")",
        ]
    )

    # Sample data section
    print_section_header(
        "Sample Data",
        "The following examples use this synthetic dataset of technical system logs:",
    )

    # Synthetic sample data - technical system logs
    sample_data = """
Log ID,Description
001,"System check on 2024-01-15 detected high CPU usage (92%) on server-01. Alert triggered at 14:30. Investigation revealed memory leak in application A. Patch applied on 2024-01-16 08:00, confirmed resolution at 09:15."
002,"Database backup failure occurred on 2024-01-20 03:00. Root cause: insufficient storage space. Emergency cleanup performed at 04:30. Backup reattempted successfully at 05:45. Added monitoring alert for storage capacity."
003,"Network connectivity drops reported on 2024-02-01 between 10:00-10:45. Affected: 3 application servers. Initial diagnosis at 10:15 identified router misconfiguration. Applied fix at 10:30, confirmed full restoration at 10:45."
004,"Two distinct performance issues on 2024-02-05: cache invalidation errors at 09:00 and slow query responses at 14:00. Cache system restarted at 09:30. Query optimization implemented at 15:00. Both issues resolved by EOD."
005,"Configuration update on 2024-02-10 09:00 caused unexpected API behavior. Detected through monitoring at 09:15. Immediate rollback initiated at 09:20. Root cause analysis completed at 11:00. New update scheduled with additional testing."
"""

    # Create DataFrame from sample data
    df = pd.read_csv(StringIO(sample_data))

    # Display sample data as markdown table
    print(df.to_markdown(index=False))
    print_code_block(
        ["# Create DataFrame from CSV data", "df = pd.read_csv(StringIO(sample_data))"]
    )

    # Initialize extractor
    extractor = Extractor.from_litellm(
        model="gpt-4o-mini",
        api_base=os.getenv("OPENAI_BASE_URL"),
        drop_params=True,
    )

    # Example 1: Extract incident timing
    q1 = "extract the main incident date and time, and any additional timestamps with their significance"
    run_extraction_example(
        extractor=extractor,
        df=df,
        title="Example 1: Extracting Incident Timing",
        description="In this example, we extract the main incident date and time, along with any additional timestamps and their significance.",
        query=q1,
        code_lines=[
            "# Extract incident timing",
            'query = "extract the main incident date and time, and any additional timestamps with their significance"',
            "result = extractor.extract(df, query)",
            "\n# Access the extraction results",
            'print(f"Extracted {result.success_count} items with {result.success_rate:.1f}% success rate")',
            "print(result.data)",
        ],
    )

    # Example 2: Extract technical details
    q2 = """
    extract incident information including:
    - system component affected
    - issue type
    - severity
    - resolution steps
    """
    run_extraction_example(
        extractor=extractor,
        df=df,
        title="Example 2: Extracting Technical Details",
        description="This example extracts more complex information about each incident including system components, issue types, severity, and resolution steps.",
        query=q2,
        code_lines=[
            "# Extract technical details",
            'query = """',
            "extract incident information including:",
            "- system component affected",
            "- issue type",
            "- severity",
            "- resolution steps",
            '"""',
            "result = extractor.extract(df, query)",
        ],
    )

    # Example 3: Complex nested extraction
    q3 = """
    extract structured information where:
    - each incident has a system component and timestamp
    - actions have timing and outcome
    - metrics include before and after values if available
    """
    results3 = run_extraction_example(
        extractor=extractor,
        df=df,
        title="Example 3: Complex Nested Extraction",
        description="This example demonstrates extracting complex nested structures with relationships between different elements.",
        query=q3,
        code_lines=[
            "# Extract complex nested structures",
            'query = """',
            "extract structured information where:",
            "- each incident has a system component and timestamp",
            "- actions have timing and outcome",
            "- metrics include before and after values if available",
            '"""',
            "result = extractor.extract(df, query)",
        ],
    )

    # Example 4: Preview schema
    print_section_header(
        "Example 4: Preview Generated Schema",
        "This example shows how to generate and inspect a schema without performing extraction.",
    )

    q4 = "extract system component, issue details, and resolution steps"
    print_code_block(
        [
            "# Generate schema without extraction",
            'query = "extract system component, issue details, and resolution steps"',
            'sample_text = df["Description"].iloc[0]',
            "DataModel = extractor.get_schema(query=query, sample_text=sample_text)",
            "\n# Print schema",
            "print(DataModel.model_json_schema())",
            "\n# Create an instance manually",
            "instance = DataModel(",
            '    system_component="API Server",',
            '    issue_details="High latency in requests",',
            '    resolution_steps="Scaled up server resources and optimized database queries"',
            ")",
            "print(instance.model_dump_json())",
        ]
    )

    DataModel = extractor.get_schema(query=q4, sample_text=df["Description"].iloc[0])

    print("\n### Token Usage for Schema Generation Process:")
    if hasattr(DataModel, "usage") and DataModel.usage:
        usage: UsageSummary = DataModel.usage.get_usage_summary()
        print(f"Total tokens used: {usage.total_tokens}")

        print("\nBreakdown by step:")
        for step in usage.steps:
            print(f"- {step.name}: {step.tokens} tokens\n")

    print("\n### Generated Schema:")
    print_json(DataModel.model_json_schema())

    # Restore stdout
    sys.stdout = sys.__stdout__

    # Write the captured output to README.md
    Path("docs/examples.md").write_text(output.getvalue(), encoding="utf-8")
    print(f"examples.md has been generated successfully!")


if __name__ == "__main__":
    main()
