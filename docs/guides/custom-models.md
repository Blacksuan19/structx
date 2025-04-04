# Custom Models

While `structx` dynamically generates models based on your queries, you can also
use your own custom Pydantic models for extraction.

## Using Custom Models

### Define Your Model

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class Metric(BaseModel):
    name: str = Field(description="Name of the metric")
    value: float = Field(description="Value of the metric")
    unit: Optional[str] = Field(default=None, description="Unit of measurement")

class Incident(BaseModel):
    timestamp: str = Field(description="When the incident occurred")
    system: str = Field(description="Affected system")
    severity: str = Field(description="Severity level")
    metrics: List[Metric] = Field(default_factory=list, description="Related metrics")
    resolution: Optional[str] = Field(default=None, description="Resolution steps")
```

### Extract with Custom Model

```python
result = extractor.extract(
    data=df,
    query="extract incident information including timestamp, system, severity, metrics, and resolution",
    model=Incident
)

# Access the extracted data
for item in result.data:
    print(f"Incident at {item.timestamp} on {item.system}")
    print(f"Severity: {item.severity}")
    for metric in item.metrics:
        print(f"- {metric.name}: {metric.value} {metric.unit or ''}")
    if item.resolution:
        print(f"Resolution: {item.resolution}")
```

## Reusing Generated Models

You can also reuse models generated from previous extractions:

```python
# First extraction generates a model
result1 = extractor.extract(
    data=df1,
    query="extract incident dates and affected systems"
)

# Reuse the model for another extraction
result2 = extractor.extract(
    data=df2,
    query="extract incident information",
    model=result1.model
)
```

## Generating Models Without Extraction

You can generate a model without performing extraction using `get_schema`:

```python
# Generate a model based on a query and sample text
IncidentModel = extractor.get_schema(
    query="extract incident dates, affected systems, and resolution steps",
    sample_text="System check on 2024-01-15 detected high CPU usage (92%) on server-01."
)

# Inspect the model
print(IncidentModel.model_json_schema())

# Use the model for extraction
result = extractor.extract(
    data=df,
    query="extract incident information",
    model=IncidentModel
)
```

## Extending Generated Models

You can extend generated models with additional fields or validation:

For more advanced model modifications, you can also use the
[Model Refinement](model-refinement.md) feature to update your models using
natural language instructions:

````python
# Generate a base model
IncidentModel = extractor.get_schema(
    query="extract incident dates and affected systems",
    sample_text="Sample text here"
)

# Refine it with natural language
EnhancedIncidentModel = extractor.refine_data_model(
    model=IncidentModel,
    instructions="""
    1. Add a 'severity' field with allowed values: 'low', 'medium', 'high'
    2. Make incident_date a required field
    3. Add validation for affected_systems to ensure it's a non-empty list
    """

# check token usage
usage = EnhancedIncidentModel.usage
print(f"Total tokens used: {usage.total_tokens}")
print(f"By step: {[(s.name, s.tokens) for s in usage.steps]}")
)

## Model Validation

Pydantic models provide built-in validation:

```python
# Create an instance with validation
try:
    incident = Incident(
        timestamp="2024-01-15 14:30",
        system="server-01",
        severity="high",
        metrics=[
            {"name": "CPU Usage", "value": 92, "unit": "%"}
        ]
    )
    print("Valid incident:", incident)
except Exception as e:
    print("Validation error:", e)
````

## Best Practices

1. **Add Field Descriptions**: Always include descriptions for your fields to
   guide the extraction
2. **Use Type Hints**: Proper type hints help ensure correct extraction
3. **Set Default Values**: Use defaults for optional fields
4. **Add Validation**: Include validation rules for better data quality
5. **Keep Models Focused**: Create models that focus on specific extraction
   tasks

## Next Steps

- Learn about [Model Refinement](model-refinement.md) for updating models with
  natural language
- Explore [Unstructured Text](unstructured-text.md) handling
- See how to use [Multiple Queries](multiple-queries.md) for complex extractions
- Try [Async Operations](async-operations.md) for better performance
