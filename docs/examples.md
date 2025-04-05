# Examples

This document contains examples of using the structx library for structured data extraction.

*Generated on: 2025-04-04 19:46:09*

## Setup

```python
from structx import Extractor
import pandas as pd
import os

# Initialize the extractor
extractor = Extractor.from_litellm(
    model="gpt-4o-mini",
    api_key="your-api-key"
)
```

## Sample Data

The following examples use this synthetic dataset of technical system logs:
|   Log ID | Description                                                                                                                                                                                                                                 |
|---------:|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|        1 | System check on 2024-01-15 detected high CPU usage (92%) on server-01. Alert triggered at 14:30. Investigation revealed memory leak in application A. Patch applied on 2024-01-16 08:00, confirmed resolution at 09:15.                     |
|        2 | Database backup failure occurred on 2024-01-20 03:00. Root cause: insufficient storage space. Emergency cleanup performed at 04:30. Backup reattempted successfully at 05:45. Added monitoring alert for storage capacity.                  |
|        3 | Network connectivity drops reported on 2024-02-01 between 10:00-10:45. Affected: 3 application servers. Initial diagnosis at 10:15 identified router misconfiguration. Applied fix at 10:30, confirmed full restoration at 10:45.           |
|        4 | Two distinct performance issues on 2024-02-05: cache invalidation errors at 09:00 and slow query responses at 14:00. Cache system restarted at 09:30. Query optimization implemented at 15:00. Both issues resolved by EOD.                 |
|        5 | Configuration update on 2024-02-10 09:00 caused unexpected API behavior. Detected through monitoring at 09:15. Immediate rollback initiated at 09:20. Root cause analysis completed at 11:00. New update scheduled with additional testing. |

```python
# Create DataFrame from CSV data
df = pd.read_csv(StringIO(sample_data))
```

## Example 1: Extracting Incident Timing

In this example, we extract the main incident date and time, along with any additional timestamps and their significance.

```python
# Extract incident timing
query = "extract the main incident date and time, and any additional timestamps with their significance"
result = extractor.extract(df, query)

# Access the extraction results
print(f"Extracted {result.success_count} items with {result.success_rate:.1f}% success rate")
print(result.data)
```

### Results:

Extracted 5 items with 100.0% success rate

### Token Usage:
Total tokens used: 4929
Tokens by step:
- analysis: 197 tokens

- refinement: 320 tokens

- schema_generation: 587 tokens

- guide: 329 tokens

- extraction: 3496 tokens


```json
[
  {
    "main_incident_date_time": "2024-02-10 09:00:00",
    "additional_timestamps": [
      {
        "timestamp": "2024-02-10 09:15:00",
        "significance": "detected through monitoring"
      },
      {
        "timestamp": "2024-02-10 09:20:00",
        "significance": "immediate rollback initiated"
      },
      {
        "timestamp": "2024-02-10 11:00:00",
        "significance": "root cause analysis completed"
      }
    ]
  },
  {
    "main_incident_date_time": "2024-01-15 00:00:00",
    "additional_timestamps": [
      {
        "timestamp": "2024-01-15 14:30:00",
        "significance": "alert triggered"
      },
      {
        "timestamp": "2024-01-16 08:00:00",
        "significance": "patch applied"
      },
      {
        "timestamp": "2024-01-16 09:15:00",
        "significance": "confirmed resolution"
      }
    ]
  },
  {
    "main_incident_date_time": "2024-02-01 10:00:00",
    "additional_timestamps": [
      {
        "timestamp": "2024-02-01 10:15:00",
        "significance": "initial diagnosis"
      },
      {
        "timestamp": "2024-02-01 10:30:00",
        "significance": "applied fix"
      },
      {
        "timestamp": "2024-02-01 10:45:00",
        "significance": "confirmed full restoration"
      }
    ]
  },
  {
    "main_incident_date_time": "2024-01-20 03:00:00",
    "additional_timestamps": [
      {
        "timestamp": "2024-01-20 04:30:00",
        "significance": "emergency cleanup performed"
      },
      {
        "timestamp": "2024-01-20 05:45:00",
        "significance": "backup reattempted successfully"
      }
    ]
  },
  {
    "main_incident_date_time": "2024-02-05 00:00:00",
    "additional_timestamps": [
      {
        "timestamp": "2024-02-05 09:00:00",
        "significance": "cache invalidation errors"
      },
      {
        "timestamp": "2024-02-05 14:00:00",
        "significance": "slow query responses"
      },
      {
        "timestamp": "2024-02-05 09:30:00",
        "significance": "cache system restarted"
      },
      {
        "timestamp": "2024-02-05 15:00:00",
        "significance": "query optimization implemented"
      },
      {
        "timestamp": "2024-02-05 23:59:59",
        "significance": "both issues resolved by EOD"
      }
    ]
  }
]
```

