#!/usr/bin/env python3
"""
LCAS Utility Functions
Common utilities used throughout the LCAS system
"""

import hashlib
import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import shutil

logger = logging.getLogger(__name__)


def calculate_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """Calculate hash of a file"""
    try:
        hash_obj = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating hash for {file_path}: {e}")
        return ""


def ensure_directory(directory_path: Path) -> bool:
    """Ensure directory exists, create if necessary"""
    try:
        directory_path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory_path}: {e}")
        return False


def copy_file_with_verification(source: Path, target: Path) -> bool:
    """Copy file and verify integrity with hash comparison"""
    try:
        # Ensure target directory exists
        ensure_directory(target.parent)

        # Copy file
        shutil.copy2(source, target)

        # Verify integrity
        source_hash = calculate_file_hash(source)
        target_hash = calculate_file_hash(target)

        if source_hash == target_hash:
            logger.debug(f"File copied and verified: {source} -> {target}")
            return True
        else:
            logger.error(f"Hash mismatch after copy: {source} -> {target}")
            return False

    except Exception as e:
        logger.error(f"Error copying file {source} -> {target}: {e}")
        return False


def load_json_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Load JSON file safely"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON file {file_path}: {e}")
        return None


def save_json_file(data: Dict[str, Any], file_path: Path) -> bool:
    """Save data to JSON file safely"""
    try:
        ensure_directory(file_path.parent)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        return True
    except Exception as e:
        logger.error(f"Error saving JSON file {file_path}: {e}")
        return False


def get_file_info(file_path: Path) -> Dict[str, Any]:
    """Get comprehensive file information"""
    try:
        stat = file_path.stat()
        return {
            "name": file_path.name,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "extension": file_path.suffix.lower(),
            "hash": calculate_file_hash(file_path)
        }
    except Exception as e:
        logger.error(f"Error getting file info for {file_path}: {e}")
        return {}


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe filesystem usage"""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit(
            '.', 1) if '.' in filename else (
            filename, '')
        max_name_length = 255 - len(ext) - 1 if ext else 255
        filename = name[:max_name_length] + ('.' + ext if ext else '')

    return filename


def create_folder_structure(
        base_path: Path, structure: Dict[str, List[str]]) -> bool:
    """Create standardized folder structure"""
    try:
        for main_folder, subfolders in structure.items():
            main_path = base_path / main_folder
            ensure_directory(main_path)

            for subfolder in subfolders:
                sub_path = main_path / subfolder
                ensure_directory(sub_path)

        return True
    except Exception as e:
        logger.error(f"Error creating folder structure: {e}")
        return False


def get_supported_file_extensions() -> Dict[str, List[str]]:
    """Get supported file extensions by category"""
    return {
        "documents": [".pdf", ".docx", ".doc", ".txt", ".rtf"],
        "spreadsheets": [".xlsx", ".xls", ".csv"],
        "images": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"],
        "emails": [".eml", ".msg"],
        "archives": [".zip", ".rar", ".7z"],
        "audio": [".mp3", ".wav", ".m4a"],
        "video": [".mp4", ".avi", ".mov", ".wmv"]
    }


def is_supported_file(file_path: Path) -> bool:
    """Check if file type is supported"""
    extension = file_path.suffix.lower()
    supported_extensions = get_supported_file_extensions()

    for category, extensions in supported_extensions.items():
        if extension in extensions:
            return True

    return False


def generate_timestamp() -> str:
    """Generate timestamp string for logging/naming"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def setup_logging(log_level: str = "INFO",
                  log_file: Optional[str] = None) -> logging.Logger:
    """Setup logging configuration"""
    handlers = [logging.StreamHandler()]

    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

    return logging.getLogger(__name__)


class ProgressTracker:
    """Simple progress tracking utility"""

    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description

    def update(self, increment: int = 1):
        """Update progress"""
        self.current += increment
        percentage = (self.current / self.total) * 100 if self.total > 0 else 0
        print(f"\r{self.description}: {self.current}/{self.total} ({percentage:.1f}%)", end="", flush=True)

    def complete(self):
        """Mark as complete"""
        print(f"\r{self.description}: Complete ({self.total}/{self.total})")


def validate_config(config: Dict[str, Any],
                    required_fields: List[str]) -> List[str]:
    """Validate configuration has required fields"""
    missing_fields = []

    for field in required_fields:
        if field not in config or not config[field]:
            missing_fields.append(field)

    return missing_fields


def merge_dictionaries(dict1: Dict[str, Any],
                       dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two dictionaries recursively"""
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(
                result[key], dict) and isinstance(value, dict):
            result[key] = merge_dictionaries(result[key], value)
        else:
            result[key] = value

    return result
