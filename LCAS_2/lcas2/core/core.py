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
# import tkinter as tk # Not directly used by core logic, but UIPlugin interface implies it for parent_widget
# from tkinter import ttk, messagebox # Not directly used by core logic
from abc import ABC, abstractmethod

# Assuming data_models.py is in the same directory or accessible via PYTHONPATH
from .data_models import FileAnalysisData # Ensure CaseTheoryConfig is here if not defined below

# Configure logging (basic setup, can be enhanced)
# Path resolution for logs needs to be robust if core.py is moved or called from different CWD
log_dir_for_core = (Path(__file__).parent.parent.parent / "logs").resolve() # Assuming LCAS_2 is project root
log_dir_for_core.mkdir(parents=True, exist_ok=True)
core_log_file_path = log_dir_for_core / "lcas_core.log"

# BasicConfig should only be called once. If other modules also call it, it might not behave as expected.
# Consider a dedicated logging setup function if issues arise.
logging.basicConfig(
    level=logging.INFO, # Default, will be overridden by LCASConfig
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(core_log_file_path),
        logging.StreamHandler(sys.stdout)
    ],
    force=True # If basicConfig might have been called before (e.g. by a plugin if not careful)
)
logger = logging.getLogger(__name__)


@dataclass
class CaseTheoryConfig: # Moved here for self-containment if not in data_models
    """Configuration for the case theory and objectives."""
    case_type: str = "general_civil"  # e.g., family_law, personal_injury, contract_dispute
    primary_objective: str = "Identify key evidence related to breach of contract."
    key_questions: List[str] = field(default_factory=list)
    desired_outcomes: List[str] = field(default_factory=list)
    # Placeholder for more complex theory components:
    # legal_elements_to_prove: List[str] = field(default_factory=list)
    # relevant_statutes: List[str] = field(default_factory=list)

@dataclass
class LCASConfig:
    case_name: str = "Untitled Case"
    source_directory: str = ""
    target_directory: str = ""
    # Path relative to project root (LCAS_2/). core.py is in lcas2/core.
    plugins_directory: str = "lcas2/plugins"
    enabled_plugins: List[str] = field(default_factory=list)
    debug_mode: bool = False
    log_level: str = "INFO"
    gui_theme: str = "system" # 'system', 'light', 'dark' - UI specific
    last_window_width: int = 1200
    last_window_height: int = 800
    ai_config_path: str = "config/ai_config.json" # Relative to project root
    ai_analysis_depth: str = "standard" # basic, standard, comprehensive
    ai_confidence_threshold: float = 0.6
    min_probative_score: float = 0.3; min_relevance_score: float = 0.5; similarity_threshold: float = 0.85
    probative_weight: float = 0.4; relevance_weight: float = 0.3; admissibility_weight: float = 0.3
    enable_deduplication: bool = True; enable_advanced_nlp: bool = True; generate_visualizations: bool = True
    max_concurrent_files: int = 5 # For parallel processing in plugins if they support it
    case_theory: 'CaseTheoryConfig' = field(default_factory=lambda: CaseTheoryConfig())

    # Standard plugin names used by core logic (e.g., for specific data passing)
    file_ingestion_plugin_name: str = "File Ingestion" # Matches plugin's @property name
    hash_generation_plugin_name: str = "Hash Generation"
    content_extraction_plugin_name: str = "Content Extraction"
    image_analysis_plugin_name: str = "Image Analysis"
    ai_wrapper_plugin_name: str = "lcas_ai_wrapper_plugin" # Actual plugin name from its class
    timeline_analysis_plugin_name: str = "Timeline Analysis"
    pattern_discovery_plugin_name: str = "Pattern Discovery"
    evidence_categorization_plugin_name: str = "Evidence Categorization"
    evidence_scoring_plugin_name: str = "Evidence Scoring" # Added
    case_management_plugin_name: str = "Case Management"
    report_generation_plugin_name: str = "Report Generation"

    pipeline_plugin_order: List[str] = field(default_factory=lambda: [
        "Content Extraction", # Produces initial FileAnalysisData with content
        "Image Analysis",     # Adds image OCR and analysis to FileAnalysisData
        "lcas_ai_wrapper_plugin", # Adds AI summaries, tags to FileAnalysisData
        "Timeline Analysis",  # Extracts events, can add to FileAnalysisData
        "Pattern Discovery",  # Identifies patterns from FileAnalysisData, can add to FAD
        "Evidence Scoring",   # Adds scores to FileAnalysisData
        "Evidence Categorization", # Assigns categories, updates FileAnalysisData
        "Case Management",    # Organizes files based on FAD categories/theories
    ])


    def __post_init__(self):
        if not self.enabled_plugins:
            self.enabled_plugins = [ # Default enabled plugins
                self.file_ingestion_plugin_name, self.hash_generation_plugin_name,
                self.content_extraction_plugin_name, self.image_analysis_plugin_name,
                self.ai_wrapper_plugin_name, self.timeline_analysis_plugin_name,
                self.pattern_discovery_plugin_name,
                self.evidence_scoring_plugin_name, # Added
                self.evidence_categorization_plugin_name,
                self.case_management_plugin_name, self.report_generation_plugin_name
            ]