### Generated Model:

Model name: `IncidentTimestamp`

```json
{
  "$defs": {
    "IncidentTimestampadditional_timestampsItem": {
      "description": "An array of objects containing additional timestamps and their significance.",
      "properties": {
        "timestamp": {
          "anyOf": [
            {
              "format": "date-time",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The specific date and time of the additional event.",
          "title": "Timestamp"
        },
        "significance": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Description of the significance of the timestamp (e.g., creation time, update time, resolution time).",
          "title": "Significance"
        }
      },
      "title": "IncidentTimestampadditional_timestampsItem",
      "type": "object"
    }
  },
  "description": "Schema for extracting incident date and time information along with additional timestamps and their significance.",
  "properties": {
    "main_incident_date_time": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "The main date and time of the incident, clearly identified.",
      "title": "Main Incident Date Time"
    },
    "additional_timestamps": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/IncidentTimestampadditional_timestampsItem"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "An array of objects containing additional timestamps and their significance.",
      "title": "Additional Timestamps"
    }
  },
  "title": "IncidentTimestamp",
  "type": "object"
}
```

## Example 2: Extracting Technical Details

This example extracts more complex information about each incident including system components, issue types, severity, and resolution steps.

```python
# Extract technical details
query = """
extract incident information including:
- system component affected
- issue type
- severity
- resolution steps
"""
result = extractor.extract(df, query)
```

