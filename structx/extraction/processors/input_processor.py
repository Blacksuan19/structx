"""Input validation, normalization, and temporary-resource ownership."""

import asyncio
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator, List, Union

import pandas as pd

from structx.core.exceptions import FileError
from structx.core.input import PreparedInput
from structx.utils.file_reader import FileReader

InputData = Union[str, Path, pd.DataFrame, List[Dict[str, str]], PreparedInput]


class InputProcessor:
    """Prepare supported inputs and own any temporary files they create."""

    @contextmanager
    def prepared(
        self, data: InputData, **kwargs: Any
    ) -> Generator[PreparedInput, None, None]:
        """Yield normalized data and always release owned temporary files."""
        owns_prepared_input = not isinstance(data, PreparedInput)
        prepared_input = self.prepare(data, **kwargs)
        try:
            yield prepared_input
        finally:
            if owns_prepared_input:
                self.cleanup(prepared_input)

    @asynccontextmanager
    async def prepared_async(
        self, data: InputData, **kwargs: Any
    ) -> AsyncGenerator[PreparedInput, None]:
        """Prepare blocking file inputs off-loop and own their lifetime."""
        owns_prepared_input = not isinstance(data, PreparedInput)
        prepared_input = await asyncio.to_thread(self.prepare, data, **kwargs)
        try:
            yield prepared_input
        finally:
            if owns_prepared_input:
                await asyncio.to_thread(self.cleanup, prepared_input)

    def prepare(self, data: InputData, **kwargs: Any) -> PreparedInput:
        """Normalize a supported input and retain its explicit resource metadata."""
        if isinstance(data, PreparedInput):
            data.ensure_open()
            prepared_input = data
        elif isinstance(data, pd.DataFrame):
            prepared_input = PreparedInput(dataframe=data)
        elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
            prepared_input = PreparedInput(dataframe=pd.DataFrame(data))
        elif isinstance(data, Path):
            path = data.expanduser()
            if not path.exists():
                raise FileError(f"File not found: {path}")
            prepared_input = FileReader.read_file(path, **kwargs)
        elif isinstance(data, str):
            if not data.strip():
                raise ValueError("Input text is empty")
            path = Path(data).expanduser()
            try:
                path_exists = path.exists()
            except OSError:
                path_exists = False

            if path_exists:
                prepared_input = FileReader.read_file(path, **kwargs)
            elif self._looks_like_file_path(data, path):
                raise FileError(f"File not found: {path}")
            else:
                prepared_input = PreparedInput(dataframe=pd.DataFrame({"text": [data]}))
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

        dataframe = prepared_input.dataframe
        if dataframe.empty:
            raise ValueError("Input data is empty")
        if not dataframe.columns.is_unique:
            raise ValueError("Column names must be unique")

        if any(not isinstance(column, str) for column in dataframe.columns):
            normalized_columns = [str(column) for column in dataframe.columns]
            if len(set(normalized_columns)) != len(normalized_columns):
                raise ValueError("Column names must be unique after string conversion")
            dataframe = dataframe.copy()
            dataframe.columns = normalized_columns
            prepared_input.dataframe = dataframe

        return prepared_input

    @staticmethod
    def _looks_like_file_path(value: str, path: Path) -> bool:
        supported_extensions = {
            *FileReader.STRUCTURED_EXTENSIONS,
            *FileReader.PDF_EXTENSIONS,
            *FileReader.DOCLING_EXTENSIONS,
        }
        windows_absolute = (
            len(value) >= 3 and value[1] == ":" and value[2] in {"/", "\\"}
        )
        return (
            path.suffix.lower() in supported_extensions
            or path.is_absolute()
            or value.startswith(("./", "../", "~/"))
            or windows_absolute
        )

    @staticmethod
    def cleanup(prepared_input: PreparedInput) -> None:
        """Remove temporary artifacts owned by a prepared input."""
        prepared_input.close()
