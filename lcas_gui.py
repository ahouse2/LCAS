#!/usr/bin/env python3
"""
LCAS GUI Application - Legal Case Analysis System with AI Integration
Modern, sleek, dark theme GUI for legal evidence analysis
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
import json
import os
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

# Configure CustomTkinter appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('lcas_gui.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

@dataclass
class AIConfig:
    """AI Configuration settings"""
    provider: str = "openai"  # openai, anthropic, local
    api_key: str = ""
    model: str = "gpt-4"
    base_url: str = ""  # For OpenAI-compatible APIs
    temperature: float = 0.1
    max_tokens: int = 4000
    enabled: bool = False

@dataclass
class LCASGUIConfig:
    """GUI Configuration settings"""
    source_directory: str = ""
    target_directory: str = ""
    
    # Analysis settings
    min_probative_score: float = 0.3
    min_relevance_score: float = 0.5
    similarity_threshold: float = 0.85
    
    # Scoring weights
    probative_weight: float = 0.4
    relevance_weight: float = 0.3
    admissibility_weight: float = 0.3
    
    # AI configuration
    ai_config: AIConfig = None
    
    # Processing options
    enable_deduplication: bool = True
    enable_neo4j: bool = False
    enable_advanced_nlp: bool = True
    generate_visualizations: bool = True
    
    def __post_init__(self):
        if self.ai_config is None:
            self.ai_config = AIConfig()

class LCASProgressDialog(ctk.CTkToplevel):
    """Progress dialog for long-running operations"""
    
    def __init__(self, parent, title="Processing..."):
        super().__init__(parent)
        self.title(title)
        self.geometry("400x200")
        self.transient(parent)
        self.grab_set()
        
        # Center on parent
        self.center_on_parent(parent)
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Progress label
        self.progress_label = ctk.CTkLabel(
            main_frame, 
            text="Initializing...",
            font=ctk.CTkFont(size=14)
        )
        self.progress_label.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(main_frame)
        self.progress_bar.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.progress_bar.set(0)
        
        # Details text
        self.details_text = ctk.CTkTextbox(main_frame, height=80)
        self.details_text.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        # Cancel button
        self.cancel_button = ctk.CTkButton(
            main_frame,
            text="Cancel",
            command=self.cancel_operation
        )
        self.cancel_button.grid(row=3, column=0, padx=20, pady=10)
        
        self.cancelled = False
    
    def center_on_parent(self, parent):
        """Center dialog on parent window"""
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def update_progress(self, progress: float, text: str, details: str = ""):
        """Update progress dialog"""
        self.progress_bar.set(progress)
        self.progress_label.configure(text=text)
        if details:
            self.details_text.insert("end", details + "\n")
            self.details_text.see("end")
        self.update()
    
    def cancel_operation(self):
        """Cancel the current operation"""
        self.cancelled = True
        self.destroy()

class AIIntegrationPanel(ctk.CTkFrame):
    """AI Integration configuration panel"""
    
    def __init__(self, parent, config: LCASGUIConfig):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the AI integration UI"""
        # Title
        title = ctk.CTkLabel(
            self, 
            text="🤖 AI Integration",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title.grid(row=0, column=0, columnspan=2, padx=20, pady=10, sticky="w")
        
        # Enable AI toggle
        self.ai_enabled_var = tk.BooleanVar(value=self.config.ai_config.enabled)
        ai_toggle = ctk.CTkSwitch(
            self,
            text="Enable AI Analysis",
            variable=self.ai_enabled_var,
            command=self.toggle_ai_options
        )
        ai_toggle.grid(row=1, column=0, columnspan=2, padx=20, pady=5, sticky="w")
        
        # AI Provider selection
        ctk.CTkLabel(self, text="AI Provider:").grid(row=2, column=0, padx=20, pady=5, sticky="w")
        self.provider_var = tk.StringVar(value=self.config.ai_config.provider)
        provider_combo = ctk.CTkComboBox(
            self,
            values=["openai", "anthropic", "local", "custom"],
            variable=self.provider_var,
            command=self.on_provider_change
        )
        provider_combo.grid(row=2, column=1, padx=20, pady=5, sticky="ew")
        
        # API Key
        ctk.CTkLabel(self, text="API Key:").grid(row=3, column=0, padx=20, pady=5, sticky="w")
        self.api_key_entry = ctk.CTkEntry(self, show="*", placeholder_text="Enter API key...")
        self.api_key_entry.grid(row=3, column=1, padx=20, pady=5, sticky="ew")
        self.api_key_entry.insert(0, self.config.ai_config.api_key)
        
        # Model selection
        ctk.CTkLabel(self, text="Model:").grid(row=4, column=0, padx=20, pady=5, sticky="w")
        self.model_var = tk.StringVar(value=self.config.ai_config.model)
        self.model_entry = ctk.CTkEntry(self, textvariable=self.model_var)
        self.model_entry.grid(row=4, column=1, padx=20, pady=5, sticky="ew")
        
        # Base URL (for custom APIs)
        ctk.CTkLabel(self, text="Base URL:").grid(row=5, column=0, padx=20, pady=5, sticky="w")
        self.base_url_entry = ctk.CTkEntry(self, placeholder_text="https://api.openai.com/v1")
        self.base_url_entry.grid(row=5, column=1, padx=20, pady=5, sticky="ew")
        self.base_url_entry.insert(0, self.config.ai_config.base_url)
        
        # Temperature
        ctk.CTkLabel(self, text="Temperature:").grid(row=6, column=0, padx=20, pady=5, sticky="w")
        self.temperature_var = tk.DoubleVar(value=self.config.ai_config.temperature)
        temperature_slider = ctk.CTkSlider(
            self,
            from_=0.0,
            to=2.0,
            number_of_steps=20,
            variable=self.temperature_var
        )
        temperature_slider.grid(row=6, column=1, padx=20, pady=5, sticky="ew")
        
        # Test connection button
        self.test_button = ctk.CTkButton(
            self,
            text="Test Connection",
            command=self.test_ai_connection
        )
        self.test_button.grid(row=7, column=0, columnspan=2, padx=20, pady=10)
        
        # Configure column weights
        self.grid_columnconfigure(1, weight=1)
        
        # Initial state
        self.toggle_ai_options()
    
    def toggle_ai_options(self):
        """Enable/disable AI options based on toggle"""
        enabled = self.ai_enabled_var.get()
        
        # Enable/disable all AI-related widgets
        widgets = [
            self.api_key_entry, self.model_entry, self.base_url_entry, self.test_button
        ]
        
        for widget in widgets:
            widget.configure(state="normal" if enabled else "disabled")
    
    def on_provider_change(self, provider):
        """Handle provider change"""
        if provider == "openai":
            self.model_entry.delete(0, "end")
            self.model_entry.insert(0, "gpt-4")
            self.base_url_entry.delete(0, "end")
            self.base_url_entry.insert(0, "https://api.openai.com/v1")
        elif provider == "anthropic":
            self.model_entry.delete(0, "end")
            self.model_entry.insert(0, "claude-3-sonnet-20240229")
            self.base_url_entry.delete(0, "end")
            self.base_url_entry.insert(0, "https://api.anthropic.com")
    
    def test_ai_connection(self):
        """Test AI API connection"""
        # This would implement actual API testing
        messagebox.showinfo("Test Result", "AI connection test would be implemented here!")
    
    def get_ai_config(self) -> AIConfig:
        """Get current AI configuration"""
        return AIConfig(
            provider=self.provider_var.get(),
            api_key=self.api_key_entry.get(),
            model=self.model_var.get(),
            base_url=self.base_url_entry.get(),
            temperature=self.temperature_var.get(),
            enabled=self.ai_enabled_var.get()
        )

class LCASMainWindow(ctk.CTk):
    """Main LCAS GUI Application Window"""
    
    def __init__(self):
        super().__init__()
        
        # Window configuration
        self.title("Legal Case Analysis System (LCAS) v2.0")
        self.geometry("1200x800")
        self.minsize(800, 600)
        
        # Load configuration
        self.config = self.load_config()
        
        # Set up the UI
        self.setup_ui()
        
        # Set up event handlers
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def load_config(self) -> LCASGUIConfig:
        """Load configuration from file"""
        config_file = "lcas_gui_config.json"
        if Path(config_file).exists():
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    # Convert nested AI config
                    if 'ai_config' in data:
                        data['ai_config'] = AIConfig(**data['ai_config'])
                    return LCASGUIConfig(**data)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        
        return LCASGUIConfig()
    
    def save_config(self):
        """Save configuration to file"""
        config_file = "lcas_gui_config.json"
        try:
            # Convert dataclass to dict
            config_dict = {
                'source_directory': self.config.source_directory,
                'target_directory': self.config.target_directory,
                'min_probative_score': self.config.min_probative_score,
                'min_relevance_score': self.config.min_relevance_score,
                'similarity_threshold': self.config.similarity_threshold,
                'probative_weight': self.config.probative_weight,
                'relevance_weight': self.config.relevance_weight,
                'admissibility_weight': self.config.admissibility_weight,
                'enable_deduplication': self.config.enable_deduplication,
                'enable_neo4j': self.config.enable_neo4j,
                'enable_advanced_nlp': self.config.enable_advanced_nlp,
                'generate_visualizations': self.config.generate_visualizations,
                'ai_config': {
                    'provider': self.config.ai_config.provider,
                    'api_key': self.config.ai_config.api_key,
                    'model': self.config.ai_config.model,
                    'base_url': self.config.ai_config.base_url,
                    'temperature': self.config.ai_config.temperature,
                    'max_tokens': self.config.ai_config.max_tokens,
                    'enabled': self.config.ai_config.enabled
                }
            }
            
            with open(config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def setup_ui(self):
        """Set up the main user interface"""
        # Configure main grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Create sidebar
        self.create_sidebar()
        
        # Create main content area
        self.create_main_content()
        
        # Create status bar
        self.create_status_bar()
    
    def create_sidebar(self):
        """Create the sidebar with navigation"""
        sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        sidebar.grid_rowconfigure(8, weight=1)
        
        # Logo/Title
        logo_label = ctk.CTkLabel(
            sidebar, 
            text="⚖️ LCAS",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        subtitle = ctk.CTkLabel(
            sidebar,
            text="Legal Case Analysis System",
            font=ctk.CTkFont(size=12)
        )
        subtitle.grid(row=1, column=0, padx=20, pady=(0, 30))
        
        # Navigation buttons
        self.nav_buttons = {}
        nav_items = [
            ("🏠 Home", "home"),
            ("📁 File Setup", "files"),
            ("🤖 AI Config", "ai"),
            ("⚙️ Settings", "settings"),
            ("📊 Results", "results"),
            ("📈 Visualizations", "viz")
        ]
        
        for i, (text, key) in enumerate(nav_items):
            btn = ctk.CTkButton(
                sidebar,
                text=text,
                command=lambda k=key: self.show_panel(k),
                height=40,
                anchor="w"
            )
            btn.grid(row=i+2, column=0, padx=20, pady=5, sticky="ew")
            self.nav_buttons[key] = btn
        
        # Version info
        version_label = ctk.CTkLabel(
            sidebar,
            text="v2.0.0 Beta",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        version_label.grid(row=9, column=0, padx=20, pady=(10, 20))
    
    def create_main_content(self):
        """Create the main content area"""
        # Main content frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        # Create all panels
        self.panels = {}
        self.create_home_panel()
        self.create_file_setup_panel()
        self.create_ai_config_panel()
        self.create_settings_panel()
        self.create_results_panel()
        self.create_visualizations_panel()
        
        # Show home panel by default
        self.show_panel("home")
    
    def create_home_panel(self):
        """Create the home/dashboard panel"""
        panel = ctk.CTkFrame(self.main_frame)
        panel.grid_columnconfigure(0, weight=1)
        
        # Welcome message
        welcome_label = ctk.CTkLabel(
            panel,
            text="Welcome to LCAS",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        welcome_label.grid(row=0, column=0, padx=30, pady=(30, 10))
        
        description = ctk.CTkLabel(
            panel,
            text="Legal Case Analysis System with AI-Powered Evidence Organization",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        description.grid(row=1, column=0, padx=30, pady=(0, 30))
        
        # Quick start section
        quick_start_frame = ctk.CTkFrame(panel)
        quick_start_frame.grid(row=2, column=0, padx=30, pady=20, sticky="ew")
        quick_start_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            quick_start_frame,
            text="Quick Start",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=10)
        
        steps = [
            "1. Set up your source and target directories",
            "2. Configure AI integration (optional but recommended)",
            "3. Adjust analysis settings to your needs",
            "4. Run the analysis and review results"
        ]
        
        for i, step in enumerate(steps):
            ctk.CTkLabel(
                quick_start_frame,
                text=step,
                font=ctk.CTkFont(size=12),
                anchor="w"
            ).grid(row=i+1, column=0, padx=20, pady=5, sticky="ew")
        
        # Start button
        start_button = ctk.CTkButton(
            panel,
            text="🚀 Start Analysis",
            command=self.start_analysis,
            height=50,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        start_button.grid(row=3, column=0, padx=30, pady=30)
        
        self.panels["home"] = panel
    
    def create_file_setup_panel(self):
        """Create the file setup panel"""
        panel = ctk.CTkScrollableFrame(self.main_frame)
        panel.grid_columnconfigure(1, weight=1)
        
        # Title
        title = ctk.CTkLabel(
            panel,
            text="📁 File Setup",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, columnspan=2, padx=20, pady=20, sticky="w")
        
        # Source directory
        ctk.CTkLabel(panel, text="Source Directory:", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=1, column=0, padx=20, pady=10, sticky="w"
        )
        
        source_frame = ctk.CTkFrame(panel)
        source_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=5, sticky="ew")
        source_frame.grid_columnconfigure(0, weight=1)
        
        self.source_entry = ctk.CTkEntry(
            source_frame,
            placeholder_text="Select source directory containing your legal files..."
        )
        self.source_entry.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.source_entry.insert(0, self.config.source_directory)
        
        ctk.CTkButton(
            source_frame,
            text="Browse",
            command=self.browse_source_directory,
            width=100
        ).grid(row=0, column=1, padx=10, pady=10)
        
        # Target directory
        ctk.CTkLabel(panel, text="Target Directory:", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=3, column=0, padx=20, pady=(20, 10), sticky="w"
        )
        
        target_frame = ctk.CTkFrame(panel)
        target_frame.grid(row=4, column=0, columnspan=2, padx=20, pady=5, sticky="ew")
        target_frame.grid_columnconfigure(0, weight=1)
        
        self.target_entry = ctk.CTkEntry(
            target_frame,
            placeholder_text="Select target directory for organized results..."
        )
        self.target_entry.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.target_entry.insert(0, self.config.target_directory)
        
        ctk.CTkButton(
            target_frame,
            text="Browse",
            command=self.browse_target_directory,
            width=100
        ).grid(row=0, column=1, padx=10, pady=10)
        
        # File preview
        ctk.CTkLabel(panel, text="File Preview:", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=5, column=0, padx=20, pady=(20, 10), sticky="w"
        )
        
        self.file_preview = ctk.CTkTextbox(panel, height=200)
        self.file_preview.grid(row=6, column=0, columnspan=2, padx=20, pady=5, sticky="ew")
        
        # Scan button
        scan_button = ctk.CTkButton(
            panel,
            text="🔍 Scan Source Directory",
            command=self.scan_source_directory
        )
        scan_button.grid(row=7, column=0, columnspan=2, padx=20, pady=20)
        
        self.panels["files"] = panel
    
    def create_ai_config_panel(self):
        """Create the AI configuration panel"""
        panel = ctk.CTkScrollableFrame(self.main_frame)
        
        # AI Integration Panel
        ai_panel = AIIntegrationPanel(panel, self.config)
        ai_panel.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        
        # Store reference to AI panel
        self.ai_panel = ai_panel
        
        self.panels["ai"] = panel
    
    def create_settings_panel(self):
        """Create the settings panel"""
        panel = ctk.CTkScrollableFrame(self.main_frame)
        panel.grid_columnconfigure(1, weight=1)
        
        # Title
        title = ctk.CTkLabel(
            panel,
            text="⚙️ Analysis Settings",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, columnspan=2, padx=20, pady=20, sticky="w")
        
        # Scoring weights section
        scoring_frame = ctk.CTkFrame(panel)
        scoring_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        scoring_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            scoring_frame,
            text="Scoring Weights",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=10, sticky="w")
        
        # Probative weight
        ctk.CTkLabel(scoring_frame, text="Probative Weight:").grid(row=1, column=0, padx=20, pady=5, sticky="w")
        self.probative_weight_var = tk.DoubleVar(value=self.config.probative_weight)
        probative_slider = ctk.CTkSlider(
            scoring_frame,
            from_=0.0,
            to=1.0,
            variable=self.probative_weight_var
        )
        probative_slider.grid(row=1, column=1, padx=20, pady=5, sticky="ew")
        
        # Relevance weight
        ctk.CTkLabel(scoring_frame, text="Relevance Weight:").grid(row=2, column=0, padx=20, pady=5, sticky="w")
        self.relevance_weight_var = tk.DoubleVar(value=self.config.relevance_weight)
        relevance_slider = ctk.CTkSlider(
            scoring_frame,
            from_=0.0,
            to=1.0,
            variable=self.relevance_weight_var
        )
        relevance_slider.grid(row=2, column=1, padx=20, pady=5, sticky="ew")
        
        # Admissibility weight
        ctk.CTkLabel(scoring_frame, text="Admissibility Weight:").grid(row=3, column=0, padx=20, pady=5, sticky="w")
        self.admissibility_weight_var = tk.DoubleVar(value=self.config.admissibility_weight)
        admissibility_slider = ctk.CTkSlider(
            scoring_frame,
            from_=0.0,
            to=1.0,
            variable=self.admissibility_weight_var
        )
        admissibility_slider.grid(row=3, column=1, padx=20, pady=5, sticky="ew")
        
        # Processing options
        options_frame = ctk.CTkFrame(panel)
        options_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        
        ctk.CTkLabel(
            options_frame,
            text="Processing Options",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=10, sticky="w")
        
        # Checkboxes for various options
        self.dedup_var = tk.BooleanVar(value=self.config.enable_deduplication)
        dedup_check = ctk.CTkCheckBox(options_frame, text="Enable Deduplication", variable=self.dedup_var)
        dedup_check.grid(row=1, column=0, padx=20, pady=5, sticky="w")
        
        self.neo4j_var = tk.BooleanVar(value=self.config.enable_neo4j)
        neo4j_check = ctk.CTkCheckBox(options_frame, text="Enable Neo4j Knowledge Graph", variable=self.neo4j_var)
        neo4j_check.grid(row=1, column=1, padx=20, pady=5, sticky="w")
        
        self.nlp_var = tk.BooleanVar(value=self.config.enable_advanced_nlp)
        nlp_check = ctk.CTkCheckBox(options_frame, text="Advanced NLP Analysis", variable=self.nlp_var)
        nlp_check.grid(row=2, column=0, padx=20, pady=5, sticky="w")
        
        self.viz_var = tk.BooleanVar(value=self.config.generate_visualizations)
        viz_check = ctk.CTkCheckBox(options_frame, text="Generate Visualizations", variable=self.viz_var)
        viz_check.grid(row=2, column=1, padx=20, pady=5, sticky="w")
        
        # Save settings button
        save_button = ctk.CTkButton(
            panel,
            text="💾 Save Settings",
            command=self.save_settings
        )
        save_button.grid(row=3, column=0, columnspan=2, padx=20, pady=20)
        
        self.panels["settings"] = panel
    
    def create_results_panel(self):
        """Create the results panel"""
        panel = ctk.CTkFrame(self.main_frame)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)
        
        # Title
        title = ctk.CTkLabel(
            panel,
            text="📊 Analysis Results",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        # Results notebook
        self.results_notebook = ctk.CTkTabview(panel)
        self.results_notebook.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        
        # Add tabs
        self.results_notebook.add("Summary")
        self.results_notebook.add("File Analysis")
        self.results_notebook.add("Argument Strength")
        self.results_notebook.add("Duplicates")
        
        # Summary tab
        summary_text = ctk.CTkTextbox(self.results_notebook.tab("Summary"))
        summary_text.pack(fill="both", expand=True, padx=10, pady=10)
        summary_text.insert("1.0", "Analysis results will appear here after running the analysis...")
        
        # File Analysis tab
        file_analysis_text = ctk.CTkTextbox(self.results_notebook.tab("File Analysis"))
        file_analysis_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Argument Strength tab
        argument_text = ctk.CTkTextbox(self.results_notebook.tab("Argument Strength"))
        argument_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Duplicates tab
        duplicates_text = ctk.CTkTextbox(self.results_notebook.tab("Duplicates"))
        duplicates_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.panels["results"] = panel
    
    def create_visualizations_panel(self):
        """Create the visualizations panel"""
        panel = ctk.CTkFrame(self.main_frame)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)
        
        # Title
        title = ctk.CTkLabel(
            panel,
            text="📈 Visualizations",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        # Placeholder for visualizations
        viz_frame = ctk.CTkFrame(panel)
        viz_frame.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        viz_frame.grid_columnconfigure(0, weight=1)
        viz_frame.grid_rowconfigure(0, weight=1)
        
        placeholder_label = ctk.CTkLabel(
            viz_frame,
            text="📊 Interactive visualizations will be displayed here\nafter analysis is complete",
            font=ctk.CTkFont(size=16),
            text_color="gray"
        )
        placeholder_label.grid(row=0, column=0, padx=20, pady=20)
        
        self.panels["viz"] = panel
    
    def create_status_bar(self):
        """Create the status bar"""
        self.status_bar = ctk.CTkFrame(self, height=30, corner_radius=0)
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.status_bar.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="Ready",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # Progress indicator
        self.progress_indicator = ctk.CTkProgressBar(self.status_bar, width=200)
        self.progress_indicator.grid(row=0, column=1, padx=10, pady=5)
        self.progress_indicator.set(0)
    
    def show_panel(self, panel_name):
        """Show the specified panel"""
        # Hide all panels
        for panel in self.panels.values():
            panel.grid_remove()
        
        # Show selected panel
        if panel_name in self.panels:
            self.panels[panel_name].grid(row=0, column=0, sticky="nsew")
        
        # Update button states
        for key, btn in self.nav_buttons.items():
            if key == panel_name:
                btn.configure(fg_color=("gray70", "gray30"))
            else:
                btn.configure(fg_color=("gray85", "gray25"))
    
    def browse_source_directory(self):
        """Browse for source directory"""
        directory = filedialog.askdirectory(
            title="Select Source Directory",
            initialdir=self.config.source_directory
        )
        if directory:
            self.source_entry.delete(0, "end")
            self.source_entry.insert(0, directory)
            self.config.source_directory = directory
            self.update_status("Source directory updated")
    
    def browse_target_directory(self):
        """Browse for target directory"""
        directory = filedialog.askdirectory(
            title="Select Target Directory",
            initialdir=self.config.target_directory
        )
        if directory:
            self.target_entry.delete(0, "end")
            self.target_entry.insert(0, directory)
            self.config.target_directory = directory
            self.update_status("Target directory updated")
    
    def scan_source_directory(self):
        """Scan source directory and show file preview"""
        source_dir = self.source_entry.get()
        if not source_dir or not Path(source_dir).exists():
            messagebox.showerror("Error", "Please select a valid source directory")
            return
        
        try:
            self.file_preview.delete("1.0", "end")
            file_count = 0
            supported_extensions = {'.pdf', '.docx', '.doc', '.txt', '.rtf', '.xlsx', '.xls', '.csv', '.eml', '.msg'}
            
            for file_path in Path(source_dir).rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                    file_count += 1
                    relative_path = file_path.relative_to(Path(source_dir))
                    self.file_preview.insert("end", f"{relative_path}\n")
            
            self.file_preview.insert("1.0", f"Found {file_count} supported files:\n\n")
            self.update_status(f"Scanned {file_count} files in source directory")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error scanning directory: {str(e)}")
    
    def save_settings(self):
        """Save current settings"""
        try:
            # Update config with current values
            self.config.probative_weight = self.probative_weight_var.get()
            self.config.relevance_weight = self.relevance_weight_var.get()
            self.config.admissibility_weight = self.admissibility_weight_var.get()
            
            self.config.enable_deduplication = self.dedup_var.get()
            self.config.enable_neo4j = self.neo4j_var.get()
            self.config.enable_advanced_nlp = self.nlp_var.get()
            self.config.generate_visualizations = self.viz_var.get()
            
            # Update AI config
            self.config.ai_config = self.ai_panel.get_ai_config()
            
            # Save to file
            self.save_config()
            
            messagebox.showinfo("Settings Saved", "Settings have been saved successfully!")
            self.update_status("Settings saved")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error saving settings: {str(e)}")
    
    def start_analysis(self):
        """Start the LCAS analysis process"""
        # Validate inputs
        if not self.config.source_directory or not Path(self.config.source_directory).exists():
            messagebox.showerror("Error", "Please select a valid source directory")
            self.show_panel("files")
            return
        
        if not self.config.target_directory:
            messagebox.showerror("Error", "Please select a target directory")
            self.show_panel("files")
            return
        
        # Show progress dialog
        progress_dialog = LCASProgressDialog(self, "LCAS Analysis")
        
        # Start analysis in separate thread
        analysis_thread = threading.Thread(
            target=self.run_analysis_thread,
            args=(progress_dialog,),
            daemon=True
        )
        analysis_thread.start()
    
    def run_analysis_thread(self, progress_dialog):
        """Run analysis in background thread"""
        try:
            # Import LCAS modules
            from lcas_main import LCASCore, LCASConfig
            from content_extraction_plugin import ContentExtractionPlugin
            
            # Create LCAS config
            lcas_config = LCASConfig(
                source_directory=self.config.source_directory,
                target_directory=self.config.target_directory,
                probative_weight=self.config.probative_weight,
                relevance_weight=self.config.relevance_weight,
                admissibility_weight=self.config.admissibility_weight
            )
            
            # Initialize LCAS
            progress_dialog.update_progress(0.1, "Initializing LCAS...", "Setting up analysis engine")
            lcas = LCASCore(lcas_config)
            
            # Register plugins
            progress_dialog.update_progress(0.2, "Loading plugins...", "Registering content extraction plugin")
            lcas.register_plugin('content_extraction', ContentExtractionPlugin(lcas_config))
            
            # Run analysis
            progress_dialog.update_progress(0.3, "Starting analysis...", "Beginning file processing")
            
            # Create folder structure
            progress_dialog.update_progress(0.4, "Creating folder structure...", "Setting up organized directories")
            lcas.create_folder_structure()
            
            # Discover files
            progress_dialog.update_progress(0.5, "Discovering files...", "Scanning source directory")
            files = lcas.discover_files()
            
            if not files:
                progress_dialog.update_progress(1.0, "Complete", "No files found to process")
                return
            
            # Process files
            total_files = len(files)
            for i, file_path in enumerate(files):
                if progress_dialog.cancelled:
                    return
                
                progress = 0.5 + (i / total_files) * 0.4
                progress_dialog.update_progress(
                    progress,
                    f"Processing file {i+1}/{total_files}",
                    f"Analyzing: {file_path.name}"
                )
                
                analysis = lcas.process_single_file(file_path)
                lcas.processed_files[str(file_path)] = analysis
            
            # Organize files
            progress_dialog.update_progress(0.9, "Organizing files...", "Moving files to categorized folders")
            lcas.organize_processed_files()
            
            # Generate reports
            progress_dialog.update_progress(0.95, "Generating reports...", "Creating analysis reports")
            lcas.generate_final_reports()
            
            # Save results
            progress_dialog.update_progress(0.98, "Saving results...", "Saving analysis data")
            lcas.save_analysis_results()
            
            # Complete
            progress_dialog.update_progress(1.0, "Analysis Complete!", "Results saved successfully")
            
            # Update UI with results
            self.after(1000, lambda: self.load_analysis_results(lcas_config.target_directory))
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            progress_dialog.update_progress(0, "Analysis Failed", f"Error: {str(e)}")
        
        # Close progress dialog after a delay
        self.after(2000, progress_dialog.destroy)
    
    def load_analysis_results(self, target_directory):
        """Load and display analysis results"""
        try:
            # Load summary report
            summary_file = Path(target_directory) / "10_VISUALIZATIONS_AND_REPORTS" / "analysis_summary.md"
            if summary_file.exists():
                with open(summary_file, 'r', encoding='utf-8') as f:
                    summary_content = f.read()
                
                summary_text = self.results_notebook.tab("Summary").winfo_children()[0]
                summary_text.delete("1.0", "end")
                summary_text.insert("1.0", summary_content)
            
            # Load argument strength report
            strength_file = Path(target_directory) / "10_VISUALIZATIONS_AND_REPORTS" / "argument_strength_analysis.md"
            if strength_file.exists():
                with open(strength_file, 'r', encoding='utf-8') as f:
                    strength_content = f.read()
                
                argument_text = self.results_notebook.tab("Argument Strength").winfo_children()[0]
                argument_text.delete("1.0", "end")
                argument_text.insert("1.0", strength_content)
            
            # Show results panel
            self.show_panel("results")
            self.update_status("Analysis complete - results loaded")
            
            # Show completion message
            messagebox.showinfo(
                "Analysis Complete",
                f"Analysis completed successfully!\n\nResults saved to:\n{target_directory}\n\nCheck the Results tab for detailed findings."
            )
            
        except Exception as e:
            logger.error(f"Error loading results: {e}")
            messagebox.showerror("Error", f"Error loading analysis results: {str(e)}")
    
    def update_status(self, message):
        """Update status bar message"""
        self.status_label.configure(text=message)
        self.update()
    
    def on_closing(self):
        """Handle window closing"""
        # Save configuration before closing
        self.save_config()
        self.destroy()

def main():
    """Main entry point for the GUI application"""
    app = LCASMainWindow()
    app.mainloop()

if __name__ == "__main__":
    main()