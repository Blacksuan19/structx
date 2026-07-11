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
    model="openai/gpt-5.5",
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
    model="openai/gpt-5.5",
    api_key="your-api-key",
    config=config
)
```

### ExtractionConfig Object

```python
from structx import ExtractionConfig

config = ExtractionConfig(
    planning={"reasoning_effort": "low"},
    extraction={
        "reasoning_effort": "medium",
        "max_completion_tokens": 16000,
    },
)

extractor = Extractor.from_litellm(
    model="openai/gpt-5.5",
    api_key="your-api-key",
    config=config
)
```

## Configuration Parameters

### Step Configuration

Each step in the extraction process can be configured separately:

1. **Planning**: Extraction instructions, target columns, and model generation
2. **Extraction**: Actual data extraction

`ExtractionConfig` ignores unrelated settings, which allows it to share a
project-wide `.env` file safely.

### Environment And Dotenv

Settings use the `STRUCTX_` prefix. Supply a complete step as JSON:

```bash
export STRUCTX_PLANNING='{"reasoning_effort":"low"}'
export STRUCTX_EXTRACTION='{"reasoning_effort":"medium","max_completion_tokens":16000}'
```

The same values can be placed in a `.env` file. Nested variables such as
`STRUCTX_EXTRACTION__REASONING_EFFORT=medium` are also supported. Constructor
values take precedence over environment values, which take precedence over
dotenv, YAML, and file secrets.

Nested numeric and boolean values are decoded before being forwarded:

```bash
export STRUCTX_EXTRACTION__TEMPERATURE=0.2
export STRUCTX_EXTRACTION__STREAM=false
```

You can also load YAML directly when constructing settings:

```python
config = ExtractionConfig.from_yaml("config.yaml")
```

Constructor values override the loaded YAML when both are supplied:

```python
config = ExtractionConfig.from_yaml(
    "config.yaml",
    extraction={"reasoning_effort": "low"},
)
```

### File Secrets

Pass a secrets directory through Pydantic Settings when configuration is
mounted as files. Filenames use the `STRUCTX_` prefix and each file contains a
JSON object for that step:

```text
/run/secrets/STRUCTX_PLANNING
/run/secrets/STRUCTX_EXTRACTION
```

```python
config = ExtractionConfig(_secrets_dir="/run/secrets")
```

For example, `STRUCTX_EXTRACTION` may contain
`{"reasoning_effort":"low"}`. Secrets have the lowest priority, so local
constructor, environment, dotenv, or YAML values can override them.

### Model Parameters

Each step accepts arbitrary LiteLLM or provider completion parameters. Structx
does not maintain its own parameter allowlist and does not provide defaults.
For example, reasoning models may use `reasoning_effort` and
`max_completion_tokens`, while other models may support `temperature`, `top_p`,
or provider-specific options.

LiteLLM drops parameters it knows are unsupported for the selected model. Model
metadata cannot describe every value restriction or custom OpenAI-compatible
endpoint, so consult the provider's model documentation before setting a value.

For lower planning latency, use a smaller model for instruction and schema
generation while keeping the primary model for document extraction:

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

You can configure retry behavior for all model-backed steps:

```python
extractor = Extractor.from_litellm(
    model="openai/gpt-4o",
    api_key="your-api-key",
    max_retries=5,      # Five retries after the initial attempt
    min_wait=2,         # Minimum seconds to wait between retries
    max_wait=30         # Maximum seconds to wait between retries
)
```

### Retry Parameters

| Parameter   | Type | Default | Description                              |
| ----------- | ---- | ------- | ---------------------------------------- |
| max_retries | int  | 3       | Retries allowed after the initial attempt |
| min_wait    | int  | 1       | Minimum seconds to wait between retries  |
| max_wait    | int  | 10      | Maximum seconds to wait between retries  |

## Processing Configuration

You can configure the processing behavior:

```python
extractor = Extractor.from_litellm(
    model="openai/gpt-4o",
    api_key="your-api-key",
    max_threads=20,     # Maximum concurrent row requests
    batch_size=50       # Rows scheduled at once
)
```

### Processing Parameters

| Parameter   | Type | Default | Description                          |
| ----------- | ---- | ------- | ------------------------------------ |
| max_threads | int  | 10      | Maximum concurrent row requests       |
| batch_size  | int  | 100     | Rows scheduled in each processing batch |

## Best Practices

1. **Model Settings**:

   - Start with no model parameters and use the provider defaults
   - Add reasoning, sampling, or token controls only when supported and needed
   - Set output limits high enough for large documents and data models

2. **Batch Size**:

   - Adjust based on your data size and memory constraints
   - Smaller batches use less memory but may be slower

3. **Concurrency**:
   - Set based on provider rate and connection limits
   - Each concurrent operation has its own `max_threads` allowance
