# Configuration Options

`structx` provides flexible configuration options for extraction.

## Configuration Methods

You can configure `structx` in several ways:

### YAML Configuration

```yaml
# config.yaml
analysis:
  temperature: 0.2
  top_p: 0.1
  max_tokens: 2000

refinement:
  temperature: 0.1
  top_p: 0.05
  max_tokens: 2000

extraction:
  temperature: 0.0
  top_p: 0.1
  max_tokens: 2000
  frequency_penalty: 0.1
```

```python
extractor = Extractor.from_litellm(
    model="gpt-4o-mini",
    api_key="your-api-key",
    config="config.yaml"
)
```

### Dictionary Configuration

```python
config = {
    "analysis": {
        "temperature": 0.2,
        "top_p": 0.1,
        "max_tokens": 2000
    },
    "refinement": {
        "temperature": 0.1,
        "top_p": 0.05,
        "max_tokens": 2000
    },
    "extraction": {
        "temperature": 0.0,
        "top_p": 0.1,
        "max_tokens": 2000,
        "frequency_penalty": 0.1
    }
}

extractor = Extractor.from_litellm(
    model="gpt-4o-mini",
    api_key="your-api-key",
    config=config
)
```

### StructXConfig Object

```python
from structx import StructXConfig, StepConfig

config = StructXConfig(
    analysis=StepConfig(
        temperature=0.2,
        top_p=0.1,
        max_tokens=2000
    ),
    refinement=StepConfig(
        temperature=0.1,
        top_p=0.05,
        max_tokens=2000
    ),
    extraction=StepConfig(
        temperature=0.0,
        top_p=0.1,
        max_tokens=2000,
        frequency_penalty=0.1
    )
)

extractor = Extractor.from_litellm(
    model="gpt-4o-mini",
    api_key="your-api-key",
    config=config
)
```

## Configuration Parameters

### Step Configuration

Each step in the extraction process can be configured separately:

1. **Analysis**: Query analysis to determine what to extract
2. **Refinement**: Query refinement and model generation
3. **Extraction**: Actual data extraction

### Common Parameters

| Parameter         | Type  | Default | Description                               |
| ----------------- | ----- | ------- | ----------------------------------------- |
| temperature       | float | varies  | Sampling temperature (0.0-1.0)            |
| top_p             | float | varies  | Nucleus sampling parameter (0.0-1.0)      |
| max_tokens        | int   | 2000    | Maximum tokens in completion              |
| presence_penalty  | float | 0.0     | Penalty for token presence (-2.0 to 2.0)  |
| frequency_penalty | float | 0.0     | Penalty for token frequency (-2.0 to 2.0) |

### Default Values

| Step       | Temperature | Top P | Max Tokens |
| ---------- | ----------- | ----- | ---------- |
| Analysis   | 0.2         | 0.1   | 2000       |
| Refinement | 0.1         | 0.05  | 2000       |
| Extraction | 0.0         | 0.1   | 2000       |

## Retry Configuration

You can configure the retry behavior for extraction:

```python
extractor = Extractor.from_litellm(
    model="gpt-4o-mini",
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
    model="gpt-4o-mini",
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

1. **Temperature Settings**:

   - Use lower temperatures (0.0-0.2) for consistent extraction
   - Higher temperatures may introduce variability

2. **Token Limits**:

   - Ensure `max_tokens` is sufficient for your extraction needs
   - Complex extractions may require higher limits

3. **Batch Size**:

   - Adjust based on your data size and memory constraints
   - Smaller batches use less memory but may be slower

4. **Thread Count**:
   - Set based on your CPU capabilities
   - Too many threads can cause resource contention
