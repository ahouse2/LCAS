#!/usr/bin/env python3
"""
Legal Case-Building and Analysis System (LCAS) - Enhanced with AI Integration
Main Application Module

This system organizes, analyzes, and scores legal evidence for court case preparation.
Designed with a modular architecture for easy maintenance and extension.
Now includes AI-powered analysis capabilities with rate limiting and user customization.
"""

import os
import sys
import json
import logging
import argparse
import hashlib
import shutil
import asyncio
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
import pandas as pd

# AI Integration imports
try:
    from ai_foundation_plugin import create_ai_plugin, AIAnalysisResult
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    logging.warning("AI Foundation Plugin not available - install dependencies or check ai_foundation_plugin.py")
    from enhanced_analysis_engine import EnhancedAnalysisEngine
    from file_preservation_module import FilePreservationManager


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
class CaseTheoryConfig:
    """User-defined case theories and legal objectives"""
    case_title: str = ""
    case_type: str = "family_law"  # family_law, personal_injury, business, criminal, etc.
    primary_legal_theories: List[str] = field(default_factory=list)
    key_facts_alleged: List[str] = field(default_factory=list)
    opposing_party_claims: List[str] = field(default_factory=list)
    evidence_priorities: Dict[str, float] = field(default_factory=dict)  # theory -> weight
    timeline_focus_periods: List[Dict[str, str]] = field(default_factory=list)  # start/end dates
    key_individuals: List[Dict[str, str]] = field(default_factory=list)  # name, role, relationship
    financial_thresholds: Dict[str, float] = field(default_factory=dict)  # significance levels
    custom_folder_structure: Optional[Dict[str, List[str]]] = None
    
    def __post_init__(self):
        """Set defaults based on case type if not provided"""
        if not self.primary_legal_theories and self.case_type == "family_law":
            self.primary_legal_theories = [
                "Asset Dissipation/Hiding",
                "Income Concealment", 
                "Abuse/Domestic Violence",
                "Fraud on the Court",
                "Constitutional Violations",
                "Attorney Misconduct"
            ]

@dataclass 
class AIRateLimitConfig:
    """Configuration for AI rate limiting and throttling"""
    max_requests_per_minute: int = 20
    max_tokens_per_hour: int = 100000
    max_cost_per_hour: float = 10.0  # dollars
    
    # Backoff settings
    initial_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 300.0  # 5 minutes
    backoff_multiplier: float = 2.0
    
    # Throttling behavior
    pause_on_limit: bool = True  # vs. disable AI entirely
    retry_failed_requests: bool = True
    max_retries: int = 3
    
    # Monitoring
    track_usage: bool = True
    usage_log_file: str = "ai_usage.log"

@dataclass
class LCASConfig:
    """Enhanced configuration settings for LCAS"""
    source_directory: str
    target_directory: str
    
    # Case-specific configuration
    case_theory: CaseTheoryConfig = field(default_factory=CaseTheoryConfig)
    
    # AI Configuration
    ai_enabled: bool = True
    ai_rate_limits: AIRateLimitConfig = field(default_factory=AIRateLimitConfig)
    ai_analysis_depth: str = "standard"  # basic, standard, comprehensive
    ai_confidence_threshold: float = 0.6  # minimum confidence for auto-categorization
    
    # Database settings (optional)
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    
    # Analysis settings - now user configurable
    min_probative_score: float = 0.3
    min_relevance_score: float = 0.5
    similarity_threshold: float = 0.85
    
    # Scoring weights - customizable per case type
    probative_weight: float = 0.4
    relevance_weight: float = 0.3
    admissibility_weight: float = 0.3
    
    # Processing options
    enable_deduplication: bool = True
    enable_neo4j: bool = False
    enable_advanced_nlp: bool = True
    enable_pattern_discovery: bool = True
    enable_timeline_analysis: bool = True
    enable_image_analysis: bool = True
    enable_relationship_mapping: bool = True
    generate_visualizations: bool = True
    max_concurrent_files: int = 5
    
    # Folder structure - now dynamic based on case theory
    folder_structure: Optional[Dict[str, List[str]]] = None
    
    def __post_init__(self):
        """Initialize folder structure based on case theory if not provided"""
        if self.folder_structure is None:
            if self.case_theory.custom_folder_structure:
                self.folder_structure = self.case_theory.custom_folder_structure
            else:
                self.folder_structure = self._generate_default_folder_structure()
    
    def _generate_default_folder_structure(self) -> Dict[str, List[str]]:
        """Generate folder structure based on case type and theories"""
        case_type = self.case_theory.case_type
        theories = self.case_theory.primary_legal_theories
        
        if case_type == "family_law":
            return {
                "01_CASE_SUMMARIES_AND_RELATED_DOCS": [
                    "AUTHORITIES", "DETAILED_ANALYSIS_OF_ARGUMENTS", "STATUTES"
                ],
                "02_FINANCIAL_EVIDENCE": [
                    "ASSET_DISSIPATION", "INCOME_CONCEALMENT", "HIDDEN_ASSETS",
                    "BANK_RECORDS", "CRYPTO_TRANSACTIONS"
                ],
                "03_ABUSE_AND_MISCONDUCT": [
                    "DOMESTIC_VIOLENCE", "ELECTRONIC_ABUSE", "COERCIVE_CONTROL",
                    "THREAT_EVIDENCE"
                ],
                "04_LEGAL_PROCESS_VIOLATIONS": [
                    "FRAUD_ON_COURT", "PERJURY_EVIDENCE", "DISCOVERY_ABUSE",
                    "EX_PARTE_COMMUNICATIONS"
                ],
                "05_COMMUNICATIONS": [
                    "TEXT_MESSAGES", "EMAILS", "VOICEMAILS", "SOCIAL_MEDIA"
                ],
                "06_COURT_RECORDS": ["FILINGS", "TRANSCRIPTS", "ORDERS"],
                "07_EXPERT_REPORTS": ["FINANCIAL_ANALYSIS", "PSYCHOLOGICAL_EVAL"],
                "08_TIMELINE_EVIDENCE": ["CHRONOLOGICAL_DOCS"],
                "09_FOR_HUMAN_REVIEW": [],
                "10_VISUALIZATIONS_AND_REPORTS": [],
                "00_ORIGINAL_FILES": []
            }
        elif case_type == "personal_injury":
            return {
                "01_MEDICAL_RECORDS": ["HOSPITAL", "DOCTORS", "SPECIALISTS", "THERAPY"],
                "02_ACCIDENT_EVIDENCE": ["POLICE_REPORTS", "PHOTOS", "WITNESS_STATEMENTS"],
                "03_FINANCIAL_DAMAGES": ["MEDICAL_BILLS", "LOST_WAGES", "RECEIPTS"],
                "04_INSURANCE_RECORDS": ["CLAIMS", "CORRESPONDENCE", "POLICIES"],
                "05_EXPERT_REPORTS": ["MEDICAL_EXPERTS", "ACCIDENT_RECONSTRUCTION"],
                "06_DISCOVERY_MATERIALS": ["DEPOSITIONS", "INTERROGATORIES"],
                "07_FOR_HUMAN_REVIEW": [],
                "08_VISUALIZATIONS_AND_REPORTS": [],
                "00_ORIGINAL_FILES": []
            }
        else:
            # Generic structure for other case types
            return {
                "01_PRIMARY_EVIDENCE": [],
                "02_SUPPORTING_DOCUMENTS": [],
                "03_COMMUNICATIONS": [],
                "04_FINANCIAL_RECORDS": [],
                "05_EXPERT_MATERIALS": [],
                "06_DISCOVERY": [],
                "07_FOR_HUMAN_REVIEW": [],
                "08_VISUALIZATIONS_AND_REPORTS": [],
                "00_ORIGINAL_FILES": []
            }