class PluginInterface(ABC):
    @property @abstractmethod
    def name(self) -> str: pass
    @property @abstractmethod
    def version(self) -> str: pass
    @property @abstractmethod
    def description(self) -> str: pass
    @property @abstractmethod
    def dependencies(self) -> List[str]: pass
    @abstractmethod
    async def initialize(self, core_app: 'LCASCore') -> bool: pass
    @abstractmethod
    async def cleanup(self) -> None: pass

class AnalysisPlugin(PluginInterface):
    @abstractmethod
    async def analyze(self, data: Any) -> Dict[str, Any]: pass
class UIPlugin(PluginInterface):
    @abstractmethod
    def create_ui_elements(self, parent_widget: Any) -> List[Any]: pass
class ExportPlugin(PluginInterface):
    @abstractmethod
    async def export(self, data: Any, output_path: str) -> bool: pass

class PluginManager:
    def __init__(self, plugins_directory: str, core_app_ref: 'LCASCore'):
        self.plugins_directory_str = plugins_directory # Store as string from config
        self.loaded_plugins: Dict[str, PluginInterface] = {}
        self.logger = logging.getLogger(f"{__name__}.PluginManager")
        self.core_app = core_app_ref # Reference to LCASCore instance

    def discover_plugins(self) -> List[str]:
        # Resolve plugins_directory relative to project_root for discovery
        # This assumes plugins_directory in config is relative to project_root
        resolved_plugins_dir = self.core_app.project_root / self.plugins_directory_str
        if not resolved_plugins_dir.exists():
            self.logger.warning(f"Plugins directory missing: {resolved_plugins_dir.resolve()}"); return []
        self.logger.info(f"Discovering plugins in: {resolved_plugins_dir.resolve()}")
        return [p.stem for p in resolved_plugins_dir.glob("*_plugin.py")] # e.g. file_ingestion_plugin

    async def load_plugin(self, plugin_name_stem: str) -> bool: # Takes stem e.g. 'file_ingestion_plugin'
        # Add plugins dir to sys.path temporarily for import
        resolved_plugins_dir = (self.core_app.project_root / self.plugins_directory_str).resolve()
        plugins_dir_abs_str = str(resolved_plugins_dir)

        original_sys_path = list(sys.path)
        if plugins_dir_abs_str not in sys.path:
            sys.path.insert(0, plugins_dir_abs_str)

        try:
            module = importlib.import_module(plugin_name_stem) # Use stem for import
            cls_name = "".join(p.capitalize() for p in plugin_name_stem.replace("_plugin","").split("_")) + "Plugin"
            if not hasattr(module, cls_name):
                self.logger.error(f"Plugin module {plugin_name_stem} has no class {cls_name}"); return False

            plugin_instance = getattr(module, cls_name)()

            # Use plugin_instance.name (from @property) as the key for loaded_plugins
            actual_plugin_name = plugin_instance.name
            if await plugin_instance.initialize(self.core_app):
                self.loaded_plugins[actual_plugin_name] = plugin_instance
                self.logger.info(f"Successfully loaded and initialized plugin: {actual_plugin_name} (from {plugin_name_stem})")
                return True
            else:
                self.logger.error(f"Failed to initialize plugin: {actual_plugin_name} (from {plugin_name_stem})"); return False
        except Exception as e:
            self.logger.error(f"Error loading plugin {plugin_name_stem}: {e}", exc_info=True); return False
        finally:
            sys.path = original_sys_path # Restore original sys.path

    async def load_all_plugins(self, enabled_plugin_names: List[str]):
        discovered_stems = self.discover_plugins()
        for plugin_stem in discovered_stems:
            # Check if this plugin (identified by its stem) should be loaded based on enabled_plugins list
            # This requires matching stem to the plugin's actual name (property) or having a mapping.
            # For now, we load then check its name.
            # A better approach might be to have plugin metadata files or a naming convention.

            # Peek at class name to guess plugin actual name for enabled check
            # This is a bit fragile, relies on consistent naming.
            temp_class_name_for_check = "".join(p.capitalize() for p in plugin_stem.replace("_plugin","").split("_")) + "Plugin"
            # This is a temporary check. A plugin should ideally have a static method or metadata to get its name before full load.
            # For now, we proceed to load and then check against enabled_plugins.
            # This means plugins not in 'enabled_plugins' are still loaded and initialized, then potentially ignored by pipeline.

            if await self.load_plugin(plugin_stem):
                # After loading, check if its actual name is in enabled_plugin_names
                # This part is tricky as load_plugin already adds to self.loaded_plugins
                # We need to find the plugin that was just loaded.
                # Assuming plugin_stem is unique enough to find the module and then its class.
                # This is a simplified approach.

                # Find the plugin instance that was just added (its key is actual_plugin_name)
                # This logic needs refinement; currently, it might pick up an unrelated plugin if names are not carefully managed.
                # A better way: load_plugin could return the instance or its actual name.
                # For now, this will rely on the fact that load_plugin adds it.

                # The check against enabled_plugin_names should ideally happen *before* full initialization
                # or plugins not in the list should be explicitly unloaded if not desired.
                # Current logic: loads all discoverable, then pipeline uses enabled_plugins list.
                pass


    def get_plugins_by_type(self, plugin_type: Type[PluginInterface]) -> List[PluginInterface]:
        return [p for p in self.loaded_plugins.values() if isinstance(p, plugin_type)]
    async def cleanup_all_plugins(self) -> None:
        for p_name in list(self.loaded_plugins.keys()): # Iterate over keys copy
            plugin = self.loaded_plugins.pop(p_name) # Remove from dict
            await plugin.cleanup()
            self.logger.info(f"Cleaned up plugin: {plugin.name}")


