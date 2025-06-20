#!/usr/bin/env python3
"""
File Ingestion Plugin for LCAS
Preserves original files, creates working copies, and verifies integrity.
"""

import tkinter as tk
from tkinter import ttk # Keep for UI part, though UI part might be simplified/removed later
import shutil
import asyncio
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import hashlib # Added for hashing

from lcas2.core import AnalysisPlugin, UIPlugin


class FileIngestionPlugin(AnalysisPlugin, UIPlugin):
    """Plugin for ingesting, preserving original files, and verifying integrity."""

    @property
    def name(self) -> str:
        return "File Ingestion"

    @property
    def version(self) -> str:
        return "1.1.0" # Version updated

    @property
    def description(self) -> str:
        return "Preserves original files, creates working copies, and verifies integrity using SHA256 hashing."

    @property
    def dependencies(self) -> List[str]:
        return []

    async def initialize(self, core_app) -> bool:
        self.core = core_app
        self.logger = core_app.logger.getChild(self.name)
        self.logger.info("FileIngestionPlugin initialized.")
        return True

    async def cleanup(self) -> None:
        self.logger.info("FileIngestionPlugin cleaned up.")
        pass

    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                # Read and update hash string value in blocks of 4K
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.logger.error(f"Error calculating hash for {file_path}: {e}", exc_info=True)
            return ""

    async def analyze(self, data: Any) -> Dict[str, Any]:
        """Ingest, preserve files, and verify their integrity."""
        source_dir_str = data.get("source_directory", "")
        target_dir_str = data.get("target_directory", "")

        if not source_dir_str:
            self.logger.error("Source directory not provided.")
            return {"error": "Source directory not provided", "success": False, "files_details": []}
        if not target_dir_str:
            self.logger.error("Target directory not provided.")
            return {"error": "Target directory not provided", "success": False, "files_details": []}

        source_dir = Path(source_dir_str)
        target_dir = Path(target_dir_str)

        if not source_dir.exists() or not source_dir.is_dir():
            self.logger.error(f"Source directory does not exist or is not a directory: {source_dir}")
            return {"error": f"Source directory not found: {source_dir}", "success": False, "files_details": []}

        backup_dir = target_dir / "00_ORIGINAL_FILES_BACKUP"
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Could not create backup directory {backup_dir}: {e}", exc_info=True)
            return {"error": f"Failed to create backup directory: {e}", "success": False, "files_details": []}

        files_details = []
        total_files_scanned = 0
        files_successfully_copied = 0
        files_with_hash_mismatch = 0
        files_failed_to_copy = 0

        self.logger.info(f"Starting file ingestion from {source_dir} to {backup_dir}")

        for file_path in source_dir.rglob("*"):
            if file_path.is_file():
                total_files_scanned += 1
                detail = {
                    "original_path": str(file_path),
                    "backup_path": "",
                    "size": 0,
                    "original_hash": "",
                    "backup_hash": "",
                    "status": "pending",
                    "error_message": ""
                }

                try:
                    rel_path = file_path.relative_to(source_dir)
                    backup_file_path = backup_dir / rel_path
                    detail["backup_path"] = str(backup_file_path)
                    detail["size"] = file_path.stat().st_size

                    backup_file_path.parent.mkdir(parents=True, exist_ok=True)

                    self.logger.debug(f"Copying {file_path} to {backup_file_path}")
                    shutil.copy2(file_path, backup_file_path) # copy2 preserves metadata

                    detail["original_hash"] = self._calculate_hash(file_path)
                    detail["backup_hash"] = self._calculate_hash(backup_file_path)

                    if detail["original_hash"] and detail["backup_hash"] and detail["original_hash"] == detail["backup_hash"]:
                        detail["status"] = "copied_verified"
                        files_successfully_copied += 1
                        self.logger.info(f"Successfully copied and verified {file_path.name}")
                    elif not detail["original_hash"] or not detail["backup_hash"]:
                        detail["status"] = "copy_error_hash_calculation"
                        detail["error_message"] = "Failed to calculate hash for original or backup."
                        self.logger.warning(f"Copied {file_path.name}, but failed to calculate hashes for verification.")
                        # Still counts as copied, but with issues.
                        files_successfully_copied +=1 # Or a different counter for 'copied_unverified'
                    else:
                        detail["status"] = "hash_mismatch"
                        files_with_hash_mismatch += 1
                        self.logger.warning(f"Hash mismatch for {file_path.name}. Original: {detail['original_hash']}, Backup: {detail['backup_hash']}")

                except Exception as e:
                    self.logger.error(f"Failed to copy or verify {file_path.name}: {e}", exc_info=True)
                    detail["status"] = "error_copying"
                    detail["error_message"] = str(e)
                    files_failed_to_copy += 1

                files_details.append(detail)

        self.logger.info(f"File ingestion summary: Scanned: {total_files_scanned}, Copied & Verified: {files_successfully_copied - files_with_hash_mismatch}, Hash Mismatches: {files_with_hash_mismatch}, Failed Copies: {files_failed_to_copy}")

        return {
            "plugin": self.name,
            "status": "completed" if files_failed_to_copy == 0 else "completed_with_errors",
            "success": files_failed_to_copy == 0, # Overall success if no outright copy failures
            "summary": {
                "total_files_scanned": total_files_scanned,
                "files_successfully_copied": files_successfully_copied,
                "files_verified_ok": files_successfully_copied - files_with_hash_mismatch - len([d for d in files_details if d["status"] == "copy_error_hash_calculation" and d["original_hash"] and d["backup_hash"]]), # count only if both hashes were calc'd for mismatch
                "files_hash_mismatch": files_with_hash_mismatch,
                "files_failed_to_copy_or_hash": files_failed_to_copy + len([d for d in files_details if d["status"] == "copy_error_hash_calculation"])
            },
            "files_details": files_details,
            "backup_directory": str(backup_dir)
        }

    def create_ui_elements(self, parent_widget) -> List[tk.Widget]:
        # UI remains simple for now, as core GUI will trigger this plugin.
        # This UI part could be enhanced to show results of last run.
        elements = []
        frame = ttk.Frame(parent_widget)
        frame.pack(fill=tk.X, padx=5, pady=2)

        # Button might be less relevant if core GUI handles triggering.
        # Consider changing this to a status display or configuration specific to this plugin.
        # For now, keep it but note its limited role.
        button = ttk.Button(frame, text="🔒 Preserve Files (Standalone Trigger)",
                   command=self.run_analysis_ui)
        button.pack(side=tk.LEFT, padx=2)
        if not hasattr(self.core, 'event_loop'): # Disable if core not fully ready for this UI path
            button.configure(state="disabled")


        self.status_label = ttk.Label(frame, text="File Ingestion Plugin Ready.")
        self.status_label.pack(side=tk.LEFT, padx=10)

        elements.extend([frame, self.status_label])
        return elements

    def run_analysis_ui(self):
        # This UI execution path is secondary to LCASCore triggering.
        # It's a standalone trigger from a potential plugin-specific UI area.
        if not (hasattr(self, 'core') and self.core and self.core.async_event_loop):
            self.status_label.config(text="Error: Core not available or not fully initialized.")
            messagebox.showerror("Core Error", "LCAS Core not ready for plugin UI action.")
            return

        self.status_label.config(text="Processing ingestion (UI triggered)...")
        self.core.update_status("File Ingestion (UI Trigger) started...") # Example of calling core's status update

        async def run_and_update():
            # Ensure config has values, or prompt user if this UI path is taken
            source_dir = self.core.config.source_directory
            target_dir = self.core.config.target_directory
            if not source_dir or not target_dir:
                messagebox.showerror("Configuration Missing", "Source and Target directories must be set in main configuration.")
                self.status_label.config(text="Configuration missing.")
                return

            result = await self.analyze({
                "source_directory": source_dir,
                "target_directory": target_dir,
                "case_name": self.core.config.case_name
            })

            # Update UI in main thread
            def update_ui_after_run():
                if result.get("error"):
                    self.status_label.config(text=f"Error: {result['error']}")
                    messagebox.showerror("Ingestion Error", result['error'])
                else:
                    summary = result.get("summary", {})
                    msg = f"Ingestion complete. Copied: {summary.get('files_successfully_copied',0)}, Verified: {summary.get('files_verified_ok',0)}"
                    self.status_label.config(text=msg)
                    messagebox.showinfo("Ingestion Complete", msg)

            # Ensure UI updates happen on the main Tkinter thread
            if hasattr(self.core, 'root') and self.core.root: # Assuming core has a reference to the root Tk window
                 self.core.root.after(0, update_ui_after_run)
            else: # Fallback if root tk reference isn't available via core (less ideal)
                self.status_label.config(text="Processing complete, check logs (UI ref missing).")


        asyncio.run_coroutine_threadsafe(run_and_update(), self.core.async_event_loop)