class AIRateLimiter:
    """Manages AI API rate limiting and throttling"""
    
    def __init__(self, config: AIRateLimitConfig):
        self.config = config
        self.request_timestamps = []
        self.token_usage_hourly = []
        self.cost_usage_hourly = []
        self.current_backoff = config.initial_backoff_seconds
        self.is_paused = False
        self.pause_until = None
        
        if config.track_usage:
            logging.basicConfig(
                filename=config.usage_log_file,
                level=logging.INFO,
                format='%(asctime)s - AI Usage - %(message)s'
            )
    
    async def check_rate_limits(self) -> bool:
        """Check if we can make an AI request right now"""
        now = time.time()
        
        # Clean old timestamps
        self._clean_old_usage(now)
        
        # Check if we're in a pause period
        if self.is_paused and self.pause_until and now < self.pause_until:
            return False
        else:
            self.is_paused = False
            self.pause_until = None
        
        # Check request rate limit
        recent_requests = [ts for ts in self.request_timestamps if now - ts < 60]
        if len(recent_requests) >= self.config.max_requests_per_minute:
            await self._handle_rate_limit("requests per minute")
            return False
        
        # Check token usage
        recent_tokens = sum(usage['tokens'] for usage in self.token_usage_hourly 
                          if now - usage['timestamp'] < 3600)
        if recent_tokens >= self.config.max_tokens_per_hour:
            await self._handle_rate_limit("tokens per hour")
            return False
        
        # Check cost usage
        recent_cost = sum(usage['cost'] for usage in self.cost_usage_hourly 
                         if now - usage['timestamp'] < 3600)
        if recent_cost >= self.config.max_cost_per_hour:
            await self._handle_rate_limit("cost per hour")
            return False
        
        return True
    
    async def record_usage(self, tokens_used: int, cost: float):
        """Record AI usage for tracking"""
        now = time.time()
        self.request_timestamps.append(now)
        self.token_usage_hourly.append({'timestamp': now, 'tokens': tokens_used})
        self.cost_usage_hourly.append({'timestamp': now, 'cost': cost})
        
        if self.config.track_usage:
            logger.info(f"AI Usage - Tokens: {tokens_used}, Cost: ${cost:.4f}")
    
    async def _handle_rate_limit(self, limit_type: str):
        """Handle when rate limit is hit"""
        logger.warning(f"AI rate limit hit: {limit_type}")
        
        if self.config.pause_on_limit:
            self.is_paused = True
            self.pause_until = time.time() + self.current_backoff
            logger.info(f"AI paused for {self.current_backoff} seconds due to {limit_type} limit")
            
            # Exponential backoff
            self.current_backoff = min(
                self.current_backoff * self.config.backoff_multiplier,
                self.config.max_backoff_seconds
            )
        else:
            logger.info("AI disabled due to rate limits - continuing without AI analysis")
    
    def _clean_old_usage(self, now: float):
        """Clean up old usage records"""
        # Keep last hour of token/cost usage
        self.token_usage_hourly = [u for u in self.token_usage_hourly if now - u['timestamp'] < 3600]
        self.cost_usage_hourly = [u for u in self.cost_usage_hourly if now - u['timestamp'] < 3600]
        
        # Keep last minute of request timestamps
        self.request_timestamps = [ts for ts in self.request_timestamps if now - ts < 60]

class FileAnalysis:
    """Enhanced data structure for file analysis results"""
    def __init__(self):
        # Basic file info (existing)
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
        
        # Content analysis (existing)
        self.content: str = ""
        self.summary: str = ""
        self.entities: List[str] = []
        self.keywords: List[str] = []
        
        # Categorization (existing)
        self.category: str = ""
        self.subcategory: str = ""
        self.confidence_score: float = 0.0
        
        # Legal scoring (existing)
        self.probative_value: float = 0.0
        self.prejudicial_value: float = 0.0
        self.relevance_score: float = 0.0
        self.admissibility_score: float = 0.0
        self.overall_impact: float = 0.0
        
        # Enhanced AI analysis results
        self.ai_analysis: Dict[str, Dict[str, Any]] = {}  # agent_name -> analysis_result
        self.ai_confidence: float = 0.0
        self.ai_entities: List[Dict[str, Any]] = []
        self.ai_tags: List[str] = []
        self.legal_theory_mapping: Dict[str, float] = {}  # theory -> relevance score
        self.case_specific_insights: List[str] = []
        
        # Flags (existing)
        self.is_duplicate: bool = False
        self.duplicate_of: str = ""
        self.requires_human_review: bool = False
        self.processing_errors: List[str] = []
        
        # Enhanced metadata
        self.processing_method: str = "basic"  # basic, ai_enhanced, comprehensive
        self.ai_processing_time: float = 0.0
        self.cost_incurred: float = 0.0

