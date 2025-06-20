#!/usr/bin/env python3
"""
Setup script for LCAS - Legal Case Analysis System
"""

from setuptools import setup, find_packages
import os

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="lcas",
    version="4.0.0",
    author="LCAS Development Team",
    author_email="support@lcas.dev",
    description="Legal Case Analysis System - AI-Powered Evidence Organization and Analysis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ahouse2/LCAS",
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
            "isort>=5.12.0",
        ],
        "advanced": [
            "transformers>=4.35.0",
            "torch>=2.1.0",
            "faiss-cpu>=1.7.4",
            "sentence-transformers>=2.2.2",
            "spacy>=3.7.0",
            "chromadb>=0.4.0",
        ],
        "gui": [
            "customtkinter>=5.2.0",
            "pillow>=10.0.0",
            "tkinter-tooltip>=2.0.0",
        ],
        "ai": [
            "openai>=1.0.0",
            "anthropic>=0.21.0",
            "httpx>=0.25.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "lcas=lcas.main:main",
            "lcas-gui=lcas.gui:main",
            "lcas-cli=lcas.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "lcas": [
            "config/*.yaml",
            "config/*.json", 
            "templates/*.html",
            "static/*",
            "plugins/*.py",
        ],
    },
    zip_safe=False,
)