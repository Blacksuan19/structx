# Configuration Options

`structx` passes model configuration through without imposing generation
defaults. When no configuration is supplied, the selected model and provider
control sampling, reasoning, and output limits.

## Configuration Methods

You can configure `structx` in several ways:

### YAML Configuration

```yaml
# config.yaml
planning:
  reasoning_effort: low

extraction:
  reasoning_effort: medium
  max_completion_tokens: 16000
```

```python
extractor = Extractor.from_litellm(
    model="gpt-5.5",
    api_key="your-api-key",
    config="config.yaml"
)
```

### Dictionary Configuration

```python
config = {
    "planning": {
        "reasoning_effort": "low"
    },
    "extraction": {
        "reasoning_effort": "medium",
        "max_completion_tokens": 16000
    }
}

extractor = Extractor.from_litellm(
    model="gpt-5.5",
    api_key="your-api-key",
    config=config
)
```

### ExtractionConfig Object

```python
from structx import ExtractionConfig

config = ExtractionConfig(
    config={
        "planning": {"reasoning_effort": "low"},
        "extraction": {
            "reasoning_effort": "medium",
            "max_completion_tokens": 16000,
        },
    }
)

extractor = Extractor.from_litellm(
    model="gpt-5.5",
    api_key="your-api-key",
    config=config
)
```

## Configuration Parameters

### Step Configuration

Each step in the extraction process can be configured separately:

1. **Planning**: Query refinement, extraction guidance, and model generation
2. **Extraction**: Actual data extraction

### Model Parameters

Each step accepts arbitrary LiteLLM or provider completion parameters. Structx
does not maintain its own parameter allowlist and does not provide defaults.
For example, reasoning models may use `reasoning_effort` and
`max_completion_tokens`, while other models may support `temperature`, `top_p`,
or provider-specific options.

LiteLLM drops parameters it knows are unsupported for the selected model. Model
metadata cannot describe every value restriction or custom OpenAI-compatible
endpoint, so consult the provider's model documentation before setting a value.

For lower planning latency, use a smaller model for schema and guide generation
while keeping the primary model for document extraction:

```python
extractor = Extractor.from_litellm(
    model="openai/gpt-5.5",
    planning_model="openai/gpt-4o",
    config={
        "extraction": {"reasoning_effort": "low"},
    },
)
```

## Retry Configuration

You can configure the retry behavior for extraction:

```python
extractor = Extractor.from_litellm(
    model="gpt-4o",
    api_key="your-api-key",
    max_retries=5,      # Maximum number of retry attempts
    min_wait=2,         # Minimum seconds to wait between retries
    max_wait=30         # Maximum seconds to wait between retries
)
```

### Retry Parameters

| Parameter   | Type | Default | Description                             |
| ----------- | ---- | ------- | --------------------------------------- |
| max_retries | int  | 3       | Maximum number of retry attempts        |
| min_wait    | int  | 1       | Minimum seconds to wait between retries |
| max_wait    | int  | 10      | Maximum seconds to wait between retries |

## Processing Configuration

You can configure the processing behavior:

```python
extractor = Extractor.from_litellm(
    model="gpt-4o",
    api_key="your-api-key",
    max_threads=20,     # Maximum number of concurrent threads
    batch_size=50       # Size of processing batches
)
```

### Processing Parameters

| Parameter   | Type | Default | Description                          |
| ----------- | ---- | ------- | ------------------------------------ |
| max_threads | int  | 10      | Maximum number of concurrent threads |
| batch_size  | int  | 100     | Size of processing batches           |

## Best Practices

1. **Model Settings**:

   - Start with no model parameters and use the provider defaults
   - Add reasoning, sampling, or token controls only when supported and needed
   - Set output limits high enough for large documents and data models

2. **Batch Size**:

   - Adjust based on your data size and memory constraints
   - Smaller batches use less memory but may be slower

3. **Thread Count**:
   - Set based on your CPU capabilities
   - Too many threads can cause resource contention