class LCASCore:
    """Enhanced core engine for the Legal Case Analysis System"""
    
    def __init__(self, config: LCASConfig):
        self.config = config
        self.plugins = {}
        self.processed_files: Dict[str, FileAnalysis] = {}
        self.file_hashes: Dict[str, str] = {}
        self.category_keywords = self._initialize_category_keywords()
        
        # AI Integration
        self.ai_plugin = None
        self.ai_rate_limiter = None
        if AI_AVAILABLE and config.ai_enabled:
            try:
                self.ai_plugin = create_ai_plugin(config)
                self.ai_rate_limiter = AIRateLimiter(config.ai_rate_limits)
                logger.info("AI Foundation Plugin loaded successfully")
            except Exception as e:
                logger.error(f"AI plugin initialization failed: {e}")
                self.ai_plugin = None
       
        # Ensure target directory exists
        Path(self.config.target_directory).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"LCAS initialized for {config.case_theory.case_type} case")
        logger.info(f"Primary theories: {', '.join(config.case_theory.primary_legal_theories)}")
        logger.info(f"AI enabled: {self.ai_plugin is not None}")
    
    def _initialize_category_keywords(self) -> Dict[str, List[str]]:
        """Initialize keyword mappings based on case theory"""
        case_type = self.config.case_theory.case_type
        theories = self.config.case_theory.primary_legal_theories
        
        # Base keywords
        keywords = {}
        
        if case_type == "family_law":
            keywords.update({
                "FINANCIAL_EVIDENCE": [
                    "asset", "income", "bank", "account", "crypto", "bitcoin", "hidden",
                    "dissipation", "spending", "transfer", "property", "value"
                ],
                "ABUSE_AND_MISCONDUCT": [
                    "abuse", "violence", "threat", "intimidate", "control", "coercive",
                    "surveillance", "tracking", "spyware", "harassment"
                ],
                "LEGAL_PROCESS_VIOLATIONS": [
                    "fraud", "perjury", "false", "lie", "deception", "manipulation",
                    "ex parte", "discovery", "contempt", "sanction"
                ],
                "COMMUNICATIONS": [
                    "text", "message", "email", "call", "voicemail", "social media",
                    "facebook", "instagram", "whatsapp"
                ]
            })
        elif case_type == "personal_injury":
            keywords.update({
                "MEDICAL_RECORDS": [
                    "medical", "doctor", "hospital", "treatment", "diagnosis", "injury",
                    "pain", "surgery", "therapy", "medication"
                ],
                "ACCIDENT_EVIDENCE": [
                    "accident", "crash", "collision", "police", "witness", "scene",
                    "damage", "fault", "negligence"
                ],
                "FINANCIAL_DAMAGES": [
                    "medical bills", "lost wages", "income", "disability", "expenses",
                    "receipts", "cost", "damage"
                ]
            })
        
        # Add user-specific keywords based on case facts
        for fact in self.config.case_theory.key_facts_alleged:
            # Simple keyword extraction from user facts
            fact_keywords = [word.lower() for word in fact.split() 
                           if len(word) > 3 and word.isalpha()]
            if fact_keywords:
                keywords[f"USER_FACT_{len(keywords)}"] = fact_keywords
        
        return keywords
    
    async def process_single_file(self, file_path: Path) -> FileAnalysis:
        """Enhanced file processing with AI integration"""
        logger.info(f"Processing: {file_path.name}")
        
        # Extract basic information
        analysis = self.extract_basic_info(file_path)
        
        # ADD THESE NEW COMPONENTS
        # File Preservation System
        self.preservation_manager = FilePreservationManager(config)
        
        # Enhanced Analysis Engine
        self.analysis_engine = EnhancedAnalysisEngine(config, self.ai_plugin)
        
        logger.info("✅ Enhanced LCAS v4.0 components initialized")
        
        # Check for duplicates
        if analysis.file_hash in self.file_hashes:
            analysis.is_duplicate = True
            analysis.duplicate_of = self.file_hashes[analysis.file_hash]
            logger.info(f"Duplicate detected: {file_path.name}")
        else:
            self.file_hashes[analysis.file_hash] = str(file_path)
        
        # Extract content (using existing plugins)
        try:
            if 'content_extraction' in self.plugins:
                analysis = self.plugins['content_extraction'].extract_content(file_path, analysis)
            else:
                # Basic content extraction
                if file_path.suffix.lower() == '.txt':
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        analysis.content = f.read()[:5000]
        except Exception as e:
            analysis.processing_errors.append(f"Content extraction error: {str(e)}")
        
        # AI-Enhanced Analysis
        if self.ai_plugin and analysis.content:
            try:
                ai_start_time = time.time()
                
                # Check rate limits
                if await self.ai_rate_limiter.check_rate_limits():
                    # Prepare context with case-specific information
                    context = {
                        "case_type": self.config.case_theory.case_type,
                        "legal_theories": self.config.case_theory.primary_legal_theories,
                        "key_facts": self.config.case_theory.key_facts_alleged,
                        "file_path": str(file_path),
                        "analysis_depth": self.config.ai_analysis_depth
                    }
                    
                    # Get AI analysis
                    ai_results = await self.ai_plugin.analyze_file_content(
                        content=analysis.content,
                        file_path=str(file_path),
                        context=context
                    )
                    
                    # Process AI results
                    await self._process_ai_results(analysis, ai_results)
                    analysis.processing_method = "ai_enhanced"
                else:
                    logger.info(f"AI rate limited - processing {file_path.name} with basic analysis")
                    analysis.processing_method = "basic_rate_limited"
                
                analysis.ai_processing_time = time.time() - ai_start_time
                
            except Exception as e:
                logger.error(f"AI analysis failed for {file_path}: {e}")
                analysis.processing_errors.append(f"AI analysis error: {str(e)}")
                analysis.processing_method = "basic_ai_failed"
        else:
            analysis.processing_method = "basic"
        
        def run_complete_analysis(self):
            """Enhanced analysis pipeline with preservation and advanced analysis"""
            logger.info("🚀 Starting Enhanced LCAS v4.0 analysis pipeline...")

            try:
                # STEP 1: File Preservation (NEW)
                logger.info("📦 Step 1: Preserving evidence files...")
                print("📦 Step 1: Preserving evidence files...")

                def preservation_progress(current, total, result):
                    if current % 10 == 0 or current == total:  # Log every 10 files
                        print(f"   Preserving {current}/{total}: {Path(result.source_path).name}")

                preservation_result = self.preservation_manager.preserve_evidence_files(preservation_progress)

                if not preservation_result["success"]:
                    raise Exception(f"File preservation failed: {preservation_result.get('error')}")

                print(f"   ✅ Preserved {preservation_result['preserved_files']} files ({preservation_result['total_size_mb']} MB)")

                # STEP 2: Enhanced File Analysis (ENHANCED)
                logger.info("🧠 Step 2: Running enhanced analysis...")
                print("🧠 Step 2: Running enhanced analysis...")

                # Get preserved files from originals folder
                preserved_files_path = Path(self.config.target_directory) / "00_PRESERVED_ORIGINALS"
                preserved_files = list(preserved_files_path.rglob("*"))
                preserved_files = [f for f in preserved_files if f.is_file()]

                if not preserved_files:
                    logger.warning("No preserved files found for analysis")
                    preserved_files = self.discover_files()  # Fallback to your existing method

                print(f"   Found {len(preserved_files)} files for analysis")

                # Enhanced analysis with progress tracking
                def analysis_progress(current, total, result):
                    if current % 5 == 0 or current == total:
                        print(f"   Analyzing {current}/{total}: {Path(result.file_path).name}")

                analysis_results = self.analysis_engine.analyze_batch_files(
                    preserved_files,
                    analysis_progress
                )

                print(f"   ✅ Analyzed {len(analysis_results)} files")

                # STEP 3: Semantic Clustering (NEW)
                logger.info("🔗 Step 3: Performing semantic clustering...")
                print("🔗 Step 3: Performing semantic clustering...")

                cluster_results = self.analysis_engine.perform_semantic_clustering()
                cluster_count = len(set(cluster_results.values())) if cluster_results else 0
                print(f"   ✅ Created {cluster_count} semantic clusters")

                # STEP 4: File Relationships (NEW)
                logger.info("🕸️ Step 4: Calculating file relationships...")
                print("🕸️ Step 4: Calculating file relationships...")

                relationship_results = self.analysis_engine.calculate_file_relationships()
                total_relationships = sum(len(rels) for rels in relationship_results.values())
                print(f"   ✅ Found {total_relationships} file relationships")

                # STEP 5: Generate Folder Indexes (ENHANCED)
                logger.info("📊 Step 5: Generating enhanced folder analysis...")
                print("📊 Step 5: Generating enhanced folder analysis...")

                self._generate_enhanced_folder_indexes()

                # STEP 6: Save Comprehensive Results (NEW)
                logger.info("💾 Step 6: Saving comprehensive results...")
                print("💾 Step 6: Saving comprehensive results...")

                self.analysis_engine.save_analysis_results()
                self.save_analysis_results()  # Your existing method too

                # STEP 7: Generate Enhanced Reports (NEW)
                self._generate_enhanced_reports()

                print("🎉 Enhanced LCAS v4.0 analysis completed successfully!")
                logger.info("Enhanced LCAS analysis pipeline completed successfully")

                return {
                    "success": True,
                    "preservation_result": preservation_result,
                    "analysis_count": len(analysis_results),
                    "cluster_count": cluster_count,
                    "relationship_count": total_relationships
                }

            except Exception as e:
                error_msg = f"Enhanced analysis failed: {e}"
                logger.error(error_msg)
                print(f"❌ {error_msg}")
                raise
        
    async def _process_ai_results(self, analysis: FileAnalysis, 
                                ai_results: Dict[str, AIAnalysisResult]):
        """Process and integrate AI analysis results"""
        total_cost = 0.0
        
        for agent_name, ai_result in ai_results.items():
            # Store AI analysis
            analysis.ai_analysis[agent_name] = ai_result.to_dict()
            
            # Track costs
            cost = ai_result.metadata.get('tokens_used', 0) * 0.0001  # Rough estimate
            total_cost += cost
            
            # Update analysis with AI findings
            if ai_result.confidence_score > analysis.ai_confidence:
                analysis.ai_confidence = ai_result.confidence_score
            
            # Merge entities and tags
            analysis.ai_entities.extend(ai_result.entities_found)
            analysis.ai_tags.extend(ai_result.tags)
            
            # Update legal theory mapping
            if hasattr(ai_result, 'legal_theory_mapping'):
                for theory, score in ai_result.legal_theory_mapping.items():
                    if theory not in analysis.legal_theory_mapping or score > analysis.legal_theory_mapping[theory]:
                        analysis.legal_theory_mapping[theory] = score
            
            # Use AI scores if confidence is high enough
            if ai_result.confidence_score >= self.config.ai_confidence_threshold:
                if ai_result.probative_value > analysis.probative_value:
                    analysis.probative_value = ai_result.probative_value
                if ai_result.relevance_score > analysis.relevance_score:
                    analysis.relevance_score = ai_result.relevance_score
                
                # Use AI categorization
                ai_category = ai_result.findings.get('evidence_category')
                if ai_category:
                    analysis.category = self._map_ai_category_to_folder(ai_category)
                    analysis.confidence_score = ai_result.confidence_score
            
            # Extract case-specific insights
            insights = ai_result.findings.get('case_specific_insights', [])
            if isinstance(insights, list):
                analysis.case_specific_insights.extend(insights)
        
        # Record usage with rate limiter
        analysis.cost_incurred = total_cost
        if total_cost > 0:
            total_tokens = sum(ai_result.metadata.get('tokens_used', 0) 
                             for ai_result in ai_results.values())
            await self.ai_rate_limiter.record_usage(total_tokens, total_cost)
    
    def _generate_enhanced_folder_indexes(self):
        """Generate enhanced analysis index for each folder"""
        logger.info("Generating enhanced folder indexes...")
        
        folders = [
            "01_CASE_SUMMARIES_AND_RELATED_DOCS",
            "02_CONSTITUTIONAL_VIOLATIONS", 
            "03_ELECTRONIC_ABUSE",
            "04_FRAUD_ON_THE_COURT",
            "05_NON_DISCLOSURE_FC2107_FC2122",
            "06_PD065288_COURT_RECORD_DOCS",
            "07_POST_TRIAL_ABUSE",
            "08_TEXT_MESSAGES",
            "09_FOR_HUMAN_REVIEW"
        ]
        
        for folder_name in folders:
            folder_path = Path(self.config.target_directory) / folder_name
            if folder_path.exists():
                try:
                    # Generate enhanced index using analysis engine
                    index = self.analysis_engine.generate_folder_analysis_index(folder_path)
                    
                    # Save enhanced index file
                    index_file = folder_path / "_ENHANCED_FOLDER_ANALYSIS.json"
                    with open(index_file, 'w', encoding='utf-8') as f:
                        json.dump(index, f, indent=2, ensure_ascii=False)
                    
                    # Also save markdown version for readability
                    self._create_enhanced_markdown_index(folder_path, index)
                    
                    logger.info(f"Enhanced index created for {folder_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to create enhanced index for {folder_name}: {e}")
    
    def _create_enhanced_markdown_index(self, folder_path: Path, index_data: Dict):
        """Create human-readable markdown index"""
        
        markdown_file = folder_path / "_FOLDER_SUMMARY.md"
        
        content = f"""# {folder_path.name.replace('_', ' ').title()}

## 📊 Folder Statistics
- **Total Files**: {index_data.get('summary_statistics', {}).get('total_files', 0)}
- **Total Size**: {index_data.get('summary_statistics', {}).get('total_size_mb', 0)} MB
- **Average Legal Relevance**: {index_data.get('summary_statistics', {}).get('average_legal_relevance', 0):.3f}
- **Average Probative Value**: {index_data.get('summary_statistics', {}).get('average_probative_value', 0):.3f}

## 🏷️ Top Named Entities
"""
        
        for entity, count in index_data.get('top_entities', [])[:10]:
            content += f"- **{entity}**: {count} mentions\n"
        
        content += "\n## 🔑 Top Key Phrases\n"
        for phrase, count in index_data.get('top_key_phrases', [])[:10]:
            content += f"- **{phrase}**: {count} occurrences\n"
        
        content += "\n## ⚖️ Top Legal Arguments\n"
        for argument, count in index_data.get('top_legal_arguments', [])[:5]:
            content += f"- **{argument}**: {count} supporting files\n"
        
        content += f"\n## 📁 File Details\n"
        for file_detail in index_data.get('file_details', []):
            content += f"""
### {file_detail['file_name']}
- **Size**: {file_detail['file_size']} bytes
- **Legal Relevance**: {file_detail['legal_relevance']:.3f}
- **Probative Value**: {file_detail['probative_value']:.3f}
- **Semantic Cluster**: {file_detail['semantic_cluster']}
- **Summary**: {file_detail['content_summary']}
"""
        
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _generate_enhanced_reports(self):
        """Generate comprehensive enhanced reports"""
        reports_dir = Path(self.config.target_directory) / "10_VISUALIZATIONS_AND_REPORTS"
        reports_dir.mkdir(exist_ok=True)
        
        # Enhanced Analysis Summary Report
        summary_report = self.analysis_engine.generate_analysis_summary_report()
        summary_file = reports_dir / "enhanced_analysis_summary.md"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary_report)
        
        logger.info("Enhanced reports generated successfully")
        # This would be more sophisticated in practice
        category_mapping = {
            "financial_evidence": "02_FINANCIAL_EVIDENCE",
            "abuse_evidence": "03_ABUSE_AND_MISCONDUCT", 
            "legal_violations": "04_LEGAL_PROCESS_VIOLATIONS",
            "communications": "05_COMMUNICATIONS",
            "court_records": "06_COURT_RECORDS"
        }
        
        return category_mapping.get(ai_category.lower(), "09_FOR_HUMAN_REVIEW")
    
    # ... [Rest of the existing methods remain the same but enhanced] ...
    
    async def run_complete_analysis(self):
        """Enhanced analysis pipeline with AI integration"""
        logger.info("Starting complete LCAS analysis with AI capabilities...")
        
        try:
            # Step 1: Create folder structure
            self.create_folder_structure()
            
            # Step 2: Discover files
            files = self.discover_files()
            
            if not files:
                logger.warning("No files found to process")
                return
            
            # Step 3: Process files with AI enhancement
            total_files = len(files)
            processed_count = 0
            
            for i, file_path in enumerate(files, 1):
                logger.info(f"Processing file {i}/{total_files}: {file_path.name}")
                
                # Process with potential AI enhancement
                analysis = await self.process_single_file(file_path)
                self.processed_files[str(file_path)] = analysis
                processed_count += 1
                
                # Rate limiting: small delay between files to be respectful
                if self.ai_plugin:
                    await asyncio.sleep(0.1)
            
            # Step 4: Organize files
            self.organize_processed_files()
            
            # Step 5: Generate enhanced reports
            await self.generate_enhanced_reports()
            
            logger.info(f"LCAS analysis completed successfully. Processed {processed_count} files.")
            
            # Log AI usage summary
            if self.ai_plugin:
                provider_status = self.ai_plugin.get_provider_status()
                total_cost = sum(status.get('total_cost', 0) for status in provider_status.values())
                total_tokens = sum(status.get('total_tokens_used', 0) for status in provider_status.values())
                logger.info(f"AI Usage Summary - Tokens: {total_tokens}, Cost: ${total_cost:.2f}")
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            raise
    
    async def generate_enhanced_reports(self):
        """Generate enhanced reports with AI insights"""
        logger.info("Generating enhanced reports with AI insights...")
        
        reports_dir = Path(self.config.target_directory) / "10_VISUALIZATIONS_AND_REPORTS"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate all standard reports
        self._generate_summary_report(reports_dir)
        self._generate_folder_strength_report(reports_dir)
        self._generate_duplicate_report(reports_dir)
        
        # Generate AI-enhanced reports
        if self.ai_plugin:
            await self._generate_ai_insights_report(reports_dir)
            await self._generate_case_theory_analysis(reports_dir)
    
    async def _generate_ai_insights_report(self, reports_dir: Path):
        """Generate report of AI insights and findings"""
        ai_insights = []
        case_specific_findings = []
        
        for file_path, analysis in self.processed_files.items():
            if analysis.ai_analysis:
                ai_insights.extend(analysis.case_specific_insights)
                
                # Collect high-confidence AI findings
                for agent_name, ai_data in analysis.ai_analysis.items():
                    if ai_data.get('confidence_score', 0) > 0.8:
                        finding = {
                            'file': analysis.original_name,
                            'agent': agent_name,
                            'confidence': ai_data.get('confidence_score'),
                            'finding': ai_data.get('findings', {}).get('summary', ''),
                            'legal_significance': ai_data.get('legal_significance', '')
                        }
                        case_specific_findings.append(finding)
        
        # Generate report
        report_content = f"""# AI Analysis Insights Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Case Type: {self.config.case_theory.case_type.replace('_', ' ').title()}

## Executive Summary

AI analysis processed {len(self.processed_files)} files with {len(case_specific_findings)} high-confidence findings.

## High-Confidence AI Findings

"""
        
        for finding in sorted(case_specific_findings, key=lambda x: x['confidence'], reverse=True):
            report_content += f"""
### {finding['file']} (Confidence: {finding['confidence']:.2f})
**Agent**: {finding['agent']}  
**Finding**: {finding['finding']}  
**Legal Significance**: {finding['legal_significance']}
---
"""
        
        report_content += f"""

## Case-Specific Insights

The AI analysis identified the following patterns and insights specific to your case:

"""
        
        # Group insights by frequency
        insight_counts = {}
        for insight in ai_insights:
            insight_counts[insight] = insight_counts.get(insight, 0) + 1
        
        for insight, count in sorted(insight_counts.items(), key=lambda x: x[1], reverse=True):
            report_content += f"- {insight} (mentioned {count} times)\n"
        
        report_content += f"""

## Legal Theory Mapping

Based on AI analysis, here's how your evidence maps to your legal theories:

"""
        
        theory_scores = {}
        for analysis in self.processed_files.values():
            for theory, score in analysis.legal_theory_mapping.items():
                if theory not in theory_scores:
                    theory_scores[theory] = []
                theory_scores[theory].append(score)
        
        for theory, scores in theory_scores.items():
            avg_score = sum(scores) / len(scores) if scores else 0
            report_content += f"- **{theory}**: {avg_score:.2f} average relevance ({len(scores)} supporting documents)\n"
        
        report_content += f"""

## AI Usage Statistics

- Total files processed with AI: {sum(1 for a in self.processed_files.values() if a.ai_analysis)}
- Average AI processing time: {sum(a.ai_processing_time for a in self.processed_files.values()) / len(self.processed_files):.2f} seconds
- Total AI cost incurred: ${sum(a.cost_incurred for a in self.processed_files.values()):.2f}

## Recommendations

1. **Priority Evidence**: Focus on the high-confidence findings listed above
2. **Evidence Gaps**: Consider gathering additional evidence for theories with low scores
3. **Human Review**: {sum(1 for a in self.processed_files.values() if a.requires_human_review)} files require human review
"""
        
        with open(reports_dir / "ai_insights_report.md", 'w', encoding='utf-8') as f:
            f.write(report_content)
    
    async def _generate_case_theory_analysis(self, reports_dir: Path):
        """Generate analysis of how evidence supports user's case theories"""
        
        theory_analysis = {}
        for theory in self.config.case_theory.primary_legal_theories:
            theory_analysis[theory] = {
                'supporting_files': [],
                'total_score': 0.0,
                'file_count': 0,
                'key_evidence': []
            }
        
        # Analyze each file's support for case theories
        for file_path, analysis in self.processed_files.items():
            for theory, score in analysis.legal_theory_mapping.items():
                if theory in theory_analysis:
                    theory_analysis[theory]['supporting_files'].append({
                        'file': analysis.original_name,
                        'score': score,
                        'summary': analysis.summary,
                        'ai_confidence': analysis.ai_confidence
                    })
                    theory_analysis[theory]['total_score'] += score
                    theory_analysis[theory]['file_count'] += 1
                    
                    if score > 0.8:  # High relevance
                        theory_analysis[theory]['key_evidence'].append(analysis.original_name)
        
        # Generate report
        report_content = f"""# Case Theory Analysis Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Case: {self.config.case_theory.case_title}

## Your Legal Theories Assessment

"""
        
        for theory, data in theory_analysis.items():
            avg_score = data['total_score'] / data['file_count'] if data['file_count'] > 0 else 0
            strength = "Strong" if avg_score > 0.7 else "Moderate" if avg_score > 0.4 else "Weak"
            
            report_content += f"""
### {theory}
**Strength**: {strength} (Score: {avg_score:.2f})  
**Supporting Evidence**: {data['file_count']} files  
**Key Evidence**: {len(data['key_evidence'])} high-relevance files

**Top Supporting Files**:
"""
            # Show top 5 supporting files
            top_files = sorted(data['supporting_files'], key=lambda x: x['score'], reverse=True)[:5]
            for file_data in top_files:
                report_content += f"- {file_data['file']} (Score: {file_data['score']:.2f})\n"
            
            report_content += "\n---\n"
        
        report_content += f"""

## Strategic Recommendations

### Strongest Arguments
"""
        strong_theories = [theory for theory, data in theory_analysis.items() 
                          if (data['total_score'] / max(data['file_count'], 1)) > 0.7]
        
        if strong_theories:
            for theory in strong_theories:
                report_content += f"- **{theory}**: Well-supported with strong evidence\n"
        else:
            report_content += "- Consider strengthening evidence collection across all theories\n"
        
        report_content += f"""

### Areas Needing Attention
"""
        weak_theories = [theory for theory, data in theory_analysis.items() 
                        if (data['total_score'] / max(data['file_count'], 1)) < 0.4]
        
        for theory in weak_theories:
            file_count = theory_analysis[theory]['file_count']
            report_content += f"- **{theory}**: Only {file_count} supporting files - consider additional evidence gathering\n"
        
        report_content += f"""

## Evidence Collection Priorities

Based on this analysis, prioritize gathering evidence for:
"""
        
        # Sort theories by weakness (lowest scores first)
        priority_theories = sorted(theory_analysis.items(), 
                                 key=lambda x: x[1]['total_score'] / max(x[1]['file_count'], 1))
        
        for theory, data in priority_theories[:3]:  # Top 3 priorities
            avg_score = data['total_score'] / max(data['file_count'], 1)
            report_content += f"1. **{theory}** (Current strength: {avg_score:.2f})\n"
        
        with open(reports_dir / "case_theory_analysis.md", 'w', encoding='utf-8') as f:
            f.write(report_content)

    def update_case_theory_from_ai_findings(self):
        """Allow AI findings to suggest updates to case theory"""
        suggested_theories = []
        new_insights = []
        
        for analysis in self.processed_files.values():
            if analysis.ai_analysis:
                for agent_name, ai_data in analysis.ai_analysis.items():
                    findings = ai_data.get('findings', {})
                    
                    # Look for suggested new legal theories
                    if 'suggested_theories' in findings:
                        suggested_theories.extend(findings['suggested_theories'])
                    
                    # Collect insights that might change case strategy
                    if 'strategic_insights' in findings:
                        new_insights.extend(findings['strategic_insights'])
        
        # Log suggestions for user review
        if suggested_theories or new_insights:
            logger.info("AI has suggested updates to your case theory:")
            for theory in set(suggested_theories):
                logger.info(f"  Suggested theory: {theory}")
            for insight in set(new_insights):
                logger.info(f"  Strategic insight: {insight}")
        
        return {
            'suggested_theories': list(set(suggested_theories)),
            'strategic_insights': list(set(new_insights))
        }

    # ... [Rest of existing methods with minimal changes] ...
    
    def extract_basic_info(self, file_path: Path) -> FileAnalysis:
        """Extract basic file information (existing method)"""
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
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file (existing method)"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            return ""
    
    def preserve_original_file(self, file_path: Path) -> str:
        """Create a preserved copy of the original file (existing method)"""
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

    def discover_files(self) -> List[Path]:
        """Discover all files in the source directory (existing method)"""
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

    def create_folder_structure(self):
        """Create the standardized folder structure for evidence organization (existing method)"""
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
        """Create an index file for a folder (existing method)"""
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

    def categorize_file(self, analysis: FileAnalysis) -> Tuple[str, str, float]:
        """Categorize a file based on content and keywords (existing method with enhancements)"""
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
                best_category = self._map_category_to_folder(category)
        
        return best_category, best_subcategory, best_score

    def _map_category_to_folder(self, category: str) -> str:
        """Map category to actual folder name"""
        # Enhanced mapping based on dynamic folder structure
        for folder_name in self.config.folder_structure.keys():
            if category.upper() in folder_name.upper():
                return folder_name
        
        return "09_FOR_HUMAN_REVIEW"

    def generate_standardized_name(self, analysis: FileAnalysis) -> str:
        """Generate a standardized filename (existing method)"""
        # Extract date if available
        date_prefix = ""
        if analysis.created_date:
            date_prefix = analysis.created_date.strftime("%y%m%d")
        
        # Category code mapping
        category_codes = {}
        for i, folder_name in enumerate(self.config.folder_structure.keys()):
            short_code = ''.join([word[0] for word in folder_name.split('_') if word.isalpha()])[:4]
            category_codes[folder_name] = short_code.upper()
        
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
        """Calculate legal scoring for a file (existing method)"""
        content_lower = analysis.content.lower()
        
        # Probative value - enhanced with case-specific keywords
        probative_keywords = [
            'evidence', 'proof', 'document', 'record', 'statement', 'testimony',
            'admission', 'confession', 'agreement', 'contract', 'receipt'
        ]
        
        # Add case-specific probative keywords
        for fact in self.config.case_theory.key_facts_alleged:
            probative_keywords.extend([word.lower() for word in fact.split() if len(word) > 3])
        
        probative_score = sum(1 for keyword in probative_keywords if keyword in content_lower)
        analysis.probative_value = min(probative_score / 10.0, 1.0)  # Normalized to 0-1
        
        # Prejudicial value
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
        
        # Overall impact score using configurable weights
        analysis.overall_impact = (
            analysis.probative_value * self.config.probative_weight +
            analysis.relevance_score * self.config.relevance_weight +
            analysis.admissibility_score * self.config.admissibility_weight
        ) - (analysis.prejudicial_value * 0.1)  # Slight penalty for prejudicial content
        
        analysis.overall_impact = max(0.0, min(1.0, analysis.overall_impact))
        
        return analysis

    def organize_processed_files(self):
        """Move processed files to their categorized folders (existing method)"""
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
        """Determine if a duplicate file should be kept (existing method)"""
        return (analysis.overall_impact > 0.7 or 
                analysis.probative_value > 0.8)

    def _update_folder_index(self, folder_path: Path, analysis: FileAnalysis):
        """Update folder index with file information (existing method)"""
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
- **AI Enhanced**: {'Yes' if analysis.ai_analysis else 'No'}
- **Processing Date**: {analysis.processing_date.strftime('%Y-%m-%d %H:%M:%S')}

