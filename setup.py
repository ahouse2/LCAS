from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="LCAS",
    version="2.0.0",
    author="ahouse",
    author_email="ahouse@housemail.com",
    description="Legal Case Analysis System - AI-Powered Evidence Organization",
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
