#!/usr/bin/env python3
"""
Hash Generation Plugin for LCAS
Generates specified cryptographic hashes for all files in a directory to ensure integrity.
"""

import tkinter as tk
from tkinter import ttk
import hashlib
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Union
from datetime import datetime

from lcas2.core import AnalysisPlugin, UIPlugin


class HashGenerationPlugin(AnalysisPlugin, UIPlugin):
    """Plugin for generating cryptographic file hashes for integrity verification."""

    SUPPORTED_HASHES = ["sha256", "md5", "sha1", "sha512"]

    @property
    def name(self) -> str:
        return "Hash Generation"

    @property
    def version(self) -> str:
        return "1.1.0" # Version updated

    @property
    def description(self) -> str:
        return f"Generates selected cryptographic hashes (e.g., {', '.join(self.SUPPORTED_HASHES)}) for files."

    @property
    def dependencies(self) -> List[str]:
        return []

    async def initialize(self, core_app) -> bool:
        self.core = core_app
        self.logger = core_app.logger.getChild(self.name)
        self.logger.info("HashGenerationPlugin initialized.")
        return True

    async def cleanup(self) -> None:
        self.logger.info("HashGenerationPlugin cleaned up.")
        pass

    def _calculate_hashes(self, file_path: Path, hash_types: List[str]) -> Dict[str, str]:
        """Calculate specified hashes for a file."""
        calculated_hashes = {}
        for hash_type in hash_types:
            if hash_type not in self.SUPPORTED_HASHES:
                self.logger.warning(f"Unsupported hash type requested: {hash_type}. Skipping for file {file_path}.")
                continue

            try:
                hasher = hashlib.new(hash_type)
                with open(file_path, "rb") as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        hasher.update(byte_block)
                calculated_hashes[hash_type] = hasher.hexdigest()
            except Exception as e:
                self.logger.error(f"Error calculating {hash_type} for {file_path}: {e}", exc_info=True)
                calculated_hashes[hash_type] = "Error calculating hash"
        return calculated_hashes

    async def analyze(self, data: Any) -> Dict[str, Any]:
        """Generate hashes for all files in the specified directory."""
        # This plugin will operate on the source_directory by default,
        # or a directory_to_hash if specified in data (for more flexibility).
        directory_to_hash_str = data.get("directory_to_hash", data.get("source_directory", ""))
        target_dir_str = data.get("target_directory", "") # For report output
        case_name = data.get("case_name", "UnknownCase")

        # Get hash types from config or data, default to sha256
        # Assuming core.config might have a 'default_hash_types' or it's passed in data
        default_hashes_from_config = ["sha256"]
        if hasattr(self.core, 'config') and hasattr(self.core.config, 'hash_generation_types'):
            default_hashes_from_config = self.core.config.hash_generation_types

        hash_types_to_generate = data.get("hash_types", default_hashes_from_config)
        # Ensure it's a list and filter for supported types
        if isinstance(hash_types_to_generate, str): # e.g. "sha256,md5"
            hash_types_to_generate = [h.strip() for h in hash_types_to_generate.split(',')]

        valid_hash_types = [ht for ht in hash_types_to_generate if ht in self.SUPPORTED_HASHES]
        if not valid_hash_types:
            valid_hash_types = ["sha256"] # Fallback
            self.logger.warning(f"No valid hash types provided or configured. Defaulting to SHA256.")


        if not directory_to_hash_str:
            self.logger.error("Directory to hash not provided.")
            return {"error": "Directory to hash not provided", "success": False}
        if not target_dir_str:
            self.logger.error("Target directory for reports not provided.")
            return {"error": "Target directory for reports not provided", "success": False}

        directory_to_hash = Path(directory_to_hash_str)
        target_dir = Path(target_dir_str) # For placing reports

        if not directory_to_hash.exists() or not directory_to_hash.is_dir():
            self.logger.error(f"Directory to hash does not exist or is not a directory: {directory_to_hash}")
            return {"error": f"Directory to hash not found: {directory_to_hash}", "success": False}

        file_hashes_data = {}
        files_processed = 0
        files_failed = 0

        self.logger.info(f"Starting hash generation ({', '.join(valid_hash_types)}) for directory: {directory_to_hash}")

        for file_path in directory_to_hash.rglob("*"):
            if file_path.is_file():
                files_processed += 1
                self.logger.debug(f"Processing file: {file_path}")
                try:
                    hashes = self._calculate_hashes(file_path, valid_hash_types)

                    rel_path_str = str(file_path.relative_to(directory_to_hash))
                    file_hashes_data[rel_path_str] = {
                        "hashes": hashes,
                        "size": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                        "full_path": str(file_path)
                    }
                except Exception as e:
                    files_failed +=1
                    self.logger.error(f"Failed to process hashes for {file_path}: {e}", exc_info=True)
                    file_hashes_data[str(file_path.relative_to(directory_to_hash))] = {
                        "hashes": {ht: "Error" for ht in valid_hash_types}, "error": str(e)
                    }

        report_filename_base = f"{case_name}_file_hashes_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        json_report_path = (target_dir / "REPORTS_LCAS" / "HASH_REPORTS" / (report_filename_base + ".json")).resolve()
        txt_report_path = (target_dir / "REPORTS_LCAS" / "HASH_REPORTS" / (report_filename_base + ".txt")).resolve()

        json_report_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(json_report_path, 'w') as f:
                json.dump(file_hashes_data, f, indent=2)
            self.logger.info(f"Hash JSON report saved to {json_report_path}")
        except Exception as e:
            self.logger.error(f"Failed to save JSON hash report: {e}", exc_info=True)

        try:
            integrity_report_content = self._generate_integrity_report(file_hashes_data, directory_to_hash_str, valid_hash_types, case_name)
            with open(txt_report_path, 'w') as f:
                f.write(integrity_report_content)
            self.logger.info(f"Hash text report saved to {txt_report_path}")
        except Exception as e:
            self.logger.error(f"Failed to save text hash report: {e}", exc_info=True)

        return {
            "plugin": self.name,
            "status": "completed" if files_failed == 0 else "completed_with_errors",
            "success": files_failed == 0,
            "files_processed": files_processed,
            "files_failed": files_failed,
            "hash_types_generated": valid_hash_types,
            "json_report_path": str(json_report_path),
            "txt_report_path": str(txt_report_path),
            "file_hashes_data": file_hashes_data # Contains the actual hash data
        }

    def _generate_integrity_report(self, file_hashes_data: Dict, input_dir: str, hash_types: List[str], case_name: str) -> str:
        report_lines = [
            "FILE INTEGRITY VERIFICATION REPORT",
            "=" * 50,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Case: {case_name}",
            f"Source Directory Scanned: {input_dir}",
            f"Total Files Processed: {len(file_hashes_data)}",
            f"Hash Algorithms Used: {', '.join(hash_types).upper()}",
            "\nPURPOSE: Evidence integrity verification and chain of custody.\n",
            "FILE INVENTORY:",
            "-" * 20
        ]

        for file_path_str, file_info in file_hashes_data.items():
            report_lines.append(f"\nFile: {file_path_str}")
            for hash_type, hash_value in file_info.get("hashes", {}).items():
                report_lines.append(f"  {hash_type.upper()}: {hash_value}")
            report_lines.append(f"  Size: {file_info.get('size', 'N/A'):,} bytes")
            report_lines.append(f"  Modified: {file_info.get('modified', 'N/A')}")
            if file_info.get("error"):
                report_lines.append(f"  ERROR: {file_info['error']}")

        report_lines.extend([
            "\n\nVERIFICATION INSTRUCTIONS:",
            "-" * 30,
            "To verify file integrity, recalculate the specified hashes and compare with this report.",
            "Any discrepancy indicates potential file modification or corruption.",
            "This report serves as cryptographic proof of file state at the time of analysis."
        ])
        return "\n".join(report_lines)

    def create_ui_elements(self, parent_widget) -> List[tk.Widget]:
        # Simplified UI for now, could be expanded with hash type selection later
        elements = []
        frame = ttk.Frame(parent_widget)
        frame.pack(fill=tk.X, padx=5, pady=2)

        # This button would trigger analysis on the currently configured source_directory
        # or a directory specified via a new UI element in this plugin's frame.
        ttk.Button(frame, text="🔐 Generate File Hashes (Current Source Dir)",
                   command=self.run_analysis_ui).pack(side=tk.LEFT, padx=2)

        ttk.Button(frame, text="📋 View Last Hash Report (JSON)",
                   command=self.view_hash_report).pack(side=tk.LEFT, padx=2) # Assumes report path is stored or known

        self.status_label = ttk.Label(frame, text="Hash Generation Plugin Ready.")
        self.status_label.pack(side=tk.LEFT, padx=10)

        elements.extend([frame, self.status_label])
        return elements

    def view_hash_report(self):
        if not (hasattr(self, 'core') and self.core and self.core.config):
            messagebox.showerror("Error", "Core or configuration not available.")
            return

        # Attempt to get the path from the last analysis result for this plugin
        last_result = self.core.get_analysis_result(self.name)
        json_report_path_str = None
        if last_result and isinstance(last_result, dict):
            json_report_path_str = last_result.get("json_report_path")

        if not json_report_path_str or not Path(json_report_path_str).exists():
            # Fallback: try to guess from target_directory if no specific report path found
            # This part is tricky as multiple reports can exist. For simplicity, this UI might need
            # to list available reports or the user navigates manually.
            # For now, we'll just say "not found" if not in last result.
            messagebox.showwarning("No Report", "No specific hash report found from last run, or path is invalid. Please run hash generation first or check the reports directory.")
            return

        json_report_path = Path(json_report_path_str)
        popup = tk.Toplevel()
        popup.title(f"File Hash Report - {json_report_path.name}")
        popup.geometry("900x700")

        frame = ttk.Frame(popup)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget = tk.Text(frame, wrap=tk.WORD, font=("Courier New", 10))
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        try:
            with open(json_report_path, 'r', encoding='utf-8') as f:
                # Display JSON content directly, or format it nicely
                # For now, pretty print JSON
                content = json.dumps(json.load(f), indent=2)
            text_widget.insert(tk.END, content)
        except Exception as e:
            text_widget.insert(tk.END, f"Error loading hash report from {json_report_path}: {e}")

        text_widget.config(state=tk.DISABLED)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)


    def run_analysis_ui(self):
        if not (hasattr(self, 'core') and self.core and self.core.async_event_loop):
            self.status_label.config(text="Error: Core not fully available.")
            messagebox.showerror("Core Error", "LCAS Core not ready for plugin UI action.")
            return

        self.status_label.config(text="Generating hashes (UI triggered)...")
        self.core.update_status("Hash Generation (UI Trigger) started...")


        async def run_and_update():
            source_dir = self.core.config.source_directory # Default to main source_dir
            target_dir = self.core.config.target_directory # For reports
            case_name = self.core.config.case_name

            if not source_dir or not target_dir:
                messagebox.showerror("Configuration Missing", "Source and Target directories must be set in main configuration.")
                self.status_label.config(text="Configuration missing for hash generation.")
                return

            # Example: use default hash types configured in LCASConfig or just sha256
            hash_types = getattr(self.core.config, 'hash_generation_types', ['sha256'])

            result = await self.analyze({
                "directory_to_hash": source_dir,
                "target_directory": target_dir,
                "case_name": case_name,
                "hash_types": hash_types
            })

            def update_ui_after_run():
                if result.get("error"):
                    self.status_label.config(text=f"Error: {result['error']}")
                    messagebox.showerror("Hash Gen Error", result['error'])
                else:
                    msg = f"Hashed {result.get('files_processed',0)} files. Types: {', '.join(result.get('hash_types_generated',[]))}. Errors: {result.get('files_failed',0)}."
                    self.status_label.config(text=msg)
                    if result.get('success', False):
                        messagebox.showinfo("Hashing Complete", msg + f"\nReports in: {Path(result.get('json_report_path','')).parent}")
                    else:
                        messagebox.showwarning("Hashing Issues", msg + f"\nReports in: {Path(result.get('json_report_path','')).parent}")

            if hasattr(self.core, 'root') and self.core.root:
                 self.core.root.after(0, update_ui_after_run)
            else:
                self.status_label.config(text="Processing complete, check logs (UI ref missing).")

        asyncio.run_coroutine_threadsafe(run_and_update(), self.core.async_event_loop)
