"""
LCAS Plugins Module
Contains all analysis plugins for the Legal Case Analysis System
"""

# Plugin registry for automatic discovery
AVAILABLE_PLUGINS = [
    "file_ingestion_plugin",
    "hash_generation_plugin", 
    "evidence_categorization_plugin",
    "ai_integration_plugin",
    "timeline_analysis_plugin",
    "pattern_discovery_plugin",
    "report_generation_plugin"
]

# Plugin metadata
PLUGIN_METADATA = {
    "file_ingestion_plugin": {
        "name": "File Ingestion",
        "category": "Core",
        "description": "Preserves original files and creates working copies",
        "enabled_by_default": True
    },
    "hash_generation_plugin": {
        "name": "Hash Generation", 
        "category": "Security",
        "description": "Generates SHA256 hashes for file integrity verification",
        "enabled_by_default": True
    },
    "evidence_categorization_plugin": {
        "name": "Evidence Categorization",
        "category": "Analysis",
        "description": "Categorizes evidence files into legal argument folders",
        "enabled_by_default": True
    },
    "ai_integration_plugin": {
        "name": "AI Integration",
        "category": "AI",
        "description": "AI-powered analysis of legal documents and evidence",
        "enabled_by_default": False
    },
    "timeline_analysis_plugin": {
        "name": "Timeline Analysis",
        "category": "Analysis", 
        "description": "Builds chronological timelines from evidence files",
        "enabled_by_default": True
    },
    "pattern_discovery_plugin": {
        "name": "Pattern Discovery",
        "category": "Analysis",
        "description": "Discovers patterns and relationships in evidence files", 
        "enabled_by_default": True
    },
    "report_generation_plugin": {
        "name": "Report Generation",
        "category": "Export",
        "description": "Generates comprehensive analysis reports and visualizations",
        "enabled_by_default": True
    }
}

def get_available_plugins():
    """Get list of available plugins"""
    return AVAILABLE_PLUGINS

def get_plugin_metadata(plugin_name=None):
    """Get metadata for plugins"""
    if plugin_name:
        return PLUGIN_METADATA.get(plugin_name)
    return PLUGIN_METADATA

def get_plugins_by_category(category):
    """Get plugins by category"""
    return [
        plugin_name for plugin_name, metadata in PLUGIN_METADATA.items()
        if metadata.get("category") == category
    ]

def get_default_enabled_plugins():
    """Get plugins that are enabled by default"""
    return [
        plugin_name for plugin_name, metadata in PLUGIN_METADATA.items()
        if metadata.get("enabled_by_default", False)
    ]
