import json
import os
import sys
from datetime import datetime
from io import StringIO

import pandas as pd

from structx import Extractor


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

    print("\n## Setup")
    print("\n```python")
    print("from structx import Extractor")
    print("import pandas as pd")
    print("import os")
    print("\n# Initialize the extractor")
    print("extractor = Extractor.from_litellm(")
    print('    model="gpt-4o-mini",')
    print('    api_key="your-api-key"')
    print(")")
    print("```")

    print("\n## Sample Data")
    print(
        "\nThe following examples use this synthetic dataset of technical system logs:"
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

    print("\n```python")
    print("# Create DataFrame from CSV data")
    print("df = pd.read_csv(StringIO(sample_data))")
    print("```")

    # Initialize extractor
    extractor = Extractor.from_litellm(
        model="gpt-4o-mini", api_base=os.getenv("OPENAI_BASE_URL")
    )

    # Example 1: Extract incident timing
    print("\n## Example 1: Extracting Incident Timing")
    print(
        "\nIn this example, we extract the main incident date and time, along with any additional timestamps and their significance."
    )

    q1 = "extract the main incident date and time, and any additional timestamps with their significance"

    print("\n```python")
    print("# Extract incident timing")
    print(
        'query = "extract the main incident date and time, and any additional timestamps with their significance"'
    )
    print("result = extractor.extract(df, query)")
    print("\n# Access the extraction results")
    print(
        'print(f"Extracted {result.success_count} items with {result.success_rate:.1f}% success rate")'
    )
    print("print(result.data)")
    print("```")

    results1 = extractor.extract(df, q1)

    print("\n### Results:")
    print(
        f"\nExtracted {results1.success_count} items with {results1.success_rate:.1f}% success rate"
    )

    # Convert extracted data to DataFrame and display as markdown table
    if hasattr(results1.data, "to_markdown"):
        # If already a DataFrame
        print(results1.data.to_markdown(index=False))
    else:
        # display as JSON

        print("\n```json")
        print(
            json.dumps(
                [item.model_dump() for item in results1.data], indent=2, default=str
            )
        )
        print("```")

    print("\n### Generated Model:")
    print(f"\nModel name: `{results1.model.__name__}`")
    print("\n```json")
    print(json.dumps(results1.model.model_json_schema(), indent=2))
    print("```")

    # Example 2: Extract technical details
    print("\n## Example 2: Extracting Technical Details")
    print(
        "\nThis example extracts more complex information about each incident including system components, issue types, severity, and resolution steps."
    )

    q2 = """
    extract incident information including:
    - system component affected
    - issue type
    - severity
    - resolution steps
    """

    print("\n```python")
    print("# Extract technical details")
    print('query = """')
    print("extract incident information including:")
    print("- system component affected")
    print("- issue type")
    print("- severity")
    print("- resolution steps")
    print('"""')
    print("result = extractor.extract(df, query)")
    print("```")

    results2 = extractor.extract(df, q2)

    print("\n### Results:")
    print(
        f"\nExtracted {results2.success_count} items with {results2.success_rate:.1f}% success rate"
    )

    # Convert extracted data to DataFrame and display as markdown table
    if hasattr(results2.data, "to_markdown"):
        print(results2.data.to_markdown(index=False))
    else:
        # display as JSON
        print("\n```json")
        print(
            json.dumps(
                [item.model_dump() for item in results2.data], indent=2, default=str
            )
        )
        print("```")

    # Example 3: Complex nested extraction
    print("\n## Example 3: Complex Nested Extraction")
    print(
        "\nThis example demonstrates extracting complex nested structures with relationships between different elements."
    )

    q3 = """
    extract structured information where:
    - each incident has a system component and timestamp
    - actions have timing and outcome
    - metrics include before and after values if available
    """

    print("\n```python")
    print("# Extract complex nested structures")
    print('query = """')
    print("extract structured information where:")
    print("- each incident has a system component and timestamp")
    print("- actions have timing and outcome")
    print("- metrics include before and after values if available")
    print('"""')
    print("result = extractor.extract(df, query)")
    print("```")

    results3 = extractor.extract(df, q3)

    print("\n### Results:")
    print(
        f"\nExtracted {results3.success_count} items with {results3.success_rate:.1f}% success rate"
    )

    # For complex nested structures, JSON might be more readable
    print("\n```json")
    print(
        json.dumps([item.model_dump() for item in results3.data], indent=2, default=str)
    )
    print("```")

    # Example 4: Preview schema
    print("\n## Example 4: Preview Generated Schema")
    print(
        "\nThis example shows how to generate and inspect a schema without performing extraction."
    )

    q4 = "extract system component, issue details, and resolution steps"

    print("\n```python")
    print("# Generate schema without extraction")
    print('query = "extract system component, issue details, and resolution steps"')
    print('sample_text = df["Description"].iloc[0]')
    print("DataModel = extractor.get_schema(query=query, sample_text=sample_text)")
    print("\n# Print schema")
    print("print(DataModel.model_json_schema())")
    print("\n# Create an instance manually")
    print("instance = DataModel(")
    print('    system_component="API Server",')
    print('    issue_details="High latency in requests",')
    print(
        '    resolution_steps="Scaled up server resources and optimized database queries"'
    )
    print(")")
    print("print(instance.model_dump_json())")
    print("```")

    DataModel = extractor.get_schema(query=q4, sample_text=df["Description"].iloc[0])

    print("\n### Generated Schema:")
    print("\n```json")
    print(json.dumps(DataModel.model_json_schema(), indent=2))
    print("```")

    # Restore stdout
    sys.stdout = sys.__stdout__

    # Write the captured output to README.md
    with open("docs/examples.md", "w") as f:
        f.write(output.getvalue())

    print(f"Examples README.md has been generated successfully!")


if __name__ == "__main__":
    main()
