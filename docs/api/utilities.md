# Utilities

Low-level file handling utilities. Most applications should use `Extractor`,
which adds validation, temporary-resource cleanup, planning, and result
collection around these operations.

::: structx.utils.file_reader.FileReader
    options:
      show_bases: false
      heading_level: 2

`read_file()` returns a [`PreparedInput`](inputs.md#preparedinput), not a bare
DataFrame. Direct callers own temporary converted PDFs and should follow the
[resource ownership](inputs.md#resource-ownership) guidance.
