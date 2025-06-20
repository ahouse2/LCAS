#!/usr/bin/env python3
"""
Tests for LCAS utility functions
"""

import pytest
import tempfile
import json
from pathlib import Path

from lcas.utils import (
    calculate_file_hash,
    ensure_directory,
    copy_file_with_verification,
    load_json_file,
    save_json_file,
    get_file_info,
    format_file_size,
    sanitize_filename,
    is_supported_file,
    validate_config
)


class TestFileOperations:
    """Test file operation utilities"""

    def test_calculate_file_hash(self):
        """Test file hash calculation"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_file = Path(f.name)

        try:
            hash_value = calculate_file_hash(temp_file)
            assert len(hash_value) == 64  # SHA256 hash length
            assert hash_value != ""

            # Test same content produces same hash
            hash_value2 = calculate_file_hash(temp_file)
            assert hash_value == hash_value2
        finally:
            temp_file.unlink()

    def test_ensure_directory(self):
        """Test directory creation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir) / "test" / "nested" / "directory"

            result = ensure_directory(test_dir)
            assert result == True
            assert test_dir.exists()
            assert test_dir.is_dir()

    def test_copy_file_with_verification(self):
        """Test file copying with verification"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create source file
            source = Path(temp_dir) / "source.txt"
            source.write_text("test content")

            # Copy to target
            target = Path(temp_dir) / "subdir" / "target.txt"

            result = copy_file_with_verification(source, target)
            assert result == True
            assert target.exists()
            assert target.read_text() == "test content"

            # Verify hashes match
            source_hash = calculate_file_hash(source)
            target_hash = calculate_file_hash(target)
            assert source_hash == target_hash


class TestJSONOperations:
    """Test JSON file operations"""

    def test_save_and_load_json(self):
        """Test JSON save and load"""
        with tempfile.TemporaryDirectory() as temp_dir:
            json_file = Path(temp_dir) / "test.json"

            test_data = {
                "name": "Test Case",
                "files": 123,
                "enabled": True,
                "nested": {"key": "value"}
            }

            # Save JSON
            result = save_json_file(test_data, json_file)
            assert result == True
            assert json_file.exists()

            # Load JSON
            loaded_data = load_json_file(json_file)
            assert loaded_data == test_data

    def test_load_invalid_json(self):
        """Test loading invalid JSON"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content {")
            invalid_file = Path(f.name)

        try:
            result = load_json_file(invalid_file)
            assert result is None
        finally:
            invalid_file.unlink()


class TestFileInfo:
    """Test file information utilities"""

    def test_get_file_info(self):
        """Test file information extraction"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            temp_file = Path(f.name)

        try:
            info = get_file_info(temp_file)
            assert "name" in info
            assert "size" in info
            assert "created" in info
            assert "modified" in info
            assert "extension" in info
            assert "hash" in info

            assert info["name"] == temp_file.name
            assert info["extension"] == ".txt"
            assert info["size"] > 0
        finally:
            temp_file.unlink()

    def test_format_file_size(self):
        """Test file size formatting"""
        assert format_file_size(0) == "0 B"
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"

    def test_sanitize_filename(self):
        """Test filename sanitization"""
        assert sanitize_filename("normal_file.txt") == "normal_file.txt"
        assert sanitize_filename(
            "file<with>bad:chars.txt") == "file_with_bad_chars.txt"
        assert sanitize_filename("file/with\\path.txt") == "file_with_path.txt"

        # Test long filename
        long_name = "a" * 300 + ".txt"
        sanitized = sanitize_filename(long_name)
        assert len(sanitized) <= 255
        assert sanitized.endswith(".txt")

    def test_is_supported_file(self):
        """Test file type support checking"""
        assert is_supported_file(Path("document.pdf")) == True
        assert is_supported_file(Path("spreadsheet.xlsx")) == True
        assert is_supported_file(Path("image.jpg")) == True
        assert is_supported_file(Path("email.eml")) == True
        assert is_supported_file(Path("unknown.xyz")) == False


class TestConfigValidation:
    """Test configuration validation"""

    def test_validate_config_valid(self):
        """Test validation of valid configuration"""
        config = {
            "case_name": "Test Case",
            "source_directory": "/path/to/source",
            "target_directory": "/path/to/target"
        }

        required_fields = ["case_name", "source_directory", "target_directory"]
        missing = validate_config(config, required_fields)
        assert missing == []

    def test_validate_config_missing_fields(self):
        """Test validation with missing fields"""
        config = {
            "case_name": "Test Case"
            # Missing source_directory and target_directory
        }

        required_fields = ["case_name", "source_directory", "target_directory"]
        missing = validate_config(config, required_fields)
        assert "source_directory" in missing
        assert "target_directory" in missing
        assert "case_name" not in missing

    def test_validate_config_empty_values(self):
        """Test validation with empty values"""
        config = {
            "case_name": "",
            "source_directory": "/path/to/source",
            "target_directory": None
        }

        required_fields = ["case_name", "source_directory", "target_directory"]
        missing = validate_config(config, required_fields)
        assert "case_name" in missing
        assert "target_directory" in missing
        assert "source_directory" not in missing


if __name__ == "__main__":
    pytest.main([__file__])