"""
        
        # Simple append for now (in production, would parse and update)
        with open(index_file, 'a', encoding='utf-8') as f:
            f.write(file_entry)

    def _generate_summary_report(self, reports_dir: Path):
        """Generate overall summary report (enhanced existing method)"""
        total_files = len(self.processed_files)
        categorized_files = sum(1 for a in self.processed_files.values() 
                               if a.category != "09_FOR_HUMAN_REVIEW")
        ai_processed_files = sum(1 for a in self.processed_files.values() if a.ai_analysis)
        
        avg_relevance = sum(a.relevance_score for a in self.processed_files.values()) / total_files
        avg_impact = sum(a.overall_impact for a in self.processed_files.values()) / total_files
        total_ai_cost = sum(a.cost_incurred for a in self.processed_files.values())
        
        report_content = f"""# LCAS Analysis Summary Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Case Type: {self.config.case_theory.case_type.replace('_', ' ').title()}
Case Title: {self.config.case_theory.case_title}

## Overall Statistics
- **Total Files Processed**: {total_files}
- **Successfully Categorized**: {categorized_files}
- **AI-Enhanced Analysis**: {ai_processed_files}
- **Requiring Human Review**: {total_files - categorized_files}
- **Average Relevance Score**: {avg_relevance:.2f}
- **Average Overall Impact Score**: {avg_impact:.2f}
- **Total AI Cost**: ${total_ai_cost:.2f}

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
        
        # Add legal theory analysis
        report_content += f"""

## Legal Theory Support Analysis

Your primary legal theories and evidence support:
"""
        
        for theory in self.config.case_theory.primary_legal_theories:
            supporting_files = sum(1 for a in self.processed_files.values() 
                                 if theory in a.legal_theory_mapping)
            avg_support = sum(score for a in self.processed_files.values() 
                            for t, score in a.legal_theory_mapping.items() 
                            if t == theory) / max(supporting_files, 1)
            
            report_content += f"- **{theory}**: {supporting_files} files, {avg_support:.2f} average support\n"
        
        # Write report
        with open(reports_dir / "analysis_summary.md", 'w', encoding='utf-8') as f:
            f.write(report_content)

    def _generate_folder_strength_report(self, reports_dir: Path):
        """Generate argument strength analysis by folder (existing method)"""
        folder_stats = {}
        
        for analysis in self.processed_files.values():
            category = analysis.category
            if category not in folder_stats:
                folder_stats[category] = {
                    'count': 0,
                    'total_impact': 0.0,
                    'total_relevance': 0.0,
                    'high_impact_files': 0,
                    'ai_enhanced_count': 0
                }
            
            stats = folder_stats[category]
            stats['count'] += 1
            stats['total_impact'] += analysis.overall_impact
            stats['total_relevance'] += analysis.relevance_score
            if analysis.overall_impact > 0.7:
                stats['high_impact_files'] += 1
            if analysis.ai_analysis:
                stats['ai_enhanced_count'] += 1
        
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
                ai_enhancement_ratio = stats['ai_enhanced_count'] / stats['count']
                
                # Calculate overall folder strength
                folder_strength = (avg_impact * 0.4 + avg_relevance * 0.3 + 
                                 high_impact_ratio * 0.2 + ai_enhancement_ratio * 0.1)
                
                folder_rankings.append({
                    'category': category,
                    'strength': folder_strength,
                    'count': stats['count'],
                    'avg_impact': avg_impact,
                    'avg_relevance': avg_relevance,
                    'high_impact_files': stats['high_impact_files'],
                    'ai_enhanced': stats['ai_enhanced_count']
                })
        
        # Sort by strength
        folder_rankings.sort(key=lambda x: x['strength'], reverse=True)
        
        for i, folder in enumerate(folder_rankings, 1):
            category_name = folder['category'].replace('_', ' ').title()
            report_content += f"""
### {i}. {category_name}
- **Overall Strength Score**: {folder['strength']:.2f}/1.0
- **File Count**: {folder['count']}
- **AI Enhanced**: {folder['ai_enhanced']} files
- **Average Impact Score**: {folder['avg_impact']:.2f}
- **Average Relevance Score**: {folder['avg_relevance']:.2f}
- **High Impact Files**: {folder['high_impact_files']} ({folder['high_impact_files']/folder['count']*100:.1f}%)

"""
        
        # Write report
        with open(reports_dir / "argument_strength_analysis.md", 'w', encoding='utf-8') as f:
            f.write(report_content)

    def _generate_duplicate_report(self, reports_dir: Path):
        """Generate duplicate files report (existing method)"""
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
        """Save detailed analysis results to JSON (enhanced existing method)"""
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
                'processing_errors': analysis.processing_errors,
                # Enhanced AI fields
                'ai_analysis': analysis.ai_analysis,
                'ai_confidence': analysis.ai_confidence,
                'ai_entities': analysis.ai_entities,
                'ai_tags': analysis.ai_tags,
                'legal_theory_mapping': analysis.legal_theory_mapping,
                'case_specific_insights': analysis.case_specific_insights,
                'processing_method': analysis.processing_method,
                'ai_processing_time': analysis.ai_processing_time,
                'cost_incurred': analysis.cost_incurred
            }
            serializable_results[path] = result
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Analysis results saved to {results_file}")

