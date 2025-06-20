#!/usr/bin/env python3
"""
Evidence Categorization Plugin for LCAS
Categorizes evidence files into legal argument folders based on a provided scheme.
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
    """Plugin for categorizing evidence files based on a dynamic scheme."""

    @property
    def name(self) -> str:
        return "Evidence Categorization"

    @property
    def version(self) -> str:
        return "1.1.0" # Version updated

    @property
    def description(self) -> str:
        return "Categorizes evidence files into folders based on a provided scheme (e.g., keywords in filenames)."

    @property
    def dependencies(self) -> List[str]:
        # This plugin might later depend on AI analysis results for smarter categorization.
        return [] # For now, filename-based, so no explicit dependencies on other plugin *results*.

    async def initialize(self, core_app) -> bool:
        self.core = core_app
        self.logger = core_app.logger.getChild(self.name)
        self.current_categorization_scheme: Dict[str, List[str]] = {} # Store the last used scheme for UI
        self.logger.info("EvidenceCategorizationPlugin initialized.")
        return True

    async def cleanup(self) -> None:
        self.logger.info("EvidenceCategorizationPlugin cleaned up.")
        pass

    async def analyze(self, data: Any) -> Dict[str, Any]:
        """Categorize files into appropriate folders based on the provided scheme."""
        source_dir_str = data.get("source_directory", "")
        target_dir_str = data.get("target_directory", "")

        # categorization_scheme is expected to be Dict[str, List[str]]
        # e.g., {"FRAUD_DOCS": ["fraud", "deceit"], "FINANCIALS": ["bank_statement", "tax"]}
        categorization_scheme = data.get("categorization_scheme", {})
        self.current_categorization_scheme = categorization_scheme # Save for UI

        # Get a list of files to process. This could be all files in source_dir,
        # or a pre-filtered list from a previous plugin (e.g., file_ingestion_plugin results)
        # For now, assume it scans source_dir like before.
        # Future: data could contain 'file_list_to_process': [{'path': '/path/to/file1.pdf', 'name': 'file1.pdf'}, ...]

        if not source_dir_str:
            return {"error": "Source directory not provided", "success": False, "categorized_files": {}, "uncategorized_files": []}
        if not target_dir_str:
            return {"error": "Target directory not provided", "success": False, "categorized_files": {}, "uncategorized_files": []}
        if not categorization_scheme:
            self.logger.warning("No categorization scheme provided. All files will be marked for human review.")
            # Proceed, but all files will go to FOR_HUMAN_REVIEW

        source_dir = Path(source_dir_str)
        target_dir = Path(target_dir_str)

        if not source_dir.exists() or not source_dir.is_dir():
            return {"error": f"Source directory not found: {source_dir}", "success": False, "categorized_files": {}, "uncategorized_files": []}

        categorized_files_report: Dict[str, List[str]] = {}
        uncategorized_files_report: List[str] = []

        # Create folder structure based on the provided scheme
        for folder_name in categorization_scheme.keys():
            try:
                folder_path = target_dir / folder_name
                folder_path.mkdir(parents=True, exist_ok=True)
                categorized_files_report[folder_name] = []
            except Exception as e:
                self.logger.error(f"Could not create category folder {target_dir / folder_name}: {e}", exc_info=True)
                # Potentially skip this category or return an error for the whole process

        review_folder = target_dir / "FOR_HUMAN_REVIEW"
        try:
            review_folder.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Could not create FOR_HUMAN_REVIEW folder {review_folder}: {e}", exc_info=True)
            # This is a critical folder, might need to error out if it fails
            return {"error": f"Failed to create review folder: {e}", "success": False, "categorized_files": {}, "uncategorized_files": []}

        files_processed_count = 0
        for file_path in source_dir.rglob("*"): # Consider using a passed file list in future
            if file_path.is_file():
                files_processed_count += 1
                filename_lower = file_path.name.lower()
                was_categorized = False

                # Use the dynamic categorization_scheme
                for folder_name, keywords in categorization_scheme.items():
                    if not keywords: continue # Skip if a category has no keywords

                    # Current matching logic: filename based.
                    # TODO (Phase 2): Enhance to use file content/summary/AI tags if available in `data` for each file.
                    if any(keyword.lower() in filename_lower for keyword in keywords):
                        dest_folder = target_dir / folder_name
                        target_file_path = dest_folder / file_path.name

                        counter = 1
                        stem, suffix = file_path.stem, file_path.suffix
                        while target_file_path.exists(): # Handle name conflicts
                            target_file_path = dest_folder / f"{stem}_{counter}{suffix}"
                            counter += 1

                        try:
                            shutil.copy2(file_path, target_file_path)
                            categorized_files_report[folder_name].append(str(target_file_path))
                            self.logger.info(f"Categorized '{file_path.name}' into '{folder_name}'")
                            was_categorized = True
                            break # Move to next file once categorized
                        except Exception as e:
                            self.logger.error(f"Could not copy {file_path.name} to {target_file_path}: {e}", exc_info=True)
                            # Decide: add to uncategorized or mark as error? For now, let it fall to uncategorized if copy fails.

                if not was_categorized:
                    target_file_path = review_folder / file_path.name
                    counter = 1
                    stem, suffix = file_path.stem, file_path.suffix
                    while target_file_path.exists():
                        target_file_path = review_folder / f"{stem}_{counter}{suffix}"
                        counter += 1

                    try:
                        shutil.copy2(file_path, target_file_path)
                        uncategorized_files_report.append(str(target_file_path))
                        self.logger.info(f"Moved '{file_path.name}' to FOR_HUMAN_REVIEW")
                    except Exception as e:
                        self.logger.error(f"Could not copy {file_path.name} to review folder {target_file_path}: {e}", exc_info=True)
                        uncategorized_files_report.append(f"ERROR_COPYING: {file_path.name} - {e}")


        total_categorized_count = sum(len(files) for files in categorized_files_report.values())
        self.logger.info(f"Categorization complete. Processed: {files_processed_count}, Categorized: {total_categorized_count}, Uncategorized: {len(uncategorized_files_report)}.")

        return {
            "plugin": self.name,
            "status": "completed",
            "success": True, # Assuming process completes, even if some files are uncategorized or had copy errors logged within lists
            "summary": {
                "files_processed": files_processed_count,
                "files_categorized": total_categorized_count,
                "files_for_human_review": len(uncategorized_files_report),
                "categories_used": list(categorization_scheme.keys())
            },
            "categorized_files_map": categorized_files_report, # folder_name -> list_of_target_paths
            "uncategorized_file_paths": uncategorized_files_report # list_of_target_paths
        }

    def create_ui_elements(self, parent_widget) -> List[tk.Widget]:
        elements = []
        frame = ttk.Frame(parent_widget)
        frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(frame, text="📁 Categorize Files (using current config)",
                   command=self.run_analysis_ui).pack(side=tk.LEFT, padx=2)
        ttk.Button(frame, text="📋 View Current Categories",
                   command=self.show_categories).pack(side=tk.LEFT, padx=2)

        self.status_label = ttk.Label(frame, text="Evidence Categorization Plugin Ready.")
        self.status_label.pack(side=tk.LEFT, padx=10)
        elements.extend([frame, self.status_label])
        return elements

    def show_categories(self):
        # Display self.current_categorization_scheme
        if not self.current_categorization_scheme:
            messagebox.showinfo("No Scheme", "No categorization scheme has been used or loaded by this plugin yet.")
            return

        categories_text = "Current Evidence Categorization Scheme:\n\n"
        for folder, keywords in self.current_categorization_scheme.items():
            categories_text += f"Category Folder: {folder}\n"
            categories_text += f"  Keywords (for filename matching): {', '.join(keywords) if keywords else 'N/A'}\n\n"

        popup = tk.Toplevel()
        popup.title("Current Categorization Scheme")
        popup.geometry("700x500")
        text_widget = tk.Text(popup, wrap=tk.WORD, font=("Arial", 11))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(tk.END, categories_text)
        text_widget.config(state=tk.DISABLED)

    def run_analysis_ui(self):
        if not (hasattr(self, "core") and self.core and self.core.async_event_loop): # Corrected hasattr
            self.status_label.config(text="Error: Core not fully available.")
            messagebox.showerror("Core Error", "LCAS Core not ready for plugin UI action.")
            return

        self.status_label.config(text="Categorizing (UI triggered)...")

        # For UI-triggered run, we need to get the categorization_scheme.
        # This should ideally come from LCASConfig or a dedicated UI section.
        # For now, let's assume it's in core.config.categorization_scheme
        # or we use a default if not found.
        categorization_scheme_from_config = {}
        if hasattr(self.core.config, 'categorization_scheme') and isinstance(self.core.config.categorization_scheme, dict):
            categorization_scheme_from_config = self.core.config.categorization_scheme
        else:
            # Fallback to a very basic default if not in config for UI run
            self.logger.warning("UI run: 'categorization_scheme' not found in core config. Using a basic default.")
            categorization_scheme_from_config = {
                "IMPORTANT_DOCS": ["important", "key", "critical"],
                "FINANCIAL": ["bank", "statement", "tax", "invoice"]
            }
            # Inform user about fallback?
            messagebox.showinfo("Categorization Info", "Using a default categorization scheme as none was found in the main configuration for this UI action.")


        async def run_and_update():
            source_dir = self.core.config.source_directory
            target_dir = self.core.config.target_directory
            if not source_dir or not target_dir:
                messagebox.showerror("Configuration Missing", "Source and Target directories must be set.")
                self.status_label.config(text="Config missing.")
                return

            result = await self.analyze({
                "source_directory": source_dir,
                "target_directory": target_dir,
                "categorization_scheme": categorization_scheme_from_config
            })

            def update_ui_after_run():
                if result.get("error"):
                    self.status_label.config(text=f"Error: {result['error']}")
                    messagebox.showerror("Categorization Error", result['error'])
                else:
                    summary = result.get("summary", {})
                    msg = f"Categorized: {summary.get('files_categorized',0)}/{summary.get('files_processed',0)}. Review: {summary.get('files_for_human_review',0)}"
                    self.status_label.config(text=msg)
                    messagebox.showinfo("Categorization Complete", msg)

            if hasattr(self.core, 'root') and self.core.root:
                 self.core.root.after(0, update_ui_after_run)
            else:
                self.status_label.config(text="Processing complete (UI ref missing).")

        asyncio.run_coroutine_threadsafe(run_and_update(), self.core.async_event_loop)
