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
    print(
        f"✅ Python version {
            version.major}.{
            version.minor}.{
                version.micro} is compatible")
    return True


def install_package():
    """Install LCAS package"""
    print("🔄 Installing LCAS package...")
    try:
        # Install in development mode if setup.py exists
        if Path("setup.py").exists():
            result = subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."],
                                    check=True, capture_output=True, text=True)
        else:
            result = subprocess.run([sys.executable, "-m", "pip", "install", "lcas"],
                                    check=True, capture_output=True, text=True)
        print("✅ LCAS package installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install LCAS package: {e.stderr}")
        return False


def install_optional_features():
    """Install optional features"""
    features = {
        "ai": "AI-powered analysis features",
        "advanced": "Advanced NLP and machine learning",
        "gui": "Enhanced GUI components",
        "dev": "Development tools"
    }

    for feature, description in features.items():
        choice = input(f"\n🔧 Install {description}? (y/N): ").strip().lower()
        if choice == 'y':
            if run_command(
                    f"{sys.executable} -m pip install lcas[{feature}]", f"Installing {feature} features"):
                print(f"✅ {description} installed")
            else:
                print(f"❌ Failed to install {description}")


def create_config_files():
    """Create default configuration files"""
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)

    # Create default LCAS config
    default_config = """{
  "case_name": "",
  "source_directory": "",
  "target_directory": "",
  "enabled_plugins": [
    "file_ingestion_plugin",
    "hash_generation_plugin",
    "evidence_categorization_plugin",
    "timeline_analysis_plugin",
    "report_generation_plugin"
  ],
  "debug_mode": false,
  "log_level": "INFO",
  "min_probative_score": 0.3,
  "min_relevance_score": 0.5,
  "similarity_threshold": 0.85,
  "probative_weight": 0.4,
  "relevance_weight": 0.3,
  "admissibility_weight": 0.3,
  "enable_deduplication": true,
  "enable_advanced_nlp": true,
  "generate_visualizations": true,
  "max_concurrent_files": 5
}"""

    config_file = config_dir / "lcas_config.json"
    if not config_file.exists():
        with open(config_file, 'w') as f:
            f.write(default_config)
        print("✅ Default configuration file created")


def test_installation():
    """Test the installation"""
    print("🔄 Testing installation...")
    try:
        # Test import
        result = subprocess.run([sys.executable, "-c", "import lcas; print(lcas.get_version())"],
                                check=True, capture_output=True, text=True)
        version = result.stdout.strip()
        print(f"✅ LCAS v{version} installed and working correctly")

        # Test CLI
        result = subprocess.run([sys.executable, "-m", "lcas.cli", "--help"],
                                check=True, capture_output=True, text=True)
        print("✅ CLI interface working")

        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation test failed: {e.stderr}")
        return False


def main():
    """Main installation function"""
    print("🚀 LCAS Installation Helper")
    print("=" * 50)

    # Check Python version
    if not check_python_version():
        sys.exit(1)

    # Install main package
    if not run_command(
            f"{sys.executable} -m pip install --upgrade pip", "Upgrading pip"):
        print("⚠️ Pip upgrade failed, continuing anyway...")

    if not install_package():
        print("❌ Failed to install LCAS package. Please check the error messages above.")
        sys.exit(1)

    # Install optional features
    install_optional_features()

    # Create config files
    create_config_files()

    # Test installation
    if test_installation():
        print("\n" + "=" * 50)
        print("🎉 LCAS Installation Complete!")
        print("\nNext steps:")
        print("1. Configure your settings: lcas-cli config")
        print("2. Run the GUI: lcas-gui")
        print("3. Or use CLI: lcas-cli --help")
        print("\nFor help, visit: https://github.com/ahouse2/LCAS")
    else:
        print(
            "\n❌ Installation completed but tests failed. Please check the error messages.")
        sys.exit(1)


if __name__ == "__main__":
    main()