[1;31mGive Feedback / Get Help: https://github.com/BerriAI/litellm/issues/new[0m
LiteLLM.Info: If you need to debug this error, use `litellm._turn_on_debug()'.


[1;31mGive Feedback / Get Help: https://github.com/BerriAI/litellm/issues/new[0m
LiteLLM.Info: If you need to debug this error, use `litellm._turn_on_debug()'.


[1;31mGive Feedback / Get Help: https://github.com/BerriAI/litellm/issues/new[0m
LiteLLM.Info: If you need to debug this error, use `litellm._turn_on_debug()'.


### Results:

Extracted 4 items with 80.0% success rate

### Token Usage:
Total tokens used: 12939
Tokens by step:
- analysis: 209 tokens

- refinement: 347 tokens

- schema_generation: 640 tokens

- guide: 323 tokens

- extraction: 11420 tokens


```json
[
  {
    "incidents": [
      {
        "system_component_affected": "API",
        "issue_type": "Unexpected behavior",
        "severity": "High",
        "resolution_steps": [
          {
            "step": "Detected through monitoring"
          },
          {
            "step": "Immediate rollback initiated"
          },
          {
            "step": "Root cause analysis completed"
          },
          {
            "step": "New update scheduled with additional testing"
          }
        ]
      }
    ]
  },
  {
    "incidents": [
      {
        "system_component_affected": "Database",
        "issue_type": "Backup Failure",
        "severity": "Critical",
        "resolution_steps": [
          {
            "step": "Identified root cause: insufficient storage space"
          },
          {
            "step": "Performed emergency cleanup"
          },
          {
            "step": "Reattempted backup successfully"
          },
          {
            "step": "Added monitoring alert for storage capacity"
          }
        ]
      }
    ]
  },
  {
    "incidents": [
      {
        "system_component_affected": "application servers",
        "issue_type": "network connectivity drop",
        "severity": "high",
        "resolution_steps": [
          {
            "step": "Initial diagnosis at 10:15 identified router misconfiguration"
          },
          {
            "step": "Applied fix at 10:30"
          },
          {
            "step": "Confirmed full restoration at 10:45"
          }
        ]
      }
    ]
  },
  {
    "incidents": [
      {
        "system_component_affected": "server-01",
        "issue_type": "high CPU usage",
        "severity": "high",
        "resolution_steps": [
          {
            "step": "Investigated the issue"
          },
          {
            "step": "Identified memory leak in application A"
          },
          {
            "step": "Applied patch"
          }
        ]
      }
    ]
  }
]
```

## Example 3: Complex Nested Extraction

This example demonstrates extracting complex nested structures with relationships between different elements.

```python
# Extract complex nested structures
query = """
extract structured information where:
- each incident has a system component and timestamp
- actions have timing and outcome
- metrics include before and after values if available
"""
result = extractor.extract(df, query)
```

### Results:

Extracted 8 items with 100.0% success rate

### Token Usage:
Total tokens used: 9611
Tokens by step:
- analysis: 213 tokens

- refinement: 330 tokens

- schema_generation: 857 tokens

- guide: 442 tokens

- extraction: 7769 tokens


```json
[
  {
    "incident": {
      "system_component": "API",
      "timestamp": "2024-02-10T09:15:00",
      "cpu_usage": null,
      "alert_triggered_at": null,
      "investigation_details": null
    },
    "action": {
      "timing": "2024-02-10T09:20:00",
      "outcome": "Rollback initiated"
    },
    "metric": {
      "before_value": null,
      "after_value": null
    }
  },
  {
    "incident": {
      "system_component": "API",
      "timestamp": "2024-02-10T11:00:00",
      "cpu_usage": null,
      "alert_triggered_at": null,
      "investigation_details": null
    },
    "action": {
      "timing": "2024-02-10T11:00:00",
      "outcome": "Root cause analysis completed"
    },
    "metric": {
      "before_value": null,
      "after_value": null
    }
  },
  {
    "incident": {
      "system_component": "Cache System",
      "timestamp": "2024-02-05T09:00:00",
      "cpu_usage": null,
      "alert_triggered_at": null,
      "investigation_details": null
    },
    "action": {
      "timing": "2024-02-05T09:30:00",
      "outcome": "Cache system restarted"
    },
    "metric": {
      "before_value": null,
      "after_value": null
    }
  },
  {
    "incident": {
      "system_component": "Database Query",
      "timestamp": "2024-02-05T14:00:00",
      "cpu_usage": null,
      "alert_triggered_at": null,
      "investigation_details": null
    },
    "action": {
      "timing": "2024-02-05T15:00:00",
      "outcome": "Query optimization implemented"
    },
    "metric": {
      "before_value": null,
      "after_value": null
    }
  },
  {
    "incident": {
      "system_component": "server-01",
      "timestamp": "2024-01-15T14:30:00",
      "cpu_usage": 92.0,
      "alert_triggered_at": "2024-01-15T14:30:00",
      "investigation_details": {
        "issue_found": null,
        "resolution_timestamp": null,
        "confirmation_timestamp": null
      }
    },
    "action": {
      "timing": "2024-01-16T08:00:00",
      "outcome": "confirmed resolution at 09:15"
    },
    "metric": {
      "before_value": 92.0,
      "after_value": null
    }
  },
  {
    "incident": {
      "system_component": "application servers",
      "timestamp": "2024-02-01T10:00:00",
      "cpu_usage": null,
      "alert_triggered_at": null,
      "investigation_details": null
    },
    "action": {
      "timing": "2024-02-01T10:30:00",
      "outcome": "full restoration confirmed"
    },
    "metric": {
      "before_value": 0.0,
      "after_value": 1.0
    }
  },
  {
    "incident": {
      "system_component": "Database",
      "timestamp": "2024-01-20T03:00:00",
      "cpu_usage": null,
      "alert_triggered_at": null,
      "investigation_details": {
        "issue_found": null,
        "resolution_timestamp": null,
        "confirmation_timestamp": null
      }
    },
    "action": {
      "timing": "2024-01-20T04:30:00",
      "outcome": "Emergency cleanup performed"
    },
    "metric": {
      "before_value": 0.0,
      "after_value": 1.0
    }
  },
  {
    "incident": {
      "system_component": "Database",
      "timestamp": "2024-01-20T05:45:00",
      "cpu_usage": null,
      "alert_triggered_at": null,
      "investigation_details": {
        "issue_found": null,
        "resolution_timestamp": null,
        "confirmation_timestamp": null
      }
    },
    "action": {
      "timing": "2024-01-20T05:45:00",
      "outcome": "Backup reattempted successfully"
    },
    "metric": {
      "before_value": 1.0,
      "after_value": 2.0
    }
  }
]
```

## Example 4: Preview Generated Schema

This example shows how to generate and inspect a schema without performing extraction.

```python
# Generate schema without extraction
query = "extract system component, issue details, and resolution steps"
sample_text = df["Description"].iloc[0]
DataModel = extractor.get_schema(query=query, sample_text=sample_text)

# Print schema
print(DataModel.model_json_schema())

# Create an instance manually
instance = DataModel(
    system_component="API Server",
    issue_details="High latency in requests",
    resolution_steps="Scaled up server resources and optimized database queries"
)
print(instance.model_dump_json())
```

### Token Usage for Schema Generation Process:
Total tokens used: 4479

Breakdown by step:
- analysis: 0 tokens

- refinement: 327 tokens

- schema_generation: 2023 tokens

- guide: 2129 tokens

- extraction: 0 tokens


### Generated Schema:

```json
{
  "$defs": {
    "SystemComponentIssueResolutionissue": {
      "description": "Details about the issue associated with the system component.",
      "properties": {
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Description of the issue.",
          "title": "Description"
        },
        "severity_level": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Severity level of the issue.",
          "title": "Severity Level"
        },
        "timestamp": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Timestamp of when the issue was detected.",
          "format": "ISO 8601",
          "title": "Timestamp",
          "type": "string"
        }
      },
      "title": "SystemComponentIssueResolutionissue",
      "type": "object"
    },
    "SystemComponentIssueResolutionresolution_stepsItem": {
      "description": "Steps taken to resolve the issue.",
      "properties": {
        "step": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Description of the resolution step.",
          "title": "Step"
        },
        "effectiveness": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Effectiveness of the resolution step.",
          "title": "Effectiveness"
        },
        "time_taken": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Time taken to implement the resolution step.",
          "format": "ISO 8601 duration",
          "title": "Time Taken",
          "type": "string"
        }
      },
      "title": "SystemComponentIssueResolutionresolution_stepsItem",
      "type": "object"
    },
    "SystemComponentIssueResolutionsystem_component": {
      "description": "Details about the system component.",
      "properties": {
        "name": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Name of the system component.",
          "title": "Name"
        },
        "type": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Type of the system component.",
          "title": "Type"
        },
        "specifications": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Specifications of the system component.",
          "title": "Specifications"
        }
      },
      "title": "SystemComponentIssueResolutionsystem_component",
      "type": "object"
    }
  },
  "description": "Schema for extracting details about system components, associated issues, and resolution steps.",
  "properties": {
    "system_component": {
      "anyOf": [
        {
          "$ref": "#/$defs/SystemComponentIssueResolutionsystem_component"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Details about the system component."
    },
    "issue": {
      "anyOf": [
        {
          "$ref": "#/$defs/SystemComponentIssueResolutionissue"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Details about the issue associated with the system component."
    },
    "resolution_steps": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/SystemComponentIssueResolutionresolution_stepsItem"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Steps taken to resolve the issue.",
      "title": "Resolution Steps"
    }
  },
  "title": "SystemComponentIssueResolution",
  "type": "object"
}
```
