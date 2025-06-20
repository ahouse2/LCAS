#!/usr/bin/env python3
"""
Report Generation Plugin for LCAS
Generates comprehensive analysis reports and visualizations
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from lcas2.core import ExportPlugin, UIPlugin


class ReportGenerationPlugin(ExportPlugin, UIPlugin):
    """Plugin for generating comprehensive analysis reports"""

    @property
    def name(self) -> str:
        return "Report Generation"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Generates comprehensive analysis reports and visualizations"

    @property
    def dependencies(self) -> List[str]:
        return []

    async def initialize(self, core_app) -> bool:
        self.core = core_app
        self.logger = core_app.logger.getChild(self.name)
        return True

    async def cleanup(self) -> None:
        pass

    async def export(self, data: Any, output_path: str) -> bool:
        """Generate and export comprehensive report"""
        try:
            # Collect all analysis results from core
            all_results = self.core.analysis_results if hasattr(
                self.core, 'analysis_results') else {}

            # Generate report content
            report_content = self._generate_comprehensive_report(
                all_results, data)

            # Write report
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)

            self.logger.info(f"Report generated: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error generating report: {e}")
            return False

    def _generate_comprehensive_report(
            self, results: Dict[str, Any], data: Dict[str, Any]) -> str:
        """Generate comprehensive analysis report"""
        report = "LCAS COMPREHENSIVE ANALYSIS REPORT\n"
        report += "=" * 60 + "\n\n"

        # Header information
        report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"Case Name: {data.get('case_name', 'Unknown')}\n"
        report += f"Source Directory: {
            data.get(
                'source_directory',
                'Unknown')}\n"
        report += f"Target Directory: {
            data.get(
                'target_directory',
                'Unknown')}\n\n"

        # Executive Summary
        report += "EXECUTIVE SUMMARY\n"
        report += "-" * 20 + "\n"
        total_plugins = len(results)
        successful_plugins = sum(1 for r in results.values()
                                 if r.get('result', {}).get('status') == 'completed')

        report += f"Analysis completed using {total_plugins} plugins\n"
        report += f"Successful analyses: {successful_plugins}/{total_plugins}\n"

        # Calculate total files processed
        total_files = 0
        for plugin_name, result_data in results.items():
            result = result_data.get('result', {})
            if 'files_processed' in result:
                total_files += result['files_processed']
            elif 'total_files' in result:
                total_files += result['total_files']

        report += f"Total files processed: {total_files}\n\n"

        # Plugin Results Section
        report += "DETAILED PLUGIN RESULTS\n"
        report += "-" * 30 + "\n\n"

        for plugin_name, result_data in results.items():
            result = result_data.get('result', {})
            timestamp = result_data.get('timestamp', 'Unknown')

            report += f"Plugin: {plugin_name}\n"
            report += f"Timestamp: {timestamp}\n"
            report += f"Status: {result.get('status', 'Unknown')}\n"

            # Add plugin-specific details
            if plugin_name == "File Ingestion":
                report += f"Files Processed: {
                    result.get(
                        'files_processed', 0)}\n"
                report += f"Files Copied: {result.get('files_copied', 0)}\n"
                report += f"Backup Directory: {
                    result.get(
                        'backup_directory',
                        'N/A')}\n"

            elif plugin_name == "Hash Generation":
                report += f"Files Hashed: {result.get('files_processed', 0)}\n"
                report += f"Hash Report: {
                    result.get(
                        'hash_report_path',
                        'N/A')}\n"

            elif plugin_name == "Evidence Categorization":
                total_files = result.get('total_files', 0)
                uncategorized = len(result.get('uncategorized_files', []))
                categorized = total_files - uncategorized
                report += f"Total Files: {total_files}\n"
                report += f"Categorized: {categorized}\n"
                report += f"For Review: {uncategorized}\n"

                folders_created = result.get('folders_created', [])
                report += f"Folders Created: {len(folders_created)}\n"
                for folder in folders_created:
                    categorized_files = result.get('categorized_files', {})
                    file_count = len(categorized_files.get(folder, []))
                    report += f"  {folder}: {file_count} files\n"

            elif plugin_name == "Timeline Analysis":
                report += f"Events Found: {result.get('events_found', 0)}\n"
                report += f"Timeline Report: {
                    result.get(
                        'timeline_report_path',
                        'N/A')}\n"

            elif plugin_name == "AI Integration":
                report += f"Files Analyzed: {
                    result.get(
                        'files_processed', 0)}\n"
                report += f"AI Provider: {result.get('ai_provider', 'N/A')}\n"
                report += f"AI Model: {result.get('ai_model', 'N/A')}\n"

            report += "\n" + "-" * 40 + "\n\n"

        # File Organization Summary
        report += "FILE ORGANIZATION SUMMARY\n"
        report += "-" * 30 + "\n"

        # Get categorization results if available
        categorization_result = None
        for plugin_name, result_data in results.items():
            if plugin_name == "Evidence Categorization":
                categorization_result = result_data.get('result', {})
                break

        if categorization_result:
            categorized_files = categorization_result.get(
                'categorized_files', {})
            for folder, files in categorized_files.items():
                report += f"{folder}: {len(files)} files\n"

            uncategorized = categorization_result.get(
                'uncategorized_files', [])
            report += f"FOR_HUMAN_REVIEW: {len(uncategorized)} files\n"
        else:
            report += "No categorization data available\n"

        report += "\n"

        # Timeline Summary
        report += "TIMELINE SUMMARY\n"
        report += "-" * 20 + "\n"

        timeline_result = None
        for plugin_name, result_data in results.items():
            if plugin_name == "Timeline Analysis":
                timeline_result = result_data.get('result', {})
                break

        if timeline_result:
            events = timeline_result.get('events', [])
            report += f"Timeline events identified: {len(events)}\n"

            if events:
                # Show first few events
                report += "\nKey Timeline Events:\n"
                for i, event in enumerate(events[:5]):
                    event_date = event.get('date', 'Unknown')
                    description = event.get(
                        'description', 'No description')[:100]
                    report += f"  {i + 1}. {event_date}: {description}...\n"

                if len(events) > 5:
                    report += f"  ... and {len(events) - 5} more events\n"
        else:
            report += "No timeline analysis data available\n"

        report += "\n"

        # Security and Integrity
        report += "SECURITY AND INTEGRITY\n"
        report += "-" * 25 + "\n"

        hash_result = None
        for plugin_name, result_data in results.items():
            if plugin_name == "Hash Generation":
                hash_result = result_data.get('result', {})
                break

        if hash_result:
            files_hashed = hash_result.get('files_processed', 0)
            report += f"Files with integrity hashes: {files_hashed}\n"
            report += f"Hash algorithm: SHA256\n"
            report += f"Integrity report: {
                hash_result.get(
                    'integrity_report_path',
                    'N/A')}\n"
            report += "All original files preserved with cryptographic verification\n"
        else:
            report += "No hash generation data available\n"

        report += "\n"

        # AI Analysis Summary
        ai_result = None
        for plugin_name, result_data in results.items():
            if plugin_name == "AI Integration":
                ai_result = result_data.get('result', {})
                break

        if ai_result:
            report += "AI ANALYSIS SUMMARY\n"
            report += "-" * 20 + "\n"
            report += f"Provider: {ai_result.get('ai_provider', 'N/A')}\n"
            report += f"Model: {ai_result.get('ai_model', 'N/A')}\n"
            report += f"Documents analyzed: {
                ai_result.get(
                    'files_processed', 0)}\n"

            analysis_results = ai_result.get('analysis_results', {})
            if analysis_results:
                report += "\nSample AI Analysis Results:\n"
                count = 0
                for file_path, analysis in analysis_results.items():
                    if count >= 3:  # Limit to 3 samples
                        break
                    report += f"\nFile: {file_path}\n"
                    summary = analysis.get('summary', '')[:200]
                    report += f"Summary: {summary}...\n"
                    count += 1
            report += "\n"

        # Recommendations
        report += "RECOMMENDATIONS\n"
        report += "-" * 15 + "\n"
        report += "1. Review files in FOR_HUMAN_REVIEW folder for proper categorization\n"
        report += "2. Verify integrity of critical evidence using generated hash values\n"
        report += "3. Cross-reference timeline events with legal arguments\n"
        report += "4. Consider additional AI analysis for complex documents\n"
        report += "5. Generate visual timeline and relationship maps for presentation\n"
        report += "6. Validate all evidence admissibility before court presentation\n\n"

        # Technical Notes
        report += "TECHNICAL NOTES\n"
        report += "-" * 15 + "\n"
        report += f"Analysis performed by LCAS v4.0\n"
        report += f"Plugins used: {', '.join(results.keys())}\n"
        report += f"Processing completed: {
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += "All file modifications tracked and logged\n"
        report += "Original evidence preserved in backup directory\n"

        return report

    def create_ui_elements(self, parent_widget) -> List[tk.Widget]:
        elements = []

        # Main frame
        main_frame = ttk.LabelFrame(parent_widget, text="Report Generation")
        main_frame.pack(fill=tk.X, padx=5, pady=2)

        # Report options frame
        options_frame = ttk.Frame(main_frame)
        options_frame.pack(fill=tk.X, padx=5, pady=2)

        # Report type options
        self.include_summary = tk.BooleanVar(value=True)
        self.include_details = tk.BooleanVar(value=True)
        self.include_timeline = tk.BooleanVar(value=True)
        self.include_ai_results = tk.BooleanVar(value=True)

        ttk.Checkbutton(options_frame, text="Executive Summary",
                        variable=self.include_summary).grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Checkbutton(options_frame, text="Detailed Results",
                        variable=self.include_details).grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Checkbutton(options_frame, text="Timeline Analysis",
                        variable=self.include_timeline).grid(row=1, column=0, sticky=tk.W, padx=5)
        ttk.Checkbutton(options_frame, text="AI Analysis",
                        variable=self.include_ai_results).grid(row=1, column=1, sticky=tk.W, padx=5)

        # Action buttons
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(action_frame, text="📄 Generate Report",
                   command=self.generate_report_ui).pack(side=tk.LEFT, padx=2)

        ttk.Button(action_frame, text="📋 Quick Summary",
                   command=self.show_quick_summary).pack(side=tk.LEFT, padx=2)

        ttk.Button(action_frame, text="📊 Export Data",
                   command=self.export_data_ui).pack(side=tk.LEFT, padx=2)

        ttk.Button(action_frame, text="🔍 View Results",
                   command=self.view_all_results).pack(side=tk.LEFT, padx=2)

        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready")
        self.status_label.pack(anchor=tk.W, padx=5, pady=2)

        elements.extend([main_frame])
        return elements

    def generate_report_ui(self):
        """Generate report from UI"""
        if not hasattr(self, 'core'):
            return

        # Get output path
        output_path = filedialog.asksaveasfilename(
            title="Save Analysis Report",
            defaultextension=".txt",
            filetypes=[
                ("Text files", "*.txt"),
                ("Markdown files", "*.md"),
                ("All files", "*.*")
            ]
        )

        if output_path:
            self.status_label.config(text="Generating report...")

            async def run_and_update():
                success = await self.export({
                    "case_name": self.core.config.case_name,
                    "source_directory": self.core.config.source_directory,
                    "target_directory": self.core.config.target_directory
                }, output_path)

                def update_ui():
                    if success:
                        self.status_label.config(text="Report generated!")
                        messagebox.showinfo(
                            "Success", f"Report saved to:\n{output_path}")
                    else:
                        self.status_label.config(
                            text="Report generation failed")
                        messagebox.showerror(
                            "Error", "Failed to generate report")

                if hasattr(self.core, 'root'):
                    self.core.root.after(0, update_ui)

            if self.core.event_loop:
                asyncio.run_coroutine_threadsafe(
                    run_and_update(), self.core.event_loop)

    def show_quick_summary(self):
        """Show quick summary of analysis results"""
        if not hasattr(self, 'core'):
            return

        results = getattr(self.core, 'analysis_results', {})

        if not results:
            messagebox.showinfo(
                "No Results",
                "No analysis results available. Run some analysis plugins first.")
            return

        # Generate quick summary
        summary = "QUICK ANALYSIS SUMMARY\n"
        summary += "=" * 30 + "\n\n"

        total_plugins = len(results)
        successful = sum(1 for r in results.values()
                         if r.get('result', {}).get('status') == 'completed')

        summary += f"Plugins Run: {total_plugins}\n"
        summary += f"Successful: {successful}\n"
        summary += f"Failed: {total_plugins - successful}\n\n"

        summary += "Plugin Status:\n"
        for plugin_name, result_data in results.items():
            status = result_data.get('result', {}).get('status', 'Unknown')
            summary += f"  {plugin_name}: {status}\n"

        messagebox.showinfo("Quick Summary", summary)

    def export_data_ui(self):
        """Export analysis data as JSON"""
        if not hasattr(self, 'core'):
            return

        results = getattr(self.core, 'analysis_results', {})

        if not results:
            messagebox.showinfo(
                "No Data", "No analysis data available to export.")
            return

        # Get output path
        output_path = filedialog.asksaveasfilename(
            title="Export Analysis Data",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if output_path:
            try:
                export_data = {
                    "case_name": self.core.config.case_name,
                    "source_directory": self.core.config.source_directory,
                    "target_directory": self.core.config.target_directory,
                    "export_timestamp": datetime.now().isoformat(),
                    "analysis_results": results
                }

                with open(output_path, 'w') as f:
                    json.dump(export_data, f, indent=2)

                self.status_label.config(text="Data exported!")
                messagebox.showinfo(
                    "Success", f"Analysis data exported to:\n{output_path}")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to export data: {e}")

    def view_all_results(self):
        """View all analysis results in a detailed window"""
        if not hasattr(self, 'core'):
            return

        results = getattr(self.core, 'analysis_results', {})

        if not results:
            messagebox.showinfo("No Results", "No analysis results available.")
            return

        # Create results viewer window
        popup = tk.Toplevel()
        popup.title("Analysis Results Viewer")
        popup.geometry("1000x700")

        # Create notebook for different views
        notebook = ttk.Notebook(popup)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Summary tab
        summary_frame = ttk.Frame(notebook)
        notebook.add(summary_frame, text="Summary")

        summary_text = tk.Text(summary_frame, wrap=tk.WORD)
        summary_scroll = ttk.Scrollbar(
            summary_frame,
            orient=tk.VERTICAL,
            command=summary_text.yview)
        summary_text.configure(yscrollcommand=summary_scroll.set)

        # Generate and display summary
        summary_content = self._generate_comprehensive_report(results, {
            "case_name": self.core.config.case_name,
            "source_directory": self.core.config.source_directory,
            "target_directory": self.core.config.target_directory
        })

        summary_text.insert(tk.END, summary_content)
        summary_text.config(state=tk.DISABLED)

        summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Raw data tab
        raw_frame = ttk.Frame(notebook)
        notebook.add(raw_frame, text="Raw Data")

        raw_text = tk.Text(raw_frame, wrap=tk.WORD, font=("Courier", 10))
        raw_scroll = ttk.Scrollbar(
            raw_frame,
            orient=tk.VERTICAL,
            command=raw_text.yview)
        raw_text.configure(yscrollcommand=raw_scroll.set)

        # Display raw JSON data
        try:
            raw_content = json.dumps(results, indent=2, default=str)
            raw_text.insert(tk.END, raw_content)
            raw_text.config(state=tk.DISABLED)
        except Exception as e:
            raw_text.insert(tk.END, f"Error displaying raw data: {e}")

        raw_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        raw_scroll.pack(side=tk.RIGHT, fill=tk.Y)
