class StructXError(Exception):
    """Base exception for errors raised directly by Structx."""

    pass


class ConfigurationError(StructXError):
    """Raised for invalid Structx configuration or runtime settings."""

    pass


class ExtractionError(StructXError):
    """Raised when a public extraction operation cannot complete."""

    pass


class ValidationError(StructXError):
    """Raised for Structx-specific input validation failures."""

    pass


class ModelGenerationError(StructXError):
    """Raised when an extraction schema cannot become a Pydantic model."""

    pass


class FileError(StructXError):
    """Raised for invalid paths, unsupported files, or conversion failures."""

    pass
