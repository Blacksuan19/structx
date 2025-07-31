import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Union

import pandas as pd

from structx.core.exceptions import FileError


class FileReader:
    """
    Handles reading different file formats with a unified approach for unstructured documents.

    For unstructured documents (TXT, DOCX, PDF), the default strategy is to convert
    everything to PDF and use instructor's multimodal PDF support. This eliminates
    the need for manual chunking and provides the best context preservation.
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

    TEXT_EXTENSIONS: List[str] = [".txt", ".md", ".py", ".html", ".xml", ".log", ".rst"]
    DOCUMENT_EXTENSIONS: List[str] = [".pdf", ".docx", ".doc"]

    @staticmethod
    def read_file(file_path: Union[str, Path], **kwargs: Any) -> pd.DataFrame:
        """
        Read a file and return its content based on the specified mode.

        For unstructured documents (TXT, DOCX, PDF), the default approach is to
        convert everything to PDF and use instructor's multimodal PDF support.
        This eliminates the need for manual chunking and provides the best
        context preservation.

        Args:
            file_path: Path to the file to read
            **kwargs: Additional options for file reading including:
                - mode: Reading mode - 'multimodal_pdf' (default), 'simple_text', or 'simple_pdf'
                - use_multimodal: Use instructor's multimodal support (default: True)
                - file_options: Additional options for reading the file

        Returns:
            pandas DataFrame with the appropriate structure for the specified mode

        Raises:
            FileError: If file cannot be read or processed
        """
        # Extract parameters from kwargs
        mode = kwargs.get("mode", "multimodal_pdf")
        use_multimodal = kwargs.get("use_multimodal", True)
        file_options = kwargs.get("file_options", {})

        # Handle legacy parameter structure
        if use_multimodal and mode == "multimodal_pdf":
            mode = "multimodal_pdf"
        elif not use_multimodal:
            mode = "simple_text"
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileError(f"File not found: {file_path}")

            file_extension = file_path.suffix.lower()

            # Handle structured files (return DataFrame)
            if file_extension in FileReader.STRUCTURED_EXTENSIONS:
                read_func = FileReader.STRUCTURED_EXTENSIONS[file_extension]
                return read_func(file_path, **file_options)

            # Handle unstructured files
            if (
                file_extension in FileReader.TEXT_EXTENSIONS
                or file_extension in FileReader.DOCUMENT_EXTENSIONS
            ):
                if mode == "multimodal_pdf":
                    # Convert all unstructured documents to PDF for instructor's multimodal support
                    pdf_path = FileReader._convert_to_pdf(file_path)
                    # Return DataFrame with required structure for multimodal processing
                    return pd.DataFrame(
                        {
                            "pdf_path": [str(pdf_path)],
                            "source": [str(file_path)],
                            "multimodal": [True],
                            "file_type": ["pdf"],
                        }
                    )
                elif mode == "simple_text":
                    # Fallback: simple text reading with chunking
                    return FileReader._read_as_text_chunks(file_path, kwargs)
                elif mode == "simple_pdf":
                    # Fallback: simple PDF reading (if it's already a PDF)
                    if file_extension == ".pdf":
                        return FileReader._read_pdf_chunks(file_path, kwargs)
                    else:
                        # Convert to PDF first, then read simply
                        pdf_path = FileReader._convert_to_pdf(file_path)
                        return FileReader._read_pdf_chunks(Path(pdf_path), kwargs)

            raise FileError(f"Unsupported file type: {file_extension}")

        except Exception as e:
            raise FileError(f"Error reading file {file_path}: {str(e)}")

    @staticmethod
    def _convert_to_pdf(file_path: Path) -> str:
        """
        Convert any supported document to PDF using docling -> markdown -> PDF pipeline.

        Returns the path to the generated PDF file for use with instructor's multimodal support.
        """
        try:
            file_extension = file_path.suffix.lower()

            # If it's already a PDF, return as-is
            if file_extension == ".pdf":
                return str(file_path)

            # For simple text files, read directly
            if file_extension in FileReader.TEXT_EXTENSIONS:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return FileReader._markdown_to_pdf(content, file_path.stem)

            # For document files, use docling to convert to markdown first
            elif (
                file_extension in FileReader.DOCUMENT_EXTENSIONS
                and file_extension != ".pdf"
            ):
                try:
                    from docling.document_converter import DocumentConverter

                    converter = DocumentConverter()
                    result = converter.convert(str(file_path))
                    markdown_content = result.document.export_to_markdown()

                    # Convert markdown to PDF
                    return FileReader._markdown_to_pdf(markdown_content, file_path.stem)

                except ImportError:
                    raise FileError(
                        f"docling not available for {file_extension} conversion"
                    )
            else:
                raise FileError(
                    f"Unsupported file type for conversion: {file_extension}"
                )

        except Exception as e:
            raise FileError(f"Error converting {file_path} to PDF: {str(e)}")

    @staticmethod
    def _markdown_to_pdf(markdown_content: str, filename: str) -> str:
        """Convert markdown content to PDF and return the path."""

        import markdown
        import weasyprint

        # Convert markdown to HTML
        md = markdown.Markdown(extensions=["extra", "codehilite"])
        html_content = md.convert(markdown_content)

        # Add basic CSS styling
        html_with_css = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                    h1, h2, h3 {{ color: #333; }}
                    pre {{ background-color: #f4f4f4; padding: 10px; border-radius: 5px; }}
                    code {{ background-color: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """

        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".pdf", prefix=f"{filename}_"
        ) as tmp_file:
            pdf_path = tmp_file.name

        # Generate PDF with weasyprint
        weasyprint.HTML(string=html_with_css).write_pdf(pdf_path)
        return pdf_path

    @staticmethod
    def _read_as_text_chunks(file_path: Path, kwargs: Dict[str, Any]) -> pd.DataFrame:
        """Simple text reading fallback with chunking."""
        try:
            file_extension = file_path.suffix.lower()
            chunk_size = kwargs.get("chunk_size", 1000)
            chunk_overlap = kwargs.get("chunk_overlap", 200)

            if file_extension in FileReader.TEXT_EXTENSIONS:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            elif file_extension == ".docx":
                try:
                    from docx import Document

                    doc = Document(file_path)
                    content = "\n".join(
                        [paragraph.text for paragraph in doc.paragraphs]
                    )
                except ImportError:
                    raise FileError("python-docx not available for DOCX reading")
            elif file_extension == ".pdf":
                content = FileReader._extract_pdf_text(file_path)
            else:
                raise FileError(f"Cannot read {file_extension} as simple text")

            # Simple chunking
            chunks = []
            for i in range(0, len(content), chunk_size - chunk_overlap):
                chunks.append(content[i : i + chunk_size])

            return pd.DataFrame(
                {
                    "text": chunks,
                    "chunk_id": range(len(chunks)),
                    "source": str(file_path),
                    "processing_method": ["simple_text"] * len(chunks),
                }
            )

        except Exception as e:
            raise FileError(f"Error reading {file_path} as text: {str(e)}")

    @staticmethod
    def _read_pdf_chunks(file_path: Path, kwargs: Dict[str, Any]) -> pd.DataFrame:
        """Simple PDF text extraction fallback with chunking."""
        try:
            chunk_size = kwargs.get("chunk_size", 1000)
            chunk_overlap = kwargs.get("chunk_overlap", 200)

            content = FileReader._extract_pdf_text(file_path)

            # Simple chunking
            chunks = []
            for i in range(0, len(content), chunk_size - chunk_overlap):
                chunks.append(content[i : i + chunk_size])

            return pd.DataFrame(
                {
                    "text": chunks,
                    "chunk_id": range(len(chunks)),
                    "source": str(file_path),
                    "processing_method": ["simple_pdf"] * len(chunks),
                }
            )

        except Exception as e:
            raise FileError(f"Error reading PDF {file_path}: {str(e)}")

    @staticmethod
    def _extract_pdf_text(file_path: Path) -> str:
        """Extract text from PDF file using PyPDF2."""
        try:
            import PyPDF2

            with open(file_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text

        except ImportError:
            raise FileError("PyPDF2 not available for simple PDF reading")
        except Exception as e:
            raise FileError(f"Error reading PDF {file_path}: {str(e)}")

    @staticmethod
    def get_file_type(file_path: Union[str, Path]) -> str:
        """Get the type of file based on its extension"""
        file_extension = Path(file_path).suffix.lower()

        if file_extension in FileReader.STRUCTURED_EXTENSIONS:
            return "structured"
        elif file_extension in FileReader.TEXT_EXTENSIONS:
            return "text"
        elif file_extension in FileReader.DOCUMENT_EXTENSIONS:
            return "document"
        else:
            return "unknown"
