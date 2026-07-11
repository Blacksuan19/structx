"""Pydantic Settings configuration for model-backed extraction steps."""

import json
from pathlib import Path
from typing import Any, Type

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from structx.core.exceptions import ConfigurationError
from structx.utils.types import DictStrAny


class StepConfig(BaseModel):
    """Provider-specific completion parameters for one extraction step."""

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    @model_validator(mode="before")
    @classmethod
    def decode_scalar_values(cls, value: Any) -> Any:
        """Decode numeric and boolean values supplied by nested environment keys."""
        if not isinstance(value, dict):
            return value
        decoded = {}
        for key, item in value.items():
            if isinstance(item, str):
                try:
                    item = json.loads(item)
                except json.JSONDecodeError:
                    pass
            decoded[key] = item
        return decoded

    def options(self) -> DictStrAny:
        """Return explicitly configured provider parameters."""
        return self.model_dump(exclude_none=True)


class ExtractionConfig(BaseSettings):
    """Settings loaded from arguments, environment, dotenv, YAML, or secrets.

    Source priority is constructor values, environment variables, ``.env``,
    YAML, then file secrets. Environment and secret names use the ``STRUCTX_``
    prefix.
    """

    planning: StepConfig = Field(default_factory=StepConfig)
    extraction: StepConfig = Field(default_factory=StepConfig)

    model_config = SettingsConfigDict(
        extra="ignore",
        env_prefix="STRUCTX_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        yaml_file=None,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Use conventional precedence with YAML below dotenv values."""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )

    @classmethod
    def from_yaml(cls, path: str | Path, **overrides: Any) -> "ExtractionConfig":
        """Load settings from a YAML file with optional highest-priority overrides."""
        yaml_path = Path(path).expanduser()
        if not yaml_path.is_file():
            raise ConfigurationError(f"Configuration file not found: {yaml_path}")

        class YamlExtractionConfig(cls):
            model_config = SettingsConfigDict(
                **{**cls.model_config, "yaml_file": yaml_path}
            )

        return YamlExtractionConfig(**overrides)

    def for_step(self, step: str) -> DictStrAny:
        """Return provider kwargs for ``planning`` or ``extraction``."""
        if step not in {"planning", "extraction"}:
            raise ConfigurationError(f"Unknown extraction step: {step}")
        return getattr(self, step).options()
