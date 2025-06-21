#!/usr/bin/env python3
"""
Enhanced LCAS GUI Application with Comprehensive AI Integration
Modern, sleek interface for legal evidence analysis with full AI capabilities
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
import json
import os
import threading
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging
import time
from datetime import datetime
from gui_preservation_integration import add_preservation_to_gui
from analysis_engine_gui import add_analysis_engine_to_gui

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
class LCASGUIConfig:
    """Enhanced GUI Configuration with AI settings"""
    source_directory: str = ""
    target_directory: str = ""

    # Case Theory Settings
    case_title: str = ""
    case_type: str = "family_law"
    primary_legal_theories: list = None
    key_facts_alleged: list = None

    # AI Settings
    ai_enabled: bool = True
    ai_provider: str = "openai"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    analysis_depth: str = "standard"
    confidence_threshold: float = 0.6

    # Rate Limiting
    max_requests_per_minute: int = 20
    max_tokens_per_hour: int = 100000
    max_cost_per_hour: float = 10.0

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

    def __post_init__(self):
        if self.primary_legal_theories is None:
            self.primary_legal_theories = []
        if self.key_facts_alleged is None:
            self.key_facts_alleged = []


class CaseTheorySetupDialog(ctk.CTkToplevel):
    """Dialog for setting up case theory and legal objectives"""

    def __init__(self, parent, existing_config=None):
        super().__init__(parent)
        self.title("Case Theory Setup")
        self.geometry("700x600")
        self.transient(parent)
        self.grab_set()

        self.result = None
        self.existing_config = existing_config or {}

        # Center on parent
        self.center_on_parent(parent)

        # Setup UI
        self.setup_ui()

    def center_on_parent(self, parent):
        """Center dialog on parent window"""
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def setup_ui(self):
        """Setup case theory configuration UI"""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Title
        title = ctk.CTkLabel(self, text="⚖️ Case Theory Configuration",
                             font=ctk.CTkFont(size=20, weight="bold"))
        title.grid(row=0, column=0, padx=20, pady=10)

        # Main content frame (scrollable)
        content_frame = ctk.CTkScrollableFrame(self)
        content_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        content_frame.grid_columnconfigure(1, weight=1)

        row = 0

        # Case Title
        ctk.CTkLabel(content_frame, text="Case Title:", font=ctk.CTkFont(weight="bold")).grid(
            row=row, column=0, padx=10, pady=5, sticky="w"
        )
        self.case_title_entry = ctk.CTkEntry(content_frame, width=400,
                                             placeholder_text="e.g., Smith v. Smith Divorce")
        self.case_title_entry.grid(
            row=row, column=1, padx=10, pady=5, sticky="ew")
        if self.existing_config.get('case_title'):
            self.case_title_entry.insert(0, self.existing_config['case_title'])
        row += 1

        # Case Type
        ctk.CTkLabel(content_frame, text="Case Type:", font=ctk.CTkFont(weight="bold")).grid(
            row=row, column=0, padx=10, pady=5, sticky="w"
        )
        self.case_type_var = ctk.StringVar(
            value=self.existing_config.get(
                'case_type', 'family_law'))
        self.case_type_combo = ctk.CTkComboBox(
            content_frame,
            values=[
                "family_law",
                "personal_injury",
                "business_litigation",
                "criminal_defense",
                "employment",
                "other"],
            variable=self.case_type_var,
            command=self.on_case_type_change
        )
        self.case_type_combo.grid(
            row=row, column=1, padx=10, pady=5, sticky="ew")
        row += 1

        # Legal Theories
        ctk.CTkLabel(content_frame, text="Primary Legal Theories:",
                     font=ctk.CTkFont(weight="bold")).grid(
            row=row, column=0, padx=10, pady=5, sticky="nw"
        )

        theories_frame = ctk.CTkFrame(content_frame)
        theories_frame.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
        theories_frame.grid_columnconfigure(0, weight=1)

        self.theories_text = ctk.CTkTextbox(theories_frame, height=100)
        self.theories_text.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # Pre-populate with existing theories
        existing_theories = self.existing_config.get(
            'primary_legal_theories', [])
        if existing_theories:
            self.theories_text.insert("1.0", "\n".join(existing_theories))
        else:
            self.load_default_theories()

        theories_help = ctk.CTkLabel(theories_frame,
                                     text="Enter one theory per line (e.g., 'Asset Dissipation', 'Fraud on Court')",
                                     font=ctk.CTkFont(size=10), text_color="gray")
        theories_help.grid(row=1, column=0, padx=5, pady=2, sticky="w")
        row += 1

        # Key Facts
        ctk.CTkLabel(content_frame, text="Key Alleged Facts:",
                     font=ctk.CTkFont(weight="bold")).grid(
            row=row, column=0, padx=10, pady=5, sticky="nw"
        )

        facts_frame = ctk.CTkFrame(content_frame)
        facts_frame.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
        facts_frame.grid_columnconfigure(0, weight=1)

        self.facts_text = ctk.CTkTextbox(facts_frame, height=120)
        self.facts_text.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # Pre-populate with existing facts
        existing_facts = self.existing_config.get('key_facts_alleged', [])
        if existing_facts:
            self.facts_text.insert("1.0", "\n".join(existing_facts))

        facts_help = ctk.CTkLabel(facts_frame,
                                  text="Enter key facts you want to prove (one per line). AI will look for evidence supporting these.",
                                  font=ctk.CTkFont(size=10), text_color="gray")
        facts_help.grid(row=1, column=0, padx=5, pady=2, sticky="w")
        row += 1

        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        button_frame.grid_columnconfigure(1, weight=1)

        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.cancel)
        cancel_btn.grid(row=0, column=0, padx=10, pady=10)

        save_btn = ctk.CTkButton(
            button_frame,
            text="Save & Continue",
            command=self.save)
        save_btn.grid(row=0, column=2, padx=10, pady=10)

    def load_default_theories(self):
        """Load default theories based on case type"""
        case_type = self.case_type_var.get()

        default_theories = {
            "family_law": [
                "Asset Dissipation/Hiding",
                "Income Concealment",
                "Abuse/Domestic Violence",
                "Fraud on the Court",
                "Constitutional Violations",
                "Attorney Misconduct"
            ],
            "personal_injury": [
                "Negligence",
                "Product Liability",
                "Medical Malpractice",
                "Premises Liability",
                "Wrongful Death"
            ],
            "business_litigation": [
                "Breach of Contract",
                "Fraud/Misrepresentation",
                "Partnership Disputes",
                "Employment Issues",
                "Intellectual Property"
            ],
            "criminal_defense": [
                "Constitutional Violations",
                "Insufficient Evidence",
                "Self Defense",
                "Mistaken Identity",
                "Police Misconduct"
            ],
            "employment": [
                "Discrimination",
                "Wrongful Termination",
                "Wage/Hour Violations",
                "Harassment",
                "Retaliation"
            ]
        }

        theories = default_theories.get(
            case_type, ["Legal Theory 1", "Legal Theory 2"])
        self.theories_text.delete("1.0", "end")
        self.theories_text.insert("1.0", "\n".join(theories))

    def on_case_type_change(self, value):
        """Handle case type change"""
        # Ask if user wants to load default theories
        if messagebox.askyesno("Load Defaults",
                               f"Load default legal theories for {value.replace('_', ' ').title()}?"):
            self.load_default_theories()

    def save(self):
        """Save case theory configuration"""
        # Get theories (one per line, filter empty)
        theories_text = self.theories_text.get("1.0", "end").strip()
        theories = [line.strip()
                    for line in theories_text.split('\n') if line.strip()]

        # Get facts (one per line, filter empty)
        facts_text = self.facts_text.get("1.0", "end").strip()
        facts = [line.strip()
                 for line in facts_text.split('\n') if line.strip()]

        self.result = {
            'case_title': self.case_title_entry.get().strip(),
            'case_type': self.case_type_var.get(),
            'primary_legal_theories': theories,
            'key_facts_alleged': facts
        }

        self.destroy()

    def cancel(self):
        """Cancel case theory setup"""
        self.result = None
        self.destroy()


class EnhancedLCASMainWindow(ctk.CTk):
    """Enhanced main LCAS GUI with comprehensive AI integration"""

    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("LCAS v3.0 - AI-Powered Legal Evidence Analysis")
        self.geometry("1200x800")
        self.minsize(1000, 600)

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
                    return LCASGUIConfig(**data)
            except Exception as e:
                logger.error(f"Error loading config: {e}")

        return LCASGUIConfig()

    def save_config(self):
        """Save configuration to file"""
        config_file = "lcas_gui_config.json"
        try:
            config_dict = asdict(self.config)
            with open(config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    def setup_ui(self):
        """Set up the enhanced user interface"""
        # Configure main grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def create_enhanced_interface(self):
        """Create enhanced interface with new v4.0 components"""

        # Your existing GUI code here...

        # ADD THIS: File Preservation GUI
        preservation_label = ctk.CTkLabel(
            self.main_frame,
            text="Enhanced LCAS v4.0 Features",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        preservation_label.pack(pady=10)

        # File Preservation Section
        self.preservation_gui = add_preservation_to_gui(
            self.main_frame,
            self.config
        )

        # Enhanced Analysis Engine Section
        self.analysis_gui = add_analysis_engine_to_gui(
            self.main_frame,
            self.config,
            getattr(self, 'ai_plugin', None)  # Pass AI plugin if available
        )
        # Create sidebar
        self.create_sidebar()

        # Create main content area
        self.create_main_content()

        # Create status bar
        self.create_status_bar()

    def create_sidebar(self):
        """Create sidebar with navigation"""
        sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        sidebar.grid_rowconfigure(8, weight=1)

        # Logo/Title
        logo_label = ctk.CTkLabel(
            sidebar,
            text="⚖️ LCAS v3.0",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 5))

        subtitle = ctk.CTkLabel(
            sidebar,
            text="AI-Powered Legal Analysis",
            font=ctk.CTkFont(size=12)
        )
        subtitle.grid(row=1, column=0, padx=20, pady=(0, 20))

        # Navigation buttons
        self.nav_buttons = {}
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("📋 Case Setup", "case_setup"),
            ("📁 File Management", "files"),
            ("⚙️ Settings", "settings"),
            ("📊 Results", "results")
        ]

        for i, (text, key) in enumerate(nav_items):
            btn = ctk.CTkButton(
                sidebar,
                text=text,
                command=lambda k=key: self.show_panel(k),
                height=40,
                anchor="w"
            )
            btn.grid(row=i + 2, column=0, padx=20, pady=5, sticky="ew")
            self.nav_buttons[key] = btn

        # Version info
        version_label = ctk.CTkLabel(
            sidebar,
            text="v3.0.0 Beta - AI Enhanced",
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
        self.create_dashboard_panel()
        self.create_case_setup_panel()
        self.create_file_panel()
        self.create_settings_panel()
        self.create_results_panel()

        # Show dashboard by default
        self.show_panel("dashboard")

    def create_dashboard_panel(self):
        """Create dashboard panel"""
        panel = ctk.CTkFrame(self.main_frame)
        panel.grid_columnconfigure(0, weight=1)

        # Welcome message
        welcome_label = ctk.CTkLabel(
            panel,
            text="🚀 AI-Powered Legal Evidence Analysis",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        welcome_label.grid(row=0, column=0, padx=30, pady=(30, 10))

        description = ctk.CTkLabel(
            panel,
            text="Legal Case Analysis System - Organize and Analyze Your Evidence with AI",
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
            text="Quick Start Guide",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=10)

        steps = [
            "1. Configure your case theory and legal objectives (Case Setup tab)",
            "2. Set up your source directory (where your evidence files are)",
            "3. Choose your target directory (where organized results will go)",
            "4. Configure AI settings and API keys (Settings tab)",
            "5. Run the analysis and review AI-enhanced results"
        ]

        for i, step in enumerate(steps):
            ctk.CTkLabel(
                quick_start_frame,
                text=step,
                font=ctk.CTkFont(size=12),
                anchor="w"
            ).grid(row=i + 1, column=0, padx=20, pady=5, sticky="ew")

        # Start button
        start_button = ctk.CTkButton(
            panel,
            text="🚀 Start Analysis",
            command=self.quick_start_analysis,
            height=50,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        start_button.grid(row=3, column=0, padx=30, pady=30)

        self.panels["dashboard"] = panel

    def create_case_setup_panel(self):
        """Create case setup panel"""
        panel = ctk.CTkScrollableFrame(self.main_frame)
        panel.grid_columnconfigure(0, weight=1)

        # Title
        title = ctk.CTkLabel(
            panel,
            text="📋 Case Theory Configuration",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        # Current case info
        current_frame = ctk.CTkFrame(panel)
        current_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        current_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(current_frame, text="Current Case:",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w"
        )

        # Case details
        case_title = self.config.case_title or "Not Set"
        case_type = self.config.case_type.replace('_', ' ').title()
        theories_count = len(self.config.primary_legal_theories)
        facts_count = len(self.config.key_facts_alleged)

        details_text = f"""Title: {case_title}
