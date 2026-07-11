# Configuration

`structx` uses Pydantic Settings to validate provider parameters and load them
from constructor values, environment variables, dotenv files, YAML, or secrets.

The two configurable steps are `planning` and `extraction`. Structx supplies no
implicit sampling or output-token defaults; each `StepConfig` contains only the
provider parameters explicitly supplied by the user.

::: structx.core.config.StepConfig
    options:
      show_bases: false
      heading_level: 2
      members:
        - options


::: structx.core.config.ExtractionConfig
    options:
      show_bases: false
      heading_level: 2
      members:
        - from_yaml
        - for_step

For source precedence, YAML examples, environment names, and runtime settings,
see [Configuration Options](../reference/configuration-options.md).
