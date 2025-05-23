#!/usr/bin/env python3
"""
LCAS Vertical Slice Architecture Implementation
Each feature is implemented as a complete vertical slice from UI to data layer
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import asyncio
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# ================================
# VERTICAL SLICE: FILE INGESTION
# ================================

@dataclass
class FileIngestionRequest:
    """Request model for file ingestion"""
    source_path: str
    target_path: str
    preserve_structure: bool = True
    file_filters: List[str] = None

@dataclass
class FileIngestionResult:
    """Result model for file ingestion"""
    success: bool
    files_processed: int
    files_copied: int
    errors: List[str]
    processing_time: float

class FileIngestionHandler:
    """Handles file ingestion vertical slice"""
    
    def __init__(self, file_service, ui_service):
        self.file_service = file_service
        self.ui_service = ui_service
    
    async def handle(self, request: FileIngestionRequest) -> FileIngestionResult:
        """Handle file ingestion request"""
        try:
            # Update UI
            await self.ui_service.update_progress(0, "Starting file ingestion...")
            
            # Validate paths
            if not Path(request.source_path).exists():
                return FileIngestionResult(
                    success=False,
                    files_processed=0,
                    files_copied=0,
                    errors=["Source path does not exist"],
                    processing_time=0
                )
            
            # Process files
            result = await self.file_service.copy_files(
                request.source_path,
                request.target_path,
                preserve_structure=request.preserve_structure,
                file_filters=request.file_filters,
                progress_callback=self.ui_service.update_progress
            )
            
            # Update UI
            await self.ui_service.update_progress(100, "File ingestion complete")
            
            return result
            
        except Exception as e:
            logger.error(f"File ingestion failed: {e}")
            return FileIngestionResult(
                success=False,
                files_processed=0,
                files_copied=0,
                errors=[str(e)],
                processing_time=0
            )

# ================================
# VERTICAL SLICE: CONTENT ANALYSIS
# ================================

@dataclass
class ContentAnalysisRequest:
    """Request model for content analysis"""
    file_path: str
    analysis_types: List[str]  # ['text_extraction', 'nlp', 'semantic']
    ai_config: Optional[Dict[str, Any]] = None

@dataclass
class ContentAnalysisResult:
    """Result model for content analysis"""
    file_path: str
    content: str
    summary: str
    entities: List[str]
    keywords: List[str]
    embeddings: Optional[List[float]]
    confidence_score: float
    processing_time: float
    errors: List[str]

class ContentAnalysisHandler:
    """Handles content analysis vertical slice"""
    
    def __init__(self, content_service, ai_service, ui_service):
        self.content_service = content_service
        self.ai_service = ai_service
        self.ui_service = ui_service
    
    async def handle(self, request: ContentAnalysisRequest) -> ContentAnalysisResult:
        """Handle content analysis request"""
        try:
            # Update UI
            await self.ui_service.update_status(f"Analyzing: {Path(request.file_path).name}")
            
            # Extract content
            content = await self.content_service.extract_content(request.file_path)
            
            # Generate summary
            summary = ""
            if 'nlp' in request.analysis_types and content:
                summary = await self.ai_service.generate_summary(content, request.ai_config)
            
            # Extract entities
            entities = []
            if 'nlp' in request.analysis_types and content:
                entities = await self.content_service.extract_entities(content)
            
            # Generate embeddings
            embeddings = None
            if 'semantic' in request.analysis_types and content:
                embeddings = await self.content_service.generate_embeddings(content)
            
            return ContentAnalysisResult(
                file_path=request.file_path,
                content=content,
                summary=summary,
                entities=entities,
                keywords=[],  # Would be extracted
                embeddings=embeddings,
                confidence_score=0.8,  # Would be calculated
                processing_time=0,  # Would be measured
                errors=[]
            )
            
        except Exception as e:
            logger.error(f"Content analysis failed for {request.file_path}: {e}")
            return ContentAnalysisResult(
                file_path=request.file_path,
                content="",
                summary="",
                entities=[],
                keywords=[],
                embeddings=None,
                confidence_score=0,
                processing_time=0,
                errors=[str(e)]
            )

# ================================
# VERTICAL SLICE: FILE CATEGORIZATION
# ================================

@dataclass
class CategorizationRequest:
    """Request model for file categorization"""
    file_analysis: ContentAnalysisResult
    folder_structure: Dict[str, List[str]]
    categorization_config: Dict[str, Any]

@dataclass
class CategorizationResult:
    """Result model for file categorization"""
    file_path: str
    category: str
    subcategory: str
    confidence_score: float
    reasoning: str
    alternative_categories: List[str]

class CategorizationHandler:
    """Handles file categorization vertical slice"""
    
    def __init__(self, categorization_service, ai_service):
        self.categorization_service = categorization_service
        self.ai_service = ai_service
    
    async def handle(self, request: CategorizationRequest) -> CategorizationResult:
        """Handle categorization request"""
        try:
            # Use AI for smart categorization
            if request.categorization_config.get('use_ai', False):
                category_result = await self.ai_service.categorize_content(
                    content=request.file_analysis.content,
                    summary=request.file_analysis.summary,
                    entities=request.file_analysis.entities,
                    folder_structure=request.folder_structure
                )
            else:
                # Fallback to rule-based categorization
                category_result = await self.categorization_service.categorize_by_keywords(
                    request.file_analysis,
                    request.folder_structure
                )
            
            return category_result
            
        except Exception as e:
            logger.error(f"Categorization failed for {request.file_analysis.file_path}: {e}")
            return CategorizationResult(
                file_path=request.file_analysis.file_path,
                category="09_FOR_HUMAN_REVIEW",
                subcategory="",
                confidence_score=0,
                reasoning=f"Error during categorization: {str(e)}",
                alternative_categories=[]
            )

# ================================
# VERTICAL SLICE: LEGAL SCORING
# ================================

@dataclass
class LegalScoringRequest:
    """Request model for legal scoring"""
    file_analysis: ContentAnalysisResult
    category: str
    subcategory: str
    scoring_config: Dict[str, Any]

@dataclass
class LegalScoringResult:
    """Result model for legal scoring"""
    file_path: str
    probative_value: float
    prejudicial_value: float
    relevance_score: float
    admissibility_score: float
    overall_impact: float
    scoring_details: Dict[str, Any]

class LegalScoringHandler:
    """Handles legal scoring vertical slice"""
    
    def __init__(self, scoring_service, ai_service):
        self.scoring_service = scoring_service
        self.ai_service = ai_service
    
    async def handle(self, request: LegalScoringRequest) -> LegalScoringResult:
        """Handle legal scoring request"""
        try:
            # Calculate base scores
            base_scores = await self.scoring_service.calculate_base_scores(
                request.file_analysis,
                request.category,
                request.subcategory
            )
            
            # Enhance with AI if enabled
            if request.scoring_config.get('use_ai_scoring', False):
                ai_scores = await self.ai_service.enhance_legal_scores(
                    content=request.file_analysis.content,
                    category=request.category,
                    base_scores=base_scores
                )
                # Combine base and AI scores
                final_scores = await self.scoring_service.combine_scores(base_scores, ai_scores)
            else:
                final_scores = base_scores
            
            return LegalScoringResult(
                file_path=request.file_analysis.file_path,
                probative_value=final_scores['probative'],
                prejudicial_value=final_scores['prejudicial'],
                relevance_score=final_scores['relevance'],
                admissibility_score=final_scores['admissibility'],
                overall_impact=final_scores['overall'],
                scoring_details=final_scores.get('details', {})
            )
            
        except Exception as e:
            logger.error(f"Legal scoring failed for {request.file_analysis.file_path}: {e}")
            return LegalScoringResult(
                file_path=request.file_analysis.file_path,
                probative_value=0,
                prejudicial_value=0,
                relevance_score=0,
                admissibility_score=0,
                overall_impact=0,
                scoring_details={'error': str(e)}
            )

# ================================
# ORCHESTRATOR - COORDINATES VERTICAL SLICES
# ================================

class LCASOrchestrator:
    """Orchestrates the execution of vertical slices"""
    
    def __init__(self, handlers: Dict[str, Any], services: Dict[str, Any]):
        self.handlers = handlers
        self.services = services
    
    async def process_single_file(self, file_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single file through all vertical slices"""
        results = {}
        
        try:
            # 1. Content Analysis Slice
            content_request = ContentAnalysisRequest(
                file_path=file_path,
                analysis_types=config.get('analysis_types', ['text_extraction', 'nlp']),
                ai_config=config.get('ai_config')
            )
            content_result = await self.handlers['content_analysis'].handle(content_request)
            results['content_analysis'] = content_result
            
            # 2. Categorization Slice
            if not content_result.errors:
                cat_request = CategorizationRequest(
                    file_analysis=content_result,
                    folder_structure=config.get('folder_structure', {}),
                    categorization_config=config.get('categorization_config', {})
                )
                cat_result = await self.handlers['categorization'].handle(cat_request)
                results['categorization'] = cat_result
                
                # 3. Legal Scoring Slice
                scoring_request = LegalScoringRequest(
                    file_analysis=content_result,
                    category=cat_result.category,
                    subcategory=cat_result.subcategory,
                    scoring_config=config.get('scoring_config', {})
                )
                scoring_result = await self.handlers['legal_scoring'].handle(scoring_request)
                results['legal_scoring'] = scoring_result
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            results['error'] = str(e)
            return results
    
    async def process_batch(self, file_paths: List[str], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process multiple files concurrently"""
        tasks = []
        
        # Create semaphore to limit concurrent processing
        semaphore = asyncio.Semaphore(config.get('max_concurrent_files', 5))
        
        async def process_with_semaphore(file_path):
            async with semaphore:
                return await self.process_single_file(file_path, config)
        
        # Create tasks for all files
        for file_path in file_paths:
            task = asyncio.create_task(process_with_semaphore(file_path))
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return results

# ================================
# SERVICE INTERFACES (ABSTRACT)
# ================================

class ContentService(ABC):
    """Abstract content service interface"""
    
    @abstractmethod
    async def extract_content(self, file_path: str) -> str:
        pass
    
    @abstractmethod
    async def extract_entities(self, content: str) -> List[str]:
        pass
    
    @abstractmethod
    async def generate_embeddings(self, content: str) -> List[float]:
        pass

class AIService(ABC):
    """Abstract AI service interface"""
    
    @abstractmethod
    async def generate_summary(self, content: str, config: Dict[str, Any]) -> str:
        pass
    
    @abstractmethod
    async def categorize_content(self, **kwargs) -> CategorizationResult:
        pass
    
    @abstractmethod
    async def enhance_legal_scores(self, **kwargs) -> Dict[str, float]:
        pass

class FileService(ABC):
    """Abstract file service interface"""
    
    @abstractmethod
    async def copy_files(self, source: str, target: str, **kwargs) -> FileIngestionResult:
        pass

class UIService(ABC):
    """Abstract UI service interface"""
    
    @abstractmethod
    async def update_progress(self, progress: float, message: str):
        pass
    
    @abstractmethod
    async def update_status(self, message: str):
        pass

# ================================
# FACTORY FOR VERTICAL SLICE SETUP
# ================================

class LCASVerticalSliceFactory:
    """Factory for setting up vertical slice architecture"""
    
    @staticmethod
    def create_orchestrator(config: Dict[str, Any]) -> LCASOrchestrator:
        """Create a fully configured orchestrator with all vertical slices"""
        
        # Create services (would be injected in real implementation)
        services = {
            'content': ContentService(),  # Would be concrete implementation
            'ai': AIService(),            # Would be concrete implementation
            'file': FileService(),        # Would be concrete implementation
            'ui': UIService()             # Would be concrete implementation
        }
        
        # Create handlers for each vertical slice
        handlers = {
            'file_ingestion': FileIngestionHandler(
                services['file'],
                services['ui']
            ),
            'content_analysis': ContentAnalysisHandler(
                services['content'],
                services['ai'],
                services['ui']
            ),
            'categorization': CategorizationHandler(
                services['content'],  # Categorization service would be part of content
                services['ai']
            ),
            'legal_scoring': LegalScoringHandler(
                services['content'],  # Scoring service would be part of content
                services['ai']
            )
        }
        
        return LCASOrchestrator(handlers, services)

# ================================
# EXAMPLE USAGE
# ================================

async def example_usage():
    """Example of how to use the vertical slice architecture"""
    
    # Configuration
    config = {
        'analysis_types': ['text_extraction', 'nlp', 'semantic'],
        'ai_config': {
            'provider': 'openai',
            'model': 'gpt-4',
            'api_key': 'your-api-key'
        },
        'folder_structure': {
            '01_CASE_SUMMARIES_AND_RELATED_DOCS': ['AUTHORITIES', 'DETAILED_ANALYSIS_OF_ARGUMENTS', 'STATUTES'],
            '02_CONSTITUTIONAL_VIOLATIONS': ['PEREMPTORY_CHALLENGE'],
            '03_ELECTRONIC_ABUSE': [],
            '04_FRAUD_ON_THE_COURT': ['ATTORNEY_MISCONDUCT_MARK', 'CURATED_TEXT_RECORD', 'EVIDENCE_MANIPULATION'],
            '05_NON_DISCLOSURE_FC2107_FC2122': [],
            '06_PD065288_COURT_RECORD_DOCS': [],
            '07_POST_TRIAL_ABUSE': [],
            '08_TEXT_MESSAGES': ['SHANE_TO_FRIENDS', 'SHANE_TO_LISA', 'SHANE_TO_MARK_ZUCKER']
        },
        'categorization_config': {
            'use_ai': True,
            'confidence_threshold': 0.7
        },
        'scoring_config': {
            'use_ai_scoring': True,
            'weights': {
                'probative': 0.4,
                'relevance': 0.3,
                'admissibility': 0.3
            }
        },
        'max_concurrent_files': 5
    }
    
    # Create orchestrator
    orchestrator = LCASVerticalSliceFactory.create_orchestrator(config)
    
    # Process files
    file_paths = ['path/to/file1.pdf', 'path/to/file2.docx', 'path/to/file3.txt']
    results = await orchestrator.process_batch(file_paths, config)
    
    # Process results
    for result in results:
        if isinstance(result, Exception):
            print(f"Error processing file: {result}")
        else:
            print(f"Processed file: {result['content_analysis'].file_path}")
            if 'categorization' in result:
                print(f"  Category: {result['categorization'].category}")
            if 'legal_scoring' in result:
                print(f"  Overall Impact: {result['legal_scoring'].overall_impact}")

if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())