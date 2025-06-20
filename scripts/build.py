#!/usr/bin/env python3
"""
LCAS Build Script
Builds distribution packages for LCAS
"""

import subprocess
import sys
import shutil
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


def clean_build():
    """Clean previous build artifacts"""
    print("🧹 Cleaning previous build artifacts...")

    dirs_to_clean = ["build", "dist", "*.egg-info"]
    for pattern in dirs_to_clean:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
                print(f"  Removed {path}")
            elif path.is_file():
                path.unlink()
                print(f"  Removed {path}")


def install_build_tools():
    """Install build tools"""
    tools = ["build", "twine", "wheel"]
    for tool in tools:
        if not run_command(
                f"{sys.executable} -m pip install {tool}", f"Installing {tool}"):
            return False
    return True


def run_tests():
    """Run tests before building"""
    print("🧪 Running tests...")
    try:
        result = subprocess.run([sys.executable, "-m", "pytest", "tests/"],
                                check=True, capture_output=True, text=True)
        print("✅ All tests passed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed: {e.stderr}")
        return False
    except FileNotFoundError:
        print("⚠️ pytest not found, skipping tests")
        return True


def build_package():
    """Build the package"""
    return run_command(f"{sys.executable} -m build", "Building package")


def check_package():
    """Check the built package"""
    return run_command("twine check dist/*", "Checking package")


def main():
    """Main build function"""
    print("🏗️ LCAS Build Script")
    print("=" * 50)

    # Clean previous builds
    clean_build()

    # Install build tools
    if not install_build_tools():
        print("❌ Failed to install build tools")
        sys.exit(1)

    # Run tests
    if not run_tests():
        choice = input(
            "Tests failed. Continue with build? (y/N): ").strip().lower()
        if choice != 'y':
            sys.exit(1)

    # Build package
    if not build_package():
        print("❌ Failed to build package")
        sys.exit(1)

    # Check package
    if not check_package():
        print("❌ Package check failed")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("🎉 Build Complete!")
    print("\nGenerated files:")

    dist_dir = Path("dist")
    if dist_dir.exists():
        for file in dist_dir.iterdir():
            print(f"  {file}")

    print("\nTo upload to PyPI:")
    print("  twine upload dist/*")


if __name__ == "__main__":
    main()
