# requirements.txt
# Core GUI and Application Framework
customtkinter>=5.2.0
tkinter-tooltip>=2.1.0
pillow>=10.0.0

# File Processing and Content Extraction
PyPDF2>=3.0.1
pdfplumber>=0.9.0
python-docx>=0.8.11
openpyxl>=3.1.2
pandas>=2.0.0
python-magic>=0.4.27
chardet>=5.2.0

# Natural Language Processing
spacy>=3.7.0
sentence-transformers>=2.2.2
nltk>=3.8.1
textblob>=0.17.1

# AI Integration (OpenAI Compatible)
openai>=1.0.0
anthropic>=0.7.0
httpx>=0.25.0
aiohttp>=3.8.0

# Knowledge Graph and Database
neo4j>=5.13.0
py2neo>=2021.2.4
networkx>=3.2.1

# Data Analysis and Machine Learning
scikit-learn>=1.3.0
numpy>=1.24.0
scipy>=1.11.0
umap-learn>=0.5.4
hdbscan>=0.8.33

# Visualization
matplotlib>=3.7.0
seaborn>=0.12.0
plotly>=5.17.0
pyvis>=0.3.2

# Utilities and Performance
tqdm>=4.66.0
joblib>=1.3.0
python-dateutil>=2.8.2
regex>=2023.10.3
fuzzywuzzy>=0.18.0
python-levenshtein>=0.21.1

# Configuration and Logging
pyyaml>=6.0.1
python-dotenv>=1.0.0
colorlog>=6.7.0

# Testing (Development)
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0

# Optional Advanced Features
# Uncomment if you want to use these features
# transformers>=4.35.0  # For advanced NLP models
# torch>=2.1.0  # For deep learning models
# faiss-cpu>=1.7.4  # For fast similarity search
# chromadb>=0.4.0  # Alternative vector database

# ================================
# setup.py
# ================================

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="lcas",
    version="2.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Legal Case Analysis System - AI-Powered Evidence Organization",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/lcas",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Legal",
        "Topic :: Office/Business :: Legal",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ],
        "advanced": [
            "transformers>=4.35.0",
            "torch>=2.1.0",
            "faiss-cpu>=1.7.4",
            "chromadb>=0.4.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "lcas=lcas.lcas_main:main",
            "lcas-gui=lcas.lcas_gui:main",
            "lcas-cli=lcas.run_lcas_script:main",
        ],
    },
    include_package_data=True,
    package_data={
        "lcas": ["config/*.yaml", "templates/*.html", "static/*"],
    },
)

# ================================
# install.py - Installation Helper
# ================================

#!/usr/bin/env python3
"""
LCAS Installation Helper
Handles installation of dependencies and setup
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major != 3 or version.minor < 9:
        print(f"❌ Python 3.9+ required. Current version: {version.major}.{version.minor}")
        return False
    print(f"✅ Python version {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def install_spacy_model():
    """Install spaCy English model"""
    print("🔄 Installing spaCy English model...")
    try:
        import spacy
        try:
            spacy.load("en_core_web_sm")
            print("✅ spaCy model already installed")
            return True
        except OSError:
            result = subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], 
                                  check=True, capture_output=True, text=True)
            print("✅ spaCy model installed successfully")
            return True
    except ImportError:
        print("⚠️ spaCy not installed yet, will install model after main installation")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install spaCy model: {e.stderr}")
        return False

def create_config_files():
    """Create default configuration files"""
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    # Create default LCAS config
    default_config = """# LCAS Configuration File
source_directory: ""
target_directory: ""

# Analysis Settings
min_probative_score: 0.3
min_relevance_score: 0.5
similarity_threshold: 0.85

# Scoring Weights
probative_weight: 0.4
relevance_weight: 0.3
admissibility_weight: 0.3

# AI Configuration
ai:
  enabled: false
  provider: "openai"  # openai, anthropic, local
  api_key: ""
  model: "gpt-4"
  base_url: ""
  temperature: 0.1
  max_tokens: 4000

# Processing Options
enable_deduplication: true
enable_neo4j: false
enable_advanced_nlp: true
generate_visualizations: true

# Performance Settings
max_concurrent_files: 5
batch_size: 100
"""
    
    config_file = config_dir / "lcas_config.yaml"
    if not config_file.exists():
        with open(config_file, 'w') as f:
            f.write(default_config)
        print("✅ Default configuration file created")

def main():
    """Main installation function"""
    print("🚀 LCAS Installation Helper")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install main requirements
    if not run_command(f"{sys.executable} -m pip install --upgrade pip", "Upgrading pip"):
        print("⚠️ Pip upgrade failed, continuing anyway...")
    
    if not run_command(f"{sys.executable} -m pip install -r requirements.txt", "Installing requirements"):
        print("❌ Failed to install requirements. Please check the error messages above.")
        sys.exit(1)
    
    # Install spaCy model
    install_spacy_model()
    
    # Create config files
    create_config_files()
    
    # Optional: Install development dependencies
    dev_choice = input("\n🔧 Install development dependencies? (y/N): ").strip().lower()
    if dev_choice == 'y':
        run_command(f"{sys.executable} -m pip install -e .[dev]", "Installing development dependencies")
    
    # Optional: Install advanced features
    advanced_choice = input("\n🚀 Install advanced AI features (transformers, torch)? (y/N): ").strip().lower()
    if advanced_choice == 'y':
        run_command(f"{sys.executable} -m pip install -e .[advanced]", "Installing advanced features")
    
    print("\n" + "=" * 50)
    print("🎉 LCAS Installation Complete!")
    print("\nNext steps:")
    print("1. Configure your settings in config/lcas_config.yaml")
    print("2. Run the GUI: python lcas_gui.py")
    print("3. Or run the CLI: python run_lcas_script.py")
    print("\nFor help, visit: https://github.com/yourusername/lcas")

if __name__ == "__main__":
    main()

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