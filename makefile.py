
# ================================
# Makefile (for Unix/Linux/macOS)
# ================================

.PHONY: install install-dev install-advanced clean test lint format run-gui run-cli

# Default Python interpreter
PYTHON := python3

# Installation targets
install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m spacy download en_core_web_sm
	$(PYTHON) install.py

install-dev: install
	$(PYTHON) -m pip install -e .[dev]

install-advanced: install
	$(PYTHON) -m pip install -e .[advanced]

# Development targets
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

test:
	$(PYTHON) -m pytest tests/ -v --cov=lcas --cov-report=html

lint:
	$(PYTHON) -m flake8 lcas/ tests/
	$(PYTHON) -m mypy lcas/

format:
	$(PYTHON) -m black lcas/ tests/
	$(PYTHON) -m isort lcas/ tests/

# Run targets
run-gui:
	$(PYTHON) lcas_gui.py

run-cli:
	$(PYTHON) run_lcas_script.py

run-test:
	$(PYTHON) lcas_main.py --create-config
	$(PYTHON) lcas_main.py --source="test_data" --target="test_output"

# Docker targets (if using Docker)
docker-build:
	docker build -t lcas:latest .

docker-run:
	docker run -v $(PWD)/data:/app/data lcas:latest

# ================================
# install.bat (for Windows)
# ================================

@echo off
echo 🚀 LCAS Installation Helper for Windows
echo ================================================

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

REM Upgrade pip
echo 🔄 Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo 🔄 Installing requirements...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install requirements
    pause
    exit /b 1
)

REM Install spaCy model
echo 🔄 Installing spaCy English model...
python -m spacy download en_core_web_sm

REM Create config directory
if not exist "config" mkdir config

REM Run installation helper
python install.py

echo.
echo 🎉 LCAS Installation Complete!
echo.
echo Next steps:
echo 1. Configure settings in config/lcas_config.yaml
echo 2. Run GUI: python lcas_gui.py
echo 3. Or run CLI: python run_lcas_script.py
echo.
pause
