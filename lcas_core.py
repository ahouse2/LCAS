#!/usr/bin/env python3
"""
LCAS Core Application - Legal Case Analysis System
Modular Plugin-Based Architecture

This is the core application that manages plugins and provides the foundation
for legal evidence analysis. All features are implemented as independent plugins.
"""

import os
import sys
import json
import logging
import asyncio
import importlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Type
from dataclasses import dataclass, asdict
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from abc import ABC, abstractmethod

# Core Configuration
@dataclass
class LCASConfig:
    """Core application configuration"""
    case_name: str = ""
    source_directory: str = ""
    target_directory: str = ""
    plugins_directory: str = "plugins"
    enabled_plugins: List[str] = None
    debug_mode: bool = False
    log_level: str = "INFO"
    
    def __post_init__(self):
        if self.enabled_plugins is None:
            self.enabled_plugins = []

# Plugin System Base Classes
class PluginInterface(ABC):
    """Base interface for all LCAS plugins"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Plugin description"""
        pass
    
    @property
    @abstractmethod
    def dependencies(self) -> List[str]:
        """Plugin dependencies"""
        pass
    
    @abstractmethod
    async def initialize(self, core_app: 'LCASCore') -> bool:
        """Initialize the plugin"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup plugin resources"""
        pass

class AnalysisPlugin(PluginInterface):
    """Base class for analysis plugins"""
    
    @abstractmethod
    async def analyze(self, data: Any) -> Dict[str, Any]:
        """Perform analysis on data"""
        pass

class UIPlugin(PluginInterface):
    """Base class for UI plugins"""
    
    @abstractmethod
    def create_ui_elements(self, parent_widget) -> List[tk.Widget]:
        """Create UI elements for this plugin"""
        pass

class ExportPlugin(PluginInterface):
    """Base class for export/visualization plugins"""
    
    @abstractmethod
    async def export(self, data: Any, output_path: str) -> bool:
        """Export data to specified format"""
        pass

# Plugin Manager
class PluginManager:
    """Manages all plugins in the LCAS system"""
    
    def __init__(self, plugins_directory: str = "plugins"):
        self.plugins_directory = Path(plugins_directory)
        self.loaded_plugins: Dict[str, PluginInterface] = {}
        self.plugin_configs: Dict[str, Dict] = {}
        self.logger = logging.getLogger(f"{__name__}.PluginManager")
        
    def discover_plugins(self) -> List[str]:
        """Discover available plugins in the plugins directory"""
        if not self.plugins_directory.exists():
            self.plugins_directory.mkdir(parents=True, exist_ok=True)
            return []
        
        plugins = []
        for file_path in self.plugins_directory.glob("*_plugin.py"):
            plugin_name = file_path.stem
            plugins.append(plugin_name)
            
        self.logger.info(f"Discovered {len(plugins)} plugins: {plugins}")
        return plugins
    
    async def load_plugin(self, plugin_name: str, core_app: 'LCASCore') -> bool:
        """Load a specific plugin"""
        try:
            # Add plugins directory to path
            sys.path.insert(0, str(self.plugins_directory))
            
            # Import the plugin module
            module = importlib.import_module(plugin_name)
            
            # Look for the plugin class (should be named <PluginName>Plugin)
            plugin_class_name = self._get_plugin_class_name(plugin_name)
            if not hasattr(module, plugin_class_name):
                self.logger.error(f"Plugin {plugin_name} does not have class {plugin_class_name}")
                return False
            
            plugin_class = getattr(module, plugin_class_name)
            plugin_instance = plugin_class()
            
            # Initialize the plugin
            if await plugin_instance.initialize(core_app):
                self.loaded_plugins[plugin_name] = plugin_instance
                self.logger.info(f"Successfully loaded plugin: {plugin_name}")
                return True
            else:
                self.logger.error(f"Failed to initialize plugin: {plugin_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error loading plugin {plugin_name}: {e}")
            return False
    
    def _get_plugin_class_name(self, plugin_name: str) -> str:
        """Convert plugin filename to expected class name"""
        # Convert snake_case to PascalCase
        parts = plugin_name.replace('_plugin', '').split('_')
        return ''.join(word.capitalize() for word in parts) + 'Plugin'
    
    async def load_all_plugins(self, core_app: 'LCASCore', enabled_only: bool = True) -> None:
        """Load all discovered plugins"""
        plugins = self.discover_plugins()
        
        for plugin_name in plugins:
            if enabled_only and plugin_name not in core_app.config.enabled_plugins:
                continue
                
            await self.load_plugin(plugin_name, core_app)
    
    def get_plugins_by_type(self, plugin_type: Type[PluginInterface]) -> List[PluginInterface]:
        """Get all loaded plugins of a specific type"""
        return [plugin for plugin in self.loaded_plugins.values() 
                if isinstance(plugin, plugin_type)]
    
    async def cleanup_all_plugins(self) -> None:
        """Cleanup all loaded plugins"""
        for plugin in self.loaded_plugins.values():
            try:
                await plugin.cleanup()
            except Exception as e:
                self.logger.error(f"Error cleaning up plugin {plugin.name}: {e}")

