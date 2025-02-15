from pathlib import Path
from typing import Union

import pandas as pd

from structx.core.exceptions import FileError


class FileReader:
    """Handles reading different file formats with validation"""

    SUPPORTED_EXTENSIONS = {
        ".csv": pd.read_csv,
        ".xlsx": pd.read_excel,
        ".xls": pd.read_excel,
        ".json": pd.read_json,
        ".parquet": pd.read_parquet,
    }

    @classmethod
    def validate_file(cls, file_path: Union[str, Path]) -> Path:
        """
        Validate file existence and format

        Args:
            file_path: Path to file

        Returns:
            Path object of validated file

        Raises:
            FileError: If file doesn't exist or format is unsupported
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileError(f"File not found: {file_path}")

        if file_path.suffix.lower() not in cls.SUPPORTED_EXTENSIONS:
            raise FileError(
                f"Unsupported file format: {file_path.suffix}. "
                f"Supported formats: {', '.join(cls.SUPPORTED_EXTENSIONS.keys())}"
            )

        return file_path

    @classmethod
    def read_file(cls, file_path: Union[str, Path], **kwargs) -> pd.DataFrame:
        """
        Read file based on its extension with validation

        Args:
            file_path: Path to file
            **kwargs: Additional arguments for the reader function

        Returns:
            DataFrame containing file contents

        Raises:
            FileError: If file reading fails
        """
        try:
            file_path = cls.validate_file(file_path)
            reader = cls.SUPPORTED_EXTENSIONS[file_path.suffix.lower()]

            df = reader(file_path, **kwargs)

            if df.empty:
                raise FileError(f"File {file_path} is empty")

            return df

        except Exception as e:
            if isinstance(e, FileError):
                raise
            raise FileError(f"Error reading file {file_path}: {str(e)}")

    @classmethod
    def get_sample(
        cls, file_path: Union[str, Path], n: int = 1, **kwargs
    ) -> pd.DataFrame:
        """
        Get sample rows from file with validation

        Args:
            file_path: Path to file
            n: Number of rows to sample
            **kwargs: Additional arguments for the reader function

        Returns:
            DataFrame containing sampled rows

        Raises:
            FileError: If sampling fails
        """
        if n < 1:
            raise FileError("Sample size must be at least 1")

        kwargs["nrows"] = n
        return cls.read_file(file_path, **kwargs)
