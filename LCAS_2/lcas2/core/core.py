#!/usr/bin/env python3
"""
LCAS Core Module
Main application logic and plugin management
"""

import os
import sys
import json
import logging
import asyncio
import importlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Type, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../logs/lcas_initial.log'), # Assuming logs dir is one level up from core dir
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


@dataclass
class LCASConfig:
    """Core application configuration"""
    case_name: str = ""
    source_directory: str = ""
    target_directory: str = ""
    plugins_directory: str = "../plugins" # Path relative to core.py location
    enabled_plugins: List[str] = None
    debug_mode: bool = False
    log_level: str = "INFO"

    # GUI specific settings
    gui_theme: str = "system"
    last_window_width: int = 1200
    last_window_height: int = 800

    # AI Plugin related configurations
    ai_config_path: str = "config/ai_config.json" # Path to AI plugin's specific config, relative to project root
    ai_analysis_depth: str = "standard" # Default for AI analysis
    ai_confidence_threshold: float = 0.6 # Default for AI confidence

    # Analysis settings
    min_probative_score: float = 0.3
    min_relevance_score: float = 0.5
    similarity_threshold: float = 0.85

    # Scoring weights
    probative_weight: float = 0.4
    relevance_weight: float = 0.3
    admissibility_weight: float = 0.3

    # Processing options
    enable_deduplication: bool = True
    enable_advanced_nlp: bool = True
    generate_visualizations: bool = True
    max_concurrent_files: int = 5

    case_theory: 'CaseTheoryConfig' = field(default_factory=lambda: CaseTheoryConfig())


    def __post_init__(self):
        if self.enabled_plugins is None:
            self.enabled_plugins = [
                "file_ingestion_plugin",
                "hash_generation_plugin",
                "evidence_categorization_plugin",
                "timeline_analysis_plugin",
                "report_generation_plugin",
                "lcas_ai_wrapper_plugin" # Assuming this is the intended name for the AI plugin wrapper
            ]

@dataclass
class CaseTheoryConfig:
    """Configuration related to case theory for AI analysis"""
    case_type: str = "general" # Default case_type for AI
    # Potentially other fields like 'custom_instructions', 'key_elements' etc.


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


