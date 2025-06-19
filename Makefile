# LCAS Makefile
# Provides common development tasks

.PHONY: install install-dev install-all clean test lint format build upload help

# Default Python interpreter
PYTHON := python3

# Help target
help:
	@echo "LCAS Development Commands"
	@echo "========================"
	@echo "install      - Install LCAS package"
	@echo "install-dev  - Install with development dependencies"
	@echo "install-all  - Install with all optional dependencies"
	@echo "clean        - Clean build artifacts and cache files"
	@echo "test         - Run test suite"
	@echo "lint         - Run code linting"
	@echo "format       - Format code with black and isort"
	@echo "build        - Build distribution packages"
	@echo "upload       - Upload to PyPI (requires credentials)"
	@echo "help         - Show this help message"

# Installation targets
install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e .

install-dev: install
	$(PYTHON) -m pip install -e .[dev]

install-all: install
	$(PYTHON) -m pip install -e .[ai,advanced,gui,dev]

# Development targets
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/

test:
	$(PYTHON) -m pytest tests/ -v --cov=lcas --cov-report=html --cov-report=term-missing

lint:
	$(PYTHON) -m flake8 lcas/ tests/
	$(PYTHON) -m mypy lcas/

format:
	$(PYTHON) -m black lcas/ tests/
	$(PYTHON) -m isort lcas/ tests/

# Build and distribution
build: clean
	$(PYTHON) -m build

upload: build
	$(PYTHON) -m twine upload dist/*

# Quick development setup
dev-setup: install-dev
	@echo "Development environment ready!"
	@echo "Run 'make test' to run tests"
	@echo "Run 'lcas-gui' to start the GUI"
	@echo "Run 'lcas-cli --help' for CLI usage"