from pathlib import Path
from typing import Any, Dict, Optional, Union

from omegaconf import OmegaConf
from pydantic import BaseModel, ConfigDict

from structx.utils.types import DictStrAny


class StepConfig(BaseModel):
    """Provider-specific completion parameters for one extraction step."""

    model_config = ConfigDict(validate_assignment=True, extra="allow")


class ExtractionConfig:
    """Configuration management for structx using OmegaConf and Pydantic"""

    DEFAULT_CONFIG = {
        "planning": {},
        "extraction": {},
    }

    def __init__(
        self,
        config: Optional[Union[Dict[str, Any], str]] = None,
        config_path: Optional[Union[str, Path]] = None,
    ):
        """
        Initialize configuration

        Args:
            config: Optional configuration dictionary or YAML string
            config_path: Optional path to YAML configuration file
        """
        # Create base config from defaults
        self.conf = OmegaConf.create(self.DEFAULT_CONFIG)

        # Load from file if provided
        if config_path:
            file_conf = OmegaConf.load(config_path)
            self.conf = OmegaConf.merge(self.conf, file_conf)

        # Merge with provided config if any
        if config:
            if isinstance(config, str):
                conf_to_merge = OmegaConf.create(config)
            else:
                conf_to_merge = OmegaConf.create(config)
            self.conf = OmegaConf.merge(self.conf, conf_to_merge)

        # Validate using Pydantic models
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate configuration using Pydantic models"""
        for step in ["planning", "extraction"]:
            step_config: DictStrAny = OmegaConf.to_container(self.conf.get(step, {}))  # type: ignore
            # Validate using StepConfig model
            StepConfig(**step_config)

    @property
    def planning(self) -> DictStrAny:
        """Get validated planning step configuration"""
        config: DictStrAny = OmegaConf.to_container(self.conf.planning)  # type: ignore
        return StepConfig(**config).model_dump(exclude_none=True)

    @property
    def extraction(self) -> DictStrAny:
        """Get validated extraction step configuration"""
        config: DictStrAny = OmegaConf.to_container(self.conf.extraction)  # type: ignore
        return StepConfig(**config).model_dump(exclude_none=True)

    def save(self, path: str) -> None:
        """Save configuration to YAML file"""
        OmegaConf.save(self.conf, path)

    def __str__(self) -> str:
        """String representation of configuration"""
        return OmegaConf.to_yaml(self.conf)

    def __repr__(self) -> str:
        """Representation of configuration"""
        return self.__str__()