# Event System
class EventBus:
    """Simple event bus for plugin communication"""
    
    def __init__(self):
        self.listeners: Dict[str, List[callable]] = {}
        self.logger = logging.getLogger(f"{__name__}.EventBus")
    
    def subscribe(self, event_type: str, callback: callable) -> None:
        """Subscribe to an event type"""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)
        self.logger.debug(f"Subscribed to {event_type}")
    
    def unsubscribe(self, event_type: str, callback: callable) -> None:
        """Unsubscribe from an event type"""
        if event_type in self.listeners:
            self.listeners[event_type].remove(callback)
    
    async def publish(self, event_type: str, data: Any = None) -> None:
        """Publish an event to all subscribers"""
        if event_type in self.listeners:
            self.logger.debug(f"Publishing {event_type} to {len(self.listeners[event_type])} listeners")
            for callback in self.listeners[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    self.logger.error(f"Error in event callback: {e}")

# Core Application
class LCASCore:
    """Core LCAS application"""
    
    def __init__(self, config: Optional[LCASConfig] = None):
        self.config = config or LCASConfig()
        self.plugin_manager = PluginManager(self.config.plugins_directory)
        self.event_bus = EventBus()
        self.logger = self._setup_logging()
        self.running = False
        
        # Core data storage
        self.analysis_results: Dict[str, Any] = {}
        self.file_metadata: Dict[str, Any] = {}
        self.case_data: Dict[str, Any] = {}
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('lcas_core.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        return logging.getLogger(__name__)
    
    async def initialize(self) -> bool:
        """Initialize the core application"""
        try:
            self.logger.info("Initializing LCAS Core Application")
            
            # Create necessary directories
            Path(self.config.target_directory).mkdir(parents=True, exist_ok=True)
            Path(self.config.plugins_directory).mkdir(parents=True, exist_ok=True)
            
            # Load plugins
            await self.plugin_manager.load_all_plugins(self)
            
            # Publish initialization complete event
            await self.event_bus.publish("core.initialized", self.config)
            
            self.running = True
            self.logger.info("LCAS Core Application initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize LCAS Core: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the application gracefully"""
        self.logger.info("Shutting down LCAS Core Application")
        
        # Publish shutdown event
        await self.event_bus.publish("core.shutdown")
        
        # Cleanup plugins
        await self.plugin_manager.cleanup_all_plugins()
        
        self.running = False
        self.logger.info("LCAS Core Application shutdown complete")
    
    # Data Management
    def set_case_data(self, key: str, value: Any) -> None:
        """Set case data"""
        self.case_data[key] = value
        asyncio.create_task(self.event_bus.publish("case.data_updated", {"key": key, "value": value}))
    
    def get_case_data(self, key: str, default: Any = None) -> Any:
        """Get case data"""
        return self.case_data.get(key, default)
    
    def set_analysis_result(self, plugin_name: str, result: Any) -> None:
        """Set analysis result from a plugin"""
        self.analysis_results[plugin_name] = {
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "plugin": plugin_name
        }
        asyncio.create_task(self.event_bus.publish("analysis.completed", {
            "plugin": plugin_name, 
            "result": result
        }))
    
    def get_analysis_result(self, plugin_name: str) -> Optional[Any]:
        """Get analysis result from a plugin"""
        result_data = self.analysis_results.get(plugin_name)
        return result_data["result"] if result_data else None
    
    # Plugin Interface Methods
    def get_analysis_plugins(self) -> List[AnalysisPlugin]:
        """Get all loaded analysis plugins"""
        return self.plugin_manager.get_plugins_by_type(AnalysisPlugin)
    
    def get_ui_plugins(self) -> List[UIPlugin]:
        """Get all loaded UI plugins"""
        return self.plugin_manager.get_plugins_by_type(UIPlugin)
    
    def get_export_plugins(self) -> List[ExportPlugin]:
        """Get all loaded export plugins"""
        return self.plugin_manager.get_plugins_by_type(ExportPlugin)
    
    # Configuration Management
    def save_config(self, config_path: str = "lcas_config.json") -> bool:
        """Save current configuration"""
        try:
            with open(config_path, 'w') as f:
                json.dump(asdict(self.config), f, indent=2)
            self.logger.info(f"Configuration saved to {config_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False
    
    @classmethod
    def load_config(cls, config_path: str = "lcas_config.json") -> 'LCASCore':
        """Load configuration and create core instance"""
        try:
            if Path(config_path).exists():
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                config = LCASConfig(**config_data)
            else:
                config = LCASConfig()
            
            return cls(config)
        except Exception as e:
            logging.error(f"Failed to load configuration: {e}")
            return cls(LCASConfig())

# Main Entry Point
async def main():
    """Main entry point for the LCAS Core Application"""
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="LCAS - Legal Case Analysis System")
    parser.add_argument("--config", default="lcas_config.json", help="Configuration file path")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--plugins-dir", default="plugins", help="Plugins directory")
    args = parser.parse_args()
    
    # Load configuration
    core = LCASCore.load_config(args.config)
    
    if args.debug:
        core.config.debug_mode = True
        core.config.log_level = "DEBUG"
        
    if args.plugins_dir:
        core.config.plugins_directory = args.plugins_dir
    
    # Initialize and run
    if await core.initialize():
        print("LCAS Core Application started successfully")
        print(f"Loaded plugins: {list(core.plugin_manager.loaded_plugins.keys())}")
        
        # Keep running (in a real app, this would be handled by the GUI or service loop)
        try:
            while core.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            await core.shutdown()
    else:
        print("Failed to start LCAS Core Application")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
