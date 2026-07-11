from functools import partial
from types import SimpleNamespace

import instructor
import litellm
from pydantic import BaseModel

from structx.core.config import ExtractionConfig
from structx.extraction.core.llm_core import LLMCore
from structx.extraction.extractor import Extractor
from structx.utils.usage import ExtractionStep


class CompletionResult(BaseModel):
    value: str


class FakeCompletions:
    def __init__(self):
        self.request = None

    def create_with_completion(self, **kwargs):
        self.request = kwargs
        return CompletionResult(value="ok"), None


def test_llm_core_sends_no_implicit_model_parameters():
    completions = FakeCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    core = LLMCore(client, "provider/model", ExtractionConfig())

    core.complete(
        messages=[{"role": "user", "content": "extract"}],
        response_model=CompletionResult,
        config=core.config.extraction,
        step=ExtractionStep.EXTRACTION,
    )

    assert completions.request == {
        "model": "provider/model",
        "response_model": CompletionResult,
        "messages": [{"role": "user", "content": "extract"}],
    }


def test_llm_core_forwards_explicit_provider_parameters():
    completions = FakeCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    config = ExtractionConfig(
        config={"extraction": {"reasoning_effort": "low", "verbosity": "low"}}
    )
    core = LLMCore(client, "provider/model", config)

    core.complete(
        messages=[{"role": "user", "content": "extract"}],
        response_model=CompletionResult,
        config=core.config.extraction,
        step=ExtractionStep.EXTRACTION,
    )

    assert completions.request["reasoning_effort"] == "low"
    assert completions.request["verbosity"] == "low"


def test_llm_core_uses_separate_planning_model():
    completions = FakeCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    core = LLMCore(
        client,
        "openai/gpt-5.5",
        ExtractionConfig(),
        planning_model_name="openai/gpt-4o",
    )

    core.complete(
        messages=[{"role": "user", "content": "plan"}],
        response_model=CompletionResult,
        config={},
        step=ExtractionStep.SCHEMA_GENERATION,
    )
    assert completions.request["model"] == "openai/gpt-4o"

    core.complete(
        messages=[{"role": "user", "content": "extract"}],
        response_model=CompletionResult,
        config={},
        step=ExtractionStep.EXTRACTION,
    )
    assert completions.request["model"] == "openai/gpt-5.5"


def test_from_litellm_scopes_unsupported_parameter_filtering(monkeypatch):
    captured = {}
    fake_client = SimpleNamespace()
    monkeypatch.setattr(litellm, "drop_params", False)

    def fake_completion(**kwargs):
        return kwargs

    def fake_from_litellm(completion):
        captured["completion"] = completion
        return fake_client

    monkeypatch.setattr(litellm, "completion", fake_completion)
    monkeypatch.setattr(instructor, "from_litellm", fake_from_litellm)

    Extractor.from_litellm(model="provider/model")

    completion = captured["completion"]
    assert isinstance(completion, partial)
    assert completion.func is fake_completion
    assert completion.keywords == {"drop_params": True}
    assert litellm.drop_params is False
