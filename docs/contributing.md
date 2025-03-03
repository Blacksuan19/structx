# Contributing

Thank you for your interest in contributing to `structx`! This document provides
guidelines and instructions for contributing to the project.

## Getting Started

1. **Fork the Repository**: Start by forking the
   [structx repository](https://github.com/yourusername/structx).

2. **Clone Your Fork**:

```bash
git clone https://github.com/your-username/structx.git
cd structx
```

3. **Set Up Development Environment**:

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev,docs]"
```

4. **Create a Branch**:

```bash
git checkout -b feature/your-feature-name
```

## Development Guidelines

### Code Style

We follow the [Black](https://black.readthedocs.io/) code style and use
[isort](https://pycqa.github.io/isort/) for import sorting:

```bash
# Format code
black structx tests

# Sort imports
isort structx tests
```

### Type Hints

We use type hints throughout the codebase. Please add appropriate type hints to
your code:

```python
def example_function(param1: str, param2: int = 0) -> bool:
    """Example function with type hints"""
    return param1.startswith(str(param2))
```

### Documentation

- Add docstrings to all public functions, classes, and methods
- Use
  [Google style docstrings](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html)
- Update documentation when adding new features

## Pull Request Process

1. **Update Documentation**: Ensure that documentation is updated to reflect
   your changes.
2. **Add Tests**: Add tests for your changes.
3. **Run Tests**: Ensure all tests pass.
4. **Commit Your Changes**:

```bash
git add .
git commit -m "Add feature: your feature description"
```

5. **Push to Your Fork**:

```bash
git push origin feature/your-feature-name
```

6. **Submit a Pull Request**: Go to the
   [structx repository](https://github.com/yourusername/structx) and submit a
   pull request.

## Feature Requests and Bug Reports

- **Feature Requests**: Open an issue with the tag `enhancement`
- **Bug Reports**: Open an issue with the tag `bug` and include:
  - Description of the bug
  - Steps to reproduce
  - Expected behavior
  - Screenshots (if applicable)
  - Environment information

## License

By contributing to `structx`, you agree that your contributions will be licensed
under the project's
[MIT License](https://github.com/blacksuan19/structx/blob/master/LICENSE).
