#!/usr/bin/env python3
"""
LCAS Modular GUI - Plugin-Based Interface
Main GUI application that dynamically loads and integrates plugins
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import asyncio
import threading
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys
import os

# Import the core application
from lcas_core import LCASCore, LCASConfig, UIPlugin, AnalysisPlugin, ExportPlugin


class LCASMainGUI:
    """Main GUI for the modular LCAS application"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("LCAS v4.0 - Modular Legal Evidence Analysis")
        self.root.geometry("1400x900")

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
        self.plugins_dir_var = tk.StringVar(value="plugins")
        self.debug_mode_var = tk.BooleanVar(value=False)

    def setup_gui(self):
        """Setup the main GUI interface"""
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

        # Analysis tab (will be populated by plugins)
        self.setup_analysis_tab()

        # Results tab
        self.setup_results_tab()

    def setup_dashboard_tab(self):
        """Setup dashboard tab"""
        dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(dashboard_frame, text="📊 Dashboard")

        # Title
        title_label = ttk.Label(dashboard_frame, text="LCAS v4.0 - Modular Legal Evidence Analysis",
                                font=('Arial', 16, 'bold'))
        title_label.pack(pady=20)

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

        # Case configuration
        case_frame = ttk.LabelFrame(config_frame, text="Case Configuration")
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

        self.plugins_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Plugin actions
        plugin_actions = ttk.Frame(plugin_frame)
        plugin_actions.pack(fill=tk.X, padx=20, pady=10)

        ttk.Button(plugin_actions, text="🔄 Refresh Plugins",
                   command=self.refresh_plugins).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(plugin_actions, text="✅ Enable Selected",
                   command=self.enable_selected_plugin).pack(side=tk.LEFT, padx=5, pady=5)

    def setup_analysis_tab(self):
        """Setup analysis tab - will be populated by plugins"""
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
            progress_frame, height=10)
        self.analysis_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def setup_results_tab(self):
        """Setup results tab"""
        results_frame = ttk.Frame(self.notebook)
        self.notebook.add(results_frame, text="📊 Results")

        # Results tree
        self.results_tree = ttk.Treeview(results_frame, columns=(
            'Plugin', 'Status', 'Score'), show='tree headings')
        self.results_tree.heading('#0', text='Result Item')
        self.results_tree.heading('Plugin', text='Plugin')
        self.results_tree.heading('Status', text='Status')
        self.results_tree.heading('Score', text='Score')
        self.results_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

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
                debug_mode=self.debug_mode_var.get()
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
        self.root.after(0, self._update_core_status, "Core: Ready", "green")
        self.root.after(0, self.refresh_plugins)

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
        self.results_tree.insert('', tk.END, text=f"{plugin_name} Result",
                                 values=(plugin_name, "Completed", "N/A"))

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
            text=f"Plugins: {loaded_count}/{total_count} loaded",
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

    # Utility Methods
    def log_message(self, message):
        """Log message to analysis log"""
        timestamp = tk._default_root.tk.call('clock', 'format',
                                             tk._default_root.tk.call(
                                                 'clock', 'seconds'),
                                             '-format', '%H:%M:%S')
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
    """Main entry point"""
    app = LCASMainGUI()
    app.run()


if __name__ == "__main__":
    main()
