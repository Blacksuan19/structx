"""Content context helpers used during extraction planning."""

from structx.core.input import PreparedInput


class ContentAnalyzer:
    """Describe explicitly prepared document inputs for schema planning."""

    @staticmethod
    def detect_content_type_and_context(prepared_input: PreparedInput) -> str:
        pdf_rows = list(prepared_input.pdf_rows.values())[:5]
        if not pdf_rows:
            return "tabular data with structured columns"

        file_types = {
            row.source.suffix.lower().lstrip(".") or "document" for row in pdf_rows
        }
        examples = [row.source.name for row in pdf_rows]
        context = f"document(s) of type: {', '.join(sorted(file_types))}"
        if examples:
            context += f". Examples: {', '.join(examples[:3])}"
        return context
