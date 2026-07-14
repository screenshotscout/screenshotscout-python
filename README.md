# Screenshot Scout Python SDK

The official Python SDK for the [Screenshot Scout](https://screenshotscout.com) screenshot API.

## Requirements

Python 3.11 or newer.

## Development

Create a virtual environment and install the package with its development tools:

```shell
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the local checks:

```shell
python -m ruff format --check .
python -m ruff check .
python -m mypy
python -m pytest
python -m build
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
