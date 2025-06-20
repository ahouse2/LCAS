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
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major != 3 or version.minor < 9:
        print(
            f"❌ Python 3.9+ required. Current version: {version.major}.{version.minor}")
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
  enabled: true
  provider: "openai"  # openai, anthropic, local
  api_key: ""
  model: "gpt-4"
  base_url: ""
  temperature: 0.1
  max_tokens: 4000

# Processing Options
enable_deduplication: true
enable_neo4j: true
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
    if not run_command(
            f"{sys.executable} -m pip install --upgrade pip", "Upgrading pip"):
        print("⚠️ Pip upgrade failed, continuing anyway...")

    if not run_command(
            f"{sys.executable} -m pip install -r requirements.txt", "Installing requirements"):
        print("❌ Failed to install requirements. Please check the error messages above.")
        sys.exit(1)

    # Install spaCy model
    install_spacy_model()

    # Create config files
    create_config_files()

    # Optional: Install development dependencies
    dev_choice = input(
        "\n🔧 Install development dependencies? (y/N): ").strip().lower()
    if dev_choice == 'y':
        run_command(
            f"{sys.executable} -m pip install -e .[dev]", "Installing development dependencies")

    # Install advanced features
    advanced_choice = input(
        "\n🚀 Install advanced AI features (transformers, torch)? (y/N): ").strip().lower()
    if advanced_choice == 'y':
        run_command(
            f"{sys.executable} -m pip install -e .[advanced]", "Installing advanced features")

    print("\n" + "=" * 50)
    print("🎉 LCAS Installation Complete!")
    print("\nNext steps:")
    print("1. Configure your settings in config/lcas_config.yaml")
    print("2. Run the GUI: python lcas_gui.py")
    print("3. Or run the CLI: python run_lcas_script.py")
    print("\nFor help, visit: https://github.com/ahouse2/LCAS")


if __name__ == "__main__":
    main()
