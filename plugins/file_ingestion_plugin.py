#!/usr/bin/env python3
"""
File Ingestion Plugin for LCAS
Preserves original files and creates working copies
"""

import tkinter as tk
from tkinter import ttk
import shutil
import asyncio
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

from lcas_core import AnalysisPlugin, UIPlugin

class FileIngestionPlugin(AnalysisPlugin, UIPlugin):
    """Plugin for ingesting and preserving original files"""
    
    @property
    def name(self) -> str:
        return "File Ingestion"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Preserves original files and creates working copies"
    
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
        """Ingest and preserve files"""
        source_dir = Path(data.get("source_directory", ""))
        target_dir = Path(data.get("target_directory", ""))
        
        if not source_dir.exists():
            return {"error": "Source directory does not exist"}
        
        # Create backup directory
        backup_dir = target_dir / "00_ORIGINAL_FILES_BACKUP"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        files_processed = 0
        files_copied = 0
        
        # Copy all files
        for file_path in source_dir.rglob("*"):
            if file_path.is_file():
                files_processed += 1
                
                # Create relative path structure
                rel_path = file_path.relative_to(source_dir)
                backup_path = backup_dir / rel_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                shutil.copy2(file_path, backup_path)
                files_copied += 1
        
        return {
            "plugin": self.name,
            "files_processed": files_processed,
            "files_copied": files_copied,
            "backup_directory": str(backup_dir),
            "status": "completed"
        }
    
    def create_ui_elements(self, parent_widget) -> List[tk.Widget]:
        elements = []
        
        frame = ttk.Frame(parent_widget)
        frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(frame, text="🔒 Preserve Original Files", 
                  command=self.run_analysis_ui).pack(side=tk.LEFT, padx=2)
        
        self.status_label = ttk.Label(frame, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        elements.extend([frame, self.status_label])
        return elements
    
    def run_analysis_ui(self):
        if hasattr(self, 'core') and self.core.event_loop:
            self.status_label.config(text="Processing...")
            
            async def run_and_update():
                result = await self.analyze({
                    "source_directory": self.core.config.source_directory,
                    "target_directory": self.core.config.target_directory
                })
                
                # Update UI in main thread
                def update_ui():
                    if "error" in result:
                        self.status_label.config(text=f"Error: {result['error']}")
                    else:
                        self.status_label.config(text=f"Copied {result['files_copied']} files")
                
                if hasattr(self.core, 'root'):
                    self.core.root.after(0, update_ui)
            
            asyncio.run_coroutine_threadsafe(run_and_update(), self.core.event_loop)
