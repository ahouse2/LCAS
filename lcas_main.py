#!/usr/bin/env python3
"""
Legal Case-Building and Analysis System (LCAS)
Main Application Module

This system organizes, analyzes, and scores legal evidence for court case preparation.
Designed with a modular architecture for easy maintenance and extension.
"""

import os
import sys
import json
import logging
import argparse
import hashlib
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('lcas.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

@dataclass
class LCASConfig:
    """Configuration settings for LCAS"""
    source_directory: str
    target_directory: str
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    
    # Analysis settings
    min_probative_score: float = 0.3
    min_relevance_score: float = 0.5
    similarity_threshold: float = 0.85
    
    # Scoring weights
    probative_weight: float = 0.4
    relevance_weight: float = 0.3
    admissibility_weight: float = 0.3
    
    # Folder structure - based on legal arguments
    folder_structure: Dict[str, List[str]] = None
    
    def __post_init__(self):
        if self.folder_structure is None:
            self.folder_structure = {
                "01_CASE_SUMMARIES_AND_RELATED_DOCS": [
                    "AUTHORITIES",
                    "DETAILED_ANALYSIS_OF_ARGUMENTS", 
                    "STATUTES"
                ],
                "02_CONSTITUTIONAL_VIOLATIONS": [
                    "PEREMPTORY_CHALLENGE"
                ],
                "03_ELECTRONIC_ABUSE": [],
                "04_FRAUD_ON_THE_COURT": [
                    "ATTORNEY_MISCONDUCT_MARK",
                    "CURATED_TEXT_RECORD", 
                    "EVIDENCE_MANIPULATION",
                    "EVIDENCE_OF_SOBRIETY",
                    "EX_PARTE_COMMUNICATIONS",
                    "JUDICIAL_MISCONDUCT",
                    "NULL_AGREEMENT",
                    "PHYSICAL_ASSAULTS_AND_COERCIVE_CONTROL"
                ],
                "05_NON_DISCLOSURE_FC2107_FC2122": [],
                "06_PD065288_COURT_RECORD_DOCS": [],
                "07_POST_TRIAL_ABUSE": [],
                "08_TEXT_MESSAGES": [
                    "SHANE_TO_FRIENDS",
                    "SHANE_TO_KATHLEEN_MCCABE", 
                    "SHANE_TO_LISA",
                    "SHANE_TO_MARK_ZUCKER",
                    "SHANE_TO_RHONDA_ZUCKER"
                ],
                "09_FOR_HUMAN_REVIEW": [],
                "10_VISUALIZATIONS_AND_REPORTS": [],
                "00_ORIGINAL_FILES": []  # For preserving originals
            }

class FileAnalysis:
    """Data structure for file analysis results"""
    def __init__(self):
        self.original_path: str = ""
        self.original_name: str = ""
        self.new_name: str = ""
        self.target_path: str = ""
        self.file_hash: str = ""
        self.file_size: int = 0
        self.file_type: str = ""
        self.created_date: datetime = None
        self.modified_date: datetime = None
        self.processing_date: datetime = datetime.now()
        
        # Content analysis
        self.content: str = ""
        self.summary: str = ""
        self.entities: List[str] = []
        self.keywords: List[str] = []
        
        # Categorization
        self.category: str = ""
        self.subcategory: str = ""
        self.confidence_score: float = 0.0
        
        # Legal scoring
        self.probative_value: float = 0.0
        self.prejudicial_value: float = 0.0
        self.relevance_score: float = 0.0
        self.admissibility_score: float = 0.0
        self.overall_impact: float = 0.0
        
        # Flags
        self.is_duplicate: bool = False
        self.duplicate_of: str = ""
        self.requires_human_review: bool = False
        self.processing_errors: List[str] = []

class LCASCore:
    """Core engine for the Legal Case Analysis System"""
    
    def __init__(self, config: LCASConfig):
        self.config = config
        self.plugins = {}
        self.processed_files: Dict[str, FileAnalysis] = {}
        self.file_hashes: Dict[str, str] = {}  # hash -> original_path
        self.category_keywords = self._initialize_category_keywords()
        
        # Ensure target directory exists
        Path(self.config.target_directory).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"LCAS initialized with source: {config.source_directory}")
        logger.info(f"Target directory: {config.target_directory}")
    
    def _initialize_category_keywords(self) -> Dict[str, List[str]]:
        """Initialize keyword mappings for categorization"""
        return {
            "CASE_SUMMARIES_AND_RELATED_DOCS": [
                "summary", "overview", "timeline", "chronology", "authorities", 
                "statute", "law", "code", "analysis", "argument"
            ],
            "CONSTITUTIONAL_VIOLATIONS": [
                "constitutional", "due process", "peremptory", "challenge", 
                "bias", "impartial", "fair trial"
            ],
            "ELECTRONIC_ABUSE": [
                "spyware", "monitoring", "electronic", "surveillance", "tracking",
                "computer", "phone", "device", "hack", "access"
            ],
            "FRAUD_ON_THE_COURT": [
                "fraud", "perjury", "false", "lie", "deception", "manipulation",
                "evidence", "exhibit", "misconduct", "ex parte", "communication"
            ],
            "NON_DISCLOSURE_FC2107_FC2122": [
                "financial", "disclosure", "asset", "income", "property", 
                "bank", "account", "cryptocurrency", "bitcoin", "coinbase"
            ],
            "TEXT_MESSAGES": [
                "text", "message", "sms", "chat", "conversation", "whatsapp",
                "imessage", "communication"
            ],
            "POST_TRIAL_ABUSE": [
                "post trial", "after", "continued", "ongoing", "harassment",
                "violation", "contempt"
            ]
        }
    
    def register_plugin(self, name: str, plugin_instance):
        """Register a plugin with the core system"""
        self.plugins[name] = plugin_instance
        logger.info(f"Registered plugin: {name}")
    
    def create_folder_structure(self):
        """Create the standardized folder structure for evidence organization"""
        logger.info("Creating folder structure...")
        
        for main_folder, subfolders in self.config.folder_structure.items():
            main_path = Path(self.config.target_directory) / main_folder
            main_path.mkdir(parents=True, exist_ok=True)
            
            # Create index file for main folder
            self._create_folder_index(main_path, main_folder)
            
            # Create subfolders
            for subfolder in subfolders:
                sub_path = main_path / subfolder
                sub_path.mkdir(parents=True, exist_ok=True)
                self._create_folder_index(sub_path, subfolder)
        
        logger.info("Folder structure created successfully")
    
    def _create_folder_index(self, folder_path: Path, folder_name: str):
        """Create an index file for a folder"""
        index_file = folder_path / "folder_index.md"
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(f"# {folder_name.replace('_', ' ').title()}\n\n")
            f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Purpose\n\n")
            f.write(f"This folder contains evidence related to: {folder_name.replace('_', ' ').title()}\n\n")
            f.write("## Files\n\n")
            f.write("Files will be listed here after processing.\n\n")
            f.write("## Statistics\n\n")
            f.write("- Total Files: 0\n")
            f.write("- Average Relevance Score: N/A\n")
            f.write("- Average Admissibility Score: N/A\n")
            f.write("- Folder Argument Strength: N/A\n\n")
    
    def discover_files(self) -> List[Path]:
        """Discover all files in the source directory"""
        logger.info(f"Discovering files in {self.config.source_directory}")
        
        files = []
        source_path = Path(self.config.source_directory)
        
        if not source_path.exists():
            logger.error(f"Source directory does not exist: {self.config.source_directory}")
            return files
        
        # Supported file extensions
        supported_extensions = {
            '.pdf', '.docx', '.doc', '.txt', '.rtf', '.xlsx', '.xls', '.csv',
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.eml', '.msg'
        }
        
        for file_path in source_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                files.append(file_path)
        
        logger.info(f"Discovered {len(files)} supported files")
        return files
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            return ""
    
    def extract_basic_info(self, file_path: Path) -> FileAnalysis:
        """Extract basic file information"""
        analysis = FileAnalysis()
        
        try:
            analysis.original_path = str(file_path)
            analysis.original_name = file_path.name
            analysis.file_hash = self.calculate_file_hash(file_path)
            
            stat = file_path.stat()
            analysis.file_size = stat.st_size
            analysis.created_date = datetime.fromtimestamp(stat.st_ctime)
            analysis.modified_date = datetime.fromtimestamp(stat.st_mtime)
            
            # Determine file type
            extension = file_path.suffix.lower()
            type_mapping = {
                '.pdf': 'PDF Document',
                '.docx': 'Word Document', '.doc': 'Word Document',
                '.txt': 'Text File', '.rtf': 'Rich Text Format',
                '.xlsx': 'Excel Spreadsheet', '.xls': 'Excel Spreadsheet',
                '.csv': 'CSV File',
                '.png': 'Image', '.jpg': 'Image', '.jpeg': 'Image',
                '.gif': 'Image', '.bmp': 'Image', '.tiff': 'Image',
                '.eml': 'Email', '.msg': 'Email'
            }
            analysis.file_type = type_mapping.get(extension, 'Unknown')
            
        except Exception as e:
            analysis.processing_errors.append(f"Error extracting basic info: {str(e)}")
            logger.error(f"Error extracting basic info for {file_path}: {e}")
        
        return analysis
    
    def preserve_original_file(self, file_path: Path) -> str:
        """Create a preserved copy of the original file"""
        try:
            preserve_dir = Path(self.config.target_directory) / "00_ORIGINAL_FILES"
            preserve_dir.mkdir(parents=True, exist_ok=True)
            
            # Maintain directory structure in preserved copy
            source_root = Path(self.config.source_directory)
            relative_path = file_path.relative_to(source_root)
            preserved_path = preserve_dir / relative_path
            
            # Create necessary directories
            preserved_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(file_path, preserved_path)
            
            return str(preserved_path)
        
        except Exception as e:
            logger.error(f"Error preserving original file {file_path}: {e}")
            return ""
    
    def categorize_file(self, analysis: FileAnalysis) -> Tuple[str, str, float]:
        """Categorize a file based on content and keywords"""
        content_lower = (analysis.content + " " + analysis.original_name).lower()
        
        best_category = "09_FOR_HUMAN_REVIEW"
        best_subcategory = ""
        best_score = 0.0
        
        for category, keywords in self.category_keywords.items():
            score = 0.0
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    score += 1.0
            
            # Normalize by number of keywords
            normalized_score = score / len(keywords) if keywords else 0.0
            
            if normalized_score > best_score:
                best_score = normalized_score
                # Map to actual folder names
                if category == "CASE_SUMMARIES_AND_RELATED_DOCS":
                    best_category = "01_CASE_SUMMARIES_AND_RELATED_DOCS"
                elif category == "CONSTITUTIONAL_VIOLATIONS":
                    best_category = "02_CONSTITUTIONAL_VIOLATIONS"
                elif category == "ELECTRONIC_ABUSE":
                    best_category = "03_ELECTRONIC_ABUSE"
                elif category == "FRAUD_ON_THE_COURT":
                    best_category = "04_FRAUD_ON_THE_COURT"
                elif category == "NON_DISCLOSURE_FC2107_FC2122":
                    best_category = "05_NON_DISCLOSURE_FC2107_FC2122"
                elif category == "TEXT_MESSAGES":
                    best_category = "08_TEXT_MESSAGES"
                elif category == "POST_TRIAL_ABUSE":
                    best_category = "07_POST_TRIAL_ABUSE"
        
        # Additional logic for specific subcategories
        if best_category == "08_TEXT_MESSAGES":
            content_lower = analysis.content.lower()
            if "shane" in content_lower and "lisa" in content_lower:
                best_subcategory = "SHANE_TO_LISA"
            elif "shane" in content_lower and "mark" in content_lower:
                best_subcategory = "SHANE_TO_MARK_ZUCKER"
            elif "shane" in content_lower and "rhonda" in content_lower:
                best_subcategory = "SHANE_TO_RHONDA_ZUCKER"
        
        return best_category, best_subcategory, best_score
    
    def generate_standardized_name(self, analysis: FileAnalysis) -> str:
        """Generate a standardized filename"""
        # Extract date if available
        date_prefix = ""
        if analysis.created_date:
            date_prefix = analysis.created_date.strftime("%y%m%d")
        
        # Category code
        category_codes = {
            "01_CASE_SUMMARIES_AND_RELATED_DOCS": "CSRD",
            "02_CONSTITUTIONAL_VIOLATIONS": "CONV",
            "03_ELECTRONIC_ABUSE": "ELAB",
            "04_FRAUD_ON_THE_COURT": "FOTC",
            "05_NON_DISCLOSURE_FC2107_FC2122": "NDIS",
            "06_PD065288_COURT_RECORD_DOCS": "CREC",
            "07_POST_TRIAL_ABUSE": "PTAB",
            "08_TEXT_MESSAGES": "TMSG",
            "09_FOR_HUMAN_REVIEW": "HRV"
        }
        
        category_code = category_codes.get(analysis.category, "UNK")
        
        # Generate descriptive title from content
        if analysis.summary:
            words = analysis.summary.split()[:5]  # First 5 words
            descriptive_title = "_".join(word.strip(".,!?") for word in words)
        else:
            # Use original filename without extension
            descriptive_title = Path(analysis.original_name).stem
        
        # Clean up title
        descriptive_title = "".join(c for c in descriptive_title if c.isalnum() or c in "_-")
        descriptive_title = descriptive_title[:30]  # Limit length
        
        # Get original extension
        extension = Path(analysis.original_name).suffix
        
        # Construct new name
        if date_prefix:
            new_name = f"{date_prefix}-{category_code}-{descriptive_title}{extension}"
        else:
            new_name = f"{category_code}-{descriptive_title}{extension}"
        
        return new_name
    
    def calculate_legal_scores(self, analysis: FileAnalysis) -> FileAnalysis:
        """Calculate legal scoring for a file"""
        content_lower = analysis.content.lower()
        
        # Probative value - how much does this prove/support the argument
        probative_keywords = [
            'evidence', 'proof', 'document', 'record', 'statement', 'testimony',
            'admission', 'confession', 'agreement', 'contract', 'receipt'
        ]
        probative_score = sum(1 for keyword in probative_keywords if keyword in content_lower)
        analysis.probative_value = min(probative_score / 5.0, 1.0)  # Normalize to 0-1
        
        # Prejudicial value - how much might this unfairly influence
        prejudicial_keywords = [
            'addiction', 'abuse', 'violence', 'criminal', 'arrest', 'drugs',
            'alcohol', 'treatment', 'therapy', 'mental', 'psychiatric'
        ]
        prejudicial_score = sum(1 for keyword in prejudicial_keywords if keyword in content_lower)
        analysis.prejudicial_value = min(prejudicial_score / 5.0, 1.0)
        
        # Relevance score - based on category match confidence
        analysis.relevance_score = analysis.confidence_score
        
        # Admissibility score - based on document type and source
        if analysis.file_type in ['PDF Document', 'Word Document']:
            analysis.admissibility_score = 0.8  # Usually admissible
        elif analysis.file_type in ['Email', 'Text File']:
            analysis.admissibility_score = 0.6  # May have authentication issues
        elif analysis.file_type == 'Image':
            analysis.admissibility_score = 0.4  # Depends on content
        else:
            analysis.admissibility_score = 0.5
        
        # Check for privileged content that might reduce admissibility
        if any(term in content_lower for term in ['attorney', 'lawyer', 'privileged', 'confidential']):
            analysis.admissibility_score *= 0.7
        
        # Overall impact score
        weights = self.config
        analysis.overall_impact = (
            analysis.probative_value * weights.probative_weight +
            analysis.relevance_score * weights.relevance_weight +
            analysis.admissibility_score * weights.admissibility_weight
        ) - (analysis.prejudicial_value * 0.1)  # Slight penalty for prejudicial content
        
        analysis.overall_impact = max(0.0, min(1.0, analysis.overall_impact))
        
        return analysis
    
    def process_single_file(self, file_path: Path) -> FileAnalysis:
        """Process a single file through the complete pipeline"""
        logger.info(f"Processing: {file_path.name}")
        
        # Extract basic information
        analysis = self.extract_basic_info(file_path)
        
        # Preserve original file
        preserved_path = self.preserve_original_file(file_path)
        if preserved_path:
            analysis.preserved_path = preserved_path
        
        # Check for duplicates
        if analysis.file_hash in self.file_hashes:
            analysis.is_duplicate = True
            analysis.duplicate_of = self.file_hashes[analysis.file_hash]
            logger.info(f"Duplicate detected: {file_path.name}")
        else:
            self.file_hashes[analysis.file_hash] = str(file_path)
        
        # Extract content (basic text extraction for now)
        try:
            if file_path.suffix.lower() == '.txt':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    analysis.content = f.read()[:5000]  # First 5000 chars
            # TODO: Add PDF, DOCX extraction in plugins
        except Exception as e:
            analysis.processing_errors.append(f"Content extraction error: {str(e)}")
        
        # Generate summary (basic for now)
        if analysis.content:
            sentences = analysis.content.split('.')[:3]  # First 3 sentences
            analysis.summary = '. '.join(sentences).strip()
        
        # Categorize file
        category, subcategory, confidence = self.categorize_file(analysis)
        analysis.category = category
        analysis.subcategory = subcategory
        analysis.confidence_score = confidence
        
        # Generate new name
        analysis.new_name = self.generate_standardized_name(analysis)
        
        # Calculate legal scores
        analysis = self.calculate_legal_scores(analysis)
        
        # Determine if human review is needed
        if (analysis.confidence_score < self.config.min_relevance_score or 
            analysis.overall_impact < self.config.min_probative_score or
            len(analysis.processing_errors) > 0):
            analysis.requires_human_review = True
            analysis.category = "09_FOR_HUMAN_REVIEW"
        
        return analysis
    
    def organize_processed_files(self):
        """Move processed files to their categorized folders"""
        logger.info("Organizing files into folder structure...")
        
        organized_count = 0
        
        for file_path, analysis in self.processed_files.items():
            try:
                # Skip duplicates unless they support different arguments
                if analysis.is_duplicate and not self._should_keep_duplicate(analysis):
                    continue
                
                # Determine target folder
                target_folder = Path(self.config.target_directory) / analysis.category
                if analysis.subcategory:
                    target_folder = target_folder / analysis.subcategory
                
                # Ensure target folder exists
                target_folder.mkdir(parents=True, exist_ok=True)
                
                # Copy file to target location
                original_file = Path(file_path)
                target_file = target_folder / analysis.new_name
                
                if original_file.exists():
                    shutil.copy2(original_file, target_file)
                    analysis.target_path = str(target_file)
                    organized_count += 1
                    
                    # Update folder index
                    self._update_folder_index(target_folder, analysis)
                
            except Exception as e:
                logger.error(f"Error organizing file {file_path}: {e}")
                continue
        
        logger.info(f"File organization completed. Organized {organized_count} files")
    
    def _should_keep_duplicate(self, analysis: FileAnalysis) -> bool:
        """Determine if a duplicate file should be kept"""
        # Keep duplicates if they have high legal value or support different arguments
        return (analysis.overall_impact > 0.7 or 
                analysis.probative_value > 0.8)
    
    def _update_folder_index(self, folder_path: Path, analysis: FileAnalysis):
        """Update folder index with file information"""
        index_file = folder_path / "folder_index.md"
        
        # Read existing content
        existing_content = ""
        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                existing_content = f.read()
        
        # Update or append file information
        file_entry = f"""
### {analysis.new_name}
- **Original Name**: {analysis.original_name}
- **File Type**: {analysis.file_type}
- **Summary**: {analysis.summary[:200]}...
- **Relevance Score**: {analysis.relevance_score:.2f}
- **Probative Value**: {analysis.probative_value:.2f}
- **Admissibility Score**: {analysis.admissibility_score:.2f}
- **Overall Impact**: {analysis.overall_impact:.2f}
- **Processing Date**: {analysis.processing_date.strftime('%Y-%m-%d %H:%M:%S')}

"""
        
        # Simple append for now (in production, would parse and update)
        with open(index_file, 'a', encoding='utf-8') as f:
            f.write(file_entry)
    
    def run_complete_analysis(self):
        """Run the complete LCAS analysis pipeline"""
        logger.info("Starting complete LCAS analysis...")
        
        try:
            # Step 1: Create folder structure
            self.create_folder_structure()
            
            # Step 2: Discover files
            files = self.discover_files()
            
            if not files:
                logger.warning("No files found to process")
                return
            
            # Step 3: Process each file
            total_files = len(files)
            for i, file_path in enumerate(files, 1):
                logger.info(f"Processing file {i}/{total_files}: {file_path.name}")
                analysis = self.process_single_file(file_path)
                self.processed_files[str(file_path)] = analysis
            
            # Step 4: Organize files
            self.organize_processed_files()
            
            # Step 5: Generate reports
            self.generate_final_reports()
            
            logger.info("LCAS analysis completed successfully")
            
        except Exception as e:
            logger.error(f"Error during LCAS analysis: {str(e)}")
            raise
    
    def generate_final_reports(self):
        """Generate comprehensive analysis reports"""
        logger.info("Generating final reports...")
        
        reports_dir = Path(self.config.target_directory) / "10_VISUALIZATIONS_AND_REPORTS"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate summary statistics
        self._generate_summary_report(reports_dir)
        
        # Generate folder strength report
        self._generate_folder_strength_report(reports_dir)
        
        # Generate duplicate files report
        self._generate_duplicate_report(reports_dir)
    
    def _generate_summary_report(self, reports_dir: Path):
        """Generate overall summary report"""
        total_files = len(self.processed_files)
        categorized_files = sum(1 for a in self.processed_files.values() 
                               if a.category != "09_FOR_HUMAN_REVIEW")
        
        avg_relevance = sum(a.relevance_score for a in self.processed_files.values()) / total_files
        avg_impact = sum(a.overall_impact for a in self.processed_files.values()) / total_files
        
        report_content = f"""# LCAS Analysis Summary Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overall Statistics
- **Total Files Processed**: {total_files}
- **Successfully Categorized**: {categorized_files}
- **Requiring Human Review**: {total_files - categorized_files}
- **Average Relevance Score**: {avg_relevance:.2f}
- **Average Overall Impact Score**: {avg_impact:.2f}

## Category Distribution
"""
        
        # Add category distribution
        category_counts = {}
        for analysis in self.processed_files.values():
            category = analysis.category
            if category not in category_counts:
                category_counts[category] = 0
            category_counts[category] += 1
        
        for category, count in sorted(category_counts.items()):
            report_content += f"- **{category.replace('_', ' ').title()}**: {count} files\n"
        
        # Write report
        with open(reports_dir / "analysis_summary.md", 'w', encoding='utf-8') as f:
            f.write(report_content)
    
    def _generate_folder_strength_report(self, reports_dir: Path):
        """Generate argument strength analysis by folder"""
        folder_stats = {}
        
        for analysis in self.processed_files.values():
            category = analysis.category
            if category not in folder_stats:
                folder_stats[category] = {
                    'count': 0,
                    'total_impact': 0.0,
                    'total_relevance': 0.0,
                    'high_impact_files': 0
                }
            
            stats = folder_stats[category]
            stats['count'] += 1
            stats['total_impact'] += analysis.overall_impact
            stats['total_relevance'] += analysis.relevance_score
            if analysis.overall_impact > 0.7:
                stats['high_impact_files'] += 1
        
        report_content = f"""# Argument Strength Analysis

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This report analyzes the strength of evidence for each legal argument category.

## Folder Strength Rankings

"""
        
        # Calculate and rank folder strengths
        folder_rankings = []
        for category, stats in folder_stats.items():
            if stats['count'] > 0:
                avg_impact = stats['total_impact'] / stats['count']
                avg_relevance = stats['total_relevance'] / stats['count']
                high_impact_ratio = stats['high_impact_files'] / stats['count']
                
                # Calculate overall folder strength
                folder_strength = (avg_impact * 0.5 + avg_relevance * 0.3 + high_impact_ratio * 0.2)
                
                folder_rankings.append({
                    'category': category,
                    'strength': folder_strength,
                    'count': stats['count'],
                    'avg_impact': avg_impact,
                    'avg_relevance': avg_relevance,
                    'high_impact_files': stats['high_impact_files']
                })
        
        # Sort by strength
        folder_rankings.sort(key=lambda x: x['strength'], reverse=True)
        
        for i, folder in enumerate(folder_rankings, 1):
            category_name = folder['category'].replace('_', ' ').title()
            report_content += f"""
### {i}. {category_name}
- **Overall Strength Score**: {folder['strength']:.2f}/1.0
- **File Count**: {folder['count']}
- **Average Impact Score**: {folder['avg_impact']:.2f}
- **Average Relevance Score**: {folder['avg_relevance']:.2f}
- **High Impact Files**: {folder['high_impact_files']} ({folder['high_impact_files']/folder['count']*100:.1f}%)

"""
        
        # Add recommendations
        report_content += """
## Recommendations

### Strongest Arguments (Score > 0.7)
"""
        strong_args = [f for f in folder_rankings if f['strength'] > 0.7]
        if strong_args:
            for folder in strong_args:
                category_name = folder['category'].replace('_', ' ').title()
                report_content += f"- **{category_name}**: Well-supported with {folder['count']} files\n"
        else:
            report_content += "- No arguments currently score above 0.7. Consider strengthening evidence.\n"
        
        report_content += """
### Areas Needing Attention (Score < 0.5)
"""
        weak_args = [f for f in folder_rankings if f['strength'] < 0.5]
        if weak_args:
            for folder in weak_args:
                category_name = folder['category'].replace('_', ' ').title()
                report_content += f"- **{category_name}**: May need additional evidence or review\n"
        else:
            report_content += "- All argument categories have adequate support.\n"
        
        # Write report
        with open(reports_dir / "argument_strength_analysis.md", 'w', encoding='utf-8') as f:
            f.write(report_content)
    
    def _generate_duplicate_report(self, reports_dir: Path):
        """Generate duplicate files report"""
        duplicates = []
        for analysis in self.processed_files.values():
            if analysis.is_duplicate:
                duplicates.append(analysis)
        
        report_content = f"""# Duplicate Files Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- **Total Duplicate Files**: {len(duplicates)}

## Duplicate Files Details

"""
        
        for dup in duplicates:
            report_content += f"""
### {dup.original_name}
- **Hash**: {dup.file_hash[:16]}...
- **Duplicate Of**: {dup.duplicate_of}
- **Overall Impact**: {dup.overall_impact:.2f}
- **Action Taken**: {'Kept (high value)' if dup.overall_impact > 0.7 else 'Removed'}

"""
        
        # Write report
        with open(reports_dir / "duplicate_files_report.md", 'w', encoding='utf-8') as f:
            f.write(report_content)
    
    def save_analysis_results(self):
        """Save detailed analysis results to JSON"""
        results_file = Path(self.config.target_directory) / "analysis_results.json"
        
        # Convert to serializable format
        serializable_results = {}
        for path, analysis in self.processed_files.items():
            result = {
                'original_path': analysis.original_path,
                'original_name': analysis.original_name,
                'new_name': analysis.new_name,
                'target_path': analysis.target_path,
                'file_hash': analysis.file_hash,
                'file_size': analysis.file_size,
                'file_type': analysis.file_type,
                'created_date': analysis.created_date.isoformat() if analysis.created_date else None,
                'modified_date': analysis.modified_date.isoformat() if analysis.modified_date else None,
                'processing_date': analysis.processing_date.isoformat(),
                'content_preview': analysis.content[:500] if analysis.content else "",
                'summary': analysis.summary,
                'entities': analysis.entities,
                'keywords': analysis.keywords,
                'category': analysis.category,
                'subcategory': analysis.subcategory,
                'confidence_score': analysis.confidence_score,
                'probative_value': analysis.probative_value,
                'prejudicial_value': analysis.prejudicial_value,
                'relevance_score': analysis.relevance_score,
                'admissibility_score': analysis.admissibility_score,
                'overall_impact': analysis.overall_impact,
                'is_duplicate': analysis.is_duplicate,
                'duplicate_of': analysis.duplicate_of,
                'requires_human_review': analysis.requires_human_review,
                'processing_errors': analysis.processing_errors
            }
            serializable_results[path] = result
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Analysis results saved to {results_file}")