def load_config(config_file: str) -> LCASConfig:
    """Load configuration from file (enhanced)"""
    if Path(config_file).exists():
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        # Handle case theory configuration
        if 'case_theory' in config_data:
            case_theory = CaseTheoryConfig(**config_data['case_theory'])
            config_data['case_theory'] = case_theory
        
        # Handle AI rate limit configuration
        if 'ai_rate_limits' in config_data:
            ai_rate_limits = AIRateLimitConfig(**config_data['ai_rate_limits'])
            config_data['ai_rate_limits'] = ai_rate_limits
        
        return LCASConfig(**config_data)
    else:
        logger.warning(f"Config file {config_file} not found, using defaults")
        return LCASConfig(
            source_directory=r"F:\POST TRIAL DIVORCE",
            target_directory=r"G:\LCAS_ANALYSIS_RESULTS"
        )

def create_default_config(config_file: str, source_dir: str = None, target_dir: str = None,
                         case_type: str = "family_law", case_title: str = "") -> LCASConfig:
    """Create a default configuration file with case-specific settings"""
    
    # Create case theory based on case type
    case_theory = CaseTheoryConfig(
        case_title=case_title,
        case_type=case_type
    )
    
    config = LCASConfig(
        source_directory=source_dir or r"F:\POST TRIAL DIVORCE",
        target_directory=target_dir or r"G:\LCAS_ANALYSIS_RESULTS",
        case_theory=case_theory
    )
    
    # Convert to dict for JSON serialization
    config_dict = asdict(config)
    
    with open(config_file, 'w') as f:
        json.dump(config_dict, f, indent=2)
    
    print(f"Default configuration created: {config_file}")
    print(f"Case type: {case_type}")
    print(f"Primary legal theories: {', '.join(case_theory.primary_legal_theories)}")
    
    return config