class PluginManager:
    """Manages all plugins in the LCAS system"""

    def __init__(self, plugins_directory: str = "plugins"):
        # Ensure plugins_directory is an absolute path or correctly relative to project root
        # core.py is in lcas2/core, so if plugins_directory is ../plugins, it refers to lcas2/plugins
        self.plugins_directory = Path(plugins_directory)
        if not self.plugins_directory.is_absolute():
             # Assuming core.py is in LCAS_2/lcas2/core/
            self.plugins_directory = Path(__file__).parent.parent / plugins_directory

        self.loaded_plugins: Dict[str, PluginInterface] = {}
        self.plugin_configs: Dict[str, Dict] = {}
        self.logger = logging.getLogger(f"{__name__}.PluginManager")
        self.logger.info(f"PluginManager initialized. Plugin directory set to: {self.plugins_directory.resolve()}")


    def discover_plugins(self) -> List[str]:
        """Discover available plugins in the plugins directory"""
        if not self.plugins_directory.exists():
            self.logger.warning(f"Plugins directory does not exist: {self.plugins_directory.resolve()}")
            self.plugins_directory.mkdir(parents=True, exist_ok=True) # Attempt to create
            return []

        plugins = []
        for file_path in self.plugins_directory.glob("*_plugin.py"):
            plugin_name = file_path.stem
            plugins.append(plugin_name)

        self.logger.info(f"Discovered {len(plugins)} plugins in {self.plugins_directory.resolve()}: {plugins}")
        return plugins

    async def load_plugin(self, plugin_name: str,
                          core_app: 'LCASCore') -> bool:
        """Load a specific plugin"""
        try:
            # Temporarily add plugins directory to sys.path for importlib
            # This ensures that plugins can be found regardless of current working directory.
            plugins_dir_str = str(self.plugins_directory.resolve())
            if plugins_dir_str not in sys.path:
                sys.path.insert(0, plugins_dir_str)

            module = importlib.import_module(plugin_name)

            # Clean up sys.path if it was added
            if sys.path[0] == plugins_dir_str: # Check if it's the one we added
                 del sys.path[0]

            plugin_class_name = self._get_plugin_class_name(plugin_name)
            if not hasattr(module, plugin_class_name):
                self.logger.error(
                    f"Plugin {plugin_name} does not have class {plugin_class_name}")
                return False

            plugin_class = getattr(module, plugin_class_name)
            plugin_instance = plugin_class()

            if await plugin_instance.initialize(core_app):
                self.loaded_plugins[plugin_name] = plugin_instance
                self.logger.info(f"Successfully loaded plugin: {plugin_name}")
                return True
            else:
                self.logger.error(
                    f"Failed to initialize plugin: {plugin_name}")
                return False

        except Exception as e:
            self.logger.error(f"Error loading plugin {plugin_name}: {e}", exc_info=True)
            # Clean up sys.path in case of error too
            plugins_dir_str_on_error = str(self.plugins_directory.resolve())
            if sys.path and sys.path[0] == plugins_dir_str_on_error:
                 del sys.path[0]
            return False

    def _get_plugin_class_name(self, plugin_name: str) -> str:
        """Convert plugin filename to expected class name"""
        parts = plugin_name.replace('_plugin', '').split('_')
        return ''.join(word.capitalize() for word in parts) + 'Plugin'

    async def load_all_plugins(
            self, core_app: 'LCASCore', enabled_only: bool = True) -> None:
        """Load all discovered plugins"""
        plugins = self.discover_plugins()

        for plugin_name in plugins:
            if enabled_only and plugin_name not in (core_app.config.enabled_plugins or []):
                self.logger.debug(f"Skipping disabled plugin: {plugin_name}")
                continue
            await self.load_plugin(plugin_name, core_app)

    def get_plugins_by_type(
            self, plugin_type: Type[PluginInterface]) -> List[PluginInterface]:
        """Get all loaded plugins of a specific type"""
        return [plugin for plugin in self.loaded_plugins.values()
                if isinstance(plugin, plugin_type)]

    async def cleanup_all_plugins(self) -> None:
        """Cleanup all loaded plugins"""
        for plugin_name, plugin in list(self.loaded_plugins.items()): # Iterate over a copy for safe removal
            try:
                await plugin.cleanup()
                self.logger.info(f"Plugin {plugin_name} cleaned up.")
            except Exception as e:
                self.logger.error(
                    f"Error cleaning up plugin {plugin.name}: {e}", exc_info=True)
        self.loaded_plugins.clear()


