#!/usr/bin/env python3
"""
Hash Generation Plugin for LCAS
Generates SHA256 hashes for all files to ensure integrity
"""

import tkinter as tk
from tkinter import ttk
import hashlib
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

from lcas_core import AnalysisPlugin, UIPlugin

class HashGenerationPlugin(AnalysisPlugin, UIPlugin):
    """Plugin for generating file hashes for integrity verification"""
    
    @property
    def name(self) -> str:
        return "Hash Generation"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Generates SHA256 hashes for all files to ensure integrity"
    
    @property
    def dependencies(self) -> List[str]:
        return []
    
    async def initialize(self, core_app) -> bool:
        self.core = core_app
        self.logger = core_app.logger.getChild(self.name)
        return True
    
    async def cleanup(self) -> None:
        pass
    
    async def analyze(self, data: Any) -> Dict[str, Any]:
        """Generate hashes for all files"""
        source_dir = Path(data.get("source_directory", ""))
        target_dir = Path(data.get("target_directory", ""))
        
        if not source_dir.exists():
            return {"error": "Source directory does not exist"}
        
        file_hashes = {}
        files_processed = 0
        
        for file_path in source_dir.rglob("*"):
            if file_path.is_file():
                try:
                    # Calculate SHA256 hash
                    sha256_hash = hashlib.sha256()
                    with open(file_path, "rb") as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            sha256_hash.update(chunk)
                    
                    rel_path = str(file_path.relative_to(source_dir))
                    file_hashes[rel_path] = {
                        "sha256": sha256_hash.hexdigest(),
                        "size": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                        "full_path": str(file_path)
                    }
                    files_processed += 1
                    
                except Exception as e:
                    self.logger.error(f"Error hashing {file_path}: {e}")
        
        # Save hash report
        hash_report_path = target_dir / "file_integrity_hashes.json"
        hash_report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(hash_report_path, 'w') as f:
            json.dump(file_hashes, f, indent=2)
        
        # Generate integrity report
        integrity_report = self._generate_integrity_report(file_hashes, data)
        report_path = target_dir / "integrity_verification_report.txt"
        with open(report_path, 'w') as f:
            f.write(integrity_report)
        
        return {
            "plugin": self.name,
            "files_processed": files_processed,
            "hash_report_path": str(hash_report_path),
            "integrity_report_path": str(report_path),
            "file_hashes": file_hashes,
            "status": "completed"
        }
    
    def _generate_integrity_report(self, file_hashes: Dict, data: Dict) -> str:
        """Generate a professional integrity verification report"""
        report = "FILE INTEGRITY VERIFICATION REPORT\n"
        report += "=" * 50 + "\n\n"
        report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"Case: {data.get('case_name', 'Unknown')}\n"
        report += f"Source Directory: {data.get('source_directory', 'Unknown')}\n"
        report += f"Total Files Processed: {len(file_hashes)}\n\n"
        
        report += "HASH ALGORITHM: SHA256\n"
        report += "PURPOSE: Evidence integrity verification and chain of custody\n\n"
        
        report += "FILE INVENTORY:\n"
        report += "-" * 20 + "\n"
        
        for file_path, file_info in file_hashes.items():
            report += f"\nFile: {file_path}\n"
            report += f"  SHA256: {file_info['sha256']}\n"
            report += f"  Size: {file_info['size']:,} bytes\n"
            report += f"  Modified: {file_info['modified']}\n"
        
        report += "\n\nVERIFICATION INSTRUCTIONS:\n"
        report += "-" * 30 + "\n"
        report += "To verify file integrity, recalculate SHA256 hashes and compare with this report.\n"
        report += "Any discrepancy indicates potential file modification or corruption.\n"
        report += "This report serves as cryptographic proof of file state at time of analysis.\n"
        
        return report
    
    def create_ui_elements(self, parent_widget) -> List[tk.Widget]:
        elements = []
        
        frame = ttk.Frame(parent_widget)
        frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(frame, text="🔐 Generate File Hashes", 
                  command=self.run_analysis_ui).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(frame, text="📋 View Hash Report", 
                  command=self.view_hash_report).pack(side=tk.LEFT, padx=2)
        
        self.status_label = ttk.Label(frame, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        elements.extend([frame, self.status_label])
        return elements
    
    def view_hash_report(self):
        """View the generated hash report"""
        if not hasattr(self, 'core'):
            return
            
        target_dir = Path(self.core.config.target_directory)
        hash_report_path = target_dir / "file_integrity_hashes.json"
        
        if not hash_report_path.exists():
            tk.messagebox.showwarning("No Report", "No hash report found. Run hash generation first.")
            return
        
        # Create popup window to show hash report
        popup = tk.Toplevel()
        popup.title("File Hash Report")
        popup.geometry("800x600")
        
        # Create text widget with scrollbar
        frame = ttk.Frame(popup)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(frame, wrap=tk.WORD, font=("Courier", 10))
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        # Load and display hash data
        try:
            with open(hash_report_path, 'r') as f:
                hash_data = json.load(f)
            
            display_text = "FILE HASH VERIFICATION REPORT\n"
            display_text += "=" * 40 + "\n\n"
            
            for file_path, file_info in hash_data.items():
                display_text += f"File: {file_path}\n"
                display_text += f"SHA256: {file_info['sha256']}\n"
                display_text += f"Size: {file_info['size']:,} bytes\n"
                display_text += f"Modified: {file_info['modified']}\n"
                display_text += "-" * 40 + "\n"
            
            text_widget.insert(tk.END, display_text)
            text_widget.config(state=tk.DISABLED)
            
        except Exception as e:
            text_widget.insert(tk.END, f"Error loading hash report: {e}")
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def run_analysis_ui(self):
        if hasattr(self, 'core') and self.core.event_loop:
            self.status_label.config(text="Generating hashes...")
            
            async def run_and_update():
                result = await self.analyze({
                    "source_directory": self.core.config.source_directory,
                    "target_directory": self.core.config.target_directory,
                    "case_name": self.core.config.case_name
                })
                
                # Update UI in main thread
                def update_ui():
                    if "error" in result:
                        self.status_label.config(text=f"Error: {result['error']}")
                    else:
                        self.status_label.config(text=f"Hashed {result['files_processed']} files")
                
                if hasattr(self.core, 'root'):
                    self.core.root.after(0, update_ui)
            
            asyncio.run_coroutine_threadsafe(run_and_update(), self.core.event_loop)
