from types import SimpleNamespace

from litellm.types.utils import Usage

from structx.utils.usage import ExtractionStep, ExtractorUsage


def test_usage_retains_litellm_objects_by_step():
    raw_usage = Usage(
        prompt_tokens=100,
        completion_tokens=25,
        total_tokens=125,
        completion_tokens_details={"reasoning_tokens": 10},
        prompt_tokens_details={"cached_tokens": 40},
    )
    usage = ExtractorUsage()

    usage.add_step_usage(ExtractionStep.SCHEMA_GENERATION, raw_usage)

    assert usage.get_step(ExtractionStep.SCHEMA_GENERATION) == [raw_usage]
    assert usage.get_step("schema_generation")[0] is raw_usage
    assert usage.thinking_tokens == 10
    assert usage.cached_tokens == 40


def test_usage_reads_provider_level_detail_aliases():
    raw_usage = SimpleNamespace(
        prompt_tokens=80,
        completion_tokens=20,
        total_tokens=100,
        reasoning_tokens=7,
        cache_read_input_tokens=30,
    )
    usage = ExtractorUsage()

    usage.add_step_usage(ExtractionStep.EXTRACTION, raw_usage)

    assert usage.thinking_tokens == 7
    assert usage.cached_tokens == 30


def test_usage_supports_responses_api_names():
    raw_usage = {
        "input_tokens": 80,
        "output_tokens": 20,
        "total_tokens": 100,
        "output_tokens_details": {"reasoning_tokens": 7},
        "input_tokens_details": {"cached_tokens": 30},
    }
    usage = ExtractorUsage()

    usage.add_step_usage(ExtractionStep.EXTRACTION, raw_usage)

    assert usage.prompt_tokens == 80
    assert usage.completion_tokens == 20
    assert usage.total_tokens == 100
    assert usage.thinking_tokens == 7
    assert usage.cached_tokens == 30


def test_usage_groups_calls_and_aggregates_metrics():
    schema_usage = {
        "prompt_tokens": 100,
        "completion_tokens": 20,
        "total_tokens": 120,
    }
    first_extraction = {
        "prompt_tokens": 200,
        "completion_tokens": 50,
        "total_tokens": 250,
        "completion_tokens_details": {"reasoning_tokens": 10},
        "prompt_tokens_details": {"cached_tokens": 40},
    }
    second_extraction = {
        "prompt_tokens": 50,
        "completion_tokens": 15,
        "total_tokens": 65,
        "completion_tokens_details": {"reasoning_tokens": 5},
        "prompt_tokens_details": {"cached_tokens": 20},
    }
    usage = ExtractorUsage()

    usage.add_step_usage(ExtractionStep.SCHEMA_GENERATION, schema_usage)
    usage.add_step_usage(ExtractionStep.EXTRACTION, first_extraction)
    usage.add_step_usage(ExtractionStep.EXTRACTION, second_extraction)

    assert usage.get_step("schema_generation") == [schema_usage]
    assert usage.get_step("extraction") == [first_extraction, second_extraction]
    assert usage.total_tokens == 435
    assert usage.prompt_tokens == 350
    assert usage.completion_tokens == 85
    assert usage.thinking_tokens == 15
    assert usage.cached_tokens == 60

    dumped = usage.model_dump()
    assert set(dumped["steps"]) == {"schema_generation", "extraction"}
    assert dumped["total_tokens"] == 435
    assert dumped["thinking_tokens"] == 15
