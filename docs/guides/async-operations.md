# Async Operations

`structx` provides async wrappers for extraction, multiple-query processing,
and schema generation. These wrappers offload the synchronous operation to an
executor so it does not block the caller's event loop.

## Basic Async Extraction

```python
import asyncio

async def extract_data():
    result = await extractor.extract_async(
        data="scripts/example_input/free-consultancy-agreement.docx",
        query="extract the main parties and the effective date"
    )
    return result

# Run the async function
result = asyncio.run(extract_data())
```

## Async Methods

For each synchronous method, there is an async counterpart:

| Synchronous Method | Asynchronous Method     |
| ------------------ | ----------------------- |
| `extract`          | `extract_async`         |
| `extract_queries`  | `extract_queries_async` |
| `get_schema`       | `get_schema_async`      |

## Parallel Processing

Process multiple documents in parallel:

### Async Processing Flow

<details>
<summary>View Async Processing Flow Diagram</summary>

```mermaid
graph TB
    A[Multiple Files] --> B[Create Async Tasks]
    B --> C[Parallel Execution]

    C --> D1[File 1 Processing]
    C --> D2[File 2 Processing]
    C --> D3[File 3 Processing]
    C --> D4[File N Processing]

    D1 --> E1[Result 1]
    D2 --> E2[Result 2]
    D3 --> E3[Result 3]
    D4 --> E4[Result N]

    E1 --> F[Gather Results]
    E2 --> F
    E3 --> F
    E4 --> F

    F --> G[Combined Output]

    subgraph "Concurrent Execution"
        D1
        D2
        D3
        D4
    end
```

</details>

```python
import asyncio

async def process_documents(docs):
    tasks = []
    for doc_path, query in docs.items():
        task = extractor.extract_async(
            data=doc_path,
            query=query
        )
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    return results

documents = {
    "scripts/example_input/free-consultancy-agreement.docx": "extract parties and governing law",
    "scripts/example_input/S0305SampleInvoice.pdf": "extract invoice number and total amount"
}
results = asyncio.run(process_documents(documents))
```

## Combining with Other Async Operations

```python
import asyncio

async def fetch_and_extract(fetch_text, query):
    content = await fetch_text()
    return await extractor.extract_async(
        data=[{"text": content}],
        query=query
    )
```

## Async Multiple Queries

```python
import asyncio

async def process_multiple_queries():
    queries = [
        "extract all clauses related to payment",
        "extract termination conditions",
        "summarize the scope of services"
    ]

    results = await extractor.extract_queries_async(
        data="scripts/example_input/free-consultancy-agreement.docx",
        queries=queries
    )

    return results

results = asyncio.run(process_multiple_queries())
```

`extract_queries_async` offloads the synchronous sequential query loop; it does
not execute the queries concurrently. Use separate `extract_async` tasks with
`asyncio.gather` when independent operations should overlap.

## Best Practices

1. **Use in Async Environments**: Only use async methods in async environments
2. **Limit Concurrency**: Be mindful of API rate limits when processing in
   parallel
3. **Handle Errors**: Use try/except with async operations
4. **Close Resources**: Ensure proper cleanup of resources in async contexts

## Next Steps

- Check out the [API Reference](../api/extractor.md) for detailed method
  signatures
- Try [Model Refinement](model-refinement.md) to enhance your data models
- Explore [Token Usage Tracking](token-tracking.md) to monitor resource
  consumption
- Learn about [retry mechanisms](retry-mechanism.md) for robust error handling
- See [Examples](../examples.md) for real-world use cases
