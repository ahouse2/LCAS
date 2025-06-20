#!/usr/bin/env python3
"""
LCAS_2 Main GUI Application
Consolidated and refactored GUI for the Legal Case Analysis System.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import customtkinter as ctk
import json
import os
import threading
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable # Added Callable
from dataclasses import dataclass, asdict, field
import logging
import time # Keep for now, might be removed if all simulations are replaced
from datetime import datetime

# Attempt to import LCASCore and related components
# Assuming LCAS_2/lcas2/ is in PYTHONPATH or we adjust sys.path
try:
    from ..core.core import LCASCore, LCASConfig, CaseTheoryConfig, UIPlugin # Adjusted import
except ImportError:
    # Fallback for environments where relative import might fail (e.g. running script directly)
    # This might require LCAS_2 to be in PYTHONPATH
    import sys
    # Assuming this script is in LCAS_2/lcas2/gui/
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    from lcas2.core.core import LCASCore, LCASConfig, CaseTheoryConfig, UIPlugin

# Configure CustomTkinter appearance
ctk.set_appearance_mode("dark") # Default, can be made configurable via LCASConfig
ctk.set_default_color_theme("blue")

logger = logging.getLogger(__name__) # Use standard logging

# --- Case Theory Dialog (adapted from enhanced_lcas_gui.py) ---
class CaseTheorySetupDialog(ctk.CTkToplevel):
    def __init__(self, parent, existing_config: Optional[CaseTheoryConfig] = None, case_name: str = ""):
        super().__init__(parent)
        self.title("Case Theory Setup")
        self.geometry("700x600")
        self.transient(parent)
        self.grab_set()

        self.result_config: Optional[CaseTheoryConfig] = None
        self.result_case_name: str = case_name
        self.existing_config = existing_config or CaseTheoryConfig()
        self.existing_case_name = case_name

        self._center_on_parent(parent)
        self._setup_ui()

    def _center_on_parent(self, parent):
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        title = ctk.CTkLabel(self, text="⚖️ Case Theory Configuration", font=ctk.CTkFont(size=20, weight="bold"))
        title.grid(row=0, column=0, padx=20, pady=10)

        content_frame = ctk.CTkScrollableFrame(self)
        content_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        content_frame.grid_columnconfigure(1, weight=1)

        row = 0
        ctk.CTkLabel(content_frame, text="Case Name/Title:", font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, padx=10, pady=5, sticky="w")
        self.case_name_entry = ctk.CTkEntry(content_frame, width=400, placeholder_text="e.g., Smith v. Smith Divorce")
        self.case_name_entry.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
        self.case_name_entry.insert(0, self.existing_case_name)
        row += 1

        ctk.CTkLabel(content_frame, text="Case Type:", font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, padx=10, pady=5, sticky="w")
        self.case_type_var = ctk.StringVar(value=self.existing_config.case_type)
        self.case_type_combo = ctk.CTkComboBox(content_frame, values=["general", "family_law", "personal_injury", "business_litigation", "criminal_defense", "employment", "other"], variable=self.case_type_var) # Removed command for now
        self.case_type_combo.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
        row += 1

        # Placeholder for more detailed case theory elements if CaseTheoryConfig is expanded
        # For now, we just use case_type from CaseTheoryConfig

        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        button_frame.grid_columnconfigure(1, weight=1) # To center buttons or space them

        ctk.CTkButton(button_frame, text="Cancel", command=self._cancel).grid(row=0, column=0, padx=10, pady=10)
        ctk.CTkButton(button_frame, text="Save & Continue", command=self._save).grid(row=0, column=2, padx=10, pady=10)

    def _save(self):
        self.result_case_name = self.case_name_entry.get().strip()
        self.result_config = CaseTheoryConfig(case_type=self.case_type_var.get())
        # Add more fields from CaseTheoryConfig if they are added to UI
        self.destroy()

    def _cancel(self):
        self.result_config = None # Ensure no result on cancel
        self.result_case_name = self.existing_case_name # Revert
        self.destroy()

# --- AI Integration Panel (adapted from lcas_gui.py) ---
class AIIntegrationPanel(ctk.CTkFrame):
    def __init__(self, parent, core_app_ref: 'LCASMainGUI'): # Pass main app ref to access core.config
        super().__init__(parent)
        self.core_app_ref = core_app_ref
        self._setup_ui()

    def _get_current_ai_config_path(self) -> Path:
        # This path is relative to project root as per LCASConfig
        project_root = Path(__file__).parent.parent.parent
        return project_root / self.core_app_ref.core.config.ai_config_path

    def _load_ai_plugin_config(self) -> dict:
        # Loads the specific ai_config.json
        ai_config_file = self._get_current_ai_config_path()
        if ai_config_file.exists():
            try:
                with open(ai_config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading AI plugin config from {ai_config_file}: {e}")
                messagebox.showerror("AI Config Error", f"Could not load {ai_config_file}:\n{e}")
        return {} # Return empty dict if not found or error

    def _save_ai_plugin_config(self, config_data: dict):
        ai_config_file = self._get_current_ai_config_path()
        ai_config_file.parent.mkdir(parents=True, exist_ok=True) # Ensure directory exists
        try:
            with open(ai_config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            logger.info(f"AI plugin configuration saved to {ai_config_file}")
            messagebox.showinfo("AI Config Saved", f"AI configuration saved to\n{ai_config_file}")
        except Exception as e:
            logger.error(f"Error saving AI plugin config to {ai_config_file}: {e}")
            messagebox.showerror("AI Config Error", f"Could not save {ai_config_file}:\n{e}")

    def _setup_ui(self):
        title = ctk.CTkLabel(self, text="🤖 AI Integration Settings (ai_config.json)", font=ctk.CTkFont(size=16, weight="bold"))
        title.grid(row=0, column=0, columnspan=2, padx=20, pady=10, sticky="w")

        # Load current ai_plugin_config
        ai_plugin_config = self._load_ai_plugin_config()
        # Default provider settings (example for openai)
        provider_settings = ai_plugin_config.get("providers", {}).get("openai", {})

        self.ai_enabled_var = ctk.BooleanVar(value=provider_settings.get("enabled", True))
        ctk.CTkSwitch(self, text="Enable OpenAI (Example Provider)", variable=self.ai_enabled_var).grid(row=1, column=0, columnspan=2, padx=20, pady=5, sticky="w")

        ctk.CTkLabel(self, text="OpenAI API Key:").grid(row=2, column=0, padx=20, pady=5, sticky="w")
        self.api_key_entry = ctk.CTkEntry(self, show="*", placeholder_text="sk-...")
        self.api_key_entry.grid(row=2, column=1, padx=20, pady=5, sticky="ew")
        self.api_key_entry.insert(0, provider_settings.get("api_key", ""))

        ctk.CTkLabel(self, text="OpenAI Model:").grid(row=3, column=0, padx=20, pady=5, sticky="w")
        self.model_entry = ctk.CTkEntry(self, placeholder_text="gpt-4")
        self.model_entry.grid(row=3, column=1, padx=20, pady=5, sticky="ew")
        self.model_entry.insert(0, provider_settings.get("model", "gpt-4"))

        # Main LCASConfig AI settings
        ctk.CTkLabel(self, text="Analysis Depth (LCASConfig):").grid(row=4, column=0, padx=20, pady=5, sticky="w")
        self.analysis_depth_var = ctk.StringVar(value=self.core_app_ref.core.config.ai_analysis_depth)
        ctk.CTkComboBox(self, values=["basic", "standard", "comprehensive"], variable=self.analysis_depth_var).grid(row=4, column=1, padx=20, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Confidence Threshold (LCASConfig):").grid(row=5, column=0, padx=20, pady=5, sticky="w")
        self.confidence_threshold_var = ctk.DoubleVar(value=self.core_app_ref.core.config.ai_confidence_threshold)
        ctk.CTkSlider(self, from_=0.0, to=1.0, variable=self.confidence_threshold_var).grid(row=5, column=1, padx=20, pady=5, sticky="ew")

        ctk.CTkButton(self, text="Save AI Settings", command=self._save_settings).grid(row=6, column=0, columnspan=2, padx=20, pady=20)
        self.grid_columnconfigure(1, weight=1)

    def _save_settings(self):
        # Update LCASConfig (main config)
        self.core_app_ref.core.config.ai_analysis_depth = self.analysis_depth_var.get()
        self.core_app_ref.core.config.ai_confidence_threshold = self.confidence_threshold_var.get()
        # self.core_app_ref.save_app_config() # Call to save the main LCASConfig

        # Update ai_config.json (AI Plugin's specific config)
        current_ai_plugin_config = self._load_ai_plugin_config()
        if "providers" not in current_ai_plugin_config: current_ai_plugin_config["providers"] = {}
        if "openai" not in current_ai_plugin_config["providers"]: current_ai_plugin_config["providers"]["openai"] = {}

        current_ai_plugin_config["providers"]["openai"]["enabled"] = self.ai_enabled_var.get()
        current_ai_plugin_config["providers"]["openai"]["api_key"] = self.api_key_entry.get()
        current_ai_plugin_config["providers"]["openai"]["model"] = self.model_entry.get()
        # Add other fields like temperature, max_tokens as UI elements are added for them

        self._save_ai_plugin_config(current_ai_plugin_config)
        self.core_app_ref.update_status("AI settings saved.")


# --- Main Application Window ---
class LCASMainGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("LCAS_2 - Legal Case Analysis System")
        self.geometry("1200x800")
        self.minsize(1000, 700)

        self.core_app: Optional[LCASCore] = None
        self.core_thread: Optional[threading.Thread] = None
        self.async_event_loop: Optional[asyncio.AbstractEventLoop] = None # For core's asyncio operations

        self._setup_logging_text_widget()
        self._setup_ui()
        self._initialize_core_async()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_logging_text_widget(self):
        # Create a handler for the GUI log text widget
        self.log_text_handler = GUILogHandler(self) # self will be updated later
        self.log_text_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.log_text_handler.setFormatter(formatter)
        logging.getLogger().addHandler(self.log_text_handler) # Add to root logger

    def _initialize_core_async(self):
        self.update_status("Initializing LCAS Core...")
        def run_core_init():
            self.async_event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.async_event_loop)

            # Load config first, then create core with it
            # Config path is relative to project root (LCAS_2/)
            config_path = Path(__file__).parent.parent.parent / "config" / "lcas_config.json"

            self.core_app = LCASCore.create_with_config(config_path=str(config_path), main_loop=self.async_event_loop)

            # Subscribe to core events
            self.core_app.event_bus.subscribe("core.initialized", self._on_core_initialized)
            self.core_app.event_bus.subscribe("core.analysis_started", self._on_analysis_started)
            self.core_app.event_bus.subscribe("core.plugin_execution_started", self._on_plugin_started)
            self.core_app.event_bus.subscribe("core.plugin_execution_completed", self._on_plugin_completed)
            self.core_app.event_bus.subscribe("core.analysis_progress", self._on_analysis_progress)
            self.core_app.event_bus.subscribe("core.analysis_completed", self._on_analysis_completed)
            self.core_app.event_bus.subscribe("core.error_occurred", self._on_core_error)
            self.core_app.event_bus.subscribe("core.preservation_started", lambda d: self.update_status("Preservation started..."))
            self.core_app.event_bus.subscribe("core.preservation_completed", self._on_preservation_completed)


            self.async_event_loop.run_until_complete(self.core_app.initialize())
            # Loop can be run here if core needs to do continuous background work
            # For now, initialize is enough. GUI will trigger async tasks.
            logger.info("Core asyncio event loop setup in thread.")

        self.core_thread = threading.Thread(target=run_core_init, daemon=True)
        self.core_thread.start()

    def _setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1) # Main content area
        self.grid_rowconfigure(1, weight=0) # Status bar
        self.grid_rowconfigure(2, weight=0) # Log area

        self._create_sidebar()
        self._create_main_content_area()
        self._create_status_bar()
        self._create_log_area() # For GUI log messages

        self.show_panel("dashboard") # Default panel

    def _create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew") # Span 2 rows to be beside main_frame and log_area
        self.sidebar_frame.grid_rowconfigure(8, weight=1) # Push items to top

        ctk.CTkLabel(self.sidebar_frame, text="LCAS_2", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, padx=20, pady=(20,10))

        self.nav_buttons = {}
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("⚙️ Config & Setup", "config_setup"), # Combined general config
            ("▶️ Run Analysis", "run_analysis"),
            ("📊 Results", "results"),
            ("🧩 Plugins", "plugins_panel") # For plugin-contributed UI
        ]
        for i, (text, key) in enumerate(nav_items):
            btn = ctk.CTkButton(self.sidebar_frame, text=text, command=lambda k=key: self.show_panel(k), height=40, anchor="w")
            btn.grid(row=i + 1, column=0, padx=20, pady=5, sticky="ew")
            self.nav_buttons[key] = btn

        ctk.CTkLabel(self.sidebar_frame, text=f"Version: {datetime.now().strftime('%Y.%m.%d')}", font=ctk.CTkFont(size=10)).grid(row=9, column=0, padx=20, pady=10, sticky="s")


    def _create_main_content_area(self):
        self.main_content_frame = ctk.CTkFrame(self)
        self.main_content_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        self.main_content_frame.grid_rowconfigure(0, weight=1)

        self.panels = {}
        # Initialize panels (specific content will be added)
        self.panels["dashboard"] = self._create_dashboard_panel()
        self.panels["config_setup"] = self._create_config_setup_panel()
        self.panels["run_analysis"] = self._create_run_analysis_panel()
        self.panels["results"] = self._create_results_panel()
        self.panels["plugins_panel"] = self._create_plugins_features_panel()


    def _create_dashboard_panel(self):
        panel = ctk.CTkFrame(self.main_content_frame)
        ctk.CTkLabel(panel, text="LCAS_2 Dashboard", font=ctk.CTkFont(size=28, weight="bold")).pack(pady=20)
        ctk.CTkLabel(panel, text="Welcome to the Legal Case Analysis System.\nUse the sidebar to navigate.", justify="center").pack(pady=10)
        # TODO: Add summary stats or quick actions
        return panel

    def _create_config_setup_panel(self):
        panel = ctk.CTkScrollableFrame(self.main_content_frame)
        panel.grid_columnconfigure(0, weight=1) # Allow content to expand

        ctk.CTkLabel(panel, text="Configuration & Setup", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(10,15), anchor="w", padx=10)

        # Case Name & Directories Frame
        dir_frame = ctk.CTkFrame(panel)
        dir_frame.pack(fill="x", pady=5, padx=10)
        dir_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(dir_frame, text="Case Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.case_name_entry = ctk.CTkEntry(dir_frame, placeholder_text="Enter case name/identifier")
        self.case_name_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(dir_frame, text="Source Directory:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.source_dir_entry = ctk.CTkEntry(dir_frame, placeholder_text="Path to evidence files")
        self.source_dir_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(dir_frame, text="Browse...", command=lambda: self._browse_directory(self.source_dir_entry)).grid(row=1, column=2, padx=5, pady=5)

        ctk.CTkLabel(dir_frame, text="Target Directory:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.target_dir_entry = ctk.CTkEntry(dir_frame, placeholder_text="Path to save results")
        self.target_dir_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(dir_frame, text="Browse...", command=lambda: self._browse_directory(self.target_dir_entry)).grid(row=2, column=2, padx=5, pady=5)

        # Case Theory Button
        ctk.CTkButton(panel, text="Setup Case Theory", command=self._open_case_theory_dialog).pack(pady=10, padx=10, anchor="w")

        # AI Settings Panel (Integrated here)
        self.ai_settings_panel = AIIntegrationPanel(panel, self) # Pass self (LCASMainGUI instance)
        self.ai_settings_panel.pack(fill="x", pady=10, padx=10)

        # General App Settings (Theme, etc.)
        general_settings_frame = ctk.CTkFrame(panel)
        general_settings_frame.pack(fill="x", pady=10, padx=10)
        general_settings_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(general_settings_frame, text="Appearance Theme:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.theme_var = ctk.StringVar(value="dark") # Default, will load from config
        theme_menu = ctk.CTkOptionMenu(general_settings_frame, variable=self.theme_var, values=["light", "dark", "system"], command=self._change_theme)
        theme_menu.grid(row=0, column=1, padx=5, pady=5, sticky="ew")


        # Additional Analysis & Processing Settings Frame
        adv_settings_frame = ctk.CTkFrame(panel)
        adv_settings_frame.pack(fill="x", pady=10, padx=10)
        adv_settings_frame.grid_columnconfigure(1, weight=0) # Label column
        adv_settings_frame.grid_columnconfigure(3, weight=0) # Label column
        adv_settings_frame.grid_columnconfigure(5, weight=1) # Entry/widget column (flexible)


        ctk.CTkLabel(adv_settings_frame, text="Advanced Settings", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=6, padx=5, pady=(5,10), sticky="w")

        # Debug Mode
        ctk.CTkLabel(adv_settings_frame, text="Debug Mode:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.debug_mode_var = ctk.BooleanVar()
        ctk.CTkCheckBox(adv_settings_frame, text="", variable=self.debug_mode_var).grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Log Level
        ctk.CTkLabel(adv_settings_frame, text="Log Level:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.log_level_var = ctk.StringVar()
        ctk.CTkOptionMenu(adv_settings_frame, variable=self.log_level_var, values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]).grid(row=1, column=3, columnspan=2, padx=5, pady=5, sticky="ew")

        # Min Probative Score
        ctk.CTkLabel(adv_settings_frame, text="Min Probative Score:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.min_probative_score_var = ctk.DoubleVar()
        ctk.CTkEntry(adv_settings_frame, textvariable=self.min_probative_score_var, width=80).grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # Min Relevance Score
        ctk.CTkLabel(adv_settings_frame, text="Min Relevance Score:").grid(row=2, column=2, padx=5, pady=5, sticky="w")
        self.min_relevance_score_var = ctk.DoubleVar()
        ctk.CTkEntry(adv_settings_frame, textvariable=self.min_relevance_score_var, width=80).grid(row=2, column=3, padx=5, pady=5, sticky="w")

        # Similarity Threshold
        ctk.CTkLabel(adv_settings_frame, text="Similarity Threshold:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.similarity_threshold_var = ctk.DoubleVar()
        ctk.CTkEntry(adv_settings_frame, textvariable=self.similarity_threshold_var, width=80).grid(row=3, column=1, padx=5, pady=5, sticky="w")

        # Max Concurrent Files
        ctk.CTkLabel(adv_settings_frame, text="Max Concurrent Files:").grid(row=3, column=2, padx=5, pady=5, sticky="w")
        self.max_concurrent_files_var = ctk.IntVar()
        ctk.CTkEntry(adv_settings_frame, textvariable=self.max_concurrent_files_var, width=80).grid(row=3, column=3, padx=5, pady=5, sticky="w")

        # Probative Weight
        ctk.CTkLabel(adv_settings_frame, text="Probative Weight:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.probative_weight_var = ctk.DoubleVar()
        ctk.CTkEntry(adv_settings_frame, textvariable=self.probative_weight_var, width=80).grid(row=4, column=1, padx=5, pady=5, sticky="w")

        # Relevance Weight
        ctk.CTkLabel(adv_settings_frame, text="Relevance Weight:").grid(row=4, column=2, padx=5, pady=5, sticky="w")
        self.relevance_weight_var = ctk.DoubleVar()
        ctk.CTkEntry(adv_settings_frame, textvariable=self.relevance_weight_var, width=80).grid(row=4, column=3, padx=5, pady=5, sticky="w")

        # Admissibility Weight
        ctk.CTkLabel(adv_settings_frame, text="Admissibility Weight:").grid(row=5, column=0, padx=5, pady=5, sticky="w")
        self.admissibility_weight_var = ctk.DoubleVar()
        ctk.CTkEntry(adv_settings_frame, textvariable=self.admissibility_weight_var, width=80).grid(row=5, column=1, padx=5, pady=5, sticky="w")

        # Boolean Processing Options
        ctk.CTkLabel(adv_settings_frame, text="Processing Options:").grid(row=6, column=0, padx=5, pady=10, sticky="w")
        self.enable_deduplication_var = ctk.BooleanVar()
        ctk.CTkCheckBox(adv_settings_frame, text="Enable Deduplication", variable=self.enable_deduplication_var).grid(row=7, column=0, columnspan=2, padx=10, pady=2, sticky="w")

        self.enable_advanced_nlp_var = ctk.BooleanVar()
        ctk.CTkCheckBox(adv_settings_frame, text="Enable Advanced NLP", variable=self.enable_advanced_nlp_var).grid(row=7, column=2, columnspan=2, padx=10, pady=2, sticky="w")

        self.generate_visualizations_var = ctk.BooleanVar()
        ctk.CTkCheckBox(adv_settings_frame, text="Generate Visualizations", variable=self.generate_visualizations_var).grid(row=8, column=0, columnspan=2, padx=10, pady=2, sticky="w")

        # Save All Config Button
        ctk.CTkButton(panel, text="💾 Save All Configurations", command=self.save_app_config).pack(pady=20, padx=10)
        return panel

    def _create_run_analysis_panel(self):
        panel = ctk.CTkFrame(self.main_content_frame)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1) # For progress text area

        ctk.CTkLabel(panel, text="Run Analysis", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, columnspan=2, pady=10, padx=10, sticky="w")

        button_frame = ctk.CTkFrame(panel)
        button_frame.grid(row=1, column=0, pady=10, padx=10, sticky="ew")

        self.run_preservation_button = ctk.CTkButton(button_frame, text="1. Run File Preservation", command=self._start_file_preservation)
        self.run_preservation_button.pack(side="left", padx=5)

        self.run_full_analysis_button = ctk.CTkButton(button_frame, text="2. Run Full Analysis", command=self._start_full_analysis)
        self.run_full_analysis_button.pack(side="left", padx=5)

        self.analysis_progress_bar = ctk.CTkProgressBar(panel)
        self.analysis_progress_bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        self.analysis_progress_bar.set(0)

        self.current_task_label = ctk.CTkLabel(panel, text="Current Task: Idle")
        self.current_task_label.grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=2)

        self.analysis_log_display = ctk.CTkTextbox(panel, height=200) # Renamed from log_text_widget
        self.analysis_log_display.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
        self.log_text_handler.textbox = self.analysis_log_display # Link handler to this specific textbox

        return panel

    def _create_results_panel(self):
        panel = ctk.CTkFrame(self.main_content_frame)
        ctk.CTkLabel(panel, text="Analysis Results", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)
        self.results_display_text = ctk.CTkTextbox(panel)
        self.results_display_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.results_display_text.insert("1.0", "Analysis results will be summarized here.")
        # TODO: Add more structured results display (e.g., treeview, report links)
        return panel

    def _create_plugins_features_panel(self):
        panel = ctk.CTkScrollableFrame(self.main_content_frame)
        ctk.CTkLabel(panel, text="Plugin Features", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10, anchor="w", padx=10)
        # This panel will be populated by UIPlugins
        return panel


    def _create_status_bar(self):
        self.status_bar_frame = ctk.CTkFrame(self, height=30, corner_radius=0)
        self.status_bar_frame.grid(row=1, column=1, sticky="ew", padx=10, pady=(0,5)) # Aligns with main_content_frame
        self.status_label = ctk.CTkLabel(self.status_bar_frame, text="Ready", anchor="w")
        self.status_label.pack(side="left", padx=10)

    def _create_log_area(self):
        # This is for general app/GUI logs, distinct from analysis_log_display
        self.app_log_frame = ctk.CTkFrame(self, height=100)
        self.app_log_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=5, pady=5) # Spans full width below sidebar and main

        log_label = ctk.CTkLabel(self.app_log_frame, text="Application Log:", font=ctk.CTkFont(size=12, weight="bold"))
        log_label.pack(anchor="w", padx=5, pady=(5,0))

        self.gui_log_textbox = ctk.CTkTextbox(self.app_log_frame, height=80)
        self.gui_log_textbox.pack(fill="both", expand=True, padx=5, pady=(0,5))
        self.log_text_handler.gui_textbox = self.gui_log_textbox # Link handler to this textbox too, if desired for general logs
        # Or create another handler for this specific box. For now, one handler might write to both.

    def show_panel(self, panel_name: str):
        for name, panel_widget in self.panels.items():
            panel_widget.grid_remove()

        if panel_name in self.panels:
            self.panels[panel_name].grid(row=0, column=0, sticky="nsew", in_=self.main_content_frame) # Ensure it's placed in main_content_frame
            logger.debug(f"Showing panel: {panel_name}")
        else:
            logger.warning(f"Panel '{panel_name}' not found.")

        for key, btn in self.nav_buttons.items():
            btn.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"] if key != panel_name else ctk.ThemeManager.theme["CTkButton"]["hover_color"])

    def update_status(self, message: str):
        self.status_label.configure(text=f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        logger.info(f"Status Update: {message}")

    def _browse_directory(self, entry_widget: ctk.CTkEntry):
        dir_path = filedialog.askdirectory(initialdir=entry_widget.get() or os.path.expanduser("~"))
        if dir_path:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, dir_path)
            self.update_status(f"Directory set: {Path(dir_path).name}")

    def _change_theme(self, new_theme: str):
        ctk.set_appearance_mode(new_theme)
        self.update_status(f"Theme changed to {new_theme}")
        # Save this to config

    def _open_case_theory_dialog(self):
        if not self.core_app: self.update_status("Core not ready."); return

        dialog = CaseTheorySetupDialog(self, self.core_app.config.case_theory, self.core_app.config.case_name)
        self.wait_window(dialog) # Blocks until dialog is closed

        if dialog.result_config:
            self.core_app.config.case_theory = dialog.result_config
            self.core_app.config.case_name = dialog.result_case_name
            self.case_name_entry.delete(0, "end"); self.case_name_entry.insert(0, dialog.result_case_name)
            # Update other UI elements if they display case_type from CaseTheoryConfig
            self.update_status(f"Case theory updated for '{dialog.result_case_name}'.")
            self.save_app_config() # Save immediately
        else:
            self.update_status("Case theory setup cancelled.")

    def save_app_config(self):
        if not self.core_app:
            messagebox.showerror("Error", "Core application not initialized. Cannot save configuration.")
            return

        # Update core_app.config from UI elements in config_setup panel
        self.core_app.config.case_name = self.case_name_entry.get()
        self.core_app.config.source_directory = self.source_dir_entry.get()
        self.core_app.config.target_directory = self.target_dir_entry.get()
        self.core_app.config.gui_theme = self.theme_var.get()

        # Save new config values
        self.core_app.config.debug_mode = self.debug_mode_var.get()
        self.core_app.config.log_level = self.log_level_var.get()
        self.core_app.config.min_probative_score = self.min_probative_score_var.get()
        self.core_app.config.min_relevance_score = self.min_relevance_score_var.get()
        self.core_app.config.similarity_threshold = self.similarity_threshold_var.get()
        self.core_app.config.probative_weight = self.probative_weight_var.get()
        self.core_app.config.relevance_weight = self.relevance_weight_var.get()
        self.core_app.config.admissibility_weight = self.admissibility_weight_var.get()
        self.core_app.config.enable_deduplication = self.enable_deduplication_var.get()
        self.core_app.config.enable_advanced_nlp = self.enable_advanced_nlp_var.get()
        self.core_app.config.generate_visualizations = self.generate_visualizations_var.get()
        self.core_app.config.max_concurrent_files = self.max_concurrent_files_var.get()

        # AI settings are saved via AIIntegrationPanel's own save button
        # CaseTheory is saved when its dialog closes

        if self.core_app.save_config(): # Uses the save_config in LCASCore
            self.update_status("Application configuration saved successfully.")
        else:
            messagebox.showerror("Error", "Failed to save application configuration. Check logs.")

    def _load_app_config_to_ui(self):
        if not self.core_app: return
        config = self.core_app.config
        self.case_name_entry.insert(0, config.case_name)
        self.source_dir_entry.insert(0, config.source_directory)
        self.target_dir_entry.insert(0, config.target_directory)
        self.theme_var.set(config.gui_theme)
        ctk.set_appearance_mode(config.gui_theme) # Apply theme

        # Load new UI variables
        if hasattr(self, "debug_mode_var"): self.debug_mode_var.set(config.debug_mode)
        if hasattr(self, "log_level_var"): self.log_level_var.set(config.log_level)
        if hasattr(self, "min_probative_score_var"): self.min_probative_score_var.set(config.min_probative_score)
        if hasattr(self, "min_relevance_score_var"): self.min_relevance_score_var.set(config.min_relevance_score)
        if hasattr(self, "similarity_threshold_var"): self.similarity_threshold_var.set(config.similarity_threshold)
        if hasattr(self, "probative_weight_var"): self.probative_weight_var.set(config.probative_weight)
        if hasattr(self, "relevance_weight_var"): self.relevance_weight_var.set(config.relevance_weight)
        if hasattr(self, "admissibility_weight_var"): self.admissibility_weight_var.set(config.admissibility_weight)
        if hasattr(self, "enable_deduplication_var"): self.enable_deduplication_var.set(config.enable_deduplication)
        if hasattr(self, "enable_advanced_nlp_var"): self.enable_advanced_nlp_var.set(config.enable_advanced_nlp)
        if hasattr(self, "generate_visualizations_var"): self.generate_visualizations_var.set(config.generate_visualizations)
        if hasattr(self, "max_concurrent_files_var"): self.max_concurrent_files_var.set(config.max_concurrent_files)

        # AI panel should load its own config based on core_app.config.ai_config_path
        if hasattr(self, 'ai_settings_panel'):
             self.ai_settings_panel._setup_ui() # Trigger AI panel to reload/refresh its display

        self.update_status("Configuration loaded into UI.")

    # --- Core Event Handlers ---
    def _on_core_initialized(self, data: Optional[dict]):
        config_data = data.get("config") if data else None
        if self.core_app and config_data:
            self.update_status("LCAS Core Initialized Successfully.")
            self.after(0, self._load_app_config_to_ui) # Load config into UI elements
            self._populate_plugin_features_tab() # Load UI from plugins
        else:
            self.update_status("LCAS Core Initialized, but config data missing in event.")
            logger.warning("Core initialized event did not pass config data as expected.")

    def _populate_plugin_features_tab(self):
        if not self.core_app: return

        plugins_ui_panel = self.panels.get("plugins_panel")
        if not plugins_ui_panel: return

        # Clear previous plugin UIs
        for widget in plugins_ui_panel.winfo_children():
            if widget.winfo_class() != 'CTkLabel': # Keep the title label
                widget.destroy()

        ui_plugins = self.core_app.get_ui_plugins()
        if not ui_plugins:
            ctk.CTkLabel(plugins_ui_panel, text="No active UI plugins found.").pack(padx=10, pady=10)
            return

        for plugin in ui_plugins:
            try:
                logger.info(f"Creating UI for plugin: {plugin.name}")
                # Create a frame for each plugin's UI for better separation
                plugin_frame = ctk.CTkFrame(plugins_ui_panel)
                plugin_frame.pack(fill="x", pady=5, padx=5)
                ctk.CTkLabel(plugin_frame, text=f"{plugin.name} Features", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5)

                plugin.create_ui_elements(plugin_frame) # Plugin adds its elements to this frame
            except Exception as e:
                logger.error(f"Error creating UI for plugin {plugin.name}: {e}", exc_info=True)
                ctk.CTkLabel(plugins_ui_panel, text=f"Error loading UI for {plugin.name}.", text_color="red").pack()


    def _on_analysis_started(self, data: Optional[dict]):
        analysis_type = data.get("type", "analysis") if data else "analysis"
        self.update_status(f"Full {analysis_type} started...")
        self.analysis_progress_bar.set(0)
        self.analysis_log_display.delete("1.0", tk.END) # Clear previous log
        self.current_task_label.configure(text=f"Current Task: Starting {analysis_type}...")

    def _on_plugin_started(self, data: dict):
        plugin_name = data.get("plugin_name", "Unknown plugin")
        self.update_status(f"Plugin started: {plugin_name}")
        self.current_task_label.configure(text=f"Current Task: Running {plugin_name}...")


    def _on_plugin_completed(self, data: dict):
        plugin_name = data.get("plugin_name", "Unknown plugin")
        result = data.get("result", {})
        status = "completed successfully" if result.get("success", True) else f"failed ({result.get('error', 'unknown error')})"
        self.update_status(f"Plugin {plugin_name} {status}.")
        logger.info(f"Plugin {plugin_name} result: {str(result)[:200]}") # Log snippet of result

    def _on_analysis_progress(self, data: dict): # This event is not yet published by core methods added
        progress = data.get("overall_progress_percentage", 0)
        task_desc = data.get("current_task_description", "Processing...")
        self.analysis_progress_bar.set(float(progress) / 100.0)
        self.current_task_label.configure(text=f"Current Task: {task_desc} ({progress}%)")

    def _on_analysis_completed(self, data: dict):
        analysis_type = data.get("type", "analysis")
        results = data.get("results", {})
        self.update_status(f"Full {analysis_type} completed.")
        self.analysis_progress_bar.set(1.0) # Mark as complete
        self.current_task_label.configure(text=f"Current Task: {analysis_type.capitalize()} complete.")

        # Display summary in results panel
        summary = f"{analysis_type.capitalize()} Completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        summary += "Plugin Results:\n"
        for plugin_name, result_data in results.items():
            status = "Success" if isinstance(result_data, dict) and result_data.get("status") == "completed" or result_data.get("success", True) else "Failed"
            details = str(result_data)[:200] + "..." if len(str(result_data)) > 200 else str(result_data)
            summary += f"  - {plugin_name}: {status}\n    Details: {details}\n"

        self.results_display_text.delete("1.0", tk.END)
        self.results_display_text.insert("1.0", summary)
        self.show_panel("results")
        messagebox.showinfo("Analysis Complete", f"{analysis_type.capitalize()} has finished. Check the Results panel and logs.")

    def _on_preservation_completed(self, data: dict):
        self.update_status("File preservation completed.")
        # Example: data might be {'file_ingestion_plugin': {'files_copied': 10, 'status': 'completed'}}
        ingestion_result = data.get("file_ingestion_plugin", {})
        files_copied = ingestion_result.get("files_copied", "N/A")
        message = f"File preservation finished. Files copied: {files_copied}."
        if ingestion_result.get("error"):
            message += f" Error: {ingestion_result['error']}"
            messagebox.showerror("Preservation Error", message)
        else:
            messagebox.showinfo("Preservation Complete", message)
        self.current_task_label.configure(text="Current Task: Preservation complete.")


    def _on_core_error(self, data: dict):
        error_msg = data.get("error_message", "Unknown core error")
        plugin_name = data.get("plugin_name")
        full_msg = f"Error: {error_msg}"
        if plugin_name:
            full_msg = f"Error in plugin {plugin_name}: {error_msg}"

        self.update_status(f"ERROR: {error_msg[:100]}") # Show truncated error in status
        logger.error(full_msg) # Log full error
        messagebox.showerror("Core Application Error", full_msg)
        self.current_task_label.configure(text=f"Current Task: Error occurred.")


    # --- GUI Actions ---
    def _start_file_preservation(self):
        if not self.core_app or not self.core_app.running:
            messagebox.showerror("Error", "LCAS Core is not running or initialized."); return
        if not self.core_app.config.source_directory or not self.core_app.config.target_directory:
            messagebox.showerror("Configuration Error", "Source and Target directories must be set."); return

        self.update_status("Starting file preservation...")
        self.analysis_progress_bar.set(0) # Reset progress
        self.current_task_label.configure(text="Current Task: Starting Preservation...")

        async def task():
            await self.core_app.run_file_preservation(progress_callback=self._gui_progress_callback)

        asyncio.run_coroutine_threadsafe(task(), self.async_event_loop)

    def _start_full_analysis(self):
        if not self.core_app or not self.core_app.running:
            messagebox.showerror("Error", "LCAS Core is not running or initialized."); return
        if not self.core_app.config.source_directory or not self.core_app.config.target_directory:
            messagebox.showerror("Configuration Error", "Source and Target directories must be set."); return

        self.update_status("Starting full analysis...")
        self.analysis_progress_bar.set(0)
        self.current_task_label.configure(text="Current Task: Starting Full Analysis...")

        async def task():
            await self.core_app.run_full_analysis(progress_callback=self._gui_progress_callback)

        asyncio.run_coroutine_threadsafe(task(), self.async_event_loop)

    def _gui_progress_callback(self, plugin_name: str, status: str, percentage: int):
        # This method is called from LCASCore via main_loop.call_soon_threadsafe
        # So it runs in the GUI thread.
        self.analysis_progress_bar.set(float(percentage) / 100.0)
        self.current_task_label.configure(text=f"Current Task: {plugin_name} - {status} ({percentage}%)")
        if status == "error":
            logger.error(f"Progress callback reported error for {plugin_name}")
        elif status == "completed" and percentage == 100:
             logger.info(f"Progress callback reported completion for {plugin_name}")


    def _on_closing(self):
        logger.info("Attempting to close application...")
        if messagebox.askokcancel("Quit LCAS_2", "Are you sure you want to quit?"):
            if self.core_app and self.core_app.running and self.async_event_loop:
                self.update_status("Shutting down LCAS Core...")
                # Ensure shutdown is awaited if it's async and loop is running
                if self.async_event_loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(self.core_app.shutdown(), self.async_event_loop)
                    try:
                        future.result(timeout=5) # Wait for shutdown to complete
                        logger.info("Core shutdown completed via future.")
                    except TimeoutError:
                        logger.warning("Core shutdown timed out.")
                    except Exception as e:
                        logger.error(f"Exception during core shutdown: {e}")
                else: # Fallback if loop isn't running (should not happen if init was ok)
                    try:
                        asyncio.run(self.core_app.shutdown()) # Won't work if loop is from different thread
                        logger.info("Core shutdown completed via asyncio.run (fallback).")
                    except RuntimeError as e:
                         logger.error(f"RuntimeError during fallback shutdown: {e} (Likely due to loop mismatch)")


            if self.async_event_loop and self.async_event_loop.is_running():
                self.async_event_loop.call_soon_threadsafe(self.async_event_loop.stop)
                logger.info("Requested asyncio event loop to stop.")

            if self.core_thread and self.core_thread.is_alive():
                self.core_thread.join(timeout=2) # Wait for thread to finish
                if self.core_thread.is_alive():
                    logger.warning("Core thread did not terminate gracefully.")

            self.destroy()
            logger.info("LCAS_2 GUI closed.")
            # Ensure all logging is flushed, etc.
            logging.shutdown()


# Helper for logging to GUI (from any thread)
class GUILogHandler(logging.Handler):
    def __init__(self, gui_instance_ref_for_after=None):
        super().__init__()
        self.gui_instance_ref_for_after = gui_instance_ref_for_after
        self.textbox = None # Will be set by LCASMainGUI to point to the log textbox
        self.gui_textbox = None # For general GUI logs

    def emit(self, record):
        log_entry = self.format(record)

        # Log to analysis_log_display if available
        if self.textbox and hasattr(self.textbox, 'insert') and hasattr(self.textbox, 'see'):
            if hasattr(self.gui_instance_ref_for_after, 'after_idle'): # Check if it's a Tkinter compatible object
                self.gui_instance_ref_for_after.after_idle(self._insert_log, self.textbox, log_entry)
            else: # Fallback or direct call if not needing `after` (e.g. if already in main thread)
                 try: self._insert_log(self.textbox, log_entry)
                 except: pass # Avoid error if textbox not fully ready

        # Also log to gui_log_textbox if available
        if self.gui_textbox and hasattr(self.gui_textbox, 'insert') and hasattr(self.gui_textbox, 'see'):
            if hasattr(self.gui_instance_ref_for_after, 'after_idle'):
                self.gui_instance_ref_for_after.after_idle(self._insert_log, self.gui_textbox, log_entry)
            else:
                try: self._insert_log(self.gui_textbox, log_entry)
                except: pass


    def _insert_log(self, textbox_widget, log_entry):
        try:
            textbox_widget.insert(tk.END, log_entry + "\n")
            textbox_widget.see(tk.END)
        except Exception as e:
            print(f"Error writing to GUI log textbox: {e}") # Print to console if GUI log fails


def main():
    # Ensure project root is in path if running this file directly for testing
    current_script_path = Path(__file__).resolve()
    project_root_if_direct = current_script_path.parent.parent.parent
    if str(project_root_if_direct) not in sys.path:
        sys.path.insert(0, str(project_root_if_direct))
        logger.info(f"Added {project_root_if_direct} to sys.path for direct execution.")

    # Setup basic logging for GUI startup issues
    log_dir = project_root_if_direct / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    gui_startup_log_file = log_dir / "lcas_gui_startup.log"

    logging.basicConfig(
        level=logging.DEBUG, # More verbose for startup
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(gui_startup_log_file),
            logging.StreamHandler(sys.stdout) # Also print to console
        ]
    )
    logger.info("Starting LCAS_2 GUI Application...")

    try:
        app = LCASMainGUI()
        # Pass the app instance to the GUILogHandler after app is created
        # This is a bit of a workaround for the handler needing a Tkinter root reference for `after_idle`
        for handler in logging.getLogger().handlers:
            if isinstance(handler, GUILogHandler):
                handler.gui_instance_ref_for_after = app
        app.mainloop()
    except Exception as e:
        logger.critical(f"Fatal error starting LCAS_2 GUI: {e}", exc_info=True)
        # Fallback message box if CustomTkinter failed to initialize fully
        try:
            root_tk = tk.Tk()
            root_tk.withdraw() # Hide empty root window
            messagebox.showerror("LCAS_2 Startup Error", f"A critical error occurred:\n{e}\n\nCheck lcas_gui_startup.log for details.")
            root_tk.destroy()
        except Exception as tk_error:
            print(f"Could not show Tkinter error message: {tk_error}")

if __name__ == "__main__":
    main()

'''

# Overwrite the LCAS_2/lcas2/gui/main_gui.py file
echo "${gui_content}" > LCAS_2/lcas2/gui/main_gui.py

echo "LCAS_2/lcas2/gui/main_gui.py has been updated with the new consolidated structure."

# Verify by printing some key class/method names
echo "--- Key elements in new main_gui.py ---"
grep -E "class LCASMainGUI\(ctk.CTk\)|class CaseTheorySetupDialog|class AIIntegrationPanel|def _initialize_core_async|def _start_full_analysis" LCAS_2/lcas2/gui/main_gui.py
echo "--- End of check ---"
