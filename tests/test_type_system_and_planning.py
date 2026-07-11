from typing import get_args, get_origin

import pytest
from pydantic import ValidationError

from structx.core.models import (
    ExtractionGuide,
    ExtractionPlan,
    ExtractionRequest,
    ModelField,
    QueryRefinement,
)
from structx.core.type_system import (
    TypeExpressionError,
    normalize_type_expression,
    resolve_type_expression,
)
from structx.extraction.generator import ModelGenerator
from structx.extraction.processors.model_operations import ModelOperations
from structx.utils.usage import ExtractionStep


@pytest.mark.parametrize(
    ("source", "canonical"),
    [
        ("array<string>|null", "Optional[List[str]]"),
        ("list[integer]", "List[int]"),
        ("Dict[str, array<number>]", "Dict[str, List[float]]"),
        ("string[]", "List[str]"),
        ("array of boolean", "List[bool]"),
        ("list of strings", "List[str]"),
        ("Union[string, null]", "Optional[str]"),
        ("object", "Dict[str, Any]"),
    ],
)
def test_type_expressions_are_normalized(source, canonical):
    assert normalize_type_expression(source) == canonical


def test_unknown_and_ambiguous_types_are_rejected():
    with pytest.raises(TypeExpressionError):
        normalize_type_expression("string|integer")

    with pytest.raises(ValidationError):
        ModelField(name="value", type="made_up_type", description="value")


def test_model_field_normalizes_legacy_types_and_constraints():
    positive_integer = ModelField(
        name="quantity",
        type="PositiveInt",
        description="Positive quantity",
    )
    constrained_list = ModelField(
        name="tags",
        type="conlist(str, min_items=1, max_items=3)",
        description="Tags",
    )

    assert positive_integer.type == "int"
    assert positive_integer.validation == {"gt": 0}
    assert constrained_list.type == "List[str]"
    assert constrained_list.validation == {"min_length": 1, "max_length": 3}

    with pytest.raises(ValidationError):
        positive_integer.type = "NegativeInt"


def test_model_field_normalizes_validation_and_removes_invalid_values():
    field = ModelField(
        name="code",
        type="EmailStr",
        description="Code",
        validation={
            "regex": "[",
            "min_items": 1,
            "allow_mutation": False,
            "const": True,
            "unknown": "ignored",
        },
    )

    assert field.type == "str"
    assert field.validation == {"min_length": 1, "frozen": True}


def test_generated_model_enforces_normalized_constraints():
    request = ExtractionRequest(
        model_name="Inventory",
        model_description="Inventory item",
        fields=[
            ModelField(
                name="quantity",
                type="PositiveInt",
                description="Positive quantity",
            )
        ],
    )
    model = ModelGenerator.from_extraction_request(request)

    with pytest.raises(ValidationError):
        model(quantity=0)


def test_nullable_json_array_generates_a_valid_pydantic_field():
    request = ExtractionRequest(
        model_name="Terms",
        model_description="Agreement terms",
        fields=[
            ModelField(
                name="deliverables",
                type="array<string>|null",
                description="Required deliverables",
            )
        ],
    )

    model = ModelGenerator.from_extraction_request(request)
    instance = model(deliverables=["report", "source code"])

    assert instance.deliverables == ["report", "source code"]
    assert get_origin(resolve_type_expression(request.fields[0].type)) is not None


def test_nested_array_uses_the_generated_item_model():
    request = ExtractionRequest(
        model_name="Agreement",
        model_description="Agreement details",
        fields=[
            ModelField(
                name="obligations",
                type="array<object>",
                description="Party obligations",
                nested_fields=[
                    ModelField(
                        name="party",
                        type="string",
                        description="Responsible party",
                    )
                ],
            )
        ],
    )

    model = ModelGenerator.from_extraction_request(request)
    annotation = model.model_fields["obligations"].annotation
    list_type = next(arg for arg in get_args(annotation) if get_origin(arg) is list)
    item_type = get_args(list_type)[0]

    assert item_type.model_fields.keys() == {"party"}
    assert (
        model(obligations=[{"party": "Consultant"}]).obligations[0].party
        == "Consultant"
    )


def test_generated_model_preserves_required_nullable_and_nested_set_semantics():
    request = ExtractionRequest(
        model_name="Agreement",
        model_description="Agreement details",
        fields=[
            ModelField(
                name="title",
                type="string",
                description="Agreement title",
                required=True,
                nullable=False,
            ),
            ModelField(
                name="parties",
                type="Set[object]",
                description="Unique parties",
                nested_fields=[
                    ModelField(name="name", type="string", description="Party name")
                ],
            ),
        ],
    )

    model = ModelGenerator.from_extraction_request(request)
    with pytest.raises(ValidationError):
        model()
    with pytest.raises(ValidationError):
        model(title=None)

    result = model(title="Consultancy", parties=[{"name": "Client"}])
    assert isinstance(result.parties, set)
    assert {party.name for party in result.parties} == {"Client"}


def test_model_field_rejects_optional_but_non_nullable_definition():
    with pytest.raises(ValidationError, match="non-required field must be nullable"):
        ModelField(
            name="title",
            type="string",
            description="Agreement title",
            nullable=False,
        )


class FakeLLMCore:
    def __init__(self, plan):
        self.plan = plan
        self.config = type("Config", (), {"planning": {}})()
        self.requests = []

    def complete(self, **kwargs):
        self.requests.append(kwargs)
        return self.plan


def test_extraction_plan_is_generated_in_one_llm_call():
    plan = ExtractionPlan(
        refined_query=QueryRefinement(refined_query="Extract terms"),
        guide=ExtractionGuide(target_columns=["invented_column"]),
        schema=ExtractionRequest(
            model_name="Terms",
            model_description="Agreement terms",
            fields=[
                ModelField(name="payment", type="string", description="Payment terms")
            ],
        ),
    )
    llm_core = FakeLLMCore(plan)
    operations = ModelOperations(llm_core)

    result = operations.generate_extraction_plan(
        query="Extract terms",
        sample_text="Payment is due monthly.",
        data_columns=["source", "pdf_path"],
    )

    assert len(llm_core.requests) == 1
    assert llm_core.requests[0]["response_model"] is ExtractionPlan
    assert llm_core.requests[0]["step"] is ExtractionStep.SCHEMA_GENERATION
    assert result.guide.target_columns == ["source", "pdf_path"]
