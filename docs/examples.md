# Examples

This document contains examples of using the structx library for structured data extraction.

*Generated on: 2025-04-05 14:35:43*

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
Total tokens used: 4867
Tokens by step:
- analysis: 197 tokens

- refinement: 303 tokens

- schema_generation: 559 tokens

- guide: 336 tokens

- extraction: 3472 tokens


```json
[
  {
    "main_incident_datetime": "2024-01-20 03:00:00",
    "additional_timestamps": [
      {
        "timestamp": "2024-01-20 04:30:00",
        "significance": "Emergency cleanup performed due to insufficient storage space."
      },
      {
        "timestamp": "2024-01-20 05:45:00",
        "significance": "Backup reattempted successfully after cleanup."
      }
    ]
  },
  {
    "main_incident_datetime": "2024-01-15 14:30:00",
    "additional_timestamps": [
      {
        "timestamp": "2024-01-16 08:00:00",
        "significance": "Patch applied to resolve the memory leak."
      },
      {
        "timestamp": "2024-01-16 09:15:00",
        "significance": "Resolution confirmed after patch application."
      }
    ]
  },
  {
    "main_incident_datetime": "2024-02-05 09:00:00",
    "additional_timestamps": [
      {
        "timestamp": "2024-02-05 09:30:00",
        "significance": "Cache system restarted"
      },
      {
        "timestamp": "2024-02-05 14:00:00",
        "significance": "Slow query responses observed"
      },
      {
        "timestamp": "2024-02-05 15:00:00",
        "significance": "Query optimization implemented"
      }
    ]
  },
  {
    "main_incident_datetime": "2024-02-01 10:00:00",
    "additional_timestamps": [
      {
        "timestamp": "2024-02-01 10:15:00",
        "significance": "Initial diagnosis identified router misconfiguration."
      },
      {
        "timestamp": "2024-02-01 10:30:00",
        "significance": "Applied fix to the router."
      },
      {
        "timestamp": "2024-02-01 10:45:00",
        "significance": "Confirmed full restoration of network connectivity."
      }
    ]
  },
  {
    "main_incident_datetime": "2024-02-10 09:00:00",
    "additional_timestamps": [
      {
        "timestamp": "2024-02-10 09:15:00",
        "significance": "Detected unexpected API behavior through monitoring."
      },
      {
        "timestamp": "2024-02-10 09:20:00",
        "significance": "Immediate rollback initiated."
      },
      {
        "timestamp": "2024-02-10 11:00:00",
        "significance": "Root cause analysis completed."
      }
    ]
  }
]
```

### Generated Model:

Model name: `IncidentTimestampExtraction`