def load_config(config_file: str) -> LCASConfig:
    """Load configuration from file"""
    if Path(config_file).exists():
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        return LCASConfig(**config_data)
    else:
        logger.warning(f"Config file {config_file} not found, using defaults")
        return LCASConfig(
            source_directory=r"F:\POST TRIAL DIVORCE",
            target_directory=r"G:\LCAS_ANALYSIS_RESULTS"
        )

def create_default_config(config_file: str, source_dir: str = None, target_dir: str = None):
    """Create a default configuration file"""
    config = LCASConfig(
        source_directory=source_dir or r"F:\POST TRIAL DIVORCE",
        target_directory=target_dir or r"G:\LCAS_ANALYSIS_RESULTS"
    )
    
    with open(config_file, 'w') as f:
        json.dump(asdict(config), f, indent=2)
    
    print(f"Default configuration created: {config_file}")

def main():
    """Main entry point for LCAS"""
    parser = argparse.ArgumentParser(description="Legal Case-Building and Analysis System")
    parser.add_argument("--config", default="lcas_config.json", help="Configuration file path")
    parser.add_argument("--source", help="Source directory path")
    parser.add_argument("--target", help="Target directory path")
    parser.add_argument("--create-config", action="store_true", help="Create default configuration file")
    
    args = parser.parse_args()
    
    if args.create_config:
        create_default_config(args.config, args.source, args.target)
        return
    
    # Load configuration
    config = load_config(args.config)
    
    # Override with command line arguments if provided
    if args.source:
        config.source_directory = args.source
    if args.target:
        config.target_directory = args.target
    
    # Initialize LCAS
    lcas = LCASCore(config)
    
    # TODO: Register plugins here when they're implemented
    # lcas.register_plugin('content_extraction', ContentExtractionPlugin(config))
    # lcas.register_plugin('nlp_analysis', NLPAnalysisPlugin(config))
    # etc.
    
    # Run complete analysis
    try:
        lcas.run_complete_analysis()
        lcas.save_analysis_results()
        
        print("\n" + "="*60)
        print("LCAS ANALYSIS COMPLETED SUCCESSFULLY")
        print("="*60)
        print(f"Results saved to: {config.target_directory}")
        print(f"Check the following for reports:")
        print(f"  - 10_VISUALIZATIONS_AND_REPORTS/analysis_summary.md")
        print(f"  - 10_VISUALIZATIONS_AND_REPORTS/argument_strength_analysis.md")
        print(f"  - analysis_results.json (detailed data)")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"\nAnalysis failed with error: {e}")
        print("Check lcas.log for detailed error information")

if __name__ == "__main__":
    main()