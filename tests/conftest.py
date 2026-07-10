from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run integration tests that use real document conversion",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: tests that use real document conversion or heavier dependencies",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-integration"):
        return

    skip_integration = pytest.mark.skip(reason="need --run-integration to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


@pytest.fixture
def example_input_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "example_input"


@pytest.fixture
def sample_docx_path(example_input_dir: Path) -> Path:
    return example_input_dir / "free-consultancy-agreement.docx"


@pytest.fixture
def sample_pdf_path(example_input_dir: Path) -> Path:
    return example_input_dir / "S0305SampleInvoice.pdf"