class EventBus:
    """Simple event bus for plugin communication"""

    def __init__(self):
        self.listeners: Dict[str, List[Callable]] = {} # Changed from List[callable] to List[Callable] for typing
        self.logger = logging.getLogger(f"{__name__}.EventBus")

    def subscribe(self, event_type: str, callback: Callable) -> None: # Changed from callable to Callable
        """Subscribe to an event type"""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)
        self.logger.debug(f"Subscribed to {event_type}: {callback.__name__ if hasattr(callback, '__name__') else callback}")

    def unsubscribe(self, event_type: str, callback: Callable) -> None: # Changed from callable to Callable
        """Unsubscribe from an event type"""
        if event_type in self.listeners:
            try:
                self.listeners[event_type].remove(callback)
                self.logger.debug(f"Unsubscribed from {event_type}: {callback.__name__ if hasattr(callback, '__name__') else callback}")
            except ValueError:
                self.logger.warning(f"Callback not found for event type {event_type} during unsubscribe.")


    async def publish(self, event_type: str, data: Any = None) -> None:
        """Publish an event to all subscribers"""
        if event_type in self.listeners:
            self.logger.debug(
                f"Publishing {event_type} to {len(self.listeners[event_type])} listeners with data: {str(data)[:100]}...")
            for callback in self.listeners[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        # If GUI callback, ensure it's run in the main thread if needed
                        # This might require a more sophisticated event bus or main thread executor
                        callback(data)
                except Exception as e:
                    self.logger.error(f"Error in event callback for {event_type} ({callback.__name__ if hasattr(callback, '__name__') else callback}): {e}", exc_info=True)


class LCASCore:
    """Core LCAS application"""

    def __init__(self, config: Optional[LCASConfig] = None, main_loop: Optional[asyncio.AbstractEventLoop] = None):
        self.config = config or LCASConfig()
        # Resolve plugins_directory relative to this file's location if it's relative
        plugins_path = Path(self.config.plugins_directory)
        if not plugins_path.is_absolute():
            plugins_path = (Path(__file__).parent.parent / plugins_path).resolve()

        self.plugin_manager = PluginManager(str(plugins_path))
        self.event_bus = EventBus()
        self.logger = self._setup_logging()
        self.running = False
        self.main_loop = main_loop or asyncio.get_event_loop()


        # Core data storage
        self.analysis_results: Dict[str, Any] = {}
        self.file_metadata: Dict[str, Any] = {} # Example: {filepath: {hash: "...", size: "..."}}
        self.case_data: Dict[str, Any] = {}     # Example: {timeline_data: {...}, theories: [...]}


    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        # Ensure log directory exists (../logs relative to this core.py file)
        log_dir = (Path(__file__).parent.parent / "logs").resolve()
        log_dir.mkdir(parents=True, exist_ok=True)

        core_log_file = log_dir / "lcas_core.log"
        initial_log_file = log_dir / "lcas_initial.log" # This seems to be for initial config logging

        # Update handlers to use absolute paths
        # Remove existing handlers to avoid duplication if this method is called multiple times
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Add new handlers
        logging.basicConfig(
            level=getattr(logging, self.config.log_level.upper(), logging.INFO),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(core_log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        # The 'lcas_initial.log' was in the global basicConfig. If specific, it needs its own handler.
        # For simplicity, let's consolidate into lcas_core.log for now.
        return logging.getLogger(__name__)

    async def initialize(self) -> bool:
        """Initialize the core application"""
        try:
            self.logger.info(f"Initializing LCAS Core Application with config: {self.config}")
            self.logger.info(f"Plugin directory: {self.plugin_manager.plugins_directory.resolve()}")


            # Create target directory if it doesn't exist
            if self.config.target_directory:
                Path(self.config.target_directory).mkdir(parents=True, exist_ok=True)
            else:
                self.logger.warning("Target directory is not set in configuration.")
                # Optionally, set a default target directory here or raise an error
                # For now, we'll allow it to be unset, but plugins might fail.

            await self.plugin_manager.load_all_plugins(self)

            await self.event_bus.publish("core.initialized", {"config": self.config})
            self.running = True
            self.logger.info("LCAS Core Application initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize LCAS Core: {e}", exc_info=True)
            return False

    async def shutdown(self) -> None:
        """Shutdown the application gracefully"""
        self.logger.info("Shutting down LCAS Core Application")
        await self.event_bus.publish("core.shutdown")
        await self.plugin_manager.cleanup_all_plugins()
        self.running = False
        self.logger.info("LCAS Core Application shutdown complete")

    # --- Core Analysis Orchestration Methods ---

    async def run_file_preservation(self, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Runs the file ingestion/preservation plugin."""
        self.logger.info("Starting file preservation task...")
        await self.event_bus.publish("core.preservation_started")

        preservation_plugin_name = "file_ingestion_plugin"
        results = {}

        plugin = self.plugin_manager.loaded_plugins.get(preservation_plugin_name)
        if plugin and isinstance(plugin, AnalysisPlugin):
            try:
                await self.event_bus.publish("core.plugin_execution_started", {"plugin_name": plugin.name})
                if progress_callback: self.main_loop.call_soon_threadsafe(progress_callback, plugin.name, "started", 0)

                result = await plugin.analyze({
                    "source_directory": self.config.source_directory,
                    "target_directory": self.config.target_directory,
                    "case_name": self.config.case_name,
                    "config": self.config # Pass full config
                })
                results[plugin.name] = result
                self.set_analysis_result(plugin.name, result)

                if progress_callback: self.main_loop.call_soon_threadsafe(progress_callback, plugin.name, "completed", 100)
                await self.event_bus.publish("core.plugin_execution_completed", {"plugin_name": plugin.name, "result": result})
                self.logger.info(f"Plugin {plugin.name} completed successfully: {str(result)[:100]}")

            except Exception as e:
                self.logger.error(f"Error running plugin {plugin.name}: {e}", exc_info=True)
                results[plugin.name] = {"error": str(e), "success": False}
                if progress_callback: self.main_loop.call_soon_threadsafe(progress_callback, plugin.name, "error", 100)
                await self.event_bus.publish("core.error_occurred", {"error_message": str(e), "plugin_name": plugin.name})
        else:
            self.logger.warning(f"Preservation plugin '{preservation_plugin_name}' not found or not an AnalysisPlugin.")
            results[preservation_plugin_name] = {"error": "Plugin not found", "success": False}
            if progress_callback: self.main_loop.call_soon_threadsafe(progress_callback, preservation_plugin_name, "error", 0)
            await self.event_bus.publish("core.error_occurred", {"error_message": "Preservation plugin not found", "plugin_name": preservation_plugin_name})

        await self.event_bus.publish("core.preservation_completed", results)
        self.logger.info("File preservation task finished.")
        return results

    async def run_full_analysis(self, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Runs the full analysis pipeline using enabled AnalysisPlugins."""
        self.logger.info("Starting full analysis...")
        await self.event_bus.publish("core.analysis_started", {"type": "full"})

        # Exclude file_ingestion_plugin from general analysis if it's run separately
        analysis_plugins = [
            p for p in self.get_analysis_plugins()
            if p.name != "File Ingestion" and p.name in (self.config.enabled_plugins or [])
        ]

        if not analysis_plugins:
            self.logger.warning("No analysis plugins (excluding ingestion) enabled or loaded for full analysis.")
            await self.event_bus.publish("core.analysis_completed", {"results": {}, "message": "No analysis plugins"})
            return {"message": "No analysis plugins enabled or loaded for full analysis."}

        overall_results = {}
        total_plugins_to_run = len(analysis_plugins)

        for i, plugin in enumerate(analysis_plugins):
            self.logger.info(f"Executing plugin {i+1}/{total_plugins_to_run}: {plugin.name}")
            await self.event_bus.publish("core.plugin_execution_started", {"plugin_name": plugin.name, "step": i+1, "total_steps": total_plugins_to_run})

            current_progress_percent = int(((i) / total_plugins_to_run) * 100)
            if progress_callback:
                 self.main_loop.call_soon_threadsafe(progress_callback, plugin.name, "started", current_progress_percent)


            try:
                plugin_input_data = {
                    "source_directory": self.config.source_directory,
                    "target_directory": self.config.target_directory,
                    "case_name": self.config.case_name,
                    "current_results": dict(overall_results), # Pass a copy
                    "config": self.config,
                    "ai_config_path": (Path(__file__).parent.parent.parent / self.config.ai_config_path).resolve()
                }

                result = await plugin.analyze(plugin_input_data)
                overall_results[plugin.name] = result
                self.set_analysis_result(plugin.name, result)

                completed_progress_percent = int(((i + 1) / total_plugins_to_run) * 100)
                if progress_callback:
                    self.main_loop.call_soon_threadsafe(progress_callback, plugin.name, "completed", completed_progress_percent)

                await self.event_bus.publish("core.plugin_execution_completed", {"plugin_name": plugin.name, "result": result, "step": i+1, "total_steps": total_plugins_to_run})
                self.logger.info(f"Plugin {plugin.name} completed: {str(result)[:100]}")

            except Exception as e:
                self.logger.error(f"Error running plugin {plugin.name}: {e}", exc_info=True)
                overall_results[plugin.name] = {"error": str(e), "success": False}
                error_progress_percent = int(((i + 1) / total_plugins_to_run) * 100)
                if progress_callback:
                    self.main_loop.call_soon_threadsafe(progress_callback, plugin.name, "error", error_progress_percent)
                await self.event_bus.publish("core.error_occurred", {"error_message": str(e), "plugin_name": plugin.name})

        await self.event_bus.publish("core.analysis_completed", {"results": overall_results, "type": "full"})
        self.logger.info("Full analysis finished.")
        return overall_results

    # --- End of Core Analysis Orchestration Methods ---

    # Data Management
    def set_case_data(self, key: str, value: Any) -> None:
        """Set case data"""
        self.case_data[key] = value
        asyncio.create_task( # Ensure this runs on the main_loop if created from different thread
            self.event_bus.publish(
                "case.data_updated", {
                    "key": key, "value": value}))

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
        # Run publish in the main event loop if called from a thread
        async def _publish():
            await self.event_bus.publish("analysis.completed", {
                "plugin": plugin_name,
                "result": result
            })
        asyncio.run_coroutine_threadsafe(_publish(), self.main_loop)


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
    def save_config(self, config_path: Optional[str] = None) -> bool:
        """Save current configuration.
        If config_path is None, uses path from self.config.ai_config_path (incorrect for main config)
        or a default. Should be project root relative for main config.
        """
        path_to_save = None
        if config_path:
            path_to_save = Path(config_path)
        else:
            # Default to saving lcas_config.json in LCAS_2/config/
            path_to_save = (Path(__file__).parent.parent.parent / "config" / "lcas_config.json").resolve()

        path_to_save.parent.mkdir(parents=True, exist_ok=True) # Ensure directory exists

        try:
            config_dict = asdict(self.config)
            # Ensure CaseTheoryConfig is also serializable if it's complex
            if isinstance(self.config.case_theory, CaseTheoryConfig):
                 config_dict['case_theory'] = asdict(self.config.case_theory)

            with open(path_to_save, 'w') as f:
                json.dump(config_dict, f, indent=2)
            self.logger.info(f"Configuration saved to {path_to_save}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save configuration to {path_to_save}: {e}", exc_info=True)
            return False

    @classmethod
    def load_config(cls, config_path: Optional[str] = None) -> 'LCASConfig': # Return LCASConfig, not LCASCore
        """Load configuration. Returns an LCASConfig instance.
        If config_path is None, uses a default path.
        Should be project root relative for main config.
        """
        path_to_load = None
        if config_path:
            path_to_load = Path(config_path)
        else:
            # Default to loading lcas_config.json from LCAS_2/config/
            path_to_load = (Path(__file__).parent.parent.parent / "config" / "lcas_config.json").resolve()

        try:
            if path_to_load.exists():
                with open(path_to_load, 'r') as f:
                    config_data = json.load(f)

                # Handle nested CaseTheoryConfig
                case_theory_data = config_data.get('case_theory')
                if isinstance(case_theory_data, dict):
                    config_data['case_theory'] = CaseTheoryConfig(**case_theory_data)

                return LCASConfig(**config_data)
            else:
                logger.info(f"Configuration file not found at {path_to_load}. Using default LCASConfig.")
                return LCASConfig()
        except Exception as e:
            logger.error(f"Failed to load configuration from {path_to_load}: {e}. Using default LCASConfig.", exc_info=True)
            return LCASConfig()

    @classmethod
    def create_with_config(cls, config_path: Optional[str] = None, main_loop: Optional[asyncio.AbstractEventLoop] = None) -> 'LCASCore':
        """Class method to create an LCASCore instance with loaded configuration."""
        config_instance = cls.load_config(config_path)
        return cls(config=config_instance, main_loop=main_loop)
