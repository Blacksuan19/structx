# Basic Extraction

This guide covers the fundamentals of data extraction with `structx`.

## Extraction Process

When you use `structx` to extract data, the following happens:

1. **Planning**: Instructions, target columns, and the schema are generated together
2. **Model Generation**: A Pydantic model is created from the planned schema
3. **Data Extraction**: The model is used to extract structured data from the
   text
4. **Result Collection**: Results are collected and returned as an
   `ExtractionResult` object

### Standard Extraction Flow

<details>
<summary>View Standard Extraction Flow Diagram</summary>

```mermaid
graph LR
    A[Raw Query] --> B[Instruction and Schema Planning]
    B --> C[Model Generation]
    C --> D[Model Creation]
    D --> E[Data Extraction]
    E --> F[Result Collection]
    F --> G[ExtractionResult]

    subgraph "LLM Operations"
        B1[Write Instructions] --> B2[Select Columns]
        B2 --> B3[Infer Schema]
    end

    B --> B1
```

</details>

### Simplified Workflow with Provided Model

When you provide a data model, the workflow is optimized:

1. **Deterministic Instructions**: The query is combined with the supplied
   model contract without a planning model call
2. **Data Extraction**: The provided model is used to extract structured data
3. **Result Collection**: Results are collected and returned as an
   `ExtractionResult` object

This workflow skips planning entirely. Every input column is retained so a
name-based heuristic cannot accidentally omit evidence needed by the model.

### Custom Model Flow

<details>
<summary>View Custom Model Flow Diagram</summary>

```mermaid
graph LR
    A[Query and Custom Model] --> B[Deterministic Instructions]
    B --> C[Keep All Input Columns]
    C --> D[Independent Row Extraction]
    D --> E[RowResult Collection]
    E --> F[ExtractionResult]
```

</details>

```python
from pydantic import BaseModel, Field
from typing import List

class Invoice(BaseModel):
    invoice_number: str = Field(..., description="The invoice number")
    total_amount: float = Field(..., description="The total amount of the invoice")
    line_items: List[str] = Field(..., description="A list of line items from the invoice")

# Extract using the provided model
result = extractor.extract(
    data="scripts/example_input/S0305SampleInvoice.pdf",
    query="extract the invoice number, total amount, and line items",
    model=Invoice
)
```

## Extraction Query

The extraction query is a natural language description of what you want to
extract. Be as specific as possible:

```python
# Simple query for a legal document
query = "extract the parties, effective date, and governing law"

# More specific query for an invoice
query = """
extract the following details from the invoice:
- invoice number
- total amount due
- list of all line items with their descriptions and costs
- payment due date
"""
```

## Input Data Types

`structx` supports various input data types, but for legal and financial
documents, you'll primarily use file paths.

!!! note "Document dependencies"
    Existing PDFs and raw strings work with the base installation. Install
    `structx[docs]` for non-PDF document paths that require conversion.

### Files

```python
# PDF invoice
result = extractor.extract(
    data="scripts/example_input/S0305SampleInvoice.pdf",
    query="extract invoice number, total amount, and line items"
)

# DOCX contract
result = extractor.extract(
    data="scripts/example_input/free-consultancy-agreement.docx",
    query="extract the parties, effective date, and payment terms"
)
```

## Output Formats

### Model Instances (Default)

```python
result = extractor.extract(
    data="scripts/example_input/S0305SampleInvoice.pdf",
    query="extract invoice number and total amount",
)

# Access as list of model instances
for item in result.data:
    print(f"Invoice Number: {item.invoice_number}")
    print(f"Total Amount: {item.total_amount}")
```

### DataFrame

```python
result = extractor.extract(
    data="scripts/example_input/S0305SampleInvoice.pdf",
    query="extract invoice number and total amount",
    return_df=True
)

# Access as DataFrame
print(result.data.head())
```

### Nested Data

For nested data structures, you can choose to flatten them:

```python
result = extractor.extract(
    data=df,
    query="extract incident dates and affected systems",
    return_df=True,
    expand_nested=True  # Flatten nested structures
)
```

## Working with Results

The `extract` method returns an `ExtractionResult` object with:

- `data`: Extracted data (DataFrame or list of model instances)
- `rows`: Ordered row outcomes containing source index, input payload, items,
  error, status, and row-specific usage
- `failed`: Derived DataFrame view of failed rows
- `model`: Generated or provided model class
- `usage`: Raw provider usage grouped by schema-generation and extraction calls
- `success_count`: Number of input rows without an extraction error
- `empty_count`: Number of successful rows that returned no model instances
- `extracted_count`: Number of returned model instances or DataFrame rows
- `failure_count`: Number of failed input rows
- `success_rate`: Success rate as a percentage

```python
# Check extraction statistics
print(f"Successful rows: {result.success_count}")
print(f"Failed rows: {result.failure_count}")
print(f"Success rate: {result.success_rate:.1f}%")

# Access the model schema
print(result.model.model_json_schema())
```

See [Working with Results](working-with-results.md) for the full distinction
between flattened `data`, canonical row outcomes, counters, and per-row usage.

## Error Handling

Failed extractions are collected in the `failed` DataFrame:

```python
if result.failure_count > 0:
    print("Failed extractions:")
    print(result.failed)
```

## Next Steps

- Learn about [Custom Models](custom-models.md) for specific extraction needs
- Try [Model Refinement](model-refinement.md) to modify data models with natural
  language
- Learn about [retry mechanisms](retry-mechanism.md) for robust error handling
- Explore [Unstructured Text](unstructured-text.md) handling for documents
- See how to use [Multiple Queries](multiple-queries.md) for complex extractions
