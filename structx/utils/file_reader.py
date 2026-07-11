import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import unquote, urlparse

import pandas as pd

from structx.core.exceptions import FileError
from structx.core.input import PdfRow, PreparedInput


class FileReader:
    """
    Handles reading different file formats.

    Structured files are read as pandas DataFrames. Document-like files are parsed
    with the optional Docling extra, rendered to PDF with WeasyPrint, and then
    passed to instructor's multimodal PDF support.
    """

    STRUCTURED_EXTENSIONS: Dict[
        str, Callable[[Union[str, Path], Dict], pd.DataFrame]
    ] = {
        ".csv": pd.read_csv,
        ".xlsx": pd.read_excel,
        ".xls": pd.read_excel,
        ".json": pd.read_json,
        ".parquet": pd.read_parquet,
        ".feather": pd.read_feather,
    }

    PDF_EXTENSIONS: List[str] = [".pdf"]

    DOCLING_EXTENSIONS: List[str] = [
        ".doc",
        ".docx",
        ".ppt",
        ".pptx",
        ".odt",
        ".ods",
        ".odp",
        ".epub",
        ".md",
        ".markdown",
        ".adoc",
        ".asciidoc",
        ".tex",
        ".html",
        ".xhtml",
        ".xml",
        ".txt",
        ".py",
        ".log",
        ".rst",
        ".png",
        ".jpg",
        ".jpeg",
        ".tiff",
        ".bmp",
        ".webp",
        ".webvtt",
        ".vtt",
    ]

    @staticmethod
    def read_file(file_path: Union[str, Path], **kwargs: Any) -> PreparedInput:
        """
        Read a file and return its content.

        Structured files are read directly as tabular data. Document-like files
        are converted through the Docling -> HTML -> PDF multimodal pipeline.

        Args:
            file_path: Path to the file to read
            **kwargs: Additional options for structured file reading, including:
                - file_options: Additional options for pandas readers

        Returns:
            Prepared input containing normalized source rows, any PDF payloads,
            a planning sample when available, and owned temporary paths.

            When this low-level method converts a document, the caller owns the
            returned temporary paths. Prefer ``Extractor`` or
            ``InputProcessor.prepared`` for automatic cleanup.

        Raises:
            FileError: If file cannot be read or processed
        """
        file_options = kwargs.get("file_options", {})

        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileError(f"File not found: {file_path}")
            if not file_path.is_file():
                raise FileError(f"Path is not a file: {file_path}")
            if file_path.stat().st_size == 0:
                raise FileError(f"File is empty: {file_path}")

            file_extension = file_path.suffix.lower()

            # Handle structured files (return DataFrame)
            if file_extension in FileReader.STRUCTURED_EXTENSIONS:
                read_func = FileReader.STRUCTURED_EXTENSIONS[file_extension]
                return PreparedInput(dataframe=read_func(file_path, **file_options))

            # Existing PDFs can be sent directly to multimodal models.
            if file_extension in FileReader.PDF_EXTENSIONS:
                with file_path.open("rb") as pdf_file:
                    header = pdf_file.read(1024)
                if b"%PDF-" not in header:
                    raise FileError(f"Invalid PDF file: {file_path}")
                return PreparedInput(
                    dataframe=pd.DataFrame({"source": [str(file_path)]}),
                    pdf_rows={0: PdfRow(pdf_path=file_path, source=file_path)},
                )

            # Convert document-like files to PDF for multimodal processing.
            if file_extension in FileReader.DOCLING_EXTENSIONS:
                pdf_path, content_sample = FileReader._convert_document(file_path)
                return PreparedInput(
                    dataframe=pd.DataFrame({"source": [str(file_path)]}),
                    pdf_rows={0: PdfRow(pdf_path=Path(pdf_path), source=file_path)},
                    planning_sample=content_sample,
                    owned_paths=[Path(pdf_path)],
                )

            raise FileError(f"Unsupported file type: {file_extension}")

        except FileError:
            raise
        except Exception as e:
            raise FileError(f"Error reading file {file_path}: {str(e)}")

    @staticmethod
    def _create_document_converter():
        """Create a Docling converter configured for multimodal PDF rendering."""
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, ImageFormatOption

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        pipeline_options.do_table_structure = False

        return DocumentConverter(
            format_options={
                InputFormat.IMAGE: ImageFormatOption(pipeline_options=pipeline_options),
            }
        )

    @staticmethod
    def _local_url_fetcher(default_fetcher: Callable, base_dir: Path) -> Callable:
        """Allow generated HTML to load data URLs and local sibling assets only."""
        allowed_root = base_dir.resolve()

        def fetch(url: str, *args: Any, **kwargs: Any) -> Any:
            parsed = urlparse(url)
            if parsed.scheme == "data":
                return default_fetcher(url, *args, **kwargs)
            if parsed.scheme == "file":
                resource = Path(unquote(parsed.path)).resolve()
                if resource.is_relative_to(allowed_root):
                    return default_fetcher(url, *args, **kwargs)
            raise FileError(f"Blocked external document resource: {url}")

        return fetch

    @staticmethod
    def _convert_document(file_path: Path) -> tuple[str, str]:
        """Convert a document once and return its PDF path and text sample."""
        pdf_path: Optional[str] = None
        try:
            import weasyprint

            result = FileReader._create_document_converter().convert(str(file_path))
            html_content = result.document.export_to_html()
            document_text = result.document.export_to_text()
            content_sample = document_text[:2000]

            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".pdf", prefix=f"{file_path.stem}_"
            ) as tmp_file:
                pdf_path = tmp_file.name

            weasyprint.HTML(
                string=html_content,
                base_url=str(file_path.parent),
                url_fetcher=FileReader._local_url_fetcher(
                    weasyprint.default_url_fetcher, file_path.parent
                ),
            ).write_pdf(pdf_path)
            rendered_pdf = Path(pdf_path)
            if (
                not rendered_pdf.is_file()
                or rendered_pdf.stat().st_size == 0
                or not FileReader._has_pdf_header(rendered_pdf)
            ):
                raise FileError(
                    f"Document conversion produced an invalid PDF: {file_path}"
                )
            return pdf_path, content_sample

        except ImportError as e:
            raise FileError(
                "Document conversion requires optional document dependencies. "
                "Install them with: pip install 'structx[docs]'"
            ) from e

        except FileError:
            if pdf_path:
                Path(pdf_path).unlink(missing_ok=True)
            raise
        except Exception as e:
            if pdf_path:
                Path(pdf_path).unlink(missing_ok=True)
            raise FileError(f"Error converting {file_path} to PDF: {str(e)}")

    @staticmethod
    def _has_pdf_header(file_path: Path) -> bool:
        with file_path.open("rb") as pdf_file:
            return pdf_file.read(4) == b"%PDF"

    @staticmethod
    def extract_text_sample(file_path: Union[str, Path], max_chars: int = 2000) -> str:
        """Extract a text sample from a document using Docling."""
        file_path = Path(file_path)
        if file_path.suffix.lower() in FileReader.PDF_EXTENSIONS:
            return ""

        try:
            result = FileReader._create_document_converter().convert(str(file_path))
            return result.document.export_to_text()[:max_chars]
        except ImportError as e:
            raise FileError(
                "Text sampling requires optional document dependencies. "
                "Install them with: pip install 'structx[docs]'"
            ) from e
        except Exception as e:
            raise FileError(f"Error extracting sample from {file_path}: {str(e)}")

    @staticmethod
    def get_file_type(file_path: Union[str, Path]) -> str:
        """Get the type of file based on its extension"""
        file_extension = Path(file_path).suffix.lower()

        if file_extension in FileReader.STRUCTURED_EXTENSIONS:
            return "structured"
        elif (
            file_extension in FileReader.PDF_EXTENSIONS
            or file_extension in FileReader.DOCLING_EXTENSIONS
        ):
            return "document"
        else:
            return "unknown"
