# Working with Results

Every extraction returns an `ExtractionResult`. It provides two complementary
views of the operation:

- `result.data` is the convenient output for downstream use.
- `result.rows` is the canonical row-by-row record with provenance, status,
  extracted items, errors, and usage.

## Output Data

By default, `data` is a flat list of all validated model instances returned
across successful rows:

```python
result = extractor.extract(
    data=[
        {"text": "Invoice A-1 totals USD 10.00."},
        {"text": "Invoice B-2 totals USD 20.00."},
    ],
    query="extract invoice number and total",
)

for item in result.data:
    print(item.model_dump())
```

A row may produce zero, one, or multiple model instances. Consequently,
`len(result.data)` does not always equal the number of input rows.

With `return_df=True`, `data` is a copy of the source DataFrame augmented with
extracted fields and `extraction_status`:

```python
result = extractor.extract(
    data=dataframe,
    query="extract incident owner and severity",
    return_df=True,
    expand_nested=True,
)

print(result.data[["extraction_status", "owner", "severity"]])
```

The status column contains `Success`, `Empty`, or `Failed: <error>`. If one row
returns multiple items, fields from later items receive numeric suffixes such
as `owner_1`. `expand_nested=True` flattens nested objects into columns.

## Row Outcomes

`rows` remains ordered by input position even when asynchronous requests finish
out of order:

```python
for row in result.rows:
    print(row.position, row.source_index, row.status)
    print([item.model_dump() for item in row.items])
```

Each `RowResult` contains:

| Attribute | Meaning |
| --- | --- |
| `position` | Unique zero-based input position |
| `source_index` | Original DataFrame index label |
| `input_data` | Text or PDF payload used for extraction |
| `items` | Validated model instances produced by the row |
| `status` | `success`, `empty`, or `failed` |
| `error` | Failure text, otherwise `None` |
| `usage` | Provider usage for that row's extraction call |

Use `position` when DataFrame index labels may be duplicated. `source_index`
preserves the original label for joining results back to application data.

## Counts and Failures

The result counters describe input rows unless their name explicitly refers to
extracted output:

| Property | Meaning |
| --- | --- |
| `attempted_count` | Input rows submitted |
| `success_count` | Rows that did not fail, including empty rows |
| `empty_count` | Successful rows that returned no items |
| `failure_count` | Failed rows |
| `extracted_count` | Length of the convenient `data` output |
| `success_rate` | Successful rows divided by attempted rows |

`failed` is a derived DataFrame view with `index`, `text`, and `error` columns:

```python
if result.failure_count:
    print(result.failed)
```

Failures are isolated per row. A failed row does not discard successful rows
from the same operation.

## Usage by Row

Top-level usage includes planning plus every successful extraction completion.
Row usage contains only that row's extraction request:

```python
print("operation tokens", result.usage.total_tokens)

for row in result.rows:
    print(row.source_index, row.usage.total_tokens)
```

If a request fails before a provider usage object is returned, its row usage
can be empty even though `row.error` is populated. See
[Token Tracking](token-tracking.md) for provider-specific usage details.

## Related API

- [`ExtractionResult`](../api/models.md#extractionresult)
- [`RowResult`](../api/models.md#rowresult)
- [Error Handling](../reference/error-handling.md)
