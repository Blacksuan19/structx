from pathlib import Path
from typing import Annotated, Any, Dict, Optional, Union

from omegaconf import OmegaConf
from pydantic import BaseModel, Field

from structx.utils.types import DictStrAny


class StepConfig(BaseModel):
    """Configuration for an individual extraction step"""

    temperature: Optional[
        Annotated[
            float, Field(ge=0.0, le=1.0, description="Sampling temperature for LLM")
        ]
    ] = None
    top_p: Optional[
        Annotated[
            float, Field(ge=0.0, le=1.0, description="Nucleus sampling parameter")
        ]
    ] = None
    max_tokens: Optional[
        Annotated[int, Field(gt=0, description="Maximum tokens in completion")]
    ] = None

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Return dictionary of non-None values merged with defaults
        """
        # Default values for each step
        defaults = {
            "temperature": 0.1,
            "top_p": 0.1,
            "max_tokens": 2000,
        }

        # Get current values, excluding None
        current = {
            k: v
            for k, v in super().model_dump(*args, **kwargs).items()
            if v is not None
        }

        # Merge with defaults, preferring current values
        return {**defaults, **current}

    class Config:
        validate_assignment = True


class ExtractionConfig:
    """Configuration management for structx using OmegaConf and Pydantic"""

    DEFAULT_CONFIG = {
        "analysis": {"temperature": 0.2, "top_p": 0.1, "max_tokens": 2000},
        "refinement": {"temperature": 0.1, "top_p": 0.05, "max_tokens": 2000},
        "extraction": {"temperature": 0.0, "top_p": 0.1, "max_tokens": 2000},
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
        for step in ["analysis", "refinement", "extraction"]:
            step_config: DictStrAny = OmegaConf.to_container(self.conf.get(step, {}))  # type: ignore
            # Validate using StepConfig model
            StepConfig(**step_config)

    @property
    def analysis(self) -> DictStrAny:
        """Get validated analysis step configuration"""
        config: DictStrAny = OmegaConf.to_container(self.conf.analysis)  # type: ignore
        return StepConfig(**config).model_dump(exclude_none=True)

    @property
    def refinement(self) -> DictStrAny:
        """Get validated refinement step configuration"""
        config: DictStrAny = OmegaConf.to_container(self.conf.refinement)  # type: ignore
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