def setup_case_theory_interactive() -> CaseTheoryConfig:
    """Interactive setup for case theory configuration"""
    print("\n" + "="*60)
    print("LCAS Case Theory Setup")
    print("="*60)
    
    case_title = input("Enter your case title (e.g., 'Smith v. Smith Divorce'): ").strip()
    
    print("\nSelect your case type:")
    case_types = [
        "family_law",
        "personal_injury", 
        "business_litigation",
        "criminal_defense",
        "employment",
        "other"
    ]
    
    for i, case_type in enumerate(case_types, 1):
        print(f"  {i}. {case_type.replace('_', ' ').title()}")
    
    while True:
        try:
            choice = int(input("\nEnter choice (1-6): "))
            if 1 <= choice <= len(case_types):
                selected_case_type = case_types[choice-1]
                break
            else:
                print("Invalid choice. Please enter 1-6.")
        except ValueError:
            print("Please enter a number.")
    
    # Create case theory with defaults
    case_theory = CaseTheoryConfig(
        case_title=case_title,
        case_type=selected_case_type
    )
    
    print(f"\nDefault legal theories for {selected_case_type}:")
    for i, theory in enumerate(case_theory.primary_legal_theories, 1):
        print(f"  {i}. {theory}")
    
    modify = input("\nWould you like to modify these theories? (y/N): ").strip().lower()
    if modify == 'y':
        print("\nEnter your legal theories (one per line, empty line to finish):")
        custom_theories = []
        while True:
            theory = input("Theory: ").strip()
            if not theory:
                break
            custom_theories.append(theory)
        
        if custom_theories:
            case_theory.primary_legal_theories = custom_theories
    
    print(f"\nCase theory configured:")
    print(f"  Title: {case_theory.case_title}")
    print(f"  Type: {case_theory.case_type}")
    print(f"  Theories: {', '.join(case_theory.primary_legal_theories)}")
    
    return case_theory

