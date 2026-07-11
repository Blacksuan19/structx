from functools import partial
import asyncio
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import instructor
import litellm
import pytest
from pydantic import BaseModel

from structx.core.config import ExtractionConfig
from structx.extraction.core.llm_core import LLMCore
from structx.extraction.extractor import Extractor
from structx.utils.usage import ExtractionStep
from structx.utils.usage import ExtractorUsage


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
        extraction={"reasoning_effort": "low", "verbosity": "low"}
    )
    core = LLMCore(client, "provider/model", config)

    core.complete(
        messages=[{"role": "user", "content": "extract"}],
        response_model=CompletionResult,
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
        step=ExtractionStep.SCHEMA_GENERATION,
    )
    assert completions.request["model"] == "openai/gpt-4o"

    core.complete(
        messages=[{"role": "user", "content": "extract"}],
        response_model=CompletionResult,
        step=ExtractionStep.EXTRACTION,
    )
    assert completions.request["model"] == "openai/gpt-5.5"


def test_from_litellm_scopes_unsupported_parameter_filtering(monkeypatch):
    captured = []
    fake_client = SimpleNamespace()
    monkeypatch.setattr(litellm, "drop_params", False)

    def fake_completion(**kwargs):
        return kwargs

    async def fake_async_completion(**kwargs):
        return kwargs

    def fake_from_litellm(completion, **kwargs):
        captured.append((completion, kwargs))
        return fake_client

    monkeypatch.setattr(litellm, "completion", fake_completion)
    monkeypatch.setattr(litellm, "acompletion", fake_async_completion)
    monkeypatch.setattr(instructor, "from_litellm", fake_from_litellm)

    Extractor.from_litellm(model="provider/model")

    completion = captured[0][0]
    assert isinstance(completion, partial)
    assert completion.func is fake_completion
    assert completion.keywords == {"drop_params": True}
    assert captured[1][0].func is fake_async_completion
    assert captured[1][0].keywords == {"drop_params": True}
    assert captured[1][1] == {"async_client": True}
    assert litellm.drop_params is False


def test_from_litellm_binds_provider_settings_without_mutating_globals(monkeypatch):
    captured = []
    fake_client = SimpleNamespace()
    monkeypatch.setattr(litellm, "api_key", "global-key")
    monkeypatch.setattr(litellm, "api_base", "https://global.example")

    def fake_completion(**kwargs):
        return kwargs

    async def fake_async_completion(**kwargs):
        return kwargs

    def fake_from_litellm(completion, **kwargs):
        captured.append((completion, kwargs))
        return fake_client

    monkeypatch.setattr(litellm, "completion", fake_completion)
    monkeypatch.setattr(litellm, "acompletion", fake_async_completion)
    monkeypatch.setattr(instructor, "from_litellm", fake_from_litellm)

    Extractor.from_litellm(
        model="provider/model",
        api_key="client-key",
        api_base="https://client.example",
    )

    assert captured[0][0].keywords == {
        "api_base": "https://client.example",
        "drop_params": True,
        "api_key": "client-key",
    }
    assert captured[1][0].keywords == captured[0][0].keywords
    assert litellm.api_key == "global-key"
    assert litellm.api_base == "https://global.example"


def test_llm_core_keeps_concurrent_operation_usage_isolated():
    class UsageCompletions:
        def create_with_completion(self, **kwargs):
            token_count = int(kwargs["messages"][0]["content"])
            return CompletionResult(value="ok"), SimpleNamespace(
                usage={
                    "prompt_tokens": token_count,
                    "completion_tokens": 1,
                    "total_tokens": token_count + 1,
                }
            )

    client = SimpleNamespace(chat=SimpleNamespace(completions=UsageCompletions()))
    core = LLMCore(client, "provider/model", ExtractionConfig())
    usages = [ExtractorUsage(), ExtractorUsage()]

    def run(index):
        core.complete(
            messages=[{"role": "user", "content": str(index + 10)}],
            response_model=CompletionResult,
            step=ExtractionStep.EXTRACTION,
            usage=usages[index],
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(run, range(2)))

    assert usages[0].total_tokens == 11
    assert usages[1].total_tokens == 12


def test_llm_core_retries_only_transient_failures():
    class StatusError(Exception):
        def __init__(self, status_code):
            self.status_code = status_code
            super().__init__(f"status {status_code}")

    class RetryingCompletions:
        def __init__(self, status_code, failures):
            self.status_code = status_code
            self.failures = failures
            self.calls = 0

        def create_with_completion(self, **kwargs):
            self.calls += 1
            if self.calls <= self.failures:
                raise StatusError(self.status_code)
            return CompletionResult(value="ok"), None

    transient = RetryingCompletions(status_code=429, failures=2)
    transient_core = LLMCore(
        SimpleNamespace(chat=SimpleNamespace(completions=transient)),
        "provider/model",
        ExtractionConfig(),
        max_retries=2,
        min_wait=0,
        max_wait=0,
    )
    result = transient_core.complete(
        messages=[{"role": "user", "content": "extract"}],
        response_model=CompletionResult,
        step=ExtractionStep.EXTRACTION,
    )
    assert result.value == "ok"
    assert transient.calls == 3

    permanent = RetryingCompletions(status_code=400, failures=3)
    permanent_core = LLMCore(
        SimpleNamespace(chat=SimpleNamespace(completions=permanent)),
        "provider/model",
        ExtractionConfig(),
        max_retries=3,
        min_wait=0,
        max_wait=0,
    )
    with pytest.raises(Exception, match="status 400"):
        permanent_core.complete(
            messages=[{"role": "user", "content": "extract"}],
            response_model=CompletionResult,
            step=ExtractionStep.EXTRACTION,
        )
    assert permanent.calls == 1


def test_llm_core_async_completion_retries_and_tracks_usage():
    class TransientError(Exception):
        status_code = 429

    class AsyncCompletions:
        def __init__(self):
            self.calls = 0

        async def create_with_completion(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise TransientError("retry")
            return CompletionResult(value="ok"), SimpleNamespace(
                usage={
                    "prompt_tokens": 4,
                    "completion_tokens": 1,
                    "total_tokens": 5,
                }
            )

    completions = AsyncCompletions()
    usage = ExtractorUsage()
    core = LLMCore(
        client=SimpleNamespace(),
        async_client=SimpleNamespace(chat=SimpleNamespace(completions=completions)),
        model_name="provider/model",
        config=ExtractionConfig(),
        max_retries=1,
        min_wait=0,
        max_wait=0,
    )

    result = asyncio.run(
        core.complete_async(
            messages=[{"role": "user", "content": "extract"}],
            response_model=CompletionResult,
            step=ExtractionStep.EXTRACTION,
            usage=usage,
        )
    )

    assert result.value == "ok"
    assert completions.calls == 2
    assert usage.total_tokens == 5
