#!/usr/bin/env python3
"""
Timeline Analysis Plugin for LCAS
Builds chronological timelines from evidence files
"""

import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from dataclasses import dataclass, asdict

from lcas_core import AnalysisPlugin, UIPlugin

@dataclass
class TimelineEvent:
    """Represents a single event in the timeline"""
    date: str  # ISO format string
    description: str
    source_file: str
    event_type: str
    confidence: float
    metadata: Dict[str, Any]

class TimelineAnalysisPlugin(AnalysisPlugin, UIPlugin):
    """Plugin for building chronological timelines from evidence"""
    
    @property
    def name(self) -> str:
        return "Timeline Analysis"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Builds chronological timelines from evidence files"
    
    @property
    def dependencies(self) -> List[str]:
        return []
    
    async def initialize(self, core_app) -> bool:
        self.core = core_app
        self.logger = core_app.logger.getChild(self.name)
        
        # Date pattern regex for extracting dates from text
        self.date_patterns = [
            r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b',  # MM/DD/YYYY or MM-DD-YYYY
            r'\b(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})\b',  # YYYY/MM/DD or YYYY-MM-DD
            r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{2})\b',  # MM/DD/YY or MM-DD-YY
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b',  # Month DD, YYYY
            r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b',  # DD Month YYYY
        ]
        
        # Month name to number mapping
        self.months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        return True
    
    async def cleanup(self) -> None:
        pass
    
    async def analyze(self, data: Any) -> Dict[str, Any]:
        """Extract timeline events from files"""
        source_dir = Path(data.get("source_directory", ""))
        target_dir = Path(data.get("target_directory", ""))
        
        if not source_dir.exists():
            return {"error": "Source directory does not exist"}
        
        all_events = []
        files_processed = 0
        
        # Process text files for date extraction
        for file_path in source_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.doc', '.docx']:
                try:
                    events = await self._extract_events_from_file(file_path, source_dir)
                    all_events.extend(events)
                    files_processed += 1
                except Exception as e:
                    self.logger.error(f"Error processing {file_path}: {e}")
        
        # Sort events chronologically
        all_events.sort(key=lambda x: x.date)
        
        # Create timeline report
        timeline_data = {
            "events": [asdict(event) for event in all_events],
            "summary": {
                "total_events": len(all_events),
                "files_processed": files_processed,
                "date_range": {
                    "earliest": all_events[0].date if all_events else None,
                    "latest": all_events[-1].date if all_events else None
                }
            },
            "generated": datetime.now().isoformat()
        }
        
        # Save timeline data
        timeline_path = target_dir / "timeline_analysis.json"
        timeline_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(timeline_path, 'w') as f:
            json.dump(timeline_data, f, indent=2)
        
        # Generate timeline report
        report_content = self._generate_timeline_report(all_events, data)
        report_path = target_dir / "timeline_report.txt"
        with open(report_path, 'w') as f:
            f.write(report_content)
        
        return {
            "plugin": self.name,
            "events_found": len(all_events),
            "files_processed": files_processed,
            "timeline_data_path": str(timeline_path),
            "timeline_report_path": str(report_path),
            "events": timeline_data["events"][:10],  # Return first 10 events
            "status": "completed"
        }
    
    async def _extract_events_from_file(self, file_path: Path, source_dir: Path) -> List[TimelineEvent]:
        """Extract timeline events from a single file"""
        events = []
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extract dates from content
            dates_found = self._extract_dates_from_text(content)
            
            # Create events for each date found
            for date_obj, context in dates_found:
                event = TimelineEvent(
                    date=date_obj.isoformat(),
                    description=context[:200] + "..." if len(context) > 200 else context,
                    source_file=str(file_path.relative_to(source_dir)),
                    event_type=self._classify_event_type(file_path.name, context),
                    confidence=self._calculate_confidence(context),
                    metadata={
                        "file_size": file_path.stat().st_size,
                        "file_modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                        "extraction_method": "text_pattern_matching"
                    }
                )
                events.append(event)
        
        except Exception as e:
            self.logger.error(f"Error extracting events from {file_path}: {e}")
        
        return events
    
    def _extract_dates_from_text(self, text: str) -> List[tuple]:
        """Extract dates and their context from text"""
        dates_with_context = []
        
        for pattern in self.date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                try:
                    date_obj = self._parse_date_match(match)
                    if date_obj:
                        # Extract context around the date
                        start = max(0, match.start() - 100)
                        end = min(len(text), match.end() + 100)
                        context = text[start:end].strip()
                        
                        dates_with_context.append((date_obj, context))
                
                except Exception as e:
                    self.logger.debug(f"Error parsing date match: {e}")
                    continue
        
        return dates_with_context
    
    def _parse_date_match(self, match) -> Optional[datetime]:
        """Parse a regex match into a datetime object"""
        groups = match.groups()
        
        try:
            if len(groups) == 3:
                # Handle different date formats
                if groups[0].isdigit() and groups[1].isdigit() and groups[2].isdigit():
                    # Numeric date format
                    if len(groups[2]) == 4:  # YYYY format
                        if len(groups[0]) == 4:  # YYYY/MM/DD
                            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                        else:  # MM/DD/YYYY
                            month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                    else:  # YY format
                        month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                        year = 2000 + year if year < 50 else 1900 + year
                
                elif groups[0].isalpha():  # Month name first
                    month_name = groups[0].lower()
                    month = self.months.get(month_name)
                    day = int(groups[1])
                    year = int(groups[2])
                
                elif groups[1].isalpha():  # Month name second
                    day = int(groups[0])
                    month_name = groups[1].lower()
                    month = self.months.get(month_name)
                    year = int(groups[2])
                
                else:
                    return None
                
                # Validate date components
                if 1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2100:
                    return datetime(year, month, day)
        
        except (ValueError, TypeError):
            pass
        
        return None
    
    def _classify_event_type(self, filename: str, context: str) -> str:
        """Classify the type of event based on filename and context"""
        filename_lower = filename.lower()
        context_lower = context.lower()
        
        # Legal document types
        if any(term in filename_lower for term in ['motion', 'pleading', 'order', 'judgment']):
            return "legal_filing"
        elif any(term in filename_lower for term in ['text', 'message', 'sms', 'email']):
            return "communication"
        elif any(term in context_lower for term in ['filed', 'served', 'ordered', 'ruled']):
            return "court_action"
        elif any(term in context_lower for term in ['meeting', 'appointment', 'hearing']):
            return "event"
        elif any(term in context_lower for term in ['payment', 'transfer', 'deposit']):
            return "financial"
        else:
            return "general"
    
    def _calculate_confidence(self, context: str) -> float:
        """Calculate confidence score for the extracted event"""
        confidence = 0.5  # Base confidence
        
        # Increase confidence for specific keywords
        legal_keywords = ['filed', 'served', 'ordered', 'hearing', 'court', 'judge']
        context_lower = context.lower()
        
        for keyword in legal_keywords:
            if keyword in context_lower:
                confidence += 0.1
        
        # Cap at 1.0
        return min(confidence, 1.0)
    
    def _generate_timeline_report(self, events: List[TimelineEvent], data: Dict) -> str:
        """Generate a comprehensive timeline report"""
        report = "TIMELINE ANALYSIS REPORT\n"
        report += "=" * 50 + "\n\n"
        report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"Case: {data.get('case_name', 'Unknown')}\n"
        report += f"Total Events: {len(events)}\n\n"
        
        if events:
            report += f"Date Range: {events[0].date} to {events[-1].date}\n\n"
            
            report += "CHRONOLOGICAL EVENT TIMELINE:\n"
            report += "-" * 30 + "\n\n"
            
            current_year = None
            for event in events:
                event_date = datetime.fromisoformat(event.date)
                
                # Add year headers
                if current_year != event_date.year:
                    current_year = event_date.year
                    report += f"\n=== {current_year} ===\n\n"
                
                report += f"Date: {event_date.strftime('%B %d, %Y')}\n"
                report += f"Type: {event.event_type.replace('_', ' ').title()}\n"
                report += f"Source: {event.source_file}\n"
                report += f"Description: {event.description}\n"
                report += f"Confidence: {event.confidence:.2f}\n"
                report += "-" * 30 + "\n\n"
        
        report += "\nTIMELINE ANALYSIS SUMMARY:\n"
        report += "-" * 30 + "\n"
        
        # Event type summary
        event_types = {}
        for event in events:
            event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
        
        report += "Event Types:\n"
        for event_type, count in sorted(event_types.items()):
            report += f"  {event_type.replace('_', ' ').title()}: {count}\n"
        
        return report
    
    def create_ui_elements(self, parent_widget) -> List[tk.Widget]:
        elements = []
        
        # Main frame
        main_frame = ttk.LabelFrame(parent_widget, text="Timeline Analysis")
        main_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Action buttons
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(action_frame, text="📅 Build Timeline", 
                  command=self.run_analysis_ui).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(action_frame, text="📋 View Timeline", 
                  command=self.view_timeline).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(action_frame, text="📊 Timeline Stats", 
                  command=self.show_timeline_stats).pack(side=tk.LEFT, padx=2)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready")
        self.status_label.pack(anchor=tk.W, padx=5, pady=2)
        
        elements.extend([main_frame])
        return elements
    
    def view_timeline(self):
        """View the generated timeline"""
        if not hasattr(self, 'core'):
            return
            
        target_dir = Path(self.core.config.target_directory)
        timeline_path = target_dir / "timeline_analysis.json"
        
        if not timeline_path.exists():
            messagebox.showwarning("No Timeline", "No timeline found. Run timeline analysis first.")
            return
        
        # Create timeline viewer window
        popup = tk.Toplevel()
        popup.title("Timeline Viewer")
        popup.geometry("1000x700")
        
        # Create notebook for different views
        notebook = ttk.Notebook(popup)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Chronological view
        chrono_frame = ttk.Frame(notebook)
        notebook.add(chrono_frame, text="Chronological View")
        
        chrono_text = tk.Text(chrono_frame, wrap=tk.WORD)
        chrono_scroll = ttk.Scrollbar(chrono_frame, orient=tk.VERTICAL, command=chrono_text.yview)
        chrono_text.configure(yscrollcommand=chrono_scroll.set)
        
        # Event list view
        events_frame = ttk.Frame(notebook)
        notebook.add(events_frame, text="Event List")
        
        # Create treeview for events
        columns = ('Date', 'Type', 'Source', 'Confidence')
        events_tree = ttk.Treeview(events_frame, columns=columns, show='tree headings')
        events_tree.heading('#0', text='Description')
        for col in columns:
            events_tree.heading(col, text=col)
        
        events_scroll = ttk.Scrollbar(events_frame, orient=tk.VERTICAL, command=events_tree.yview)
        events_tree.configure(yscrollcommand=events_scroll.set)
        
        # Load and display timeline data
        try:
            with open(timeline_path, 'r') as f:
                timeline_data = json.load(f)
            
            events = timeline_data.get("events", [])
            
            # Populate chronological view
            chrono_display = "CHRONOLOGICAL TIMELINE\n"
            chrono_display += "=" * 50 + "\n\n"
            
            for event in events:
                event_date = datetime.fromisoformat(event['date'])
                chrono_display += f"📅 {event_date.strftime('%B %d, %Y')}\n"
                chrono_display += f"📝 {event['description'][:100]}...\n"
                chrono_display += f"📁 Source: {event['source_file']}\n"
                chrono_display += f"🏷️ Type: {event['event_type'].replace('_', ' ').title()}\n"
                chrono_display += f"⭐ Confidence: {event['confidence']:.2f}\n"
                chrono_display += "-" * 50 + "\n\n"
            
            chrono_text.insert(tk.END, chrono_display)
            chrono_text.config(state=tk.DISABLED)
            
            # Populate events tree
            for event in events:
                event_date = datetime.fromisoformat(event['date'])
                events_tree.insert('', tk.END, 
                                 text=event['description'][:50] + "...",
                                 values=(
                                     event_date.strftime('%Y-%m-%d'),
                                     event['event_type'].replace('_', ' ').title(),
                                     event['source_file'],
                                     f"{event['confidence']:.2f}"
                                 ))
            
        except Exception as e:
            chrono_text.insert(tk.END, f"Error loading timeline: {e}")
        
        # Pack widgets
        chrono_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        chrono_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        events_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        events_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def show_timeline_stats(self):
        """Show timeline statistics"""
        if not hasattr(self, 'core'):
            return
            
        target_dir = Path(self.core.config.target_directory)
        timeline_path = target_dir / "timeline_analysis.json"
        
        if not timeline_path.exists():
            messagebox.showwarning("No Timeline", "No timeline found. Run timeline analysis first.")
            return
        
        try:
            with open(timeline_path, 'r') as f:
                timeline_data = json.load(f)
            
            summary = timeline_data.get("summary", {})
            events = timeline_data.get("events", [])
            
            # Calculate additional stats
            event_types = {}
            confidence_sum = 0
            
            for event in events:
                event_type = event['event_type']
                event_types[event_type] = event_types.get(event_type, 0) + 1
                confidence_sum += event['confidence']
            
            avg_confidence = confidence_sum / len(events) if events else 0
            
            stats_text = f"""TIMELINE STATISTICS
================================

Total Events: {summary.get('total_events', 0)}
Files Processed: {summary.get('files_processed', 0)}
Average Confidence: {avg_confidence:.2f}

Date Range:
  Earliest: {summary.get('date_range', {}).get('earliest', 'N/A')}
  Latest: {summary.get('date_range', {}).get('latest', 'N/A')}

Event Types:
"""
            
            for event_type, count in sorted(event_types.items()):
                stats_text += f"  {event_type.replace('_', ' ').title()}: {count}\n"
            
            messagebox.showinfo("Timeline Statistics", stats_text)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading timeline statistics: {e}")
    
    def run_analysis_ui(self):
        """Run timeline analysis from UI"""
        if hasattr(self, 'core') and self.core.event_loop:
            self.status_label.config(text="Building timeline...")
            
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
                        self.status_label.config(text=f"Found {result['events_found']} events")
                
                if hasattr(self.core, 'root'):
                    self.core.root.after(0, update_ui)
            
            asyncio.run_coroutine_threadsafe(run_and_update(), self.core.event_loop)
