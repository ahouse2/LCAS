#!/usr/bin/env python3
"""
AI Integration Plugin for LCAS
Provides AI-powered analysis capabilities for legal documents
"""

import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
import json
import httpx
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from lcas_core import AnalysisPlugin, UIPlugin

@dataclass
class AIConfig:
    """Configuration for AI services"""
    provider: str = "openai"
    api_key: str = ""
    model: str = "gpt-4"
    base_url: str = ""
    temperature: float = 0.1
    max_tokens: int = 4000
    timeout: int = 60
    enabled: bool = False

@dataclass
class AIResponse:
    """Response from AI service"""
    content: str
    usage: Dict[str, int]
    model: str
    success: bool
    error: Optional[str] = None

class AIIntegrationPlugin(AnalysisPlugin, UIPlugin):
    """Plugin for AI-powered legal document analysis"""
    
    @property
    def name(self) -> str:
        return "AI Integration"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "AI-powered analysis of legal documents and evidence"
    
    @property
    def dependencies(self) -> List[str]:
        return ["httpx"]
    
    async def initialize(self, core_app) -> bool:
        self.core = core_app
        self.logger = core_app.logger.getChild(self.name)
        
        # Load AI configuration
        self.ai_config = AIConfig()
        self._load_ai_config()
        
        return True
    
    async def cleanup(self) -> None:
        pass
    
    def _load_ai_config(self):
        """Load AI configuration from file or core config"""
        try:
            config_path = Path("ai_config.json")
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                    self.ai_config = AIConfig(**config_data)
        except Exception as e:
            self.logger.warning(f"Could not load AI config: {e}")
    
    def _save_ai_config(self):
        """Save AI configuration to file"""
        try:
            config_path = Path("ai_config.json")
            with open(config_path, 'w') as f:
                json.dump({
                    "provider": self.ai_config.provider,
                    "api_key": self.ai_config.api_key,
                    "model": self.ai_config.model,
                    "base_url": self.ai_config.base_url,
                    "temperature": self.ai_config.temperature,
                    "max_tokens": self.ai_config.max_tokens,
                    "timeout": self.ai_config.timeout,
                    "enabled": self.ai_config.enabled
                }, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save AI config: {e}")
    
    async def analyze(self, data: Any) -> Dict[str, Any]:
        """Perform AI analysis on documents"""
        if not self.ai_config.enabled or not self.ai_config.api_key:
            return {"error": "AI integration not configured or disabled"}
        
        source_dir = Path(data.get("source_directory", ""))
        target_dir = Path(data.get("target_directory", ""))
        
        if not source_dir.exists():
            return {"error": "Source directory does not exist"}
        
        analysis_results = {}
        files_processed = 0
        
        # Find text-based files for analysis
        text_files = []
        for file_path in source_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.doc', '.docx', '.pdf']:
                text_files.append(file_path)
        
        # Process files in batches
        for file_path in text_files[:10]:  # Limit to 10 files for demo
            try:
                file_content = await self._extract_file_content(file_path)
                if file_content:
                    ai_analysis = await self._analyze_with_ai(file_content, file_path.name)
                    if ai_analysis.success:
                        analysis_results[str(file_path.relative_to(source_dir))] = {
                            "summary": ai_analysis.content,
                            "model": ai_analysis.model,
                            "tokens_used": ai_analysis.usage.get("total_tokens", 0),
                            "timestamp": datetime.now().isoformat()
                        }
                        files_processed += 1
                    
            except Exception as e:
                self.logger.error(f"Error analyzing {file_path}: {e}")
        
        # Save AI analysis report
        if analysis_results:
            report_path = target_dir / "ai_analysis_report.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(report_path, 'w') as f:
                json.dump(analysis_results, f, indent=2)
        
        return {
            "plugin": self.name,
            "files_processed": files_processed,
            "analysis_results": analysis_results,
            "ai_provider": self.ai_config.provider,
            "ai_model": self.ai_config.model,
            "status": "completed"
        }
    
    async def _extract_file_content(self, file_path: Path) -> str:
        """Extract text content from file"""
        try:
            if file_path.suffix.lower() == '.txt':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()[:5000]  # Limit content length
            # For other file types, we'd need additional libraries
            # This is a simplified implementation
            return ""
        except Exception as e:
            self.logger.error(f"Error extracting content from {file_path}: {e}")
            return ""
    
    async def _analyze_with_ai(self, content: str, filename: str) -> AIResponse:
        """Analyze content with AI"""
        try:
            prompt = f"""Analyze this legal document or evidence file and provide:
1. A brief summary of the content
2. Key legal concepts or arguments present
3. Potential relevance to different legal arguments
4. Notable dates, names, or events mentioned

Filename: {filename}
Content: {content}

Provide a concise but thorough analysis:"""

            headers = {
                "Authorization": f"Bearer {self.ai_config.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.ai_config.model,
                "messages": [
                    {"role": "system", "content": "You are a legal analysis AI assistant helping organize evidence for court cases."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.ai_config.temperature,
                "max_tokens": self.ai_config.max_tokens
            }
            
            base_url = self.ai_config.base_url or "https://api.openai.com/v1"
            url = f"{base_url}/chat/completions"
            
            async with httpx.AsyncClient(timeout=self.ai_config.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    return AIResponse(
                        content=result["choices"][0]["message"]["content"],
                        usage=result.get("usage", {}),
                        model=result.get("model", self.ai_config.model),
                        success=True
                    )
                else:
                    return AIResponse(
                        content="",
                        usage={},
                        model=self.ai_config.model,
                        success=False,
                        error=f"API Error: {response.status_code}"
                    )
                    
        except Exception as e:
            return AIResponse(
                content="",
                usage={},
                model=self.ai_config.model,
                success=False,
                error=str(e)
            )
    
    def create_ui_elements(self, parent_widget) -> List[tk.Widget]:
        elements = []
        
        # Main frame
        main_frame = ttk.LabelFrame(parent_widget, text="AI Integration")
        main_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Configuration frame
        config_frame = ttk.Frame(main_frame)
        config_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # AI Provider selection
        ttk.Label(config_frame, text="Provider:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.provider_var = tk.StringVar(value=self.ai_config.provider)
        provider_combo = ttk.Combobox(config_frame, textvariable=self.provider_var, 
                                     values=["openai", "anthropic", "local"], width=15)
        provider_combo.grid(row=0, column=1, padx=5)
        
        # Model selection
        ttk.Label(config_frame, text="Model:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.model_var = tk.StringVar(value=self.ai_config.model)
        model_entry = ttk.Entry(config_frame, textvariable=self.model_var, width=20)
        model_entry.grid(row=0, column=3, padx=5)
        
        # API Key
        ttk.Label(config_frame, text="API Key:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.api_key_var = tk.StringVar(value=self.ai_config.api_key)
        api_key_entry = ttk.Entry(config_frame, textvariable=self.api_key_var, show="*", width=30)
        api_key_entry.grid(row=1, column=1, columnspan=2, padx=5, sticky=tk.W)
        
        # Enable checkbox
        self.enabled_var = tk.BooleanVar(value=self.ai_config.enabled)
        ttk.Checkbutton(config_frame, text="Enable AI Analysis", 
                       variable=self.enabled_var).grid(row=1, column=3, padx=5)
        
        # Action buttons
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(action_frame, text="💾 Save Config", 
                  command=self.save_config_ui).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="🧠 Run AI Analysis", 
                  command=self.run_analysis_ui).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="🔍 Test Connection", 
                  command=self.test_connection).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="📋 View Results", 
                  command=self.view_ai_results).pack(side=tk.LEFT, padx=2)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready")
        self.status_label.pack(anchor=tk.W, padx=5, pady=2)
        
        elements.extend([main_frame])
        return elements
    
    def save_config_ui(self):
        """Save AI configuration from UI"""
        self.ai_config.provider = self.provider_var.get()
        self.ai_config.model = self.model_var.get()
        self.ai_config.api_key = self.api_key_var.get()
        self.ai_config.enabled = self.enabled_var.get()
        
        self._save_ai_config()
        self.status_label.config(text="Configuration saved")
        
    def test_connection(self):
        """Test AI connection"""
        if not self.ai_config.api_key:
            messagebox.showerror("Error", "Please enter API key first")
            return
            
        self.status_label.config(text="Testing connection...")
        
        async def test_async():
            result = await self._analyze_with_ai("Test message", "test.txt")
            
            def update_ui():
                if result.success:
                    self.status_label.config(text="✅ Connection successful")
                    messagebox.showinfo("Success", "AI connection test successful!")
                else:
                    self.status_label.config(text="❌ Connection failed")
                    messagebox.showerror("Error", f"Connection failed: {result.error}")
            
            if hasattr(self.core, 'root'):
                self.core.root.after(0, update_ui)
        
        if hasattr(self, 'core') and self.core.event_loop:
            asyncio.run_coroutine_threadsafe(test_async(), self.core.event_loop)
    
    def view_ai_results(self):
        """View AI analysis results"""
        if not hasattr(self, 'core'):
            return
            
        target_dir = Path(self.core.config.target_directory)
        report_path = target_dir / "ai_analysis_report.json"
        
        if not report_path.exists():
            messagebox.showwarning("No Results", "No AI analysis results found. Run AI analysis first.")
            return
        
        # Create popup window
        popup = tk.Toplevel()
        popup.title("AI Analysis Results")
        popup.geometry("900x700")
        
        # Create text widget with scrollbar
        frame = ttk.Frame(popup)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(frame, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        # Load and display results
        try:
            with open(report_path, 'r') as f:
                results = json.load(f)
            
            display_text = "AI ANALYSIS RESULTS\n"
            display_text += "=" * 50 + "\n\n"
            
            for file_path, analysis in results.items():
                display_text += f"File: {file_path}\n"
                display_text += f"Model: {analysis['model']}\n"
                display_text += f"Tokens Used: {analysis['tokens_used']}\n"
                display_text += f"Timestamp: {analysis['timestamp']}\n"
                display_text += f"\nAnalysis:\n{analysis['summary']}\n"
                display_text += "-" * 50 + "\n\n"
            
            text_widget.insert(tk.END, display_text)
            text_widget.config(state=tk.DISABLED)
            
        except Exception as e:
            text_widget.insert(tk.END, f"Error loading results: {e}")
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def run_analysis_ui(self):
        """Run AI analysis from UI"""
        if not self.ai_config.enabled:
            messagebox.showwarning("AI Disabled", "Please enable AI analysis first")
            return
            
        if not self.ai_config.api_key:
            messagebox.showerror("Error", "Please configure API key first")
            return
            
        if hasattr(self, 'core') and self.core.event_loop:
            self.status_label.config(text="Running AI analysis...")
            
            async def run_and_update():
                result = await self.analyze({
                    "source_directory": self.core.config.source_directory,
                    "target_directory": self.core.config.target_directory,
                    "case_name": self.core.config.case_name
                })
                
                def update_ui():
                    if "error" in result:
                        self.status_label.config(text=f"Error: {result['error']}")
                    else:
                        self.status_label.config(text=f"Analyzed {result['files_processed']} files")
                
                if hasattr(self.core, 'root'):
                    self.core.root.after(0, update_ui)
            
            asyncio.run_coroutine_threadsafe(run_and_update(), self.core.event_loop)
