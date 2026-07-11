import os
from dataclasses import dataclass, field
from pathlib import Path

import pytest


@dataclass(frozen=True)
class LiveLLMConfig:
    api_key: str = field(repr=False)
    api_base: str
    model: str


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run integration tests that use real document conversion",
    )
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="run tests that call the configured live LLM endpoint",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: tests that use real document conversion or heavier dependencies",
    )
    config.addinivalue_line(
        "markers",
        "live: tests that call a configured external LLM endpoint",
    )


def pytest_collection_modifyitems(config, items):
    skip_integration = pytest.mark.skip(reason="need --run-integration to run")
    skip_live = pytest.mark.skip(reason="need --run-live to run")
    for item in items:
        if "integration" in item.keywords and not config.getoption("--run-integration"):
            item.add_marker(skip_integration)
        if "live" in item.keywords and not config.getoption("--run-live"):
            item.add_marker(skip_live)


def _load_local_env() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


@pytest.fixture
def live_llm_config() -> LiveLLMConfig:
    _load_local_env()
    required = ["OPENAI_API_KEY", "OPENAI_BASE_URL"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        pytest.skip(f"missing live LLM settings: {', '.join(missing)}")
    return LiveLLMConfig(
        api_key=os.environ["OPENAI_API_KEY"],
        api_base=os.environ["OPENAI_BASE_URL"],
        model=os.getenv("STRUCTX_TEST_MODEL", "openai/gpt-5.5"),
    )


@pytest.fixture
def example_input_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "example_input"


@pytest.fixture
def sample_docx_path(example_input_dir: Path) -> Path:
    return example_input_dir / "free-consultancy-agreement.docx"


@pytest.fixture
def sample_pdf_path(example_input_dir: Path) -> Path:
    return example_input_dir / "S0305SampleInvoice.pdf"