class EventBus:
    def __init__(self): self.listeners: Dict[str, List[Callable]] = {}; self.logger = logging.getLogger(f"{__name__}.EventBus")
    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self.listeners: self.listeners[event_type] = []
        if callback not in self.listeners[event_type]: self.listeners[event_type].append(callback)
    def unsubscribe(self, event_type: str, callback: Callable):
        if event_type in self.listeners and callback in self.listeners[event_type]: self.listeners[event_type].remove(callback)
    async def publish(self, event_type: str, data: Any = None):
        self.logger.debug(f"Publishing event: {event_type} with data: {str(data)[:100]}...")
        for cb in self.listeners.get(event_type,[]):
            try:
                if asyncio.iscoroutinefunction(cb): await cb(data)
                else: cb(data)
            except Exception as e: self.logger.error(f"EventBus callback error for {event_type}: {e}", exc_info=True)


class LCASCore:
    def __init__(self, config: Optional[LCASConfig] = None, main_loop: Optional[asyncio.AbstractEventLoop] = None, project_root_dir: Optional[Path] = None):
        self.project_root = project_root_dir if project_root_dir else Path(__file__).resolve().parent.parent.parent
        self.config = config or self.load_config(self.project_root / "config" / "lcas_config.json")

        # Resolve relative paths in config to be absolute
        if not Path(self.config.plugins_directory).is_absolute():
            self.config.plugins_directory = str((self.project_root / self.config.plugins_directory).resolve())
        if self.config.target_directory and not Path(self.config.target_directory).is_absolute():
            self.config.target_directory = str((self.project_root / self.config.target_directory).resolve())
        if self.config.source_directory and not Path(self.config.source_directory).is_absolute():
            self.config.source_directory = str((self.project_root / self.config.source_directory).resolve())
        # ai_config_path is handled by lcas_ai_wrapper_plugin using similar project_root logic

        self.logger = self._setup_logging() # Setup logging early
        self.plugin_manager = PluginManager(self.config.plugins_directory, self) # Pass self
        self.event_bus = EventBus()
        self.running = False
        self.main_loop = main_loop or asyncio.get_event_loop()
        self.analysis_results: Dict[str, Any] = {}
        self.master_processed_files: Dict[str, FileAnalysisData] = {}

    def _setup_logging(self) -> logging.Logger:
        log_level_str = getattr(self.config, 'log_level', 'INFO').upper()
        numeric_log_level = getattr(logging, log_level_str, logging.INFO)

        # Ensure log directory exists using project_root
        log_dir = self.project_root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        core_log_file = log_dir / "lcas_core.log"

        # Reconfigure root logger if necessary, or configure LCAS specific loggers
        # Using force=True with basicConfig can affect other modules if not careful
        # If multiple calls to basicConfig happen, subsequent ones might be ignored without force=True
        logging.basicConfig(level=numeric_log_level,
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            handlers=[logging.FileHandler(core_log_file), logging.StreamHandler(sys.stdout)],
                            force=True)
        return logging.getLogger(__name__)

    async def initialize(self) -> bool:
        self.logger.info(f"Initializing LCASCore. Project Root: {self.project_root}")
        self.logger.info(f"Using Target Directory: {self.config.target_directory}")
        if self.config.target_directory: Path(self.config.target_directory).mkdir(parents=True, exist_ok=True)
        else: self.logger.warning("Target directory is not set! Some plugins might fail.");

        await self.plugin_manager.load_all_plugins(self.config.enabled_plugins or []) # Pass enabled plugin names
        await self.event_bus.publish("core.initialized", {"config": asdict(self.config)}); self.running = True; return True

    async def shutdown(self) -> None:
        await self.event_bus.publish("core.shutdown_started")
        await self.plugin_manager.cleanup_all_plugins()
        self.running = False
        self.logger.info("LCASCore shutdown complete.")
        await self.event_bus.publish("core.shutdown_completed")


    async def run_file_preservation(self, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        self.logger.info("Starting file preservation process...")
        plugin = self.plugin_manager.loaded_plugins.get(self.config.file_ingestion_plugin_name)
        if plugin and isinstance(plugin, AnalysisPlugin) and plugin.name in self.config.enabled_plugins:
            try:
                ingestion_input = {
                    "source_directory": self.config.source_directory,
                    "target_directory": self.config.target_directory,
                    "case_name": self.config.case_name,
                    "config_options": {"copy_files": True, "verify_hashes": True}
                }
                result = await plugin.analyze(ingestion_input)
                self.set_analysis_result(plugin.name, result)

                if result.get("success") and isinstance(result.get("files_details"), list):
                    for item_detail_dict in result.get("files_details", []):
                        if isinstance(item_detail_dict, dict) and item_detail_dict.get("original_path"):
                            # Assuming item_detail_dict structure matches FileIngestionDetail fields
                            fad = FileAnalysisData(file_path=item_detail_dict["original_path"])
                            fad.ingestion_details = item_detail_dict # This should ideally be FileIngestionDetail(**item_detail_dict)
                            fad.size_bytes = item_detail_dict.get("size")
                            if not fad.file_name: fad.file_name = Path(fad.file_path).name
                            self.master_processed_files[fad.file_path] = fad
                    self.logger.info(f"File preservation successful. {len(result.get('files_details',[]))} files processed into master_processed_files.")
                elif not result.get("success"): self.logger.error(f"File Ingestion plugin reported failure: {result.get('error', 'Unknown error')}")
                else: self.logger.warning("File Ingestion plugin result format unexpected or no files_details.")
                return result
            except Exception as e:
                self.logger.error(f"Error running File Ingestion plugin: {e}", exc_info=True)
                return {"error": f"File Ingestion plugin execution error: {e}", "success": False}
        else:
            self.logger.warning(f"File Ingestion plugin '{self.config.file_ingestion_plugin_name}' not found, not AnalysisPlugin, or not enabled.")
            return {"error": "File Ingestion plugin not available/enabled.", "success": False}


    async def run_full_analysis(self, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        self.logger.info("Starting full analysis pipeline...")
        await self.event_bus.publish("core.analysis_started", {"type": "full"})

        if not self.master_processed_files and self.config.source_directory:
            self.logger.info("Master processed files is empty. Attempting to populate from source directory for analysis.")
            source_path = Path(self.config.source_directory)
            if source_path.is_dir():
                 for p_file in source_path.rglob("*"):
                     if p_file.is_file() and str(p_file) not in self.master_processed_files:
                         self.master_processed_files[str(p_file)] = FileAnalysisData(file_path=str(p_file))
                 self.logger.info(f"Populated master_processed_files with {len(self.master_processed_files)} files from source_directory.")
            else:
                 self.logger.error(f"Source directory {source_path} not found for initial file scan. Cannot proceed with analysis.")
                 return {"error": "Source directory for scan not found", "success": False}
        elif not self.master_processed_files:
            self.logger.error("Master processed files is empty and no source directory provided. Cannot proceed.")
            return {"error": "No files to analyze.", "success": False}


        pipeline_plugins_names = self.config.pipeline_plugin_order
        total_plugins_in_pipeline = len(pipeline_plugins_names)

        for i, plugin_name_from_config in enumerate(pipeline_plugins_names):
            plugin: Optional[AnalysisPlugin] = None # Ensure type hint for plugin
            # Find the loaded plugin by its actual name (property), which should match plugin_name_from_config
            loaded_plugin_instance = self.plugin_manager.loaded_plugins.get(plugin_name_from_config)
            if isinstance(loaded_plugin_instance, AnalysisPlugin):
                plugin = loaded_plugin_instance

            if not plugin or plugin.name not in self.config.enabled_plugins:
                self.logger.warning(f"Skipping plugin '{plugin_name_from_config}' (not loaded as AnalysisPlugin, or not in enabled_plugins list).")
                continue

            self.logger.info(f"Pipeline Step {i+1}/{total_plugins_in_pipeline}: Executing plugin {plugin.name}")
            await self.event_bus.publish("core.plugin_execution_started", {"plugin_name": plugin.name, "step": i+1, "total_steps": total_plugins_in_pipeline})
            if progress_callback: self.main_loop.call_soon_threadsafe(progress_callback, plugin.name, "started", int((i / total_plugins_in_pipeline) * 100))

            try:
                plugin_input_data = {
                    "source_directory": self.config.source_directory,
                    "target_directory": self.config.target_directory,
                    "case_name": self.config.case_name,
                    "config": self.config,
                    "processed_files": self.master_processed_files,
                    "file_category_mapping": self.analysis_results.get(self.config.evidence_categorization_plugin_name, {}).get("result", {}).get("file_category_mapping"),
                    "potential_theories": self.analysis_results.get(self.config.pattern_discovery_plugin_name, {}).get("result", {}).get("theories")
                }

                raw_plugin_result = await plugin.analyze(plugin_input_data)
                self.set_analysis_result(plugin.name, raw_plugin_result)

                if isinstance(raw_plugin_result, dict) and raw_plugin_result.get("success"):
                    returned_processed_files = raw_plugin_result.get("processed_files_output")

                    if isinstance(returned_processed_files, dict):
                        self.logger.debug(f"Plugin {plugin.name} returned 'processed_files_output'. Updating master list.")
                        for fp_str, fad_dict_or_obj in returned_processed_files.items():
                            if not isinstance(fad_dict_or_obj, dict) and not isinstance(fad_dict_or_obj, FileAnalysisData):
                                self.logger.warning(f"Plugin {plugin.name} returned invalid item type in processed_files_output for {fp_str}. Skipping.")
                                continue

                            current_fad = self.master_processed_files.get(fp_str)
                            if not current_fad:
                                try:
                                    self.master_processed_files[fp_str] = FileAnalysisData(**fad_dict_or_obj) if isinstance(fad_dict_or_obj, dict) else fad_dict_or_obj
                                except Exception as e_create: self.logger.error(f"Error creating new FAD for {fp_str} from {plugin.name}: {e_create}")
                                continue

                            if isinstance(fad_dict_or_obj, dict):
                                for key, value in fad_dict_or_obj.items():
                                    if hasattr(current_fad, key):
                                        setattr(current_fad, key, value)
                            elif isinstance(fad_dict_or_obj, FileAnalysisData) and fad_dict_or_obj is not current_fad:
                                 self.master_processed_files[fp_str] = fad_dict_or_obj

                if progress_callback: self.main_loop.call_soon_threadsafe(progress_callback, plugin.name, "completed", int(((i + 1) / total_plugins_in_pipeline) * 100))
                await self.event_bus.publish("core.plugin_execution_completed", {"plugin_name": plugin.name, "result": raw_plugin_result, "step": i+1, "total_steps": total_plugins_in_pipeline})
            except Exception as e:
                self.logger.error(f"Error running plugin {plugin.name} in pipeline: {e}", exc_info=True)
                self.set_analysis_result(plugin.name, {"error": str(e), "success": False, "plugin_name": plugin.name})
                if progress_callback: self.main_loop.call_soon_threadsafe(progress_callback, plugin.name, "error", int(((i + 1) / total_plugins_in_pipeline) * 100))
                await self.event_bus.publish("core.error_occurred", {"error_message": str(e), "plugin_name": plugin.name})

        final_master_output = {fp: asdict(fad) for fp, fad in self.master_processed_files.items()}
        self.set_analysis_result("MasterFileAnalysisData", {"result": final_master_output, "success":True, "status":"completed"})

        await self.event_bus.publish("core.analysis_completed", {"results": self.analysis_results, "type": "full"})
        self.logger.info("Full analysis pipeline finished.")
        return self.analysis_results

    def set_analysis_result(self, plugin_name: str, result: Any):
        wrapped_result = {"result": result, "timestamp": datetime.now().isoformat(), "plugin_name": plugin_name}
        self.analysis_results[plugin_name] = wrapped_result
        asyncio.create_task(self.event_bus.publish("core.plugin_result_updated", wrapped_result))

    def get_analysis_result(self, plugin_name: str) -> Optional[Any]:
        return self.analysis_results.get(plugin_name)

    def get_analysis_plugins(self) -> List[AnalysisPlugin]: return self.plugin_manager.get_plugins_by_type(AnalysisPlugin) #type: ignore
    def get_ui_plugins(self) -> List[UIPlugin]: return self.plugin_manager.get_plugins_by_type(UIPlugin) #type: ignore
    def get_export_plugins(self) -> List[ExportPlugin]: return self.plugin_manager.get_plugins_by_type(ExportPlugin) #type: ignore

    def save_config(self, config_path: Optional[str] = None) -> bool:
        path_to_save_str = config_path if config_path else "config/lcas_config.json"
        path_to_save = self.project_root / path_to_save_str
        try:
            path_to_save.parent.mkdir(parents=True, exist_ok=True)
            # Ensure case_theory is properly converted to dict for asdict to work on LCASConfig
            config_data_to_save = asdict(self.config)
            # if isinstance(self.config.case_theory, CaseTheoryConfig): # Not needed if CaseTheoryConfig is already a dataclass
            #    config_data_to_save['case_theory'] = asdict(self.config.case_theory)

            with open(path_to_save, 'w') as f: json.dump(config_data_to_save, f, indent=2)
            self.logger.info(f"Configuration saved to {path_to_save.resolve()}")
            return True
        except Exception as e: self.logger.error(f"Error saving config to {path_to_save.resolve()}: {e}", exc_info=True); return False

    @classmethod
    def load_config(cls, config_path_abs: Optional[Path] = None) -> 'LCASConfig':
        path_to_load = config_path_abs
        if not path_to_load:
             project_r = Path(__file__).resolve().parent.parent.parent
             path_to_load = (project_r / "config" / "lcas_config.json").resolve()

        if path_to_load.exists():
            try:
                with open(path_to_load, 'r') as f: config_data = json.load(f)
                case_theory_data = config_data.get('case_theory')
                if isinstance(case_theory_data, dict):
                    config_data['case_theory'] = CaseTheoryConfig(**case_theory_data)
                elif case_theory_data is None : # Handle if case_theory is missing from JSON
                    config_data['case_theory'] = CaseTheoryConfig()

                return LCASConfig(**config_data)
            except Exception as e: logger.error(f"Error loading config from {path_to_load}: {e}. Using default.", exc_info=True)
        return LCASConfig()

    @classmethod
    def create_with_config(cls, config_path_str: Optional[str] = None, main_loop: Optional[asyncio.AbstractEventLoop] = None, project_root_dir: Optional[Path] = None) -> 'LCASCore':
        proj_root = project_root_dir if project_root_dir else Path(__file__).resolve().parent.parent.parent

        abs_config_path_to_load : Optional[Path] = None
        if config_path_str:
            config_p = Path(config_path_str)
            if config_p.is_absolute(): abs_config_path_to_load = config_p
            else: abs_config_path_to_load = (proj_root / config_path_str).resolve()

        config_instance = cls.load_config(abs_config_path_to_load)
        return cls(config=config_instance, main_loop=main_loop, project_root_dir=proj_root)
