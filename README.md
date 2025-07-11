# Jenkins Scripts
A collection of scripts and documentation for accessing the Jenkins servers hosted by Adoptium (our upstream partner for the Microsoft Build of OpenJDK).

## Development

This repository includes automated code quality checks for all Python scripts using:

- **ruff**: Code linting and formatting
- **mypy**: Static type checking  
- **pytest**: Testing with coverage reporting

### Setup

Install development dependencies:

```bash
pip install -e .[dev]
```

### Running Quality Checks Locally

```bash
# Lint and format code
ruff check .
ruff format .

# Type checking
mypy .

# Run tests with coverage
pytest --cov
```

### CI/CD

All Python files are automatically checked on pull requests using GitHub Actions. The workflow runs on Python 3.8-3.12 and must pass before merging.

