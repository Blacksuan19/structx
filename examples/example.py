import json
import os
from io import StringIO

import pandas as pd

from structx import Extractor

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


extractor = Extractor.from_litellm(
    model="gpt-4o-mini", api_base=os.getenv("OPENAI_BASE_URL")
)  # or your specific model name


# Example 1: Extract incident timing
print("\nExample 1: Extracting incident timing")
print("-" * 50)

results1, failed1 = extractor.extract(
    df,
    "extract the main incident date and time, and any additional timestamps with their significance",
)


print("\nResults:")
print(json.dumps([item.model_dump() for item in results1], indent=2, default=str))


# Example 2: Extract technical details
print("\nExample 2: Extracting technical details")
print("-" * 50)

results2, failed2 = extractor.extract(
    df,
    """
    extract incident information including:
    - system component affected
    - issue type
    - severity
    - resolution steps
    """,
)

print("\nResults:")
print(json.dumps([item.model_dump() for item in results2], indent=2, default=str))

# Example 3: Complex nested extraction
print("\nExample 3: Complex nested extraction")
print("-" * 50)

results3, failed3 = extractor.extract(
    df,
    """
    extract structured information where:
    - each incident has a system component and timestamp
    - actions have timing and outcome
    - metrics include before and after values if available
    """,
)

print("\nResults:")
print(json.dumps([item.model_dump() for item in results3], indent=2, default=str))

# Example 4: Preview schema
print("\nExample 4: Preview generated schema")
print("-" * 50)

schema = extractor.get_schema(
    query="extract system component, issue details, and resolution steps",
    sample_text=df["Description"].iloc[0],
)

print("\nGenerated Schema:")
print(json.dumps(schema, indent=2, default=str))