```json
{
  "$defs": {
    "IncidentTimestampExtractionadditional_timestampsItem": {
      "description": "A collection of additional timestamps related to the incident, each with its significance.",
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
          "description": "The context or significance of the additional timestamp.",
          "title": "Significance"
        }
      },
      "title": "IncidentTimestampExtractionadditional_timestampsItem",
      "type": "object"
    }
  },
  "description": "Schema for extracting incident timestamps and their significance from reports.",
  "properties": {
    "main_incident_datetime": {
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
      "title": "Main Incident Datetime"
    },
    "additional_timestamps": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/IncidentTimestampExtractionadditional_timestampsItem"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "A collection of additional timestamps related to the incident, each with its significance.",
      "title": "Additional Timestamps"
    }
  },
  "title": "IncidentTimestampExtraction",
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

### Results:

Extracted 5 items with 100.0% success rate

### Token Usage:
Total tokens used: 16260
Tokens by step:
- analysis: 209 tokens

- refinement: 346 tokens

- schema_generation: 644 tokens

- guide: 355 tokens

- extraction: 14706 tokens


```json
[
  {
    "incidents": [
      {
        "system_component_affected": "Database",
        "issue_type": "Backup Failure",
        "severity": "high",
        "resolution_steps": [
          {
            "step": "Emergency cleanup performed"
          },
          {
            "step": "Backup reattempted successfully"
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
        "system_component_affected": "API",
        "issue_type": "Unexpected behavior",
        "severity": "high",
        "resolution_steps": [
          {
            "step": "Rollback initiated"
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
        "system_component_affected": "server-01",
        "issue_type": "high CPU usage",
        "severity": "high",
        "resolution_steps": [
          {
            "step": "Investigated high CPU usage"
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
  },
  {
    "incidents": [
      {
        "system_component_affected": "3 application servers",
        "issue_type": "Network connectivity drops",
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
        "system_component_affected": "Cache System",
        "issue_type": "Cache Invalidation Error",
        "severity": "high",
        "resolution_steps": [
          {
            "step": "Cache system restarted at 09:30"
          },
          {
            "step": "Issue resolved by EOD"
          }
        ]
      },
      {
        "system_component_affected": "Database",
        "issue_type": "Slow Query Response",
        "severity": "medium",
        "resolution_steps": [
          {
            "step": "Query optimization implemented at 15:00"
          },
          {
            "step": "Issue resolved by EOD"
          }
        ]
      }
    ]
  }
]
```

### Generated Model:

Model name: `IncidentReport`

```json
{
  "$defs": {
    "IncidentReportincidentsItem": {
      "description": "List of incidents reported.",
      "properties": {
        "system_component_affected": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The system component that was affected by the incident.",
          "title": "System Component Affected"
        },
        "issue_type": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The type of issue encountered.",
          "title": "Issue Type"
        },
        "severity": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The severity level of the incident (e.g., low, medium, high).",
          "title": "Severity"
        },
        "resolution_steps": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/incidentsItemresolution_stepsItem"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Steps taken to resolve the incident.",
          "title": "Resolution Steps"
        }
      },
      "title": "IncidentReportincidentsItem",
      "type": "object"
    },
    "incidentsItemresolution_stepsItem": {
      "description": "Steps taken to resolve the incident.",
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
          "description": "A specific step taken to resolve the incident.",
          "title": "Step"
        }
      },
      "title": "incidentsItemresolution_stepsItem",
      "type": "object"
    }
  },
  "description": "Schema for extracting structured incident information including system components, issue types, severity, and resolution steps.",
  "properties": {
    "incidents": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/IncidentReportincidentsItem"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "List of incidents reported.",
      "title": "Incidents"
    }
  },
  "title": "IncidentReport",
  "type": "object"
}
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

Extracted 6 items with 100.0% success rate

### Token Usage:
Total tokens used: 5873
Tokens by step:
- analysis: 213 tokens

- refinement: 345 tokens

- schema_generation: 679 tokens

- guide: 340 tokens

- extraction: 4296 tokens


```json
[
  {
    "incidents": [
      {
        "system_component": "Database",
        "timestamp": "2024-01-20 03:00:00"
      }
    ],
    "actions": [
      {
        "timing": "2024-01-20 04:30:00",
        "outcome": "Emergency cleanup performed"
      },
      {
        "timing": "2024-01-20 05:45:00",
        "outcome": "Backup reattempted successfully"
      },
      {
        "timing": "2024-01-20 05:45:00",
        "outcome": "Added monitoring alert for storage capacity"
      }
    ],
    "metrics": [
      {
        "before_value": 0.0,
        "after_value": 1.0
      },
      {
        "before_value": 0.0,
        "after_value": 1.0
      },
      {
        "before_value": 0.0,
        "after_value": 1.0
      }
    ]
  },
  {
    "incidents": [
      {
        "system_component": "server-01",
        "timestamp": "2024-01-15 14:30:00"
      }
    ],
    "actions": [
      {
        "timing": "2024-01-16 08:00:00",
        "outcome": "Patch applied"
      },
      {
        "timing": "2024-01-16 09:15:00",
        "outcome": "Confirmed resolution"
      }
    ],
    "metrics": [
      {
        "before_value": 92.0,
        "after_value": null
      }
    ]
  },
  {
    "incidents": [
      {
        "system_component": "cache",
        "timestamp": "2024-02-05 09:00:00"
      }
    ],
    "actions": [
      {
        "timing": "2024-02-05 09:30:00",
        "outcome": "Cache system restarted"
      }
    ],
    "metrics": [
      {
        "before_value": null,
        "after_value": null
      }
    ]
  },
  {
    "incidents": [
      {
        "system_component": "query",
        "timestamp": "2024-02-05 14:00:00"
      }
    ],
    "actions": [
      {
        "timing": "2024-02-05 15:00:00",
        "outcome": "Query optimization implemented"
      }
    ],
    "metrics": [
      {
        "before_value": null,
        "after_value": null
      }
    ]
  },
  {
    "incidents": [
      {
        "system_component": "API",
        "timestamp": "2024-02-10 09:15:00"
      }
    ],
    "actions": [
      {
        "timing": "2024-02-10 09:20:00",
        "outcome": "Rollback initiated"
      },
      {
        "timing": "2024-02-10 11:00:00",
        "outcome": "Root cause analysis completed"
      }
    ],
    "metrics": [
      {
        "before_value": 1.0,
        "after_value": 0.0
      }
    ]
  },
  {
    "incidents": [
      {
        "system_component": "application servers",
        "timestamp": "2024-02-01 10:00:00"
      }
    ],
    "actions": [
      {
        "timing": "2024-02-01 10:15:00",
        "outcome": "initial diagnosis identified router misconfiguration"
      },
      {
        "timing": "2024-02-01 10:30:00",
        "outcome": "applied fix"
      },
      {
        "timing": "2024-02-01 10:45:00",
        "outcome": "confirmed full restoration"
      }
    ],
    "metrics": [
      {
        "before_value": null,
        "after_value": null
      },
      {
        "before_value": null,
        "after_value": null
      },
      {
        "before_value": null,
        "after_value": null
      }
    ]
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
Total tokens used: 3209

Breakdown by step:
- analysis: 0 tokens

- refinement: 326 tokens

- schema_generation: 748 tokens

- guide: 2135 tokens

- extraction: 0 tokens


### Generated Schema:

```json
{
  "$defs": {
    "SystemComponentIssueResolutionissue": {
      "description": "Details about the issue related to the system component.",
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
          "description": "Timestamp of when the issue was detected, in ISO 8601 format.",
          "title": "Timestamp"
        }
      },
      "title": "SystemComponentIssueResolutionissue",
      "type": "object"
    },
    "SystemComponentIssueResolutionresolution": {
      "description": "Details about the resolution of the issue.",
      "properties": {
        "action_taken": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Action taken to resolve the issue.",
          "title": "Action Taken"
        },
        "responsible_personnel": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Personnel responsible for the resolution.",
          "title": "Responsible Personnel"
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
          "description": "Time taken for resolution, in ISO 8601 duration format.",
          "title": "Time Taken"
        }
      },
      "title": "SystemComponentIssueResolutionresolution",
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
  "description": "Schema for extracting details about system components, issues, and resolution steps.",
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
      "description": "Details about the issue related to the system component."
    },
    "resolution": {
      "anyOf": [
        {
          "$ref": "#/$defs/SystemComponentIssueResolutionresolution"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Details about the resolution of the issue."
    }
  },
  "title": "SystemComponentIssueResolution",
  "type": "object"
}
```
