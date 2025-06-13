#!/usr/bin/env python3
"""
Pattern Discovery Plugin for LCAS
Discovers patterns and relationships in evidence files
"""

import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
from collections import defaultdict, Counter
from dataclasses import dataclass

from lcas_core import AnalysisPlugin, UIPlugin

@dataclass
class Pattern:
    """Represents a discovered pattern"""
    pattern_type: str
    description: str
    files: List[str]
    confidence: float
    metadata: Dict[str, Any]

class PatternDiscoveryPlugin(AnalysisPlugin, UIPlugin):
    """Plugin for discovering patterns and relationships in evidence"""
    
    @property
    def name(self) -> str:
        return "Pattern Discovery"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Discovers patterns and relationships in evidence files"
    
    @property
    def dependencies(self) -> List[str]:
        return []
    
    async def initialize(self, core_app) -> bool:
        self.core = core_app
        self.logger = core_app.logger.getChild(self.name)
        
        # Pattern detection configurations
        self.name_patterns = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Full names
            r'\b[A-Z]\. [A-Z][a-z]+\b',      # Initial + last name
        ]
        
        self.phone_patterns = [
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # Phone numbers
            r'\(\d{3}\)\s?\d{3}[-.\s]?\d{4}\b',    # (XXX) XXX-XXXX
        ]
        
        self.email_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        ]
        
        self.legal_terms = [
            'plaintiff', 'defendant', 'court', 'judge', 'attorney', 'counsel',
            'motion', 'order', 'ruling', 'objection', 'evidence', 'witness',
            'testimony', 'deposition', 'discovery', 'subpoena', 'trial',
            'hearing', 'appeal', 'judgment', 'verdict', 'settlement'
        ]
        
        return True
    
    async def cleanup(self) -> None:
        pass
    
    async def analyze(self, data: Any) -> Dict[str, Any]:
        """Discover patterns in evidence files"""
        source_dir = Path(data.get("source_directory", ""))
        target_dir = Path(data.get("target_directory", ""))
        
        if not source_dir.exists():
            return {"error": "Source directory does not exist"}
        
        # Initialize pattern tracking
        all_patterns = []
        file_contents = {}
        entity_tracking = defaultdict(set)
        
        files_processed = 0
        
        # Process text files
        for file_path in source_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.doc', '.docx']:
                try:
                    content = await self._extract_file_content(file_path)
                    if content:
                        rel_path = str(file_path.relative_to(source_dir))
                        file_contents[rel_path] = content
                        
                        # Extract entities from this file
                        entities = self._extract_entities(content)
                        for entity_type, entity_values in entities.items():
                            for value in entity_values:
                                entity_tracking[entity_type].add((value, rel_path))
                        
                        files_processed += 1
                        
                except Exception as e:
                    self.logger.error(f"Error processing {file_path}: {e}")
        
        # Discover patterns
        patterns = []
        
        # 1. Name co-occurrence patterns
        name_patterns = self._find_name_cooccurrence(file_contents)
        patterns.extend(name_patterns)
        
        # 2. Communication patterns
        comm_patterns = self._find_communication_patterns(file_contents)
        patterns.extend(comm_patterns)
        
        # 3. Legal term clustering
        legal_patterns = self._find_legal_term_patterns(file_contents)
        patterns.extend(legal_patterns)
        
        # 4. Timeline patterns (if timeline data exists)
        timeline_patterns = await self._find_timeline_patterns(target_dir)
        patterns.extend(timeline_patterns)
        
        # 5. File relationship patterns
        file_patterns = self._find_file_relationship_patterns(file_contents)
        patterns.extend(file_patterns)
        
        # Sort patterns by confidence
        patterns.sort(key=lambda x: x.confidence, reverse=True)
        
        # Generate pattern report
        pattern_data = {
            "patterns": [self._pattern_to_dict(p) for p in patterns],
            "entity_summary": {
                entity_type: len(entities) 
                for entity_type, entities in entity_tracking.items()
            },
            "files_processed": files_processed,
            "total_patterns": len(patterns),
            "generated": datetime.now().isoformat()
        }
        
        # Save pattern data
        pattern_path = target_dir / "pattern_discovery.json"
        pattern_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(pattern_path, 'w') as f:
            json.dump(pattern_data, f, indent=2)
        
        # Generate pattern report
        report_content = self._generate_pattern_report(patterns, entity_tracking, data)
        report_path = target_dir / "pattern_discovery_report.txt"
        with open(report_path, 'w') as f:
            f.write(report_content)
        
        return {
            "plugin": self.name,
            "patterns_found": len(patterns),
            "files_processed": files_processed,
            "entity_types": list(entity_tracking.keys()),
            "pattern_data_path": str(pattern_path),
            "pattern_report_path": str(report_path),
            "top_patterns": [self._pattern_to_dict(p) for p in patterns[:5]],
            "status": "completed"
        }
    
    async def _extract_file_content(self, file_path: Path) -> str:
        """Extract text content from file"""
        try:
            if file_path.suffix.lower() == '.txt':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            # For other file types, basic text extraction
            return ""
        except Exception as e:
            self.logger.error(f"Error extracting content from {file_path}: {e}")
            return ""
    
    def _extract_entities(self, content: str) -> Dict[str, Set[str]]:
        """Extract named entities from content"""
        entities = defaultdict(set)
        
        # Extract names
        for pattern in self.name_patterns:
            matches = re.findall(pattern, content)
            entities['names'].update(matches)
        
        # Extract phone numbers
        for pattern in self.phone_patterns:
            matches = re.findall(pattern, content)
            entities['phone_numbers'].update(matches)
        
        # Extract email addresses
        for pattern in self.email_patterns:
            matches = re.findall(pattern, content)
            entities['emails'].update(matches)
        
        # Extract legal terms
        content_lower = content.lower()
        for term in self.legal_terms:
            if term in content_lower:
                entities['legal_terms'].add(term)
        
        return entities
    
    def _find_name_cooccurrence(self, file_contents: Dict[str, str]) -> List[Pattern]:
        """Find patterns of names appearing together"""
        patterns = []
        name_cooccurrence = defaultdict(list)
        
        # Extract all names and track their co-occurrence
        for file_path, content in file_contents.items():
            names_in_file = set()
            for pattern in self.name_patterns:
                matches = re.findall(pattern, content)
                names_in_file.update(matches)
            
            # Record co-occurrences
            names_list = list(names_in_file)
            for i, name1 in enumerate(names_list):
                for name2 in names_list[i+1:]:
                    pair = tuple(sorted([name1, name2]))
                    name_cooccurrence[pair].append(file_path)
        
        # Create patterns for significant co-occurrences
        for (name1, name2), files in name_cooccurrence.items():
            if len(files) >= 2:  # Appears together in multiple files
                confidence = min(0.9, len(files) * 0.3)
                pattern = Pattern(
                    pattern_type="name_cooccurrence",
                    description=f"Names '{name1}' and '{name2}' appear together in {len(files)} files",
                    files=files,
                    confidence=confidence,
                    metadata={
                        "name1": name1,
                        "name2": name2,
                        "cooccurrence_count": len(files)
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    def _find_communication_patterns(self, file_contents: Dict[str, str]) -> List[Pattern]:
        """Find communication-related patterns"""
        patterns = []
        
        # Track files that mention communication methods
        comm_files = defaultdict(list)
        for file_path, content in file_contents.items():
            content_lower = content.lower()
            
            if any(term in content_lower for term in ['text', 'message', 'sms', 'email', 'call', 'phone']):
                comm_files['communication'].append(file_path)
            
            if any(term in content_lower for term in ['meeting', 'appointment', 'conference']):
                comm_files['meetings'].append(file_path)
            
            if any(term in content_lower for term in ['threat', 'intimidation', 'harassment']):
                comm_files['threatening'].append(file_path)
        
        # Create patterns for communication clusters
        for comm_type, files in comm_files.items():
            if len(files) >= 2:
                confidence = min(0.8, len(files) * 0.2)
                pattern = Pattern(
                    pattern_type="communication_cluster",
                    description=f"{len(files)} files contain {comm_type}-related content",
                    files=files,
                    confidence=confidence,
                    metadata={
                        "communication_type": comm_type,
                        "file_count": len(files)
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    def _find_legal_term_patterns(self, file_contents: Dict[str, str]) -> List[Pattern]:
        """Find legal term clustering patterns"""
        patterns = []
        term_files = defaultdict(list)
        
        # Track which files contain which legal terms
        for file_path, content in file_contents.items():
            content_lower = content.lower()
            for term in self.legal_terms:
                if term in content_lower:
                    term_files[term].append(file_path)
        
        # Find terms that appear together frequently
        term_cooccurrence = defaultdict(list)
        for file_path, content in file_contents.items():
            content_lower = content.lower()
            terms_in_file = [term for term in self.legal_terms if term in content_lower]
            
            for i, term1 in enumerate(terms_in_file):
                for term2 in terms_in_file[i+1:]:
                    pair = tuple(sorted([term1, term2]))
                    term_cooccurrence[pair].append(file_path)
        
        # Create patterns for significant term co-occurrences
        for (term1, term2), files in term_cooccurrence.items():
            if len(files) >= 2:
                confidence = min(0.7, len(files) * 0.25)
                pattern = Pattern(
                    pattern_type="legal_term_cooccurrence",
                    description=f"Legal terms '{term1}' and '{term2}' appear together in {len(files)} files",
                    files=files,
                    confidence=confidence,
                    metadata={
                        "term1": term1,
                        "term2": term2,
                        "cooccurrence_count": len(files)
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _find_timeline_patterns(self, target_dir: Path) -> List[Pattern]:
        """Find timeline-based patterns"""
        patterns = []
        
        # Check if timeline analysis exists
        timeline_path = target_dir / "timeline_analysis.json"
        if not timeline_path.exists():
            return patterns
        
        try:
            with open(timeline_path, 'r') as f:
                timeline_data = json.load(f)
            
            events = timeline_data.get("events", [])
            
            # Find temporal clustering
            date_files = defaultdict(list)
            for event in events:
                event_date = event['date'][:10]  # YYYY-MM-DD
                source_file = event['source_file']
                date_files[event_date].append(source_file)
            
            # Create patterns for dates with multiple files
            for date, files in date_files.items():
                if len(files) >= 2:
                    unique_files = list(set(files))
                    if len(unique_files) >= 2:
                        confidence = min(0.8, len(unique_files) * 0.3)
                        pattern = Pattern(
                            pattern_type="temporal_clustering",
                            description=f"{len(unique_files)} files reference events on {date}",
                            files=unique_files,
                            confidence=confidence,
                            metadata={
                                "date": date,
                                "event_count": len(files),
                                "unique_files": len(unique_files)
                            }
                        )
                        patterns.append(pattern)
        
        except Exception as e:
            self.logger.error(f"Error analyzing timeline patterns: {e}")
        
        return patterns
    
    def _find_file_relationship_patterns(self, file_contents: Dict[str, str]) -> List[Pattern]:
        """Find relationships between files based on content similarity"""
        patterns = []
        
        # Simple keyword-based similarity
        file_keywords = {}
        
        for file_path, content in file_contents.items():
            # Extract significant words (longer than 4 characters)
            words = re.findall(r'\b\w{5,}\b', content.lower())
            # Count word frequency
            word_counts = Counter(words)
            # Keep top 20 most frequent words
            top_words = [word for word, count in word_counts.most_common(20)]
            file_keywords[file_path] = set(top_words)
        
        # Find files with significant keyword overlap
        file_pairs = []
        file_list = list(file_keywords.keys())
        
        for i, file1 in enumerate(file_list):
            for file2 in file_list[i+1:]:
                keywords1 = file_keywords[file1]
                keywords2 = file_keywords[file2]
                
                if keywords1 and keywords2:
                    overlap = len(keywords1.intersection(keywords2))
                    total = len(keywords1.union(keywords2))
                    
                    if total > 0:
                        similarity = overlap / total
                        if similarity > 0.3:  # 30% similarity threshold
                            file_pairs.append((file1, file2, similarity))
        
        # Create patterns for similar files
        for file1, file2, similarity in file_pairs:
            confidence = min(0.9, similarity)
            pattern = Pattern(
                pattern_type="content_similarity",
                description=f"Files '{file1}' and '{file2}' have {similarity:.1%} content similarity",
                files=[file1, file2],
                confidence=confidence,
                metadata={
                    "file1": file1,
                    "file2": file2,
                    "similarity_score": similarity
                }
            )
            patterns.append(pattern)
        
        return patterns
    
    def _pattern_to_dict(self, pattern: Pattern) -> Dict[str, Any]:
        """Convert Pattern object to dictionary"""
        return {
            "pattern_type": pattern.pattern_type,
            "description": pattern.description,
            "files": pattern.files,
            "confidence": pattern.confidence,
            "metadata": pattern.metadata
        }
    
    def _generate_pattern_report(self, patterns: List[Pattern], entity_tracking: Dict, data: Dict) -> str:
        """Generate comprehensive pattern discovery report"""
        report = "PATTERN DISCOVERY REPORT\n"
        report += "=" * 40 + "\n\n"
        
        report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"Case: {data.get('case_name', 'Unknown')}\n"
        report += f"Total Patterns Found: {len(patterns)}\n\n"
        
        # Pattern summary by type
        pattern_types = Counter(p.pattern_type for p in patterns)
        report += "PATTERN TYPES SUMMARY:\n"
        report += "-" * 25 + "\n"
        for pattern_type, count in pattern_types.items():
            report += f"{pattern_type.replace('_', ' ').title()}: {count}\n"
        report += "\n"
        
        # Entity summary
        report += "ENTITY EXTRACTION SUMMARY:\n"
        report += "-" * 30 + "\n"
        for entity_type, entities in entity_tracking.items():
            unique_values = set(item[0] for item in entities)
            report += f"{entity_type.replace('_', ' ').title()}: {len(unique_values)} unique\n"
        report += "\n"
        
        # Top patterns
        report += "TOP PATTERNS BY CONFIDENCE:\n"
        report += "-" * 35 + "\n"
        
        for i, pattern in enumerate(patterns[:10], 1):
            report += f"\n{i}. {pattern.pattern_type.replace('_', ' ').title()}\n"
            report += f"   Description: {pattern.description}\n"
            report += f"   Confidence: {pattern.confidence:.2f}\n"
            report += f"   Files Involved: {len(pattern.files)}\n"
            
            if len(pattern.files) <= 5:
                for file in pattern.files:
                    report += f"     - {file}\n"
            else:
                for file in pattern.files[:3]:
                    report += f"     - {file}\n"
                report += f"     ... and {len(pattern.files) - 3} more files\n"
            
            # Add specific metadata
            if pattern.pattern_type == "name_cooccurrence":
                report += f"   Names: {pattern.metadata['name1']} & {pattern.metadata['name2']}\n"
            elif pattern.pattern_type == "temporal_clustering":
                report += f"   Date: {pattern.metadata['date']}\n"
                report += f"   Events: {pattern.metadata['event_count']}\n"
            elif pattern.pattern_type == "content_similarity":
                score = pattern.metadata['similarity_score']
                report += f"   Similarity Score: {score:.1%}\n"
        
        # Recommendations
        report += "\n\nRECOMMendATIONS:\n"
        report += "-" * 15 + "\n"
        report += "1. Review high-confidence name co-occurrences for relationship mapping\n"
        report += "2. Investigate temporal clustering patterns for timeline coherence\n"
        report += "3. Examine content similarity patterns for duplicate or related evidence\n"
        report += "4. Cross-reference communication patterns with case arguments\n"
        report += "5. Use entity extraction results for witness and evidence lists\n"
        
        return report
    
    def create_ui_elements(self, parent_widget) -> List[tk.Widget]:
        elements = []
        
        # Main frame
        main_frame = ttk.LabelFrame(parent_widget, text="Pattern Discovery")
        main_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Options frame
        options_frame = ttk.Frame(main_frame)
        options_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Pattern type options
        self.find_names = tk.BooleanVar(value=True)
        self.find_communications = tk.BooleanVar(value=True)
        self.find_timeline = tk.BooleanVar(value=True)
        self.find_similarity = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(options_frame, text="Name Patterns", 
                       variable=self.find_names).grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Checkbutton(options_frame, text="Communication Patterns", 
                       variable=self.find_communications).grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Checkbutton(options_frame, text="Timeline Patterns", 
                       variable=self.find_timeline).grid(row=1, column=0, sticky=tk.W, padx=5)
        ttk.Checkbutton(options_frame, text="Content Similarity", 
                       variable=self.find_similarity).grid(row=1, column=1, sticky=tk.W, padx=5)
        
        # Action buttons
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(action_frame, text="🔍 Discover Patterns", 
                  command=self.run_analysis_ui).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(action_frame, text="📋 View Patterns", 
                  command=self.view_patterns).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(action_frame, text="🕸️ Pattern Map", 
                  command=self.show_pattern_map).pack(side=tk.LEFT, padx=2)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready")
        self.status_label.pack(anchor=tk.W, padx=5, pady=2)
        
        elements.extend([main_frame])
        return elements
    
    def view_patterns(self):
        """View discovered patterns"""
        if not hasattr(self, 'core'):
            return
            
        target_dir = Path(self.core.config.target_directory)
        pattern_path = target_dir / "pattern_discovery.json"
        
        if not pattern_path.exists():
            messagebox.showwarning("No Patterns", "No patterns found. Run pattern discovery first.")
            return
        
        # Create pattern viewer window
        popup = tk.Toplevel()
        popup.title("Pattern Discovery Results")
        popup.geometry("1000x700")
        
        # Create notebook for different views
        notebook = ttk.Notebook(popup)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Patterns list view
        patterns_frame = ttk.Frame(notebook)
        notebook.add(patterns_frame, text="Patterns")
        
        # Create treeview for patterns
        columns = ('Type', 'Confidence', 'Files', 'Description')
        patterns_tree = ttk.Treeview(patterns_frame, columns=columns, show='headings')
        
        for col in columns:
            patterns_tree.heading(col, text=col)
            patterns_tree.column(col, width=150)
        
        patterns_scroll = ttk.Scrollbar(patterns_frame, orient=tk.VERTICAL, command=patterns_tree.yview)
        patterns_tree.configure(yscrollcommand=patterns_scroll.set)
        
        # Entity summary view
        entities_frame = ttk.Frame(notebook)
        notebook.add(entities_frame, text="Entities")
        
        entities_text = tk.Text(entities_frame, wrap=tk.WORD)
        entities_scroll = ttk.Scrollbar(entities_frame, orient=tk.VERTICAL, command=entities_text.yview)
        entities_text.configure(yscrollcommand=entities_scroll.set)
        
        # Load and display pattern data
        try:
            with open(pattern_path, 'r') as f:
                pattern_data = json.load(f)
            
            patterns = pattern_data.get("patterns", [])
            entity_summary = pattern_data.get("entity_summary", {})
            
            # Populate patterns tree
            for pattern in patterns:
                patterns_tree.insert('', tk.END, values=(
                    pattern['pattern_type'].replace('_', ' ').title(),
                    f"{pattern['confidence']:.2f}",
                    len(pattern['files']),
                    pattern['description'][:50] + "..."
                ))
            
            # Populate entity summary
            entities_display = "ENTITY EXTRACTION SUMMARY\n"
            entities_display += "=" * 40 + "\n\n"
            
            for entity_type, count in entity_summary.items():
                entities_display += f"{entity_type.replace('_', ' ').title()}: {count} unique\n"
            
            entities_text.insert(tk.END, entities_display)
            entities_text.config(state=tk.DISABLED)
            
        except Exception as e:
            patterns_tree.insert('', tk.END, values=("Error", "N/A", "N/A", str(e)))
        
        # Pack widgets
        patterns_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        patterns_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        entities_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        entities_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def show_pattern_map(self):
        """Show a simplified pattern relationship map"""
        messagebox.showinfo("Pattern Map", "Pattern relationship mapping feature coming soon!\n\nThis will show visual connections between:\n- Names and their relationships\n- File similarities\n- Timeline connections\n- Communication patterns")
    
    def run_analysis_ui(self):
        """Run pattern discovery from UI"""
        if hasattr(self, 'core') and self.core.event_loop:
            self.status_label.config(text="Discovering patterns...")
            
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
                        self.status_label.config(text=f"Found {result['patterns_found']} patterns")
                
                if hasattr(self.core, 'root'):
                    self.core.root.after(0, update_ui)
            
            asyncio.run_coroutine_threadsafe(run_and_update(), self.core.event_loop)
