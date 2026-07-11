import pytest

from structx.core.config import ExtractionConfig, StepConfig
from structx.core.exceptions import ConfigurationError


def test_step_config_has_no_implicit_model_parameters():
    assert StepConfig().model_dump() == {}


def test_step_config_preserves_provider_specific_parameters():
    assert StepConfig(
        reasoning_effort="low",
        max_completion_tokens=16_000,
    ).options() == {
        "reasoning_effort": "low",
        "max_completion_tokens": 16_000,
    }


def test_extraction_config_only_returns_explicit_parameters():
    config = ExtractionConfig(
        planning={"reasoning_effort": "low"},
        extraction={"max_completion_tokens": 16_000},
    )

    assert config.for_step("planning") == {"reasoning_effort": "low"}
    assert config.for_step("extraction") == {"max_completion_tokens": 16_000}


def test_extraction_config_loads_yaml(tmp_path):
    config_path = tmp_path / "structx.yml"
    config_path.write_text(
        "planning:\n  reasoning_effort: low\nextraction:\n  temperature: 0.2\n",
        encoding="utf-8",
    )

    config = ExtractionConfig.from_yaml(config_path)

    assert config.for_step("planning") == {"reasoning_effort": "low"}
    assert config.for_step("extraction") == {"temperature": 0.2}


def test_extraction_config_environment_overrides_yaml(monkeypatch, tmp_path):
    config_path = tmp_path / "structx.yml"
    config_path.write_text("extraction:\n  temperature: 0.2\n", encoding="utf-8")
    monkeypatch.setenv("STRUCTX_EXTRACTION", '{"temperature": 0.7}')

    config = ExtractionConfig.from_yaml(config_path)

    assert config.for_step("extraction") == {"temperature": 0.7}


def test_extraction_config_decodes_nested_environment_scalars(monkeypatch):
    monkeypatch.setenv("STRUCTX_EXTRACTION__TEMPERATURE", "0.2")
    monkeypatch.setenv("STRUCTX_EXTRACTION__STREAM", "false")

    config = ExtractionConfig(_env_file=None)

    assert config.for_step("extraction") == {
        "temperature": 0.2,
        "stream": False,
    }


def test_extraction_config_rejects_missing_yaml():
    with pytest.raises(ConfigurationError, match="Configuration file not found"):
        ExtractionConfig.from_yaml("missing.yml")


def test_extraction_config_rejects_unknown_step_lookup():
    with pytest.raises(ConfigurationError, match="Unknown extraction step"):
        ExtractionConfig().for_step("guide")
