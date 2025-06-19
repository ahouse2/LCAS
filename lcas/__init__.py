"""
LCAS - Legal Case Analysis System
A comprehensive tool for organizing and analyzing legal evidence
"""

__version__ = "4.0.0"
__author__ = "LCAS Development Team"
__email__ = "support@lcas.dev"
__description__ = "Legal Case Analysis System - AI-Powered Evidence Organization"

# Core imports
from .core import LCASCore, LCASConfig
from .plugins import PluginManager, PluginInterface

# Version info
VERSION_INFO = {
    "major": 4,
    "minor": 0,
    "patch": 0,
    "release": "stable"
}

def get_version():
    """Get the current version string"""
    return __version__

def get_version_info():
    """Get detailed version information"""
    return VERSION_INFO

# Package-level configuration
DEFAULT_CONFIG = {
    "log_level": "INFO",
    "max_workers": 4,
    "timeout": 300,
    "enable_ai": False,
    "preserve_originals": True
}

__all__ = [
    "LCASCore",
    "LCASConfig", 
    "PluginManager",
    "PluginInterface",
    "get_version",
    "get_version_info",
    "DEFAULT_CONFIG"
]