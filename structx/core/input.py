"""Typed contracts for prepared extraction inputs."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd


@dataclass(frozen=True)
class PdfRow:
    """A PDF payload associated with one source row.

    Attributes:
        pdf_path: PDF sent to Instructor's multimodal input.
        source: Original user-supplied document path. For converted documents,
            this differs from ``pdf_path``.
    """

    pdf_path: Path
    source: Path


RowPayload = Union[str, PdfRow]


@dataclass
class PreparedInput:
    """Normalized extraction input and its owned resources.

    ``InputProcessor`` creates this contract before planning or row processing.
    Application code normally receives an ``ExtractionResult`` instead; this
    type is primarily useful when calling ``FileReader`` directly.

    Attributes:
        dataframe: Source rows retained for planning, provenance, and optional
            DataFrame output.
        pdf_rows: Positional row mappings for multimodal PDF payloads.
        planning_sample: Text extracted once from a converted document for
            schema planning. Existing PDFs usually leave this unset and are
            attached directly to the planning request.
        owned_paths: Temporary files that must be deleted after processing.
            ``InputProcessor.prepared`` handles this automatically.
    """

    dataframe: pd.DataFrame
    pdf_rows: Dict[int, PdfRow] = field(default_factory=dict)
    planning_sample: Optional[str] = None
    owned_paths: List[Path] = field(default_factory=list)
    _closed: bool = field(default=False, init=False, repr=False)

    @property
    def closed(self) -> bool:
        """Whether temporary resources owned by this input were released."""
        return self._closed

    def ensure_open(self) -> None:
        """Reject reuse after explicit cleanup."""
        if self._closed:
            raise RuntimeError("Prepared input is closed")

    def close(self) -> None:
        """Release owned temporary resources. This operation is idempotent."""
        if self._closed:
            return
        for path in self.owned_paths:
            Path(path).unlink(missing_ok=True)
        self.owned_paths.clear()
        self._closed = True

    def row_payload(
        self, position: int, row: pd.Series, target_columns: List[str]
    ) -> RowPayload:
        """Build the text or PDF payload for one positional input row."""
        self.ensure_open()
        pdf_row = self.pdf_rows.get(position)
        if pdf_row is not None:
            return pdf_row
        return row[target_columns].to_markdown()
