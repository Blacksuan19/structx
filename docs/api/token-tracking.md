# Token Usage Tracking

`ExtractionResult.usage` contains raw provider usage objects grouped by
schema-generation and extraction calls, plus computed operation totals. See the
[Token Tracking Guide](../guides/token-tracking.md) for examples.

## ExtractorUsage

::: structx.utils.usage.ExtractorUsage
    options:
      show_bases: false
      heading_level: 2
      members:
        - get_step
        - total_tokens
        - prompt_tokens
        - completion_tokens
        - thinking_tokens
        - cached_tokens

## ExtractionStep

::: structx.utils.usage.ExtractionStep
    options:
      show_bases: false
      heading_level: 2

Only `schema_generation` and `extraction` are tracked. With a custom model,
schema generation is absent. Each `RowResult` also exposes the extraction usage
for its own input row.
