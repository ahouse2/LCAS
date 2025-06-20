#!/usr/bin/env python3
"""
LCAS GUI Module
Modern graphical interface for the Legal Case Analysis System
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from ttkthemes import ThemedTk
import asyncio
import threading
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys
import os
import json
from datetime import datetime

from .core import LCASCore, LCASConfig, UIPlugin, AnalysisPlugin, ExportPlugin


class LCASMainGUI:
    """Main GUI for the LCAS application"""

    def __init__(self):
        self.root = ThemedTk(theme="equilux")
        self.root.title("LCAS v4.0 - Legal Case Analysis System")
        self.root.geometry("1400x900")
        self.root.minsize(1000, 600)

        # Core application instance
        self.core: Optional[LCASCore] = None
        self.core_thread: Optional[threading.Thread] = None
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None

        # GUI State
        self.plugin_frames: Dict[str, ttk.Frame] = {}
        self.plugin_ui_elements: Dict[str, List[tk.Widget]] = {}

        # Configuration variables
        self.setup_config_vars()

        # Setup GUI
        self.setup_gui()

        # Initialize core application
        self.initialize_core()

    def setup_config_vars(self):
        """Setup configuration variables"""
        self.case_name_var = tk.StringVar()
        self.source_dir_var = tk.StringVar()
        self.target_dir_var = tk.StringVar()

        # Existing vars from LCASConfig that were in LCASMainGUI
        self.plugins_dir_var = tk.StringVar(
            value="plugins")  # Matches LCASConfig default
        self.debug_mode_var = tk.BooleanVar(
            value=False)    # Matches LCASConfig default

        # New vars from LCASConfig
        self.log_level_var = tk.StringVar(
            value="INFO")    # Matches LCASConfig default

        self.min_probative_score_var = tk.DoubleVar(
            value=0.3)  # Matches LCASConfig default
        self.min_relevance_score_var = tk.DoubleVar(
            value=0.5)  # Matches LCASConfig default
        self.similarity_threshold_var = tk.DoubleVar(
            value=0.85)  # Matches LCASConfig default

        self.probative_weight_var = tk.DoubleVar(
            value=0.4)    # Matches LCASConfig default
        self.relevance_weight_var = tk.DoubleVar(
            value=0.3)    # Matches LCASConfig default
        self.admissibility_weight_var = tk.DoubleVar(
            value=0.3)  # Matches LCASConfig default

        self.enable_deduplication_var = tk.BooleanVar(
            value=True)  # Matches LCASConfig default
        self.enable_advanced_nlp_var = tk.BooleanVar(
            value=True)  # Matches LCASConfig default
        self.generate_visualizations_var = tk.BooleanVar(
            value=True)  # Matches LCASConfig default
        self.max_concurrent_files_var = tk.IntVar(
            value=5)  # Matches LCASConfig default

    def setup_gui(self):
        """Setup the main GUI interface"""
        # Configure style
        style = ttk.Style()
        # style.theme_use('clam') # Theme now set by ThemedTk

        # Main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Core tabs
        self.setup_core_tabs()

        # Status bar
        self.status_var = tk.StringVar(
            value="LCAS v4.0 Ready - Initializing Core...")
        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def setup_core_tabs(self):
        """Setup core application tabs"""
        # Dashboard tab
        self.setup_dashboard_tab()

        # Configuration tab
        self.setup_configuration_tab()

        # Plugin Management tab
        self.setup_plugin_management_tab()

        # Analysis tab
        self.setup_analysis_tab()

        # Results tab
        self.setup_results_tab()

        # Plugin UI tab
        self.setup_plugin_ui_tab()

    def setup_dashboard_tab(self):
        """Setup dashboard tab"""
        dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(dashboard_frame, text="📊 Dashboard")

        # Title
        title_label = ttk.Label(dashboard_frame, text="LCAS v4.0 - Legal Case Analysis System",
                                font=('Arial', 16, 'bold'))
        title_label.pack(pady=20)

        # Description
        desc_text = """
        Welcome to the Legal Case Analysis System (LCAS) v4.0

        A comprehensive tool for organizing, analyzing, and presenting legal evidence.
        Built with a modular plugin architecture for maximum flexibility and extensibility.

        Key Features:
        • Intelligent evidence organization
        • AI-powered document analysis
        • Comprehensive reporting
        • File integrity verification
        • Timeline analysis
        • Pattern discovery
        """

        desc_label = ttk.Label(
            dashboard_frame,
            text=desc_text,
            justify=tk.LEFT)
        desc_label.pack(pady=10, padx=20)

        # System status
        status_frame = ttk.LabelFrame(dashboard_frame, text="System Status")
        status_frame.pack(fill=tk.X, padx=20, pady=10)

        self.core_status_label = ttk.Label(
            status_frame,
            text="Core: Initializing...",
            foreground="orange")
        self.core_status_label.pack(anchor=tk.W, padx=10, pady=5)

        self.plugins_status_label = ttk.Label(
            status_frame, text="Plugins: Loading...", foreground="orange")
        self.plugins_status_label.pack(anchor=tk.W, padx=10, pady=5)

        # Quick actions
        actions_frame = ttk.LabelFrame(dashboard_frame, text="Quick Actions")
        actions_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Button(actions_frame, text="🔄 Refresh System",
                   command=self.refresh_system).pack(side=tk.LEFT, padx=10, pady=10)
        ttk.Button(actions_frame, text="📁 Open Case Folder",
                   command=self.open_case_folder).pack(side=tk.LEFT, padx=10, pady=10)
        ttk.Button(actions_frame, text="🚀 Start Analysis",
                   command=self.start_analysis).pack(side=tk.LEFT, padx=10, pady=10)

    def setup_configuration_tab(self):
        """Setup configuration tab"""
        config_frame = ttk.Frame(self.notebook)
        self.notebook.add(config_frame, text="⚙️ Configuration")

        # Scrollable frame
        canvas = tk.Canvas(config_frame)
        scrollbar = ttk.Scrollbar(
            config_frame,
            orient="vertical",
            command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Case configuration
        case_frame = ttk.LabelFrame(
            scrollable_frame, text="Case Configuration")
        case_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(
            case_frame,
            text="Case Name:").grid(
            row=0,
            column=0,
            sticky=tk.W,
            padx=10,
            pady=5)
        ttk.Entry(
            case_frame,
            textvariable=self.case_name_var,
            width=50).grid(
            row=0,
            column=1,
            padx=10,
            pady=5)

        ttk.Label(
            case_frame,
            text="Source Directory:").grid(
            row=1,
            column=0,
            sticky=tk.W,
            padx=10,
            pady=5)
        ttk.Entry(
            case_frame,
            textvariable=self.source_dir_var,
            width=50).grid(
            row=1,
            column=1,
            padx=10,
            pady=5)
        ttk.Button(case_frame, text="Browse",
                   command=lambda: self.browse_directory(self.source_dir_var)).grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(
            case_frame,
            text="Target Directory:").grid(
            row=2,
            column=0,
            sticky=tk.W,
            padx=10,
            pady=5)
        ttk.Entry(
            case_frame,
            textvariable=self.target_dir_var,
            width=50).grid(
            row=2,
            column=1,
            padx=10,
            pady=5)
        ttk.Button(case_frame, text="Browse",
                   command=lambda: self.browse_directory(self.target_dir_var)).grid(row=2, column=2, padx=5, pady=5)

        # Save configuration button (moved to the end of the tab)
        # ttk.Button(case_frame, text="💾 Save Configuration",
        # command=self.save_configuration).grid(row=3, column=0, columnspan=3,
        # pady=10)

        # Logging & Debugging Frame
        log_debug_frame = ttk.LabelFrame(
            scrollable_frame, text="Logging & Debugging")
        log_debug_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(
            log_debug_frame,
            text="Log Level:").grid(
            row=0,
            column=0,
            sticky=tk.W,
            padx=10,
            pady=5)
        ttk.Combobox(log_debug_frame, textvariable=self.log_level_var,
                     values=["DEBUG", "INFO", "WARNING", "ERROR"], width=47).grid(row=0, column=1, padx=10, pady=5)

        ttk.Checkbutton(log_debug_frame, text="Debug Mode",
                        variable=self.debug_mode_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=10, pady=5)

      main

        ttk.Label(
            log_debug_frame,
            text="Plugins Directory:").grid(
            row=2,
            column=0,
            sticky=tk.W,
            padx=10,
            pady=5)
        ttk.Entry(
            log_debug_frame,
            textvariable=self.plugins_dir_var,
            width=50).grid(
            row=2,
            column=1,
            padx=10,
            pady=5)

        # Analysis Parameters Frame
        analysis_params_frame = ttk.LabelFrame(
            scrollable_frame, text="Analysis Parameters")
        analysis_params_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(
            analysis_params_frame,
            text="Min Probative Score:").grid(
            row=0,
            column=0,
            sticky=tk.W,
            padx=10,
            pady=5)
        ttk.Entry(
            analysis_params_frame,
            textvariable=self.min_probative_score_var,
            width=10).grid(
            row=0,
            column=1,
            padx=10,
            pady=5)

        ttk.Label(
            analysis_params_frame,
            text="Min Relevance Score:").grid(
            row=1,
            column=0,
            sticky=tk.W,
            padx=10,
            pady=5)
        ttk.Entry(
            analysis_params_frame,
            textvariable=self.min_relevance_score_var,
            width=10).grid(
            row=1,
            column=1,
            padx=10,
            pady=5)

        ttk.Label(
            analysis_params_frame,
            text="Similarity Threshold:").grid(
            row=2,
            column=0,
            sticky=tk.W,
            padx=10,
            pady=5)
        ttk.Entry(
            analysis_params_frame,
            textvariable=self.similarity_threshold_var,
            width=10).grid(
            row=2,
            column=1,
            padx=10,
            pady=5)

        ttk.Label(
            analysis_params_frame,
            text="Probative Weight:").grid(
            row=0,
            column=2,
            sticky=tk.W,
            padx=10,
            pady=5)
        ttk.Entry(
            analysis_params_frame,
            textvariable=self.probative_weight_var,
            width=10).grid(
            row=0,
            column=3,
            padx=10,
            pady=5)

        ttk.Label(
            analysis_params_frame,
            text="Relevance Weight:").grid(
            row=1,
            column=2,
            sticky=tk.W,
            padx=10,
            pady=5)
        ttk.Entry(
            analysis_params_frame,
            textvariable=self.relevance_weight_var,
            width=10).grid(
            row=1,
            column=3,
            padx=10,
            pady=5)

        ttk.Label(
            analysis_params_frame,
            text="Admissibility Weight:").grid(
            row=2,
            column=2,
            sticky=tk.W,
            padx=10,
            pady=5)
        ttk.Entry(
            analysis_params_frame,
            textvariable=self.admissibility_weight_var,
            width=10).grid(
            row=2,
            column=3,
            padx=10,
            pady=5)
        
        main
        
        # Processing Options Frame
        proc_options_frame = ttk.LabelFrame(
            scrollable_frame, text="Processing Options")
        proc_options_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Checkbutton(proc_options_frame, text="Enable Deduplication",
                        variable=self.enable_deduplication_var).grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        ttk.Checkbutton(proc_options_frame, text="Enable Advanced NLP",
                        variable=self.enable_advanced_nlp_var).grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)
        ttk.Checkbutton(proc_options_frame, text="Generate Visualizations",
                        variable=self.generate_visualizations_var).grid(row=0, column=2, sticky=tk.W, padx=10, pady=5)

        ttk.Label(
            proc_options_frame,
            text="Max Concurrent Files:").grid(
            row=1,
            column=0,
            sticky=tk.W,
            padx=10,
            pady=5)
        ttk.Entry(
            proc_options_frame,
            textvariable=self.max_concurrent_files_var,
            width=10).grid(
            row=1,
            column=1,
            padx=10,
            pady=5)

        # Save Configuration Button (centralized at the bottom of the tab)
        # Use main scrollable_frame
        save_button_frame = ttk.Frame(scrollable_frame)
        save_button_frame.pack(fill=tk.X, padx=20, pady=15)
        ttk.Button(save_button_frame, text="💾 Save All Configurations",
                   command=self.save_configuration).pack()

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def setup_plugin_management_tab(self):
        """Setup plugin management tab"""
        plugin_frame = ttk.Frame(self.notebook)
        self.notebook.add(plugin_frame, text="🔌 Plugin Manager")

        # Available plugins
        available_frame = ttk.LabelFrame(
            plugin_frame, text="Available Plugins")
        available_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Create treeview for plugins
        columns = ('Status', 'Version', 'Description')
        self.plugins_tree = ttk.Treeview(
            available_frame, columns=columns, show='tree headings')
        self.plugins_tree.heading('#0', text='Plugin Name')
        self.plugins_tree.heading('Status', text='Status')
        self.plugins_tree.heading('Version', text='Version')
        self.plugins_tree.heading('Description', text='Description')

        # Scrollbar for treeview
        plugins_scrollbar = ttk.Scrollbar(
            available_frame,
            orient=tk.VERTICAL,
            command=self.plugins_tree.yview)
        self.plugins_tree.configure(yscrollcommand=plugins_scrollbar.set)

        self.plugins_tree.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True,
            padx=10,
            pady=10)
        plugins_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)

        # Plugin actions
        plugin_actions = ttk.Frame(plugin_frame)
        plugin_actions.pack(fill=tk.X, padx=20, pady=10)

        ttk.Button(plugin_actions, text="🔄 Refresh Plugins",
                   command=self.refresh_plugins).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(plugin_actions, text="✅ Enable Selected",
                   command=self.enable_selected_plugin).pack(side=tk.LEFT, padx=5, pady=5)

    def setup_analysis_tab(self):
        """Setup analysis tab"""
        self.analysis_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analysis_frame, text="🔬 Analysis")

        # Analysis progress
        progress_frame = ttk.LabelFrame(
            self.analysis_frame, text="Analysis Progress")
        progress_frame.pack(fill=tk.X, padx=20, pady=10)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=10, pady=5)

        self.analysis_log = scrolledtext.ScrolledText(
            progress_frame, height=15)
        self.analysis_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Analysis controls
        controls_frame = ttk.Frame(self.analysis_frame)
        controls_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Button(controls_frame, text="▶️ Start Analysis",
                   command=self.start_analysis).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="⏹️ Stop Analysis",
                   command=self.stop_analysis).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="🗑️ Clear Log",
                   command=self.clear_analysis_log).pack(side=tk.LEFT, padx=5)

    def setup_results_tab(self):
        """Setup results tab"""
        results_frame = ttk.Frame(self.notebook)
        self.notebook.add(results_frame, text="📊 Results")

        # Results tree
        results_tree_frame = ttk.LabelFrame(
            results_frame, text="Analysis Results")
        results_tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        columns = ('Plugin', 'Status', 'Timestamp')
        self.results_tree = ttk.Treeview(
            results_tree_frame,
            columns=columns,
            show='tree headings')
        self.results_tree.heading('#0', text='Result Item')
        self.results_tree.heading('Plugin', text='Plugin')
        self.results_tree.heading('Status', text='Status')
        self.results_tree.heading('Timestamp', text='Timestamp')

        results_scrollbar = ttk.Scrollbar(
            results_tree_frame,
            orient=tk.VERTICAL,
            command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=results_scrollbar.set)

        self.results_tree.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True,
            padx=10,
            pady=10)
        results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)

        # Results actions
        results_actions = ttk.Frame(results_frame)
        results_actions.pack(fill=tk.X, padx=20, pady=10)

        ttk.Button(results_actions, text="📄 Generate Report",
                   command=self.generate_report).pack(side=tk.LEFT, padx=5)
        ttk.Button(results_actions, text="📁 Open Results Folder",
                   command=self.open_results_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(results_actions, text="💾 Export Results",
                   command=self.export_results).pack(side=tk.LEFT, padx=5)

    def setup_plugin_ui_tab(self):
        """Setup the tab for UI elements contributed by plugins."""
        self.plugin_ui_host_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.plugin_ui_host_frame, text="🧩 Plugin Features")

        # Optional: Add a placeholder label if no plugins contribute UI initially
        # placeholder_label = ttk.Label(self.plugin_ui_host_frame, text="UI elements from UI plugins appear here.")
        # placeholder_label.pack(padx=10, pady=10)
        # self.log_message("Plugin UI tab created.") # Log to internal GUI log
        # if desired

    # Core Application Methods
    def initialize_core(self):
        """Initialize the core application in a separate thread"""
        def run_core():
            # Create new event loop for this thread
            self.event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.event_loop)

            # Create core configuration
            config = LCASConfig(
                case_name=self.case_name_var.get(),
                source_directory=self.source_dir_var.get(),
                target_directory=self.target_dir_var.get(),
                plugins_directory=self.plugins_dir_var.get(),
                enabled_plugins=None,  # This will be set by LCASConfig's __post_init__ or loaded value
                debug_mode=self.debug_mode_var.get(),
                log_level=self.log_level_var.get(),
                min_probative_score=self.min_probative_score_var.get(),
                min_relevance_score=self.min_relevance_score_var.get(),
                similarity_threshold=self.similarity_threshold_var.get(),
                probative_weight=self.probative_weight_var.get(),
                relevance_weight=self.relevance_weight_var.get(),
                admissibility_weight=self.admissibility_weight_var.get(),
                enable_deduplication=self.enable_deduplication_var.get(),
                enable_advanced_nlp=self.enable_advanced_nlp_var.get(),
                generate_visualizations=self.generate_visualizations_var.get(),
                max_concurrent_files=self.max_concurrent_files_var.get()
            )

            # Create core instance
            self.core = LCASCore(config)

            # Subscribe to core events
            self.core.event_bus.subscribe(
                "core.initialized", self.on_core_initialized)
            self.core.event_bus.subscribe(
                "analysis.completed", self.on_analysis_completed)

            # Initialize core
            self.event_loop.run_until_complete(self.core.initialize())

            # Keep event loop running
            try:
                self.event_loop.run_forever()
            except Exception as e:
                self.log_message(f"Core event loop error: {e}")

        self.core_thread = threading.Thread(target=run_core, daemon=True)
        self.core_thread.start()

    def on_core_initialized(self, data):
        """Called when core is initialized"""
        self.root.after(0, self._update_core_status, "Core: Ready ✓", "green")
        self.root.after(0, self.refresh_plugins)  # This will load plugin info

        # Reflect loaded config (data is self.core.config) in UI
        if self.core and data:
            self.case_name_var.set(data.case_name)
            self.source_dir_var.set(data.source_directory)
            self.target_dir_var.set(data.target_directory)
            self.plugins_dir_var.set(data.plugins_directory)
            self.debug_mode_var.set(data.debug_mode)
            self.log_level_var.set(data.log_level)
            self.min_probative_score_var.set(data.min_probative_score)
            self.min_relevance_score_var.set(data.min_relevance_score)
            self.similarity_threshold_var.set(data.similarity_threshold)
            self.probative_weight_var.set(data.probative_weight)
            self.relevance_weight_var.set(data.relevance_weight)
            self.admissibility_weight_var.set(data.admissibility_weight)
            self.enable_deduplication_var.set(data.enable_deduplication)
            self.enable_advanced_nlp_var.set(data.enable_advanced_nlp)
            self.generate_visualizations_var.set(data.generate_visualizations)
            self.max_concurrent_files_var.set(data.max_concurrent_files)
            # Note: enabled_plugins is managed by PluginManager UI, not a
            # simple var here.

        # Load UI from UIPlugins
        if self.core and self.plugin_ui_host_frame:
            ui_plugins = self.core.get_ui_plugins()
            if ui_plugins:
                self.log_message(
                    f"Found {
                        len(ui_plugins)} UI plugins. Loading their UIs...")
                for ui_plugin in ui_plugins:
                    try:
                        self.log_message(
                            f"Loading UI for plugin: {
                                ui_plugin.name}")
                        widgets = ui_plugin.create_ui_elements(
                            self.plugin_ui_host_frame)
                        if widgets:  # Store a reference if needed, or just let them be managed by parent
                            self.plugin_ui_elements[ui_plugin.name] = widgets
                            self.log_message(
                                f"Successfully loaded UI for {
                                    ui_plugin.name}")
                        else:
                            self.log_message(
                                f"Plugin {
                                    ui_plugin.name} provided no UI elements.")
                    except Exception as e:
                        self.log_message(
                            f"Error loading UI for plugin {
                                ui_plugin.name}: {e}")
            else:
                self.log_message("No UI plugins found or active.")

    def on_analysis_completed(self, data):
        """Called when analysis is completed"""
        plugin_name = data.get("plugin", "Unknown")
        result = data.get("result")
        self.root.after(0, self._add_analysis_result, plugin_name, result)

    def _update_core_status(self, text, color):
        """Update core status label"""
        self.core_status_label.config(text=text, foreground=color)

    def _add_analysis_result(self, plugin_name, result):
        """Add analysis result to results tree"""
        status = result.get(
            "status", "Unknown") if isinstance(
            result, dict) else "Completed"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.results_tree.insert('', tk.END, text=f"{plugin_name} Result",
                                 values=(plugin_name, status, timestamp))

    # Plugin Management Methods
    def refresh_plugins(self):
        """Refresh the plugins list"""
        if not self.core:
            self.log_message("Core not initialized yet")
            return

        # Run in core thread
        if self.event_loop:
            asyncio.run_coroutine_threadsafe(
                self._refresh_plugins_async(), self.event_loop)

    async def _refresh_plugins_async(self):
        """Async plugin refresh"""
        # Discover plugins
        available_plugins = self.core.plugin_manager.discover_plugins()

        # Update UI in main thread
        self.root.after(0, self._update_plugins_tree, available_plugins)

    def _update_plugins_tree(self, plugins):
        """Update the plugins tree view"""
        # Clear existing items
        for item in self.plugins_tree.get_children():
            self.plugins_tree.delete(item)

        # Add plugins
        for plugin_name in plugins:
            status = "Loaded" if plugin_name in self.core.plugin_manager.loaded_plugins else "Available"

            if plugin_name in self.core.plugin_manager.loaded_plugins:
                plugin = self.core.plugin_manager.loaded_plugins[plugin_name]
                version = plugin.version
                description = plugin.description
            else:
                version = "Unknown"
                description = "Not loaded"

            self.plugins_tree.insert('', tk.END, text=plugin_name,
                                     values=(status, version, description))

        # Update status
        loaded_count = len(self.core.plugin_manager.loaded_plugins)
        total_count = len(plugins)
        self.plugins_status_label.config(
            text=f"Plugins: {loaded_count}/{total_count} loaded ✓",
            foreground="green" if loaded_count > 0 else "orange"
        )

    def enable_selected_plugin(self):
        """Enable selected plugin"""
        selection = self.plugins_tree.selection()
        if not selection:
            messagebox.showwarning(
                "No Selection",
                "Please select a plugin to enable")
            return

        plugin_name = self.plugins_tree.item(selection[0])['text']

        if self.event_loop:
            asyncio.run_coroutine_threadsafe(
                self.core.plugin_manager.load_plugin(plugin_name, self.core),
                self.event_loop
            )

        self.root.after(1000, self.refresh_plugins)  # Refresh after delay

    # Analysis Methods
    def start_analysis(self):
        """Start analysis using loaded plugins"""
        if not self.core:
            messagebox.showerror("Error", "Core not initialized")
            return

        if not self.source_dir_var.get() or not self.target_dir_var.get():
            messagebox.showerror(
                "Error", "Please configure source and target directories")
            return

        self.log_message("Starting analysis...")

        # Run analysis in core thread
        if self.event_loop:
            asyncio.run_coroutine_threadsafe(
                self._run_analysis_async(), self.event_loop)

    async def _run_analysis_async(self):
        """Run analysis asynchronously"""
        try:
            analysis_plugins = self.core.get_analysis_plugins()

            if not analysis_plugins:
                self.root.after(
                    0, self.log_message, "No analysis plugins loaded")
                return

            total_plugins = len(analysis_plugins)

            for i, plugin in enumerate(analysis_plugins):
                self.root.after(
                    0, self.log_message, f"Running {
                        plugin.name}...")
                self.root.after(0, self.update_progress,
                                (i / total_plugins) * 100)

                try:
                    # Run plugin analysis
                    result = await plugin.analyze({
                        "source_directory": self.core.config.source_directory,
                        "target_directory": self.core.config.target_directory,
                        "case_name": self.core.config.case_name
                    })

                    # Store result
                    self.core.set_analysis_result(plugin.name, result)

                except Exception as e:
                    self.root.after(
                        0, self.log_message, f"Error in {
                            plugin.name}: {e}")

            self.root.after(0, self.update_progress, 100)
            self.root.after(0, self.log_message, "Analysis complete!")

        except Exception as e:
            self.root.after(0, self.log_message, f"Analysis failed: {e}")

    def stop_analysis(self):
        """Stop current analysis"""
        self.log_message("Analysis stop requested")
        # Implementation would depend on how analysis is structured

    def clear_analysis_log(self):
        """Clear the analysis log"""
        self.analysis_log.delete(1.0, tk.END)

    # Utility Methods
    def log_message(self, message):
        """Log message to analysis log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        self.analysis_log.insert(tk.END, formatted_message)
        self.analysis_log.see(tk.END)

    def update_progress(self, value):
        """Update progress bar"""
        self.progress_var.set(value)

    def browse_directory(self, var):
        """Browse for directory"""
        directory = filedialog.askdirectory()
        if directory:
            var.set(directory)

    def save_configuration(self):
        """Save current configuration"""
        if self.core:
          
            self.core.config.log_level = self.log_level_var.get()

            self.core.config.min_probative_score = self.min_probative_score_var.get()
            self.core.config.min_relevance_score = self.min_relevance_score_var.get()
            self.core.config.similarity_threshold = self.similarity_threshold_var.get()

            self.core.config.probative_weight = self.probative_weight_var.get()
            self.core.config.relevance_weight = self.relevance_weight_var.get()
            self.core.config.admissibility_weight = self.admissibility_weight_var.get()

            self.core.config.enable_deduplication = self.enable_deduplication_var.get()
            self.core.config.enable_advanced_nlp = self.enable_advanced_nlp_var.get()
            self.core.config.generate_visualizations = self.generate_visualizations_var.get()
            self.core.config.max_concurrent_files = self.max_concurrent_files_var.get()

            if self.core.save_config():
              
                messagebox.showinfo(
                    "Success", "Configuration saved successfully!")
            else:
                messagebox.showerror("Error", "Failed to save configuration")

    def refresh_system(self):
        """Refresh entire system"""
        self.refresh_plugins()
        self.status_var.set("System refreshed")

    def open_case_folder(self):
        """Open case folder in file explorer"""
        target_dir = self.target_dir_var.get()
        if target_dir and os.path.exists(target_dir):
            if sys.platform == "win32":
                os.startfile(target_dir)
            elif sys.platform == "darwin":
                os.system(f"open '{target_dir}'")
            else:
                os.system(f"xdg-open '{target_dir}'")
        else:
            messagebox.showwarning(
                "Warning", "Target directory not set or doesn't exist")

    def generate_report(self):
        """Generate analysis report using the first available export plugin."""
        if not self.core:
            messagebox.showerror("Error", "Core not initialized.")
            return

        if not self.core.event_loop:
            messagebox.showerror("Error", "Core event loop not available.")
            return

        export_plugins = self.core.get_export_plugins()
        if not export_plugins:
            messagebox.showinfo(
                "No Report Plugins",
                "No report generation plugins are active.")
            return

        report_plugin = export_plugins[0]
        self.log_message(f"Using report plugin: {report_plugin.name}")

        output_filepath = filedialog.asksaveasfilename(
            title="Save Report As",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"),
                       ("Markdown files", "*.md"),
                       ("PDF files", "*.pdf"),
                       ("All files", "*.*")]
        )

        if not output_filepath:
            return  # User cancelled

        report_data = self.core.analysis_results
        if not report_data:
            messagebox.showinfo(
                "No Data", "No analysis results available to generate a report.")
            return

        try:
            self.log_message(
                f"Starting report generation by {
                    report_plugin.name} to {output_filepath}...")
            # Run the export method in the core's event loop
            future = asyncio.run_coroutine_threadsafe(
                report_plugin.export(report_data, output_filepath),
                self.event_loop
            )

            # For now, we just inform the user. A more robust solution would
            # use callbacks or check future.result()
            messagebox.showinfo("Report Generation",
                                f"Report generation started by {
                                    report_plugin.name}.\n"
                                f"Output will be saved to: {output_filepath}\n"
                                "Check logs for status and completion.")
            # Example of how one might handle the result if the export function is quick or if blocking is acceptable:
            # try:
            #     success = future.result(timeout=30) # Timeout after 30 seconds
            #     if success:
            #         messagebox.showinfo("Report Complete", f"Report successfully generated by {report_plugin.name} to {output_filepath}")
            #     else:
            #         messagebox.showerror("Report Failed", f"Report generation by {report_plugin.name} failed. Check logs.")
            # except concurrent.futures.TimeoutError:
            #     messagebox.showinfo("Report In Progress", f"Report generation by {report_plugin.name} is taking longer than expected. Check logs for completion.")
            # except Exception as e:
            #     messagebox.showerror("Report Error", f"Error during report generation by {report_plugin.name}: {e}")

        except Exception as e:
            self.log_message(f"Error initiating report generation: {e}")
            messagebox.showerror("Report Error",
                                 f"Failed to start report generation: {e}")

    def open_results_folder(self):
        """Open results folder"""
        self.open_case_folder()

    def export_results(self):
        """Export analysis results to a JSON file."""
        if not self.core or not hasattr(self.core, 'analysis_results'):
            messagebox.showwarning(
                "No Data",
                "Core is not initialized or no analysis results available to export.")
            return

        if not self.core.analysis_results:
            messagebox.showinfo("No Results",
                                "There are no analysis results to export.")
            return

        output_filepath = filedialog.asksaveasfilename(
            title="Export Analysis Results As",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if not output_filepath:
            return  # User cancelled

        try:
            with open(output_filepath, 'w', encoding='utf-8') as f:
                json.dump(self.core.analysis_results, f,
                          indent=2, ensure_ascii=False)
            messagebox.showinfo(
                "Export Successful",
                f"Analysis results exported successfully to:\n{output_filepath}")
            self.log_message(f"Results exported to {output_filepath}")
        except Exception as e:
            self.log_message(f"Error exporting results: {e}")
            messagebox.showerror(
                "Export Error",
                f"Failed to export results: {e}")

    def on_closing(self):
        """Handle application closing"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            # Shutdown core
            if self.core and self.event_loop:
                asyncio.run_coroutine_threadsafe(
                    self.core.shutdown(), self.event_loop)

            self.root.destroy()

    def run(self):
        """Start the GUI application"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()


def main():
    """Main entry point for GUI"""
    app = LCASMainGUI()
    app.run()


if __name__ == "__main__":
    main()
