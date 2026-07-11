from types import SimpleNamespace

from instructor.processing.multimodal import PDF
from pydantic import BaseModel

from structx.core.models import ExtractionGuide, QueryRefinement
from structx.extraction.engines.extraction_engine import ExtractionEngine


class Contact(BaseModel):
    name: str


class FakeLLMCore:
    def __init__(self):
        self.config = SimpleNamespace(extraction={})
        self.request = None

    def complete_with_retry(self, **kwargs):
        self.request = kwargs
        return kwargs["response_model"](items=[Contact(name="Ada Lovelace")])


def test_extract_with_multimodal_pdf_uses_current_instructor_api(sample_pdf_path):
    llm_core = FakeLLMCore()
    engine = ExtractionEngine(llm_core)

    result = engine.extract_with_multimodal_pdf(
        pdf_path=str(sample_pdf_path),
        extraction_model=Contact,
        refined_query=QueryRefinement(
            refined_query="Extract the contact name",
            data_characteristics=None,
            structural_requirements=None,
        ),
        guide=ExtractionGuide(
            target_columns=["pdf_path"],
            structural_patterns={},
            relationship_rules=[],
            organization_principles=[],
        ),
    )

    assert result == [Contact(name="Ada Lovelace")]
    assert llm_core.request is not None
    content = llm_core.request["messages"][1]["content"]
    assert isinstance(content[1], PDF)
