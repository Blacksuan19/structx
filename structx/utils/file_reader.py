import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Union

import pandas as pd

from structx.core.exceptions import FileError


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
    def read_file(file_path: Union[str, Path], **kwargs: Any) -> pd.DataFrame:
        """
        Read a file and return its content.

        Structured files are read directly as tabular data. Document-like files
        are converted through the Docling -> HTML -> PDF multimodal pipeline.

        Args:
            file_path: Path to the file to read
            **kwargs: Additional options for structured file reading, including:
                - file_options: Additional options for pandas readers

        Returns:
            pandas DataFrame with the appropriate structure for the specified mode

        Raises:
            FileError: If file cannot be read or processed
        """
        file_options = kwargs.get("file_options", {})

        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileError(f"File not found: {file_path}")

            file_extension = file_path.suffix.lower()

            # Handle structured files (return DataFrame)
            if file_extension in FileReader.STRUCTURED_EXTENSIONS:
                read_func = FileReader.STRUCTURED_EXTENSIONS[file_extension]
                return read_func(file_path, **file_options)

            # Existing PDFs can be sent directly to multimodal models.
            if file_extension in FileReader.PDF_EXTENSIONS:
                return pd.DataFrame(
                    {
                        "pdf_path": [str(file_path)],
                        "source": [str(file_path)],
                        "multimodal": [True],
                        "file_type": ["pdf"],
                    }
                )

            # Convert document-like files to PDF for multimodal processing.
            if file_extension in FileReader.DOCLING_EXTENSIONS:
                pdf_path = FileReader._convert_to_pdf(file_path)
                return pd.DataFrame(
                    {
                        "pdf_path": [str(pdf_path)],
                        "source": [str(file_path)],
                        "multimodal": [True],
                        "file_type": ["pdf"],
                    }
                )

            raise FileError(f"Unsupported file type: {file_extension}")

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
    def _convert_to_pdf(file_path: Path) -> str:
        """
        Convert a supported document to PDF using Docling -> HTML -> WeasyPrint.

        Returns the path to the generated PDF file for use with instructor's multimodal support.
        """
        try:
            import weasyprint

            converter = FileReader._create_document_converter()
            result = converter.convert(str(file_path))
            html_content = result.document.export_to_html()

            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".pdf", prefix=f"{file_path.stem}_"
            ) as tmp_file:
                pdf_path = tmp_file.name

            weasyprint.HTML(
                string=html_content,
                base_url=str(file_path.parent),
            ).write_pdf(pdf_path)
            return pdf_path

        except ImportError as e:
            raise FileError(
                "Document conversion requires optional document dependencies. "
                "Install them with: pip install 'structx[docs]'"
            ) from e

        except Exception as e:
            raise FileError(f"Error converting {file_path} to PDF: {str(e)}")

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
