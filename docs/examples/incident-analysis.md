# Incident Analysis

This example demonstrates how to use `structx` to analyze incident reports.

## Setup

```python
from structx import Extractor
import pandas as pd

# Initialize extractor
extractor = Extractor.from_litellm(
    model="gpt-4o-mini",
    api_key="your-api-key"
)

# Sample data
data = [
    {"description": "System check on 2024-01-15 detected high CPU usage (92%) on server-01. Alert triggered at 14:30. Investigation revealed memory leak in application A. Patch applied on 2024-01-16 08:00, confirmed resolution at 09:15."},
    {"description": "Database backup failure occurred on 2024-01-20 03:00. Root cause: insufficient storage space. Emergency cleanup performed at 04:30. Backup reattempted successfully at 05:45. Added monitoring alert for storage capacity."},
    {"description": "Network connectivity drops reported on 2024-02-01 between 10:00-10:45. Affected: 3 application servers. Initial diagnosis at 10:15 identified router misconfiguration. Applied fix at 10:30, confirmed full restoration at 10:45."}
]

df = pd.DataFrame(data)
```

## Basic Incident Information

```python
result = extractor.extract(
    data=df,
    query="""
    extract incident information including:
    - date and time of occurrence
    - affected system
    - issue type
    - resolution time
    """
)

print(f"Extracted {result.success_count} incidents")
for item in result.data:
    print(f"Incident: {item.date_and_time_of_occurrence}")
    print(f"System: {item.affected_system}")
    print(f"Issue: {item.issue_type}")
    print(f"Resolution: {item.resolution_time}")
    print()
```

## Timeline Analysis

```python
result = extractor.extract(
    data=df,
    query="""
    extract incident timeline including:
    - incident start time
    - detection time
    - investigation time
    - resolution time
    - total downtime
    """
)

# Convert to DataFrame for analysis
timeline_df = pd.DataFrame([item.model_dump() for item in result.data])

# Calculate average response times
avg_detection = (pd.to_datetime(timeline_df['detection_time']) -
                pd.to_datetime(timeline_df['incident_start_time'])).mean()
avg_resolution = (pd.to_datetime(timeline_df['resolution_time']) -
                 pd.to_datetime(timeline_df['detection_time'])).mean()

print(f"Average detection time: {avg_detection}")
print(f"Average resolution time: {avg_resolution}")
```

## Root Cause Analysis

```python
result = extractor.extract(
    data=df,
    query="""
    extract root cause information including:
    - primary cause
    - contributing factors
    - preventive measures
    """
)

# Analyze common causes
from collections import Counter

causes = [item.primary_cause for item in result.data]
common_causes = Counter(causes)

print("Common root causes:")
for cause, count in common_causes.most_common():
    print(f"- {cause}: {count}")
```

## Multiple Analysis Aspects

```python
queries = [
    "extract temporal information (dates, times, durations)",
    "extract technical details (systems, components, metrics)",
    "extract impact information (severity, affected users, business impact)"
]

results = extractor.extract_queries(
    data=df,
    queries=queries
)

# Access results by query
for query, result in results.items():
    print(f"\nResults for: {query}")
    print(f"Extracted {result.success_count} items")

    # Convert to DataFrame for this aspect
    aspect_df = pd.DataFrame([item.model_dump() for item in result.data])
    print(aspect_df.head())
```

## Complete Analysis Script

```python
def analyze_incidents(file_path):
    """Comprehensive incident analysis"""
    # Load data
    df = pd.read_csv(file_path)

    # Extract basic information
    basic_info = extractor.extract(
        data=df,
        query="extract incident date, system, and issue type"
    )

    # Extract timeline
    timeline = extractor.extract(
        data=df,
        query="extract incident start, detection, and resolution times"
    )

    # Extract root causes
    root_causes = extractor.extract(
        data=df,
        query="extract root cause and contributing factors"
    )

    # Extract impact
    impact = extractor.extract(
        data=df,
        query="extract severity, affected users, and business impact"
    )

    # Combine results
    results = {
        "basic_info": basic_info,
        "timeline": timeline,
        "root_causes": root_causes,
        "impact": impact
    }

    return results

# Run the analysis
analysis = analyze_incidents("incidents.csv")

# Generate report
for aspect, result in analysis.items():
    print(f"\n== {aspect.upper()} ==")
    print(f"Extracted {result.success_count} items")

    # Show sample data
    if isinstance(result.data, pd.DataFrame):
        print(result.data.head())
    else:
        for i, item in enumerate(result.data[:3]):
            print(f"\nItem {i+1}:")
            print(item.model_dump_json(indent=2))
```