def main():
    """Enhanced main entry point for LCAS"""
    parser = argparse.ArgumentParser(description="Legal Case-Building and Analysis System with AI")
    parser.add_argument("--config", default="lcas_config.json", help="Configuration file path")
    parser.add_argument("--source", help="Source directory path")
    parser.add_argument("--target", help="Target directory path")
    parser.add_argument("--case-type", help="Type of case (family_law, personal_injury, etc.)")
    parser.add_argument("--case-title", help="Title/name of your case")
    parser.add_argument("--create-config", action="store_true", help="Create default configuration file")
    parser.add_argument("--interactive-setup", action="store_true", help="Interactive case theory setup")
    parser.add_argument("--disable-ai", action="store_true", help="Disable AI analysis")
    parser.add_argument("--ai-depth", choices=["basic", "standard", "comprehensive"], 
                       default="standard", help="AI analysis depth")
    
    args = parser.parse_args()
    
    if args.create_config:
        if args.interactive_setup:
            case_theory = setup_case_theory_interactive()
            create_default_config(args.config, args.source, args.target, 
                                case_theory.case_type, case_theory.case_title)
        else:
            create_default_config(args.config, args.source, args.target, 
                                args.case_type or "family_law", args.case_title or "")
        return
    
    # Load configuration
    config = load_config(args.config)
    
    # Override with command line arguments if provided
    if args.source:
        config.source_directory = args.source
    if args.target:
        config.target_directory = args.target
    if args.case_type:
        config.case_theory.case_type = args.case_type
    if args.case_title:
        config.case_theory.case_title = args.case_title
    if args.disable_ai:
        config.ai_enabled = False
    if args.ai_depth:
        config.ai_analysis_depth = args.ai_depth
    
    # Initialize LCAS
    lcas = LCASCore(config)
    
    # Register plugins
    try:
        from content_extraction_plugin import ContentExtractionPlugin
        lcas.register_plugin('content_extraction', ContentExtractionPlugin(config))
        logger.info("Content extraction plugin loaded")
    except ImportError:
        logger.warning("Content extraction plugin not available")
    
    # Run complete analysis
    try:
        # Run async analysis
        import asyncio
        asyncio.run(lcas.run_complete_analysis())
        
        # Save results
        lcas.save_analysis_results()
        
        # Check for AI-suggested case theory updates
        if lcas.ai_plugin:
            ai_suggestions = lcas.update_case_theory_from_ai_findings()
            if ai_suggestions['suggested_theories'] or ai_suggestions['strategic_insights']:
                print("\n" + "="*60)
                print("AI RECOMMENDATIONS FOR CASE THEORY")
                print("="*60)
                
                if ai_suggestions['suggested_theories']:
                    print("\nSuggested additional legal theories:")
                    for theory in ai_suggestions['suggested_theories']:
                        print(f"  • {theory}")
                
                if ai_suggestions['strategic_insights']:
                    print("\nStrategic insights from AI analysis:")
                    for insight in ai_suggestions['strategic_insights']:
                        print(f"  • {insight}")
                
                print("\nConsider updating your case configuration to include these insights.")
        
        print("\n" + "="*60)
        print("LCAS ANALYSIS COMPLETED SUCCESSFULLY")
        print("="*60)
        print(f"Case: {config.case_theory.case_title}")
        print(f"Type: {config.case_theory.case_type.replace('_', ' ').title()}")
        print(f"Results saved to: {config.target_directory}")
        print(f"\nKey reports to review:")
        print(f"  • 10_VISUALIZATIONS_AND_REPORTS/analysis_summary.md")
        print(f"  • 10_VISUALIZATIONS_AND_REPORTS/argument_strength_analysis.md")
        print(f"  • 10_VISUALIZATIONS_AND_REPORTS/case_theory_analysis.md")
        if lcas.ai_plugin:
            print(f"  • 10_VISUALIZATIONS_AND_REPORTS/ai_insights_report.md")
        print(f"  • analysis_results.json (detailed data)")
        
        # AI usage summary
        if lcas.ai_plugin:
            provider_status = lcas.ai_plugin.get_provider_status()
            total_cost = sum(status.get('total_cost', 0) for status in provider_status.values())
            total_tokens = sum(status.get('total_tokens_used', 0) for status in provider_status.values())
            print(f"\nAI Usage Summary:")
            print(f"  • Total tokens used: {total_tokens:,}")
            print(f"  • Estimated cost: ${total_cost:.2f}")
            
            for provider_name, status in provider_status.items():
                if status['total_tokens_used'] > 0:
                    print(f"  • {provider_name}: {status['total_tokens_used']:,} tokens, ${status['total_cost']:.2f}")
        
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user")
        logger.info("Analysis interrupted by user")
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"\nAnalysis failed with error: {e}")
        print("Check lcas.log for detailed error information")
        
        # If AI was involved, show usage even on failure
        if hasattr(lcas, 'ai_plugin') and lcas.ai_plugin:
            provider_status = lcas.ai_plugin.get_provider_status()
            total_cost = sum(status.get('total_cost', 0) for status in provider_status.values())
            if total_cost > 0:
                print(f"AI usage before failure: ${total_cost:.2f}")

if __name__ == "__main__":
    main()
