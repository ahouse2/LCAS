#!/usr/bin/env python3
"""
Evidence Categorization Plugin for LCAS
Determines category for evidence files based on content, AI tags, and a provided scheme.
Updates FileAnalysisData instances and outputs a mapping.
"""

import tkinter as tk
from tkinter import ttk
# import shutil # No longer used
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import re
import json # Added import
from dataclasses import asdict # For converting FAD to dict for output

from lcas2.core import AnalysisPlugin, UIPlugin, LCASCore
from lcas2.core.data_models import FileAnalysisData # Import FileAnalysisData

class EvidenceCategorizationPlugin(AnalysisPlugin, UIPlugin):
    """Plugin for determining file categories based on content, AI suggestions, and a dynamic scheme."""

    @property
    def name(self) -> str: return "Evidence Categorization"
    @property
    def version(self) -> str: return "1.3.1" # Version updated
    @property
    def description(self) -> str: return "Categorizes files using AI tags, content/filename keywords from FileAnalysisData, updates FAD instances, and outputs mapping."
    @property
    def dependencies(self) -> List[str]: return ["lcas_ai_wrapper_plugin", "Content Extraction", "Image Analysis"] # Needs comprehensive FAD

    async def initialize(self, core_app: LCASCore) -> bool:
        self.core = core_app
        self.logger = core_app.logger.getChild(self.name)
        self.current_categorization_scheme: Dict[str, Dict[str, Any]] = {}
        self.logger.info(f"{self.name} initialized.")
        return True

    async def cleanup(self) -> None: self.logger.info(f"{self.name} cleaned up.")

    def _text_contains_keywords(self, text: Optional[str], keywords: List[str]) -> bool:
        if not text or not keywords: return False
        text_lower = text.lower()
        # Ensure keywords are strings
        return any(re.search(r'\b' + re.escape(str(kw).lower()) + r'\b', text_lower) for kw in keywords if isinstance(kw, str))


    async def analyze(self, data: Any) -> Dict[str, Any]:
        processed_files_input_any: Any = data.get("processed_files", {})
        if not isinstance(processed_files_input_any, dict):
            self.logger.error(f"Expected 'processed_files' to be a Dict, got {type(processed_files_input_any)}.")
            return {"plugin": self.name, "status": "error", "success": False, "message": "Invalid 'processed_files' format."}
        processed_files_input: Dict[str, Any] = processed_files_input_any # Now known to be a dict

        categorization_scheme: Dict[str, Dict[str, Any]] = data.get("categorization_scheme", {})
        self.current_categorization_scheme = categorization_scheme

        if not processed_files_input:
            return {"plugin": self.name, "status": "no_data", "success": False, "message": "No 'processed_files' (FileAnalysisData) provided."}
        if not categorization_scheme:
            self.logger.warning("No categorization scheme. Files will be mapped to FOR_HUMAN_REVIEW.")
            # Provide a minimal default scheme if none is given
            categorization_scheme = {"FOR_HUMAN_REVIEW": {"priority": 1000, "description": "Files needing manual categorization"}}

        file_to_category_mapping: Dict[str, Dict[str, str]] = {}
        files_processed_count = 0; categorized_count = 0; human_review_count = 0

        output_fad_dict: Dict[str, FileAnalysisData] = {} # To store FAD instances for output

        sorted_categories = sorted(categorization_scheme.items(), key=lambda item: item[1].get("priority", 99))

        for original_file_path_str, fad_object_or_dict in processed_files_input.items():
            files_processed_count += 1
            fad_instance: Optional[FileAnalysisData] = None
            if isinstance(fad_object_or_dict, FileAnalysisData):
                fad_instance = fad_object_or_dict
            elif isinstance(fad_object_or_dict, dict):
                try:
                    fad_instance = FileAnalysisData(**fad_object_or_dict)
                except TypeError as te:
                    self.logger.warning(f"Could not cast dict to FAD for {original_file_path_str}: {te}")
                    fad_instance = FileAnalysisData(file_path=original_file_path_str, file_name=Path(original_file_path_str).name)
                    fad_instance.error_log.append(f"Failed to cast input dict to FileAnalysisData: {te}")

            if not fad_instance: # If still None after attempts
                file_to_category_mapping[original_file_path_str] = {"category_folder_name": "FOR_HUMAN_REVIEW", "reason": "Invalid file_data format", "original_filename": Path(original_file_path_str).name}
                human_review_count += 1; continue

            output_fad_dict[original_file_path_str] = fad_instance # Add to output dict for return

            file_name_lower = fad_instance.file_name.lower() if fad_instance.file_name else ""

            texts_to_search = [fad_instance.content, fad_instance.summary_auto, fad_instance.ai_summary, fad_instance.ocr_text_from_images]
            searchable_text = "\n".join(t for t in texts_to_search if t)

            all_ai_tags_for_file = set(t.lower() for t in (fad_instance.ai_tags or []))
            if fad_instance.ai_suggested_category: all_ai_tags_for_file.add(fad_instance.ai_suggested_category.lower())

            assigned_category_name: Optional[str] = None
            categorization_reason = "No matching criteria"

            for folder_name_key, criteria in sorted_categories:
                if not isinstance(criteria, dict): continue
                current_category_target_name = folder_name_key

                ai_tags_to_match = [str(t).lower() for t in criteria.get("ai_tags", []) if isinstance(t, str)]
                if ai_tags_to_match and any(tag in all_ai_tags_for_file for tag in ai_tags_to_match):
                    assigned_category_name = current_category_target_name
                    categorization_reason = f"Matched AI tag(s): {', '.join(t for t in ai_tags_to_match if t in all_ai_tags_for_file)}"
                    break

                content_keywords_to_match = criteria.get("content_keywords", [])
                if content_keywords_to_match and self._text_contains_keywords(searchable_text, content_keywords_to_match):
                    assigned_category_name = current_category_target_name
                    matched_kws = [kw for kw in content_keywords_to_match if isinstance(kw, str) and re.search(r'\b' + re.escape(kw.lower()) + r'\b', searchable_text.lower())]
                    categorization_reason = f"Matched content keyword(s): {', '.join(matched_kws)}"
                    break

                filename_keywords_to_match = criteria.get("filename_keywords", [])
                if filename_keywords_to_match and any(str(kw).lower() in file_name_lower for kw in filename_keywords_to_match if isinstance(kw,str)):
                    assigned_category_name = current_category_target_name
                    matched_kws = [kw for kw in filename_keywords_to_match if isinstance(kw,str) and kw.lower() in file_name_lower]
                    categorization_reason = f"Matched filename keyword(s): {', '.join(matched_kws)}"
                    break

            final_category_folder_name = assigned_category_name if assigned_category_name else "FOR_HUMAN_REVIEW"
            if assigned_category_name: categorized_count +=1
            else: human_review_count +=1; categorization_reason = "Sent to human review (no criteria matched)"

            fad_instance.assigned_category_folder_name = final_category_folder_name
            fad_instance.categorization_reason = categorization_reason

            file_to_category_mapping[original_file_path_str] = {
                "category_folder_name": final_category_folder_name,
                "reason": categorization_reason,
                "original_filename": fad_instance.file_name if fad_instance.file_name else Path(original_file_path_str).name
            }
            self.logger.info(f"File '{fad_instance.file_name}': Mapped to category '{final_category_folder_name}'. Reason: {categorization_reason}")

        self.logger.info(f"Categorization mapping complete. Processed: {files_processed_count}, Mapped: {categorized_count}, Review: {human_review_count}.")
        return {
            "plugin": self.name, "status": "completed", "success": True,
            "summary": {"files_processed": files_processed_count, "files_categorized_mapped": categorized_count, "files_for_human_review_mapped": human_review_count, "categories_in_scheme": list(categorization_scheme.keys()) },
            "file_category_mapping": file_to_category_mapping,
            "processed_files_output": {k:asdict(v) for k,v in output_fad_dict.items()}
        }

    def create_ui_elements(self, parent_widget) -> List[tk.Widget]:
        try:
            import tkinter as tk # Keep imports local to UI methods where possible
            from tkinter import ttk
            from tkinter import simpledialog, messagebox
        except ImportError:
            self.logger.warning("Tkinter not available, UI elements cannot be created.")
            return []

        elements = []
        frame = ttk.Frame(parent_widget)
        frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(frame, text="📁 Determine Categories (uses current FADs)", command=self.run_analysis_ui).pack(side=tk.LEFT, padx=2)
        ttk.Button(frame, text="📋 View Scheme", command=self.show_categories).pack(side=tk.LEFT, padx=2)

        self.status_label = ttk.Label(frame, text="Ready.")
        self.status_label.pack(side=tk.LEFT, padx=10)
        elements.append(frame)
        return elements

    def show_categories(self):
        scheme_str = json.dumps(self.current_categorization_scheme, indent=2)
        if not scheme_str or scheme_str == '{}': scheme_str = "No scheme loaded or scheme is empty."

        try:
            import tkinter as tk
            from tkinter import messagebox # Ensure messagebox is imported here too

            top = tk.Toplevel()
            top.title("Current Categorization Scheme")
            txt = tk.Text(top, wrap=tk.WORD, height=20, width=60)
            txt.insert(tk.END, scheme_str)
            txt.config(state=tk.DISABLED)
            txt_scroll = ttk.Scrollbar(top, command=txt.yview)
            txt['yscrollcommand'] = txt_scroll.set
            txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            txt_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        except Exception as e:
             self.logger.error(f"Failed to display categorization scheme UI: {e}")
             messagebox.showinfo("Categorization Scheme", scheme_str) # Fallback


    def run_analysis_ui(self):
        if not (hasattr(self, "core") and self.core and self.core.async_event_loop):
            if hasattr(self, 'status_label'): self.status_label.config(text="Error: Core not ready.")
            else: self.logger.error("UI run failed: Core not ready.")
            return

        if hasattr(self, 'status_label'): self.status_label.config(text="Determining categories (UI)...")

        processed_files_for_ui = {}
        if hasattr(self.core, 'analysis_results'):
            pd_results = self.core.analysis_results.get("Pattern Discovery", {}).get("result", {})
            if pd_results.get("success") and isinstance(pd_results.get("processed_files_output"), dict):
                processed_files_for_ui = pd_results["processed_files_output"]

            if not processed_files_for_ui:
                ai_wrapper_results = self.core.analysis_results.get("lcas_ai_wrapper_plugin", {}).get("result", {})
                if ai_wrapper_results.get("success") and isinstance(ai_wrapper_results.get("processed_files_output"), dict):
                    processed_files_for_ui = ai_wrapper_results["processed_files_output"]
                elif ai_wrapper_results.get("success") and isinstance(ai_wrapper_results.get("ai_enriched_processed_files"), dict):
                    processed_files_for_ui = ai_wrapper_results["ai_enriched_processed_files"]

            if not processed_files_for_ui:
                content_ext_results = self.core.analysis_results.get("Content Extraction", {}).get("result", {})
                if content_ext_results.get("success") and isinstance(content_ext_results.get("processed_files_output"), dict):
                     processed_files_for_ui = content_ext_results["processed_files_output"]

        if not processed_files_for_ui:
            messagebox.showerror("Input Missing", "No 'processed_files' found in prior results from relevant plugins.");
            if hasattr(self, 'status_label'): self.status_label.config(text="Error: No processed_files.")
            return

        processed_files_fad_instances = {}
        for k,v_dict in processed_files_for_ui.items():
            if isinstance(v_dict, dict):
                try: processed_files_fad_instances[k] = FileAnalysisData(**v_dict)
                except Exception as e: self.logger.warning(f"Could not cast dict to FAD for {k} in UI run: {e}"); continue
            elif isinstance(v_dict, FileAnalysisData):
                 processed_files_fad_instances[k] = v_dict
            else: self.logger.warning(f"Item {k} is not a dict or FAD, skipping.")

        if not processed_files_fad_instances :
            messagebox.showerror("Input Error", "Could not form FileAnalysisData instances from prior results.");
            if hasattr(self, 'status_label'): self.status_label.config(text="Error: FAD conversion failed.")
            return

        categorization_scheme_from_config = {}
        if hasattr(self.core.config, 'categorization_scheme') and isinstance(self.core.config.categorization_scheme, dict):
            categorization_scheme_from_config = self.core.config.categorization_scheme
        else:
            self.logger.warning("No categorization_scheme found in LCASConfig or it's not a dict. Using empty scheme for UI run.")
            # Ensure messagebox is imported for this path too
            try: from tkinter import messagebox except ImportError: pass
            messagebox.showwarning("Scheme Missing", "No categorization scheme found in configuration. Defaulting to 'FOR_HUMAN_REVIEW'.")

        target_dir = self.core.config.target_directory if hasattr(self.core.config, 'target_directory') else "."

        async def run_and_update():
            result = await self.analyze({"processed_files": processed_files_fad_instances,
                                         "target_directory": target_dir,
                                         "categorization_scheme": categorization_scheme_from_config })
            def update_ui_callback():
                if hasattr(self, 'status_label'):
                    if result.get("success"): self.status_label.config(text="Categorization complete (UI).")
                    else: self.status_label.config(text=f"Categorization error (UI): {result.get('message','Unknown')}")
                messagebox.showinfo("Categorization Result", f"Categorization finished. Status: {result.get('status')}\nFiles Processed: {result.get('summary',{}).get('files_processed','N/A')}\nFiles Categorized: {result.get('summary',{}).get('files_categorized_mapped','N/A')}")

            if hasattr(self.core, 'root') and self.core.root: self.core.root.after(0, update_ui_callback)
            elif hasattr(self.core, 'main_loop') and self.core.main_loop : self.core.main_loop.call_soon_threadsafe(update_ui_callback)
            else: self.logger.info("UI update callback skipped (no root or main_loop).")

        asyncio.run_coroutine_threadsafe(run_and_update(), self.core.async_event_loop)
