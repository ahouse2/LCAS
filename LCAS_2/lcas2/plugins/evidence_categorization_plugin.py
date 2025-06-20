#!/usr/bin/env python3
"""
Evidence Categorization Plugin for LCAS
Categorizes evidence files into predefined legal argument folders
"""

import tkinter as tk
from tkinter import ttk
import shutil
import asyncio
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

from lcas2.core import AnalysisPlugin, UIPlugin


class EvidenceCategorizationPlugin(AnalysisPlugin, UIPlugin):
    """Plugin for categorizing evidence into legal argument folders"""

    @property
    def name(self) -> str:
        return "Evidence Categorization"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Categorizes evidence files into predefined legal argument folders"

    @property
    def dependencies(self) -> List[str]:
        return []

    async def initialize(self, core_app) -> bool:
        self.core = core_app
        self.logger = core_app.logger.getChild(self.name)

        # Define standard folder structure
        self.folder_structure = {
            "CASE_SUMMARIES_AND_RELATED_DOCS": ["summary", "case", "pleading", "motion"],
            "CONSTITUTIONAL_VIOLATIONS": ["constitutional", "due_process", "rights"],
            "ELECTRONIC_ABUSE": ["spyware", "electronic", "surveillance", "digital"],
            "FRAUD_ON_THE_COURT": ["fraud", "deception", "misrepresentation"],
            "NON_DISCLOSURE": ["financial", "asset", "disclosure", "fc2107", "fc2122"],
            "TEXT_MESSAGES": ["text", "message", "sms", "communication"],
            "POST_TRIAL_ABUSE": ["harassment", "violation", "abuse"]
        }

        return True

    async def cleanup(self) -> None:
        pass

    async def analyze(self, data: Any) -> Dict[str, Any]:
        """Categorize files into appropriate folders"""
        source_dir = Path(data.get("source_directory", ""))
        target_dir = Path(data.get("target_directory", ""))

        if not source_dir.exists():
            return {"error": "Source directory does not exist"}

        categorized_files = {}
        uncategorized_files = []

        # Create folder structure
        for folder_name in self.folder_structure.keys():
            folder_path = target_dir / folder_name
            folder_path.mkdir(parents=True, exist_ok=True)
            categorized_files[folder_name] = []

        # Create FOR_HUMAN_REVIEW folder
        review_folder = target_dir / "FOR_HUMAN_REVIEW"
        review_folder.mkdir(parents=True, exist_ok=True)

        # Categorize files
        for file_path in source_dir.rglob("*"):
            if file_path.is_file():
                filename_lower = file_path.name.lower()
                categorized = False

                # Check against keywords for each folder
                for folder_name, keywords in self.folder_structure.items():
                    if any(keyword.lower()
                           in filename_lower for keyword in keywords):
                        # Copy file to appropriate folder
                        target_file = target_dir / folder_name / file_path.name

                        # Handle name conflicts
                        counter = 1
                        while target_file.exists():
                            stem = file_path.stem
                            suffix = file_path.suffix
                            target_file = target_dir / folder_name / \
                                f"{stem}_{counter}{suffix}"
                            counter += 1

                        shutil.copy2(file_path, target_file)
                        categorized_files[folder_name].append(str(target_file))
                        categorized = True
                        break

                if not categorized:
                    # Move to review folder
                    target_file = review_folder / file_path.name

                    # Handle name conflicts
                    counter = 1
                    while target_file.exists():
                        stem = file_path.stem
                        suffix = file_path.suffix
                        target_file = review_folder / \
                            f"{stem}_{counter}{suffix}"
                        counter += 1

                    shutil.copy2(file_path, target_file)
                    uncategorized_files.append(str(target_file))

        # Generate categorization report
        total_files = sum(
            len(files) for files in categorized_files.values()) + len(uncategorized_files)

        return {
            "plugin": self.name,
            "total_files": total_files,
            "categorized_files": categorized_files,
            "uncategorized_files": uncategorized_files,
            "folders_created": list(self.folder_structure.keys()),
            "status": "completed"
        }

    def create_ui_elements(self, parent_widget) -> List[tk.Widget]:
        elements = []

        frame = ttk.Frame(parent_widget)
        frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(frame, text="📁 Categorize Evidence",
                   command=self.run_analysis_ui).pack(side=tk.LEFT, padx=2)

        ttk.Button(frame, text="📋 View Categories",
                   command=self.show_categories).pack(side=tk.LEFT, padx=2)

        self.status_label = ttk.Label(frame, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=10)

        elements.extend([frame, self.status_label])
        return elements

    def show_categories(self):
        """Show categorization structure"""
        categories_text = "Evidence Categories:\n\n"
        for folder, keywords in self.folder_structure.items():
            categories_text += f"{folder}:\n"
            categories_text += f"  Keywords: {', '.join(keywords)}\n\n"

        # Create popup window
        popup = tk.Toplevel()
        popup.title("Evidence Categories")
        popup.geometry("600x400")

        text_widget = tk.Text(popup, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(tk.END, categories_text)
        text_widget.config(state=tk.DISABLED)

    def run_analysis_ui(self):
        if hasattr(self, 'core') and self.core.event_loop:
            self.status_label.config(text="Categorizing...")

            async def run_and_update():
                result = await self.analyze({
                    "source_directory": self.core.config.source_directory,
                    "target_directory": self.core.config.target_directory
                })

                # Update UI in main thread
                def update_ui():
                    if "error" in result:
                        self.status_label.config(
                            text=f"Error: {result['error']}")
                    else:
                        total = result['total_files']
                        uncategorized = len(result['uncategorized_files'])
                        categorized = total - uncategorized
                        self.status_label.config(
                            text=f"Categorized {categorized}/{total} files")

                if hasattr(self.core, 'root'):
                    self.core.root.after(0, update_ui)

            asyncio.run_coroutine_threadsafe(
                run_and_update(), self.core.event_loop)
