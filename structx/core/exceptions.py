class StructXError(Exception):
    """Base exception for all structx errors"""

    pass


class ConfigurationError(StructXError):
    """Error in configuration"""

    pass


class ExtractionError(StructXError):
    """Error during extraction process"""

    pass


class ValidationError(StructXError):
    """Error in data validation"""

    pass


class ModelGenerationError(StructXError):
    """Error in dynamic model generation"""

    pass


class FileError(StructXError):
    """Error in file operations"""

    pass
