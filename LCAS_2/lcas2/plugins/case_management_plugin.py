#!/usr/bin/env python3
"""
Case Management Plugin for LCAS
Organizes files into a hierarchical folder structure based on categorization and legal theories.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import shutil
import asyncio
import re # For sanitizing folder names
from dataclasses import dataclass, asdict, field
from collections import defaultdict # Added for file_to_theories_map

from lcas2.core import AnalysisPlugin, LCASCore, LCASConfig

logger = logging.getLogger(__name__)

@dataclass
class FileOperationDetail:
    original_path: str
    new_path: str
    status: str
    reason: Optional[str] = None
    theory_applied: Optional[str] = None # New field

class CaseManagementPlugin(AnalysisPlugin):
    """
    Manages the case file structure, organizing files based on categorization and theories.
    Phase 2: Integrates legal theories for a hierarchical structure.
    """

    @property
    def name(self) -> str: return "Case Management"
    @property
    def version(self) -> str: return "0.2.0" # Version updated
    @property
    def description(self) -> str: return "Organizes files into theory-based hierarchical folders using categorization data."
    @property
    def dependencies(self) -> List[str]:
        return ["Evidence Categorization", "Pattern Discovery"]

    async def initialize(self, core_app: LCASCore) -> bool:
        self.core = core_app
        self.logger = core_app.logger.getChild(self.name)
        # Default base folders if no theories apply or for general categorization
        self.general_evidence_folder_name = "GENERAL_EVIDENCE"
        self.logger.info(f"{self.name} initialized.")
        return True

    async def cleanup(self) -> None:
        self.logger.info(f"{self.name} cleaned up.")
        pass

    def _sanitize_foldername(self, name: str) -> str:
        """Sanitizes a string to be a valid folder name."""
        if not name: return "Unnamed_Folder"
        # Remove invalid characters (simplified: keeping alphanumeric, underscore, hyphen)
        name = re.sub(r'[^a-zA-Z0-9_\-\s]', '', name)
        # Replace spaces with underscores
        name = re.sub(r'\s+', '_', name)
        # Truncate if too long
        return name[:100] if len(name) > 100 else name

    async def analyze(self, data: Any) -> Dict[str, Any]:
        """
        Creates hierarchical folder structure based on theories and categories, then organizes files.

        Expected in data:
            - 'target_directory': str
            - 'file_category_mapping': Dict[str, Dict[str,str]]
                {orig_path: {"category_folder_name": "...", "reason": ..., "original_filename": ...}}
            - 'potential_theories': Optional[List[Dict]]
                (List of dicts, each representing a LegalTheory, must include 'theory_name' and 'evidence_files' list)
            - 'case_name': Optional[str]
        """
        target_dir_str: Optional[str] = data.get("target_directory")
        file_category_mapping: Dict[str, Dict[str,str]] = data.get("file_category_mapping", {})
        potential_theories_input: List[Dict[str, Any]] = data.get("potential_theories", [])

        if not target_dir_str:
            return {"plugin": self.name, "status": "error", "success": False, "error": "Target directory not provided."}

        target_dir = Path(target_dir_str)
        case_files_root = target_dir / "CASE_FILES"
        case_files_root.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Starting Phase 2 case file organization in: {case_files_root}")

        operations_summary: List[FileOperationDetail] = []
        folders_created_set = set()
        files_organized_count = 0
        errors_count = 0

        # Pre-process theories: create a mapping from original_file_path to a list of theory names it supports
        file_to_theories_map: Dict[str, List[str]] = defaultdict(list)
        valid_theories_for_folders: Dict[str, Path] = {} # Sanitized theory name -> Path object

        if potential_theories_input:
            for theory_dict in potential_theories_input:
                if isinstance(theory_dict, dict) and theory_dict.get("theory_name") and isinstance(theory_dict.get("evidence_files"), list):
                    theory_name_original = theory_dict["theory_name"]
                    sanitized_theory_name = "THEORY_" + self._sanitize_foldername(theory_name_original)
                    theory_folder_path = case_files_root / sanitized_theory_name
                    valid_theories_for_folders[sanitized_theory_name] = theory_folder_path

                    for evidence_file_path_str in theory_dict["evidence_files"]:
                        # Ensure the path from theory is stored consistently (e.g. as string)
                        file_to_theories_map[str(evidence_file_path_str)].append(sanitized_theory_name)
                else:
                    self.logger.warning(f"Skipping malformed theory: {str(theory_dict)[:100]}")

        # Create theory folders
        for theory_path in valid_theories_for_folders.values():
            try:
                if not theory_path.exists():
                    await asyncio.to_thread(theory_path.mkdir, parents=True, exist_ok=True)
                    folders_created_set.add(theory_path.name)
            except Exception as e:
                self.logger.error(f"Could not create theory folder {theory_path}: {e}", exc_info=True)
                # Continue, files for this theory might go to general or error out.

        # Create general evidence folder if no theories or for files not fitting theories
        general_evidence_path = case_files_root / self._sanitize_foldername(self.general_evidence_folder_name)

        for original_path_str, mapping_info in file_category_mapping.items():
            original_file_path = Path(original_path_str)
            category_folder_name_raw = mapping_info.get("category_folder_name", "FOR_HUMAN_REVIEW")
            category_folder_name_sanitized = self._sanitize_foldername(category_folder_name_raw)
            original_filename = mapping_info.get("original_filename", original_file_path.name)

            # Determine base path: under a theory or general?
            # Use str(original_file_path) for map lookup if keys are stored as strings
            applicable_theories = file_to_theories_map.get(str(original_file_path), [])

            base_path_for_category = general_evidence_path
            applied_theory_name = None

            if applicable_theories:
                # Simple strategy: use the first applicable theory folder
                chosen_theory_sanitized_name = applicable_theories[0]
                base_path_for_category = valid_theories_for_folders.get(chosen_theory_sanitized_name, general_evidence_path)
                applied_theory_name = chosen_theory_sanitized_name
                if len(applicable_theories) > 1:
                    self.logger.info(f"File '{original_filename}' applies to multiple theories ({applicable_theories}), placed under '{chosen_theory_sanitized_name}'.")

            destination_category_path = base_path_for_category / category_folder_name_sanitized

            try:
                if not destination_category_path.exists():
                    await asyncio.to_thread(destination_category_path.mkdir, parents=True, exist_ok=True)
                    folders_created_set.add(str(destination_category_path.relative_to(case_files_root)))

                target_file_path = destination_category_path / original_filename
                counter = 1
                stem, suffix = Path(original_filename).stem, Path(original_filename).suffix
                while await asyncio.to_thread(target_file_path.exists):
                    target_file_path = destination_category_path / f"{stem}_{counter}{suffix}"
                    counter += 1

                if not await asyncio.to_thread(original_file_path.exists):
                    self.logger.warning(f"Original file not found for copy: {original_path_str}")
                    operations_summary.append(FileOperationDetail(original_path_str, str(target_file_path), "error", "Original file not found", applied_theory_name))
                    errors_count += 1
                    continue

                await asyncio.to_thread(shutil.copy2, original_file_path, target_file_path)
                self.logger.info(f"Copied '{original_filename}' to '{destination_category_path.relative_to(target_dir)}'")
                operations_summary.append(FileOperationDetail(original_path_str, str(target_file_path), "copied", mapping_info.get("reason"), applied_theory_name))
                files_organized_count += 1

            except Exception as e:
                self.logger.error(f"Error organizing file {original_filename} into {destination_category_path}: {e}", exc_info=True)
                operations_summary.append(FileOperationDetail(original_path_str, str(destination_category_path / original_filename), "error", str(e), applied_theory_name))
                errors_count += 1

        # Ensure GENERAL_EVIDENCE folder is noted if used, even if not explicitly in folders_created_set
        if any(op.new_path.startswith(str(general_evidence_path)) for op in operations_summary):
            folders_created_set.add(general_evidence_path.name)

        self.logger.info(f"Hierarchical organization complete. Organized: {files_organized_count}. Errors: {errors_count}.")
        return {
            "plugin": self.name,
            "status": "completed" if errors_count == 0 else "completed_with_errors",
            "success": errors_count == 0,
            "summary": {
                "files_organized": files_organized_count,
                "folders_created_or_used": len(folders_created_set),
                "organization_errors": errors_count,
                "case_files_root": str(case_files_root),
                "theories_applied_count": len(valid_theories_for_folders)
            },
            "operations_details": [asdict(op) for op in operations_summary]
        }

    def create_ui_elements(self, parent_widget) -> List[Any]: # Changed to List[Any] for tk flexibility
        try:
            import tkinter as tk
            from tkinter import ttk
        except ImportError:
            self.logger.warning("Tkinter not available, UI elements for CaseManagementPlugin cannot be created.")
            return []

        frame = ttk.Frame(parent_widget)
        frame.pack(fill=tk.X, padx=5, pady=2)
        label = ttk.Label(frame, text=f"{self.name}: Organizes files. Runs post-categorization/pattern discovery.")
        label.pack(side=tk.LEFT, padx=2)
        return [frame]
