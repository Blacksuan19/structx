# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Support for more file formats
- Additional configuration options
- Enhanced error handling

## [0.2.1] - 2025-03-02

### Added

- Support for unstructured text extraction
- PDF document processing
- DOCX document processing
- Automatic retry mechanism with exponential backoff
- ExtractionResult class for better result handling

### Changed

- Improved model generation for complex nested structures
- Enhanced error handling and reporting
- Better handling of large documents with chunking

### Fixed

- Issue with nested model generation
- Memory usage optimization for large datasets
- Type conversion issues in DataFrame output

## [0.2.0] - 2025-03-02

### Added

- Multiple query processing with `extract_queries`
- Async support for all extraction methods
- Custom model support
- Expanded documentation and examples

### Changed

- Refactored extraction pipeline for better performance
- Improved type safety throughout the codebase
- Enhanced configuration options

## [0.1.0] - 2025-02-19

### Added

- Initial release
- Basic extraction functionality
- Support for CSV, Excel, and JSON files
- Dynamic model generation
- Multi-threaded processing