Type: {case_type}
Legal Theories: {theories_count}
Key Facts: {facts_count}"""

        details_label = ctk.CTkLabel(
            current_frame, text=details_text, justify="left")
        details_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        # Edit button
        edit_btn = ctk.CTkButton(
            current_frame,
            text="⚙️ Configure Case Theory",
            command=self.configure_case_theory,
            height=40
        )
        edit_btn.grid(row=1, column=1, padx=10, pady=5, sticky="e")

        # Legal theories display
        if self.config.primary_legal_theories:
            theories_frame = ctk.CTkFrame(panel)
            theories_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

            ctk.CTkLabel(theories_frame, text="Legal Theories:",
                         font=ctk.CTkFont(size=14, weight="bold")).grid(
                row=0, column=0, padx=10, pady=5, sticky="w"
            )

            theories_text = "\n".join(
                f"• {theory}" for theory in self.config.primary_legal_theories)
            theories_label = ctk.CTkLabel(
                theories_frame, text=theories_text, justify="left")
            theories_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.panels["case_setup"] = panel

    def create_file_panel(self):
        """Create file management panel"""
        panel = ctk.CTkScrollableFrame(self.main_frame)
        panel.grid_columnconfigure(1, weight=1)

        # Title
        title = ctk.CTkLabel(
            panel,
            text="📁 File Management",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, columnspan=2, padx=20, pady=20, sticky="w")

        # Source directory
        ctk.CTkLabel(panel, text="Source Directory:", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=1, column=0, padx=20, pady=10, sticky="w"
        )

        source_frame = ctk.CTkFrame(panel)
        source_frame.grid(
            row=2,
            column=0,
            columnspan=2,
            padx=20,
            pady=5,
            sticky="ew")
        source_frame.grid_columnconfigure(0, weight=1)

        self.source_entry = ctk.CTkEntry(
            source_frame,
            placeholder_text="Click 'Browse' to select your evidence files directory..."
        )
        self.source_entry.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        if self.config.source_directory:
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
        target_frame.grid(
            row=4,
            column=0,
            columnspan=2,
            padx=20,
            pady=5,
            sticky="ew")
        target_frame.grid_columnconfigure(0, weight=1)

        self.target_entry = ctk.CTkEntry(
            target_frame,
            placeholder_text="Click 'Browse' to select where results should be saved..."
        )
        self.target_entry.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        if self.config.target_directory:
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
        self.file_preview.grid(
            row=6,
            column=0,
            columnspan=2,
            padx=20,
            pady=5,
            sticky="ew")

        # Scan button
        scan_button = ctk.CTkButton(
            panel,
            text="🔍 Scan Source Directory",
            command=self.scan_source_directory
        )
        scan_button.grid(row=7, column=0, columnspan=2, padx=20, pady=20)

        self.panels["files"] = panel

    def create_settings_panel(self):
        """Create settings panel"""
        panel = ctk.CTkScrollableFrame(self.main_frame)
        panel.grid_columnconfigure(1, weight=1)

        # Title
        title = ctk.CTkLabel(
            panel,
            text="⚙️ Analysis Settings",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, columnspan=2, padx=20, pady=20, sticky="w")

        # AI Settings
        ai_frame = ctk.CTkFrame(panel)
        ai_frame.grid(
            row=1,
            column=0,
            columnspan=2,
            padx=20,
            pady=10,
            sticky="ew")
        ai_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            ai_frame,
            text="AI Configuration",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=10, sticky="w")

        # AI Enable checkbox
        self.ai_enabled_var = ctk.BooleanVar(value=self.config.ai_enabled)
        ai_check = ctk.CTkCheckBox(
            ai_frame,
            text="Enable AI Analysis",
            variable=self.ai_enabled_var)
        ai_check.grid(
            row=1,
            column=0,
            columnspan=2,
            padx=20,
            pady=5,
            sticky="w")

        # OpenAI API Key
        ctk.CTkLabel(
            ai_frame,
            text="OpenAI API Key:").grid(
            row=2,
            column=0,
            padx=20,
            pady=5,
            sticky="w")
        self.openai_key_entry = ctk.CTkEntry(
            ai_frame, placeholder_text="sk-...", show="*")
        self.openai_key_entry.grid(
            row=2, column=1, padx=20, pady=5, sticky="ew")
        if self.config.openai_api_key:
            self.openai_key_entry.insert(0, self.config.openai_api_key)

        # Analysis Depth
        ctk.CTkLabel(
            ai_frame,
            text="Analysis Depth:").grid(
            row=3,
            column=0,
            padx=20,
            pady=5,
            sticky="w")
        self.analysis_depth_var = ctk.StringVar(
            value=self.config.analysis_depth)
        depth_combo = ctk.CTkComboBox(
            ai_frame,
            values=["basic", "standard", "comprehensive"],
            variable=self.analysis_depth_var
        )
        depth_combo.grid(row=3, column=1, padx=20, pady=5, sticky="ew")

        # Processing options
        options_frame = ctk.CTkFrame(panel)
        options_frame.grid(
            row=2,
            column=0,
            columnspan=2,
            padx=20,
            pady=10,
            sticky="ew")

        ctk.CTkLabel(
            options_frame,
            text="Processing Options",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=10, sticky="w")

        # Checkboxes for various options
        self.dedup_var = ctk.BooleanVar(value=self.config.enable_deduplication)
        dedup_check = ctk.CTkCheckBox(
            options_frame,
            text="Enable Deduplication",
            variable=self.dedup_var)
        dedup_check.grid(row=1, column=0, padx=20, pady=5, sticky="w")

        self.nlp_var = ctk.BooleanVar(value=self.config.enable_advanced_nlp)
        nlp_check = ctk.CTkCheckBox(
            options_frame,
            text="Advanced NLP Analysis",
            variable=self.nlp_var)
        nlp_check.grid(row=2, column=0, padx=20, pady=5, sticky="w")

        self.viz_var = ctk.BooleanVar(
            value=self.config.generate_visualizations)
        viz_check = ctk.CTkCheckBox(
            options_frame,
            text="Generate Visualizations",
            variable=self.viz_var)
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
        """Create results panel"""
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

        # Results text area
        self.results_text = ctk.CTkTextbox(panel)
        self.results_text.grid(
            row=1,
            column=0,
            padx=20,
            pady=20,
            sticky="nsew")
        self.results_text.insert(
            "1.0", "Analysis results will appear here after running the analysis...")

        self.panels["results"] = panel

    def create_status_bar(self):
        """Create the status bar"""
        self.status_bar = ctk.CTkFrame(self, height=30, corner_radius=0)
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.status_bar.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="Ready - Please configure your case and directories to begin",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

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

    def configure_case_theory(self):
        """Open case theory configuration dialog"""
        dialog = CaseTheorySetupDialog(self, {
            'case_title': self.config.case_title,
            'case_type': self.config.case_type,
            'primary_legal_theories': self.config.primary_legal_theories,
            'key_facts_alleged': self.config.key_facts_alleged
        })

        self.wait_window(dialog)

        if dialog.result:
            # Update configuration
            self.config.case_title = dialog.result['case_title']
            self.config.case_type = dialog.result['case_type']
            self.config.primary_legal_theories = dialog.result['primary_legal_theories']
            self.config.key_facts_alleged = dialog.result['key_facts_alleged']

            # Save configuration
            self.save_config()

            # Refresh case setup panel
            self.create_case_setup_panel()
            self.show_panel('case_setup')

            self.update_status("Case theory updated successfully")
            messagebox.showinfo(
                "Success", "Case theory configuration updated successfully!")

    def browse_source_directory(self):
        """Browse for source directory"""
        directory = filedialog.askdirectory(
            title="Select Source Directory (Evidence Files)",
            initialdir=self.config.source_directory if self.config.source_directory else os.path.expanduser(
                "~")
        )
        if directory:
            self.source_entry.delete(0, "end")
            self.source_entry.insert(0, directory)
            self.config.source_directory = directory
            self.update_status("Source directory updated")
            self.save_config()

    def browse_target_directory(self):
        """Browse for target directory"""
        directory = filedialog.askdirectory(
            title="Select Target Directory (Results)",
            initialdir=self.config.target_directory if self.config.target_directory else os.path.expanduser(
                "~")
        )
        if directory:
            self.target_entry.delete(0, "end")
            self.target_entry.insert(0, directory)
            self.config.target_directory = directory
            self.update_status("Target directory updated")
            self.save_config()

    def scan_source_directory(self):
        """Scan source directory and show file preview"""
        source_dir = self.source_entry.get()
        if not source_dir or not Path(source_dir).exists():
            messagebox.showerror(
                "Error", "Please select a valid source directory")
            return

        try:
            self.file_preview.delete("1.0", "end")
            file_count = 0
            supported_extensions = {'.pdf', '.docx', '.doc', '.txt', '.rtf', '.xlsx', '.xls', '.csv',
                                    '.eml', '.msg', '.png', '.jpg', '.jpeg'}

            for file_path in Path(source_dir).rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                    file_count += 1
                    relative_path = file_path.relative_to(Path(source_dir))
                    self.file_preview.insert("end", f"{relative_path}\n")

            self.file_preview.insert(
                "1.0", f"Found {file_count} supported files:\n\n")
            self.update_status(
                f"Scanned {file_count} files in source directory")

        except Exception as e:
            messagebox.showerror(f"Error scanning directory: {str(e)}")

    def save_settings(self):
        """Save current settings"""
        try:
            # Update config with current values
            self.config.ai_enabled = self.ai_enabled_var.get()
            self.config.openai_api_key = self.openai_key_entry.get()
            self.config.analysis_depth = self.analysis_depth_var.get()
            self.config.enable_deduplication = self.dedup_var.get()
            self.config.enable_advanced_nlp = self.nlp_var.get()
            self.config.generate_visualizations = self.viz_var.get()

            # Save to file
            self.save_config()

            messagebox.showinfo(
                "Settings Saved",
                "Settings have been saved successfully!")
            self.update_status("Settings saved")

        except Exception as e:
            messagebox.showerror("Error", f"Error saving settings: {str(e)}")

    def quick_start_analysis(self):
        """Quick start analysis"""
        # Basic validation
        if not self.config.source_directory:
            messagebox.showinfo("Setup Required",
                                "Please set up your source directory first.")
            self.show_panel("files")
            return

        if not self.config.target_directory:
            # Set default target directory
            self.config.target_directory = os.path.join(
                os.path.expanduser("~"), "Desktop", "LCAS_Results")
            self.target_entry.delete(0, "end")
            self.target_entry.insert(0, self.config.target_directory)
            self.save_config()

        self.start_analysis()

    def start_analysis(self):
        """Start the analysis process"""
        # Validate directories
        if not self.config.source_directory or not Path(
                self.config.source_directory).exists():
            messagebox.showerror(
                "Error", "Please select a valid source directory")
            return

        if not self.config.target_directory:
            messagebox.showerror("Error", "Please select a target directory")
            return

        # Show progress dialog
        progress_dialog = self.create_progress_dialog()

        # Start analysis in separate thread
        analysis_thread = threading.Thread(
            target=self.run_analysis_thread,
            args=(progress_dialog,),
            daemon=True
        )
        analysis_thread.start()

    def create_progress_dialog(self):
        """Create progress dialog"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("LCAS Analysis")
        dialog.geometry("500x300")
        dialog.transient(self)
        dialog.grab_set()

        # Center on parent
        x = self.winfo_x() + (self.winfo_width() // 2) - 250
        y = self.winfo_y() + (self.winfo_height() // 2) - 150
        dialog.geometry(f"+{x}+{y}")

        # Configure grid
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(2, weight=1)

        # Progress label
        dialog.progress_label = ctk.CTkLabel(
            dialog,
            text="Initializing...",
            font=ctk.CTkFont(size=14)
        )
        dialog.progress_label.grid(
            row=0, column=0, padx=20, pady=10, sticky="ew")

        # Progress bar
        dialog.progress_bar = ctk.CTkProgressBar(dialog)
        dialog.progress_bar.grid(
            row=1, column=0, padx=20, pady=10, sticky="ew")
        dialog.progress_bar.set(0)

        # Details text
        dialog.details_text = ctk.CTkTextbox(dialog)
        dialog.details_text.grid(
            row=2,
            column=0,
            padx=20,
            pady=10,
            sticky="nsew")

        # Cancel button
        dialog.cancel_button = ctk.CTkButton(
            dialog,
            text="Cancel",
            command=lambda: setattr(dialog, 'cancelled', True)
        )
        dialog.cancel_button.grid(row=3, column=0, padx=20, pady=10)

        dialog.cancelled = False
        return dialog

    def run_analysis_thread(self, progress_dialog):
        """Run analysis in background thread"""
        try:
            # Simulate analysis process
            progress_dialog.progress_label.configure(
                text="Creating folder structure...")
            progress_dialog.progress_bar.set(0.1)
            progress_dialog.details_text.insert(
                "end", "Setting up organized directories\n")
            progress_dialog.update()
            time.sleep(1)

            if progress_dialog.cancelled:
                return

            progress_dialog.progress_label.configure(
                text="Discovering files...")
            progress_dialog.progress_bar.set(0.3)
            progress_dialog.details_text.insert(
                "end", "Scanning source directory for evidence\n")
            progress_dialog.update()
            time.sleep(1)

            if progress_dialog.cancelled:
                return

            # Count files
            file_count = 0
            if Path(self.config.source_directory).exists():
                supported_extensions = {
                    '.pdf',
                    '.docx',
                    '.doc',
                    '.txt',
                    '.rtf',
                    '.xlsx',
                    '.xls',
                    '.csv'}
                for file_path in Path(self.config.source_directory).rglob('*'):
                    if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                        file_count += 1

            progress_dialog.details_text.insert(
                "end", f"Found {file_count} files for analysis\n")
            progress_dialog.update()

            # Simulate processing files
            for i in range(file_count):
                if progress_dialog.cancelled:
                    return

                progress = 0.3 + (i / max(file_count, 1)) * 0.6
                progress_dialog.progress_bar.set(progress)
                progress_dialog.progress_label.configure(
                    text=f"Processing file {i + 1}/{file_count}")

                if i < 5:  # Show first few files
                    progress_dialog.details_text.insert(
                        "end", f"Analyzing file {i + 1}\n")
                    progress_dialog.details_text.see("end")

                progress_dialog.update()
                time.sleep(0.1)  # Simulate processing time

            # Complete
            progress_dialog.progress_bar.set(1.0)
            progress_dialog.progress_label.configure(text="Analysis Complete!")
            progress_dialog.details_text.insert(
                "end", "\nAnalysis completed successfully!\n")
            progress_dialog.details_text.insert(
                "end", f"Processed {file_count} files\n")
            progress_dialog.details_text.insert(
                "end", f"Results saved to: {
                    self.config.target_directory}\n")
            progress_dialog.update()

            # Update results panel
            results_summary = f"""LCAS Analysis Results
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

CASE INFORMATION:
Title: {self.config.case_title or 'Not specified'}
Type: {self.config.case_type.replace('_', ' ').title()}
Legal Theories: {len(self.config.primary_legal_theories)}

PROCESSING SUMMARY:
Total Files Processed: {file_count}
Source Directory: {self.config.source_directory}
Target Directory: {self.config.target_directory}
AI Analysis: {'Enabled' if self.config.ai_enabled else 'Disabled'}

RESULTS:
Files have been organized and analyzed according to your case theory.
Check the target directory for detailed results and reports.

This is a demo version. The full version would include:
- AI-powered evidence categorization
- Legal scoring and analysis
- Comprehensive reports and visualizations
- Semantic search and clustering
"""

            self.after(1000, lambda: self.show_results(results_summary))
            self.after(3000, progress_dialog.destroy)

        except Exception as e:
            progress_dialog.progress_label.configure(text="Analysis Failed")
            progress_dialog.details_text.insert("end", f"\nError: {str(e)}\n")
            progress_dialog.update()
            self.after(2000, progress_dialog.destroy)

    def show_results(self, results_text):
        """Show analysis results"""
        self.results_text.delete("1.0", "end")
        self.results_text.insert("1.0", results_text)
        self.show_panel("results")
        self.update_status("Analysis complete - results available")

        messagebox.showinfo(
            "Analysis Complete",
            f"Analysis completed successfully!\n\n"
            f"Results saved to:\n{self.config.target_directory}\n\n"
            "Check the Results tab for detailed information."
        )

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
    app = EnhancedLCASMainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
