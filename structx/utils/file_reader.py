from pathlib import Path
from typing import Any, Callable, Dict, List, Union

import pandas as pd

from structx.core.exceptions import FileError


class FileReader:
    """Handles reading different file formats"""

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

    @classmethod
    def validate_file(cls, file_path: Union[str, Path]) -> Path:
        """
        Validate file existence and format
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileError(f"File not found: {file_path}")

        return file_path

    @classmethod
    def read_file(cls, file_path: Union[str, Path], **kwargs: Any) -> pd.DataFrame:
        """
        Read file based on its extension

        Args:
            file_path: Path to input file
            **kwargs: Additional options for file reading
                - chunk_size: Size of text chunks (for unstructured text)
                - overlap: Overlap between chunks (for unstructured text)
                - encoding: Text encoding (for unstructured text)

        Returns:
            DataFrame with file contents
        """
        file_path = cls.validate_file(file_path)
        extension = file_path.suffix.lower()

        # Handle structured data formats
        if extension in cls.STRUCTURED_EXTENSIONS:
            reader = cls.STRUCTURED_EXTENSIONS[extension]
            return reader(file_path, **kwargs)

        # Handle unstructured text formats
        elif extension in cls.TEXT_EXTENSIONS:
            return cls.read_text_file(file_path, **kwargs)

        # Handle document formats
        elif extension in cls.DOCUMENT_EXTENSIONS:
            if extension == ".pdf":
                return cls.read_pdf_file(file_path, **kwargs)
            elif extension in [".docx", ".doc"]:
                return cls.read_docx_file(file_path, **kwargs)

        # Try as text file for unknown extensions
        else:
            try:
                return cls.read_text_file(file_path, **kwargs)
            except Exception as e:
                raise FileError(
                    f"Unsupported file format: {extension}. "
                    f"Supported formats: "
                    f"{', '.join(cls.STRUCTURED_EXTENSIONS.keys() + cls.TEXT_EXTENSIONS + cls.DOCUMENT_EXTENSIONS)}"
                ) from e

    @classmethod
    def read_text_file(cls, file_path: Union[str, Path], **kwargs) -> pd.DataFrame:
        """Read text file into DataFrame with chunking"""
        encoding: str = kwargs.pop("encoding", "utf-8")
        chunk_size: int = kwargs.pop("chunk_size", 1000)
        overlap: int = kwargs.pop("overlap", 100)

        try:
            text = file_path.open(encoding=encoding).read()

            # Split into chunks with overlap
            chunks = []
            for i in range(0, len(text), chunk_size - overlap):
                chunks.append(text[i : i + chunk_size])

            # Create DataFrame with chunks and metadata
            return pd.DataFrame(
                {
                    "text": chunks,
                    "chunk_id": range(len(chunks)),
                    "source": str(file_path),
                }
            )
        except Exception as e:
            raise FileError(f"Error reading text file {file_path}: {str(e)}") from e

    @classmethod
    def read_pdf_file(cls, file_path: Union[str, Path], **kwargs) -> pd.DataFrame:
        """Read PDF file into DataFrame with chunking"""
        try:
            import pypdf  # Import here to avoid dependency if not used
        except ImportError:
            raise ImportError(
                "pypdf package is required for PDF support. "
                "Install it with: pip install pypdf"
            )

        chunk_size: int = kwargs.pop("chunk_size", 1000)
        overlap: int = kwargs.pop("overlap", 100)

        try:
            # Read PDF
            pdf = pypdf.PdfReader(file_path)

            chunks = []
            page_numbers = []

            # Process each page
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text() + "\n\n"

                # Split page text into chunks if needed
                if len(page_text) <= chunk_size:
                    chunks.append(page_text)
                    page_numbers.append(page_num + 1)
                else:
                    # Split into chunks with overlap
                    for i in range(0, len(page_text), chunk_size - overlap):
                        chunks.append(page_text[i : i + chunk_size])
                        page_numbers.append(page_num + 1)

            # Create DataFrame with chunks and metadata
            return pd.DataFrame(
                {
                    "text": chunks,
                    "chunk_id": range(len(chunks)),
                    "page": page_numbers,
                    "source": str(file_path),
                    "total_pages": len(pdf.pages),
                }
            )
        except Exception as e:
            raise FileError(f"Error reading PDF file {file_path}: {str(e)}") from e

    @classmethod
    def read_docx_file(cls, file_path: Union[str, Path], **kwargs) -> pd.DataFrame:
        """Read DOCX file into DataFrame with chunking"""
        try:
            import docx  # Import here to avoid dependency if not used
        except ImportError:
            raise ImportError(
                "python-docx package is required for DOCX support. "
                "Install it with: pip install python-docx"
            )

        chunk_size = kwargs.pop("chunk_size", 1000)
        overlap = kwargs.pop("overlap", 100)

        try:
            # Read DOCX
            doc = docx.Document(file_path)
            text = "\n\n".join([para.text for para in doc.paragraphs])

            # Split into chunks with overlap
            chunks = []
            for i in range(0, len(text), chunk_size - overlap):
                chunks.append(text[i : i + chunk_size])

            # Create DataFrame with chunks and metadata
            return pd.DataFrame(
                {
                    "text": chunks,
                    "chunk_id": range(len(chunks)),
                    "source": str(file_path),
                }
            )
        except Exception as e:
            raise FileError(f"Error reading DOCX file {file_path}: {str(e)}") from e
