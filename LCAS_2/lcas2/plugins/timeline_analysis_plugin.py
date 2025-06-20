#!/usr/bin/env python3
"""
Timeline Analysis Plugin for LCAS
Builds chronological timelines from text content of evidence files.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass, asdict, field

from lcas2.core import AnalysisPlugin, UIPlugin, LCASCore
from lcas2.core.data_models import FileAnalysisData # Import FileAnalysisData

# TimelineEvent dataclass can remain here or move to data_models.py if widely shared.
# For now, keeping it local to this plugin for simplicity as its output is primarily consumed by itself or pattern_discovery.
@dataclass
class TimelineEvent:
    """Represents a single event in the timeline"""
    date: str  # ISO format string
    description: str
    source_file_path: str
    event_type: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class TimelineAnalysisPlugin(AnalysisPlugin, UIPlugin):
    """Plugin for building chronological timelines from text content of FileAnalysisData objects."""

    @property
    def name(self) -> str: return "Timeline Analysis"
    @property
    def version(self) -> str: return "1.2.0" # Version updated
    @property
    def description(self) -> str: return "Extracts dates from FileAnalysisData content to build timelines."
    @property
    def dependencies(self) -> List[str]: return ["Content Extraction"] # Depends on text content

    async def initialize(self, core_app: LCASCore) -> bool:
        self.core = core_app
        self.logger = core_app.logger.getChild(self.name)
        self.date_patterns = [
            # DD/MM/YYYY or MM/DD/YYYY (covers common cases, ambiguity handled by trying both)
            r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b',
            # YYYY/MM/DD
            r'\b(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})\b',
            # DD/MM/YY or MM/DD/YY (2-digit year)
            r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{2})\b',
            # Month_name DD, YYYY (e.g., January 15, 2023 or Jan 15, 2023)
            r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*)\s+(\d{1,2}),?\s+(\d{4})\b',
            # DD Month_name YYYY (e.g., 15 January 2023 or 15 Jan 2023)
            r'\b(\d{1,2})\s+((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*)\s+(\d{4})\b',
             # YYYY Month_name DD (e.g., 2023 January 15 or 2023 Jan 15)
            r'\b(\d{4})\s+((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*)\s+(\d{1,2})\b',
        ]
        self.months = {'jan':1, 'feb':2, 'mar':3, 'apr':4, 'may':5, 'jun':6, 'jul':7, 'aug':8, 'sep':9, 'oct':10, 'nov':11, 'dec':12}
        self.logger.info("TimelineAnalysisPlugin initialized.")
        return True

    async def cleanup(self) -> None: self.logger.info("TimelineAnalysisPlugin cleaned up.")

    async def analyze(self, data: Any) -> Dict[str, Any]:
        # Ensure processed_files_input defaults to an empty dict if not provided
        processed_files_input_any: Any = data.get("processed_files", {})

        # Explicitly type check and handle if it's not a dictionary as expected.
        if not isinstance(processed_files_input_any, dict):
            self.logger.error(f"Expected 'processed_files' to be a Dict, got {type(processed_files_input_any)}. Aborting timeline analysis.")
            return {"plugin": self.name, "status": "error", "success": False, "message": "Invalid 'processed_files' format."}

        # Now we can safely type hint it for the rest of the method.
        processed_files_input: Dict[str, Any] = processed_files_input_any

        target_dir_str = data.get("target_directory", self.core.config.target_directory if self.core and hasattr(self.core, 'config') else "timeline_results")
        case_name = data.get("case_name", self.core.config.case_name if self.core and hasattr(self.core, 'config') else "UnknownCase")

        if not processed_files_input:
            return {"plugin": self.name, "status": "no_data", "success": False, "message": "No 'processed_files' (FileAnalysisData) provided."}
        if not target_dir_str:
            return {"plugin": self.name, "status": "error", "success": False, "error": "Target directory not provided."}

        target_dir = Path(target_dir_str); target_dir.mkdir(parents=True, exist_ok=True)
        all_events: List[TimelineEvent] = []
        files_processed_for_timeline = 0

        output_fad_dict: Dict[str, FileAnalysisData] = {}


        for file_path_str, fad_object_or_dict in processed_files_input.items():
            fad_instance: Optional[FileAnalysisData] = None
            if isinstance(fad_object_or_dict, FileAnalysisData):
                fad_instance = fad_object_or_dict
            elif isinstance(fad_object_or_dict, dict):
                try: fad_instance = FileAnalysisData(**fad_object_or_dict)
                except TypeError as te: self.logger.warning(f"Could not cast dict to FileAnalysisData for {file_path_str}, skipping for timeline: {te}"); continue
            else: self.logger.warning(f"Unexpected data type for {file_path_str} in processed_files: {type(fad_object_or_dict)}. Skipping."); continue

            output_fad_dict[file_path_str] = fad_instance # Keep for output

            text_content = fad_instance.content if fad_instance.content else fad_instance.summary_auto
            if not text_content: text_content = fad_instance.ai_summary
            if not text_content: text_content = fad_instance.ocr_text_from_images

            if not text_content: self.logger.debug(f"No text content for timeline in {file_path_str}"); continue

            try:
                self.logger.debug(f"Extracting timeline events from text of {file_path_str}")
                events_from_file = await asyncio.to_thread(self._extract_events_from_text_content, text_content, file_path_str)
                if events_from_file:
                    all_events.extend(events_from_file)
                    fad_instance.timeline_events_extracted = [asdict(e) for e in events_from_file]
                files_processed_for_timeline += 1
            except Exception as e: self.logger.error(f"Error processing {file_path_str} for timeline: {e}", exc_info=True)

        all_events.sort(key=lambda x: x.date)
        timeline_data_output = {
            "events": [asdict(event) for event in all_events],
            "summary": {
                "total_events_found": len(all_events),
                "files_processed_for_timeline": files_processed_for_timeline,
                "date_range": {"earliest": all_events[0].date if all_events else None, "latest": all_events[-1].date if all_events else None},
                "key_events_summary": [f"{evt.date}: {evt.description[:70]}... (Source: {Path(evt.source_file_path).name})" for evt in all_events[:10]]
            }, "generated": datetime.now().isoformat()
        }

        report_filename_base = f"{case_name}_timeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        json_report_path = (target_dir / "REPORTS_LCAS" / "TIMELINE_REPORTS" / (report_filename_base + ".json")).resolve()
        txt_report_path = (target_dir / "REPORTS_LCAS" / "TIMELINE_REPORTS" / (report_filename_base + ".txt")).resolve()
        json_report_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(json_report_path, 'w', encoding='utf-8') as f: json.dump(timeline_data_output, f, indent=2)
        except Exception as e: self.logger.error(f"Failed to save JSON timeline: {e}", exc_info=True)
        try:
            report_content = self._generate_timeline_report_text(all_events, case_name or "Unknown Case")
            with open(txt_report_path, 'w', encoding='utf-8') as f: f.write(report_content)
        except Exception as e: self.logger.error(f"Failed to save text timeline: {e}", exc_info=True)

        return {
            "plugin": self.name, "status": "completed", "success": True,
            "summary": timeline_data_output["summary"],
            "report_path_json": str(json_report_path), "report_path_txt": str(txt_report_path),
            "processed_files_output": {k:asdict(v) for k,v in output_fad_dict.items() if isinstance(v,FileAnalysisData)}
        }

    def _extract_events_from_text_content(self, text_content: str, source_file_path_str: str) -> List[TimelineEvent]:
        events = []; dates_found = self._extract_dates_from_text(text_content)
        file_path_obj = Path(source_file_path_str)
        for date_obj, context_snippet in dates_found:
            events.append(TimelineEvent(date=date_obj.isoformat(), description=context_snippet[:250] + ("..." if len(context_snippet)>250 else ""), source_file_path=source_file_path_str, event_type=self._classify_event_type(file_path_obj.name, context_snippet), confidence=self._calculate_confidence(context_snippet), metadata={}))
        return events

    def _extract_dates_from_text(self, text: str) -> List[Tuple[datetime, str]]:
        dates_with_context: List[Tuple[datetime, str]] = []; unique_dates_positions = {}
        for pattern_idx, pattern in enumerate(self.date_patterns):
            try:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    try:
                        date_obj = self._parse_date_match(match, pattern_idx) # Pass pattern_idx to help parser
                        if date_obj and (date_obj, match.start()) not in unique_dates_positions:
                            start = max(0, match.start() - 80); end = min(len(text), match.end() + 80)
                            context = text[start:end].strip().replace("\n", " ")
                            dates_with_context.append((date_obj, context)); unique_dates_positions[(date_obj, match.start())] = True
                    except Exception as e: self.logger.debug(f"Date parsing error for match '{match.group(0)}': {e}")
            except re.error as re_err: self.logger.error(f"Regex error with pattern '{pattern}': {re_err}"); continue
        dates_with_context.sort(key=lambda x: (x[0], text.find(x[1])))
        return dates_with_context

    def _parse_date_match(self, match_obj: re.Match, pattern_index: int) -> Optional[datetime]:
        groups = match_obj.groups()
        try:
            year, month, day = 0,0,0
            if pattern_index == 0: # DD/MM/YYYY or MM/DD/YYYY
                d1, d2, d3 = int(groups[0]), int(groups[1]), int(groups[2])
                try: return datetime(d3, d1, d2) # Try YYYY, MM, DD
                except ValueError: return datetime(d3, d2, d1) # Try YYYY, DD, MM
            elif pattern_index == 1: # YYYY/MM/DD
                return datetime(int(groups[0]), int(groups[1]), int(groups[2]))
            elif pattern_index == 2: # DD/MM/YY or MM/DD/YY
                d1, d2, d3 = int(groups[0]), int(groups[1]), int(groups[2])
                year_full = d3 + 2000 if d3 < 70 else d3 + 1900 # Heuristic for 2-digit year
                try: return datetime(year_full, d1, d2)
                except ValueError: return datetime(year_full, d2, d1)
            elif pattern_index == 3: # Month_name DD, YYYY
                month_name_full, day_str, year_str = groups[0], groups[1], groups[2]
                month_name = month_name_full.lower()[:3]
                return datetime(int(year_str), self.months[month_name], int(day_str))
            elif pattern_index == 4: # DD Month_name YYYY
                day_str, month_name_full, year_str = groups[0], groups[1], groups[2]
                month_name = month_name_full.lower()[:3]
                return datetime(int(year_str), self.months[month_name], int(day_str))
            elif pattern_index == 5: # YYYY Month_name DD
                year_str, month_name_full, day_str = groups[0], groups[1], groups[2]
                month_name = month_name_full.lower()[:3]
                return datetime(int(year_str), self.months[month_name], int(day_str))

        except (ValueError, KeyError) as e: # Catches invalid date values or month key errors
            self.logger.debug(f"Could not parse date from '{match_obj.group(0)}' with pattern {pattern_index}: {e}")
            return None
        return None

    def _classify_event_type(self, filename: str, context: str) -> str:
        context_lower = context.lower()
        if "meeting" in context_lower or "call" in context_lower: return "communication"
        if "payment" in context_lower or "invoice" in context_lower or "transfer" in context_lower : return "financial"
        if "incident" in context_lower or "report" in context_lower and "police" in context_lower : return "legal_incident"
        return "general_mention"

    def _calculate_confidence(self, context: str) -> float:
        # Basic confidence, could be more sophisticated
        if len(context) > 50 : return 0.7
        return 0.5

    def _generate_timeline_report_text(self, events: List[TimelineEvent], case_name: str) -> str:
        report_lines = [f"Timeline Report for Case: {case_name}", "="*40, ""]
        for event in events:
            report_lines.append(f"Date: {event.date}")
            report_lines.append(f"  Event: {event.description}")
            report_lines.append(f"  Source: {Path(event.source_file_path).name} (Type: {event.event_type}, Confidence: {event.confidence:.2f})")
            report_lines.append("")
        return "\n".join(report_lines)

    def create_ui_elements(self, parent_widget) -> List[tk.Widget]:
        try:
            import tkinter as tk
            from tkinter import ttk
        except ImportError:
            self.logger.warning("Tkinter not available, UI elements for TimelineAnalysisPlugin cannot be created.")
            return []
        frame = ttk.Frame(parent_widget); frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(frame, text=f"{self.name}: Extracts date-based events from file content.").pack(side=tk.LEFT, padx=2)
        # Add button to view last generated JSON if needed, or keep it simple
        return [frame]

    # UI specific methods (view_timeline_json, run_analysis_ui) would typically be more complex
    # For now, they are placeholders or simplified.
    def view_timeline_json(self):
        # This would ideally load the last generated JSON report path from plugin state
        messagebox.showinfo("View Timeline", "Functionality to view last timeline (e.g., opening the JSON) would be here.")

    def run_analysis_ui(self):
        # This is usually triggered by LCASCore. This button could allow re-running with current data.
        messagebox.showinfo("Run Timeline Analysis", "Timeline analysis is typically run as part of the main LCAS process.")
