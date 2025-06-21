#!/usr/bin/env python3
"""
Report Generation Plugin for LCAS
Generates comprehensive analysis reports in Markdown format.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import asdict # For converting FileAnalysisData if needed by report

from lcas2.core import ExportPlugin, UIPlugin, LCASCore
from lcas2.core.data_models import FileAnalysisData # Import to understand its structure for reporting

# Plugin Name Constants (ensure these match actual plugin names in LCASConfig)
FILE_INGESTION_PLUGIN_NAME = "File Ingestion"
HASH_GENERATION_PLUGIN_NAME = "Hash Generation"
CONTENT_EXTRACTION_PLUGIN_NAME = "Content Extraction"
IMAGE_ANALYSIS_PLUGIN_NAME = "Image Analysis"
AI_WRAPPER_PLUGIN_NAME = "lcas_ai_wrapper_plugin"
TIMELINE_ANALYSIS_PLUGIN_NAME = "Timeline Analysis"
PATTERN_DISCOVERY_PLUGIN_NAME = "Pattern Discovery"
EVIDENCE_SCORING_PLUGIN_NAME = "Evidence Scoring"
EVIDENCE_CATEGORIZATION_PLUGIN_NAME = "Evidence Categorization"
CASE_MANAGEMENT_PLUGIN_NAME = "Case Management"


class ReportGenerationPlugin(ExportPlugin, UIPlugin):
    """Plugin for generating comprehensive analysis reports in Markdown."""

    @property
    def name(self) -> str: return "Report Generation"
    @property
    def version(self) -> str: return "1.3.0" # Version updated
    @property
    def description(self) -> str: return "Generates detailed, structured Markdown reports from all analysis phases."
    @property
    def dependencies(self) -> List[str]: return [] # Relies on data in core.analysis_results

    async def initialize(self, core_app: LCASCore) -> bool:
        self.core = core_app
        self.logger = core_app.logger.getChild(self.name)
        # UI control variables for report sections
        self.include_exec_summary = tk.BooleanVar(value=True)
        self.include_pipeline_summary = tk.BooleanVar(value=True)
        self.include_file_inventory_hashes = tk.BooleanVar(value=False) # Potentially long
        self.include_content_extraction_summary = tk.BooleanVar(value=True)
        self.include_image_analysis_summary = tk.BooleanVar(value=True)
        self.include_ai_analysis_highlights = tk.BooleanVar(value=True)
        self.include_timeline_highlights = tk.BooleanVar(value=True)
        self.include_pattern_discovery_summary = tk.BooleanVar(value=True)
        self.include_evidence_scoring_summary = tk.BooleanVar(value=True)
        self.include_categorization_summary = tk.BooleanVar(value=True)
        self.include_case_organization_summary = tk.BooleanVar(value=True)
        self.include_detailed_file_reports = tk.BooleanVar(value=False) # Potentially very long
        self.include_recommendations = tk.BooleanVar(value=True)
        self.include_technical_notes = tk.BooleanVar(value=True)
        self.logger.info("ReportGenerationPlugin initialized.")
        return True

    async def cleanup(self) -> None: self.logger.info("ReportGenerationPlugin cleaned up.")

    async def export(self, data_context_for_header: Any, output_path: str) -> bool:
        try:
            all_plugin_results = self.core.analysis_results if hasattr(self.core, 'analysis_results') else {}

            report_options = {
                "include_exec_summary": self.include_exec_summary.get(),
                "include_pipeline_summary": self.include_pipeline_summary.get(),
                "include_file_inventory_hashes": self.include_file_inventory_hashes.get(),
                "include_content_extraction_summary": self.include_content_extraction_summary.get(),
                "include_image_analysis_summary": self.include_image_analysis_summary.get(),
                "include_ai_analysis_highlights": self.include_ai_analysis_highlights.get(),
                "include_timeline_highlights": self.include_timeline_highlights.get(),
                "include_pattern_discovery_summary": self.include_pattern_discovery_summary.get(),
                "include_evidence_scoring_summary": self.include_evidence_scoring_summary.get(),
                "include_categorization_summary": self.include_categorization_summary.get(),
                "include_case_organization_summary": self.include_case_organization_summary.get(),
                "include_detailed_file_reports": self.include_detailed_file_reports.get(),
                "include_recommendations": self.include_recommendations.get(),
                "include_technical_notes": self.include_technical_notes.get()
            }
            # The 'data' argument for export is now primarily for header info like case name, dirs
            report_content = self._generate_markdown_report(all_plugin_results, data_context_for_header, report_options)
            with open(output_path, 'w', encoding='utf-8') as f: f.write(report_content)
            self.logger.info(f"Markdown report generated: {output_path}")
            return True
        except Exception as e: self.logger.error(f"Error generating Markdown report: {e}", exc_info=True); return False

    def _format_fad_for_report(self, fad_dict: Dict[str,Any]) -> List[str]:
        """Formats a single FileAnalysisData (as dict) for inclusion in the detailed report."""
        lines = []
        lines.append(f"#### File: `{fad_dict.get('file_name', Path(fad_dict.get('file_path','Unnamed')).name)}`")
        lines.append(f"- **Full Path**: `{fad_dict.get('file_path')}`")
        ingestion_details = fad_dict.get('ingestion_details')
        if ingestion_details and isinstance(ingestion_details,dict) : # Check it's a dict
            lines.append(f"- **Ingested**: {ingestion_details.get('status', 'N/A')} (SHA256: `{ingestion_details.get('original_hash', 'N/A')[:16]}...`)")

        lines.append(f"- **Content Extracted**: {'Yes' if fad_dict.get('content') or fad_dict.get('ocr_text_from_images') else 'No'}") # More direct check
        if fad_dict.get('content_extraction_error'): lines.append(f"  - Extraction Error: `{fad_dict['content_extraction_error']}`")
        extraction_meta = fad_dict.get('extraction_meta')
        if extraction_meta and isinstance(extraction_meta, dict): # Check it's a dict
            lines.append(f"  - Format: {extraction_meta.get('format_detected','N/A')}, Method: {extraction_meta.get('extraction_method','N/A')}")
            if extraction_meta.get('page_count'): lines.append(f"  - Pages: {extraction_meta['page_count']}")

        if fad_dict.get('summary_auto'): lines.append(f"- **Auto Summary**: {fad_dict['summary_auto'][:300].replace('|','-')}{'...' if len(fad_dict['summary_auto']) > 300 else ''}")
        if fad_dict.get('ai_summary'): lines.append(f"- **AI Summary**: {fad_dict['ai_summary'][:300].replace('|','-')}{'...' if len(fad_dict['ai_summary']) > 300 else ''}")
        if fad_dict.get('ocr_text_from_images'): lines.append(f"- **OCR Text (snippet)**: {fad_dict['ocr_text_from_images'][:200].replace('|','-')}{'...' if len(fad_dict['ocr_text_from_images']) > 200 else ''}")

        image_analysis_results = fad_dict.get('image_analysis_results')
        if image_analysis_results and isinstance(image_analysis_results, list):
            lines.append(f"- **Image Analysis**: {len(image_analysis_results)} image(s) analyzed.")
            for img_res in image_analysis_results[:2]: # Max 2 images summary
                if isinstance(img_res, dict): # Ensure img_res is a dict
                    lines.append(f"  - Image ID: `{img_res.get('image_sub_id')}`: {img_res.get('visual_description', 'N/A')[:100].replace('|','-')}... (Type: {img_res.get('evidence_type_classification')})")

        if fad_dict.get('ai_tags'): lines.append(f"- **AI Tags**: `{', '.join(fad_dict['ai_tags'])}`")
        if fad_dict.get('ai_suggested_category'): lines.append(f"- **AI Suggested Category**: `{fad_dict['ai_suggested_category']}`")

        evidence_scores = fad_dict.get('evidence_scores')
        if evidence_scores and isinstance(evidence_scores, dict):
            lines.append("- **Evidence Scores**:")
            for score_type, score_detail_dict in evidence_scores.items():
                if isinstance(score_detail_dict, dict):
                     score_val = score_detail_dict.get('score', 'N/A')
                     score_str = f"{score_val:.2f}" if isinstance(score_val, (float, int)) else str(score_val)
                     lines.append(f"  - `{score_type.replace('_',' ').title()}`: **{score_str}** - _{score_detail_dict.get('justification', 'N/A')[:150].replace('|','-')}_")

        if fad_dict.get('assigned_category_folder_name'):
            lines.append(f"- **Assigned Category**: `{fad_dict['assigned_category_folder_name']}` (Reason: {fad_dict.get('categorization_reason', 'N/A')})")

        associated_patterns = fad_dict.get('associated_patterns')
        if associated_patterns and isinstance(associated_patterns, list):
            lines.append(f"- **Associated Patterns**: {len(associated_patterns)} found.")
            for pat_dict in associated_patterns[:2]: # Max 2 patterns summary
                if isinstance(pat_dict, dict): # Ensure pat_dict is a dict
                    pat_conf = pat_dict.get('confidence_score',0)
                    pat_conf_str = f"{pat_conf:.2f}" if isinstance(pat_conf, (float,int)) else str(pat_conf)
                    lines.append(f"  - Pattern: `{pat_dict.get('title')}` (Type: {pat_dict.get('pattern_type')}, Confidence: {pat_conf_str})")
        lines.append("")
        return lines

    def _generate_markdown_report(self, all_plugin_results: Dict[str, Any], header_data: Dict[str, Any], options: Dict[str, bool]) -> str:
        report_parts = [f"# LCAS Comprehensive Analysis Report\n"]
        report_parts.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report_parts.append(f"**Case Name:** {header_data.get('case_name', 'Unknown')}\n")
        report_parts.append(f"**Source Directory:** `{header_data.get('source_directory', 'Unknown')}`\n")
        report_parts.append(f"**Target Directory (Results Root):** `{header_data.get('target_directory', 'Unknown')}`\n")

        master_file_data_wrapper = all_plugin_results.get("MasterFileAnalysisData", {})
        master_file_data_dict: Dict[str, Dict[str,Any]] = master_file_data_wrapper.get("result", {}) if isinstance(master_file_data_wrapper, dict) else {}


        if options.get("include_exec_summary", True):
            report_parts.append("## Executive Summary\n")
            # Count plugins excluding MasterFileAnalysisData meta-entry
            executed_plugin_names = [name for name in all_plugin_results.keys() if name != "MasterFileAnalysisData"]
            successful_plugins = sum(1 for name in executed_plugin_names if isinstance(all_plugin_results[name].get('result'), dict) and all_plugin_results[name]['result'].get('success', False) is True)
            report_parts.append(f"- Analysis involved **{len(executed_plugin_names)}** processing plugins.")
            report_parts.append(f"- Successfully executed plugins: **{successful_plugins}**.")
            report_parts.append(f"- Total files processed (from MasterFileAnalysisData): **{len(master_file_data_dict)}** files.\n")
            # Add more high-level insights here
            if PATTERN_DISCOVERY_PLUGIN_NAME in all_plugin_results:
                pd_summary = all_plugin_results[PATTERN_DISCOVERY_PLUGIN_NAME].get("result",{}).get("summary",{})
                report_parts.append(f"- Discovered **{pd_summary.get('discovered_patterns_count','N/A')}** patterns and **{pd_summary.get('potential_theories_count','N/A')}** potential legal theories.")
            if EVIDENCE_SCORING_PLUGIN_NAME in all_plugin_results:
                 es_summary = all_plugin_results[EVIDENCE_SCORING_PLUGIN_NAME].get("result",{}).get("summary",{})
                 report_parts.append(f"- Scored evidence for **{es_summary.get('files_successfully_scored_at_least_once','N/A')}** files across {len(es_summary.get('score_types_applied',[]))} criteria.")
            report_parts.append("\nThis report details the findings from each executed plugin, highlights key patterns and theories, and provides an overview of the case file organization.\n")

        if options.get("include_pipeline_summary", True):
            report_parts.append("## Analysis Pipeline Summary\n")
            for plugin_name_const, result_data_wrapper in all_plugin_results.items():
                if plugin_name_const == "MasterFileAnalysisData": continue
                result = result_data_wrapper.get('result', {})
                report_parts.append(f"### {plugin_name_const}")
                report_parts.append(f"- Status: `{result.get('status', 'N/A')}`, Success: `{result.get('success', 'N/A')}`")
                summary = result.get('summary', {})
                if isinstance(summary, dict):
                    for k, v in summary.items(): report_parts.append(f"  - {k.replace('_',' ').title()}: `{v}`") # Values in backticks
                elif isinstance(summary, str): report_parts.append(f"  - Summary: {summary}")
                report_parts.append("")
            report_parts.append("\n")

        if options.get("include_file_inventory_hashes", False) and HASH_GENERATION_PLUGIN_NAME in all_plugin_results:
            report_parts.append(f"## File Inventory & Hashes (from {HASH_GENERATION_PLUGIN_NAME})\n")
            hg_res_wrapper = all_plugin_results[HASH_GENERATION_PLUGIN_NAME] # Get wrapper
            hg_res = hg_res_wrapper.get("result", {}) if isinstance(hg_res_wrapper, dict) else {} # Get result from wrapper
            if hg_res.get("success"):
                report_parts.append(f"- Hash Types Generated: `{', '.join(hg_res.get('hash_types_generated',[]))}`")
                report_parts.append(f"- JSON Report Path: `{hg_res.get('json_report_path')}`")
                report_parts.append(f"- Text Report Path: `{hg_res.get('txt_report_path')}`")
                report_parts.append("  *(Refer to the generated JSON/TXT reports for detailed hash list.)*\n")
            else: report_parts.append("- Hash generation data not available or task failed.\n")

        if options.get("include_pattern_discovery_summary", True) and PATTERN_DISCOVERY_PLUGIN_NAME in all_plugin_results:
            report_parts.append(f"## Pattern Discovery & Legal Theory Highlights\n")
            pd_res_wrapper = all_plugin_results[PATTERN_DISCOVERY_PLUGIN_NAME]
            pd_res = pd_res_wrapper.get("result",{}) if isinstance(pd_res_wrapper, dict) else {}
            pd_summary = pd_res.get("summary", {})
            report_parts.append(f"- Patterns Found: `{pd_summary.get('discovered_patterns_count', 'N/A')}`")
            report_parts.append(f"- Legal Theories Suggested: `{pd_summary.get('potential_theories_count', 'N/A')}`")
            theories = pd_res.get("potential_theories_output_list_of_dicts", [])
            if theories and isinstance(theories, list):
                report_parts.append("### Top Suggested Legal Theories (Max 5):")
                for i, theory_dict in enumerate(theories[:5]):
                    if isinstance(theory_dict, dict):
                        report_parts.append(f"  {i+1}. **{theory_dict.get('theory_name')}** (Strength: {theory_dict.get('evidence_strength',0.0):.2f})")
                        report_parts.append(f"     - Description: {theory_dict.get('description','N/A')[:150].replace('|','-')}...")
                        report_parts.append(f"     - Supporting Pattern IDs: `{', '.join(theory_dict.get('supporting_patterns',[]))[:100]}...`")
            report_parts.append(f"- Detailed Reports located in folder: `{pd_res.get('report_path_root')}`\n")

        if options.get("include_evidence_scoring_summary", True) and EVIDENCE_SCORING_PLUGIN_NAME in all_plugin_results:
            report_parts.append(f"## Evidence Scoring Summary\n")
            es_res_wrapper = all_plugin_results[EVIDENCE_SCORING_PLUGIN_NAME]
            es_res = es_res_wrapper.get("result",{}) if isinstance(es_res_wrapper, dict) else {}
            es_summary = es_res.get("summary", {})
            report_parts.append(f"- Files considered for scoring: `{es_summary.get('files_considered_for_scoring','N/A')}`")
            report_parts.append(f"- Files successfully scored (at least one type): `{es_summary.get('files_successfully_scored_at_least_once','N/A')}`")
            report_parts.append(f"- Score types applied: `{', '.join(es_summary.get('score_types_applied',[]))}`")
            report_parts.append("  *(Refer to 'Detailed Analysis Per File' section for scores on individual files if enabled, or JSON export of MasterFileAnalysisData.)*\n")


        if options.get("include_case_organization_summary", True) and CASE_MANAGEMENT_PLUGIN_NAME in all_plugin_results:
            report_parts.append(f"## Case File Organization Summary\n")
            cm_res_wrapper = all_plugin_results[CASE_MANAGEMENT_PLUGIN_NAME]
            cm_res = cm_res_wrapper.get("result",{}) if isinstance(cm_res_wrapper, dict) else {}
            cm_summary = cm_res.get("summary", {})
            report_parts.append(f"- Case Files Root Directory: `{cm_summary.get('case_files_root')}`")
            report_parts.append(f"- Files Organized: `{cm_summary.get('files_organized')}`")
            report_parts.append(f"- Folders Created/Used: `{cm_summary.get('folders_created_or_used')}`")
            report_parts.append(f"- Theories Applied to Structure: `{cm_summary.get('theories_applied_count', 'N/A')}`\n")

        if options.get("include_detailed_file_reports", False) and master_file_data_dict:
            report_parts.append("## Detailed Analysis Per File\n")
            sorted_file_paths = sorted(master_file_data_dict.keys())
            report_parts.append(f"*(Displaying details for up to 20 files if more exist)*\n")
            for i, file_path_str in enumerate(sorted_file_paths):
                if i >= 20 and len(sorted_file_paths) > 25 :
                    report_parts.append(f"\n... and {len(sorted_file_paths) - i} more files. Full details in application or JSON export of MasterFileAnalysisData.\n")
                    break
                fad_dict = master_file_data_dict[file_path_str]
                report_parts.extend(self._format_fad_for_report(fad_dict))
            report_parts.append("\n")

        if options.get("include_recommendations", True): report_parts.extend(["## Recommendations\n", "- Review files in FOR_HUMAN_REVIEW folder.", "- Verify integrity of critical evidence using hash reports if available.", "- Further investigate high-confidence patterns and synthesized legal theories with legal counsel.\n"])
        if options.get("include_technical_notes", True):
            lcas_version = getattr(self.core.config, 'lcas_version', 'N/A') if hasattr(self.core, 'config') else 'N/A'
            report_parts.extend(["## Technical Notes\n", f"- Analysis performed by LCAS (Legal Case Analysis System) v{lcas_version}", f"- Active Plugins in this run: `{', '.join(name for name in all_plugin_results.keys() if name != 'MasterFileAnalysisData')}`\n"])

        return "\n".join(report_parts)

    def create_ui_elements(self, parent_widget) -> List[Any]:
        try:
            import tkinter as tk_ui
            from tkinter import ttk
        except ImportError: self.logger.warning("Tkinter not available for ReportGeneration UI."); return []

        elements = []; main_frame = ttk.LabelFrame(parent_widget, text=self.name); main_frame.pack(fill=tk_ui.X, padx=5, pady=2)
        options_frame = ttk.Frame(main_frame); options_frame.pack(fill=tk_ui.X, padx=5, pady=2)

        checkboxes = [
            ("Exec Summary", self.include_exec_summary), ("Pipeline Summary", self.include_pipeline_summary),
            ("File Inventory/Hashes", self.include_file_inventory_hashes),
            ("Content Extraction Sum.", self.include_content_extraction_summary),
            ("Image Analysis Sum.", self.include_image_analysis_summary),
            ("AI Highlights", self.include_ai_analysis_highlights),
            ("Timeline Highlights", self.include_timeline_highlights),
            ("Pattern/Theory Sum.", self.include_pattern_discovery_summary),
            ("Evidence Scoring Sum.", self.include_evidence_scoring_summary),
            ("Categorization Sum.", self.include_categorization_summary),
            ("Case Organization Sum.", self.include_case_organization_summary),
            ("Detailed File Reports (Max 20)", self.include_detailed_file_reports),
            ("Recommendations", self.include_recommendations), ("Tech Notes", self.include_technical_notes)
        ]
        row, col = 0, 0
        for i, (text, var) in enumerate(checkboxes):
            cb = ttk.Checkbutton(options_frame, text=text, variable=var)
            cb.grid(row=row, column=col, sticky=tk_ui.W, padx=5, pady=2)
            col +=1
            if col >= 2: col = 0; row +=1

        action_frame = ttk.Frame(main_frame); action_frame.pack(fill=tk_ui.X, padx=5, pady=5)
        ttk.Button(action_frame, text="📄 Generate Markdown Report", command=self.generate_report_ui).pack(side=tk_ui.LEFT, padx=2)

        self.status_label = ttk.Label(main_frame, text="Ready for Markdown report generation."); self.status_label.pack(anchor=tk_ui.W, padx=5, pady=2)
        elements.append(main_frame); return elements

    def generate_report_ui(self):
        if not (hasattr(self, 'core') and self.core and self.core.async_event_loop): messagebox.showerror("Core Error", "LCAS Core not ready."); return
        output_path = filedialog.asksaveasfilename(title="Save Analysis Report", defaultextension=".md", filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")])
        if not output_path: return
        self.status_label.config(text="Generating Markdown report...")
        async def run_and_update():
            export_data_context = {"case_name": self.core.config.case_name if hasattr(self.core.config, 'case_name') else "Unknown",
                                   "source_directory": self.core.config.source_directory if hasattr(self.core.config, 'source_directory') else "Unknown",
                                   "target_directory": self.core.config.target_directory if hasattr(self.core.config, 'target_directory') else "Unknown"}
            success = await self.export(export_data_context, output_path)
            def update_ui():
                if success: self.status_label.config(text="Markdown Report generated!"); messagebox.showinfo("Success", f"Report saved to:\n{output_path}")
                else: self.status_label.config(text="Report generation failed"); messagebox.showerror("Error", "Failed to generate report")

            # Ensure UI updates happen on the main thread if core.main_loop is available
            if hasattr(self.core, 'main_loop') and self.core.main_loop and self.core.main_loop.is_running():
                 self.core.main_loop.call_soon_threadsafe(update_ui)
            elif hasattr(self.core, 'root') and self.core.root: # Fallback for older UI setup
                 self.core.root.after(0, update_ui)
            else: update_ui() # Direct call if no event loop context (e.g. testing)

        # Ensure the event loop is running to schedule the coroutine
        if self.core.async_event_loop and self.core.async_event_loop.is_running():
            asyncio.run_coroutine_threadsafe(run_and_update(), self.core.async_event_loop)
        else: # Fallback for environments where loop might not be running or managed externally
            self.logger.warning("Async event loop not running or not available from core. Running export synchronously for UI call (may block UI).")
            # This is not ideal as it blocks UI. Proper async handling from UI is better.
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running(): # If a loop is running, try to use it
                     asyncio.run_coroutine_threadsafe(run_and_update(), loop)
                else: # Last resort, run synchronously (blocks)
                     loop.run_until_complete(run_and_update())
            except RuntimeError: # If no event loop at all
                 asyncio.run(run_and_update()) # Will create a new loop for this task
