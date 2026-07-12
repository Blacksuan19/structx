from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

import pytest
from pydantic import BaseModel, Field, field_validator

from structx import (
    ExtractionRequest,
    ModelField,
    get_type_capabilities,
    model_from_extraction_request,
    model_to_extraction_request,
)
from structx.core.exceptions import ModelGenerationError


class Address(BaseModel):
    street: str = Field(min_length=2)
    postal_code: Optional[str] = None


class ManualRecord(BaseModel):
    record_id: UUID
    amount: Decimal = Decimal("1.50")
    issued_on: date
    tags: list[str]
    unique_codes: set[int]
    address: Address


def field_by_name(request: ExtractionRequest, name: str) -> ModelField:
    return next(field for field in request.fields if field.name == name)


def test_type_capabilities_are_canonical_and_alias_free():
    capabilities = get_type_capabilities()

    scalar_ids = {item.id for item in capabilities.scalars}
    container_ids = {item.id for item in capabilities.containers}

    assert scalar_ids == {
        "Any",
        "bool",
        "date",
        "datetime",
        "Decimal",
        "float",
        "int",
        "str",
        "time",
        "UUID",
    }
    assert container_ids == {"Dict", "FrozenSet", "List", "Set", "Tuple"}
    assert "string" not in scalar_ids
    assert "array" not in container_ids
    assert capabilities.modifiers.required is True
    assert capabilities.modifiers.nullable is True


def test_manual_pydantic_model_round_trips_through_extraction_request():
    request = model_to_extraction_request(
        ManualRecord,
        model_description="A manually defined record",
    )

    assert request.model_name == "ManualRecord"
    assert request.model_description == "A manually defined record"

    amount = field_by_name(request, "amount")
    assert amount.type == "Decimal"
    assert amount.required is False
    assert amount.nullable is False
    assert amount.has_default is True
    assert amount.default == "1.50"

    assert field_by_name(request, "tags").type == "List[str]"
    assert field_by_name(request, "unique_codes").type == "Set[int]"

    address = field_by_name(request, "address")
    assert address.type == "Dict[str, Any]"
    assert address.nested_fields is not None
    assert [field.name for field in address.nested_fields] == [
        "street",
        "postal_code",
    ]
    assert address.nested_fields[0].validation == {"min_length": 2}

    stored_definition = request.model_dump(mode="json")
    rebuilt = model_from_extraction_request(stored_definition)
    value = rebuilt(
        record_id="64c26f2a-8fd0-4ef8-b1ec-7969ebbe91cb",
        issued_on="2026-07-11",
        tags=["one", "two"],
        unique_codes=[1, 1, 2],
        address={"street": "Main Street"},
    )

    assert value.record_id == UUID("64c26f2a-8fd0-4ef8-b1ec-7969ebbe91cb")
    assert value.amount == Decimal("1.50")
    assert value.issued_on == date(2026, 7, 11)
    assert value.unique_codes == {1, 2}
    assert value.address.street == "Main Street"


def test_extraction_request_methods_preserve_the_original_definition():
    request = ExtractionRequest(
        model_name="Invoice",
        model_description="Invoice fields",
        fields=[
            ModelField(
                name="invoice_number",
                type="string",
                description="Unique invoice number",
                required=True,
                nullable=False,
                validation={"min_length": 2},
            )
        ],
    )

    model = model_from_extraction_request(request)
    restored = model_to_extraction_request(model)

    assert restored == request
    assert model(invoice_number="A1").invoice_number == "A1"


def test_model_conversion_does_not_inherit_base_model_documentation():
    class UndocumentedModel(BaseModel):
        value: str

    request = model_to_extraction_request(UndocumentedModel)

    assert request.model_description == ""


def test_model_conversion_rejects_executable_model_behavior():
    class ValidatedModel(BaseModel):
        value: str

        @field_validator("value")
        @classmethod
        def normalize_value(cls, value: str) -> str:
            return value.strip()

    with pytest.raises(ModelGenerationError, match="Custom validators"):
        model_to_extraction_request(ValidatedModel)


def test_model_conversion_rejects_default_factories():
    class FactoryModel(BaseModel):
        values: list[str] = Field(default_factory=list)

    with pytest.raises(ModelGenerationError, match="Default factories"):
        model_to_extraction_request(FactoryModel)
