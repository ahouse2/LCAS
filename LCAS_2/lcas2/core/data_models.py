from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from pathlib import Path # Though paths are often stored as strings in data interchange

# Note: The actual ImageAnalysisResult, TimelineEvent, Pattern, LegalTheory dataclasses
# are currently defined within their respective plugins. For a truly shared model,
# those might also move here or be imported if they are to be part of FileAnalysisData directly.
# For now, we'll represent them as Dict[str, Any] or List[Dict[str,Any]] in FileAnalysisData
# to avoid circular dependencies until a broader data model refactor.

@dataclass
class FileExtractionMetadata:
    """Metadata from content extraction process."""
    format_detected: Optional[str] = None
    extraction_method: Optional[str] = None
    page_count: Optional[int] = None # For PDFs, DOCX
    line_count: Optional[int] = None # For text files
    word_count: Optional[int] = None # Calculated after content extraction
    character_count: Optional[int] = None # Calculated after content extraction
    # Add other specific metadata as needed by extractors, e.g., encoding_used

@dataclass
class FileIngestionDetail:
    """Details from the file ingestion process (subset of what file_ingestion_plugin returns per file)."""
    original_path: str
    backup_path: Optional[str] = None
    size: Optional[int] = None
    original_hash: Optional[str] = None # SHA256 from source
    backup_hash: Optional[str] = None   # SHA256 from backup (if different or for verification)
    status: Optional[str] = None # e.g., "copied_verified", "hash_mismatch"
    ingestion_timestamp: Optional[str] = None

@dataclass
class FileHashDetail:
    """Represents multiple hashes for a single file."""
    file_path: str # The path of the file that was hashed
    hashes: Dict[str, str] = field(default_factory=dict) # e.g., {"sha256": "...", "md5": "..."}
    size: Optional[int] = None
    last_modified: Optional[str] = None

@dataclass
class FileAnalysisData:
    """
    Represents the consolidated analysis data for a single file.
    This structure is expected as the value in the 'processed_files' dictionary
    that is passed between many plugins.
    Plugins contribute to or consume fields from this model.
    """
    # Core identifiers
    file_path: str  # Absolute path to the original file, used as the key in processed_files
    file_name: Optional[str] = None # Basename of the file

    # From FileIngestionPlugin (or general file attributes)
    ingestion_details: Optional[FileIngestionDetail] = None
    size_bytes: Optional[int] = None
    created_timestamp: Optional[str] = None
    modified_timestamp: Optional[str] = None
    accessed_timestamp: Optional[str] = None

    # From ContentExtractionPlugin
    content: Optional[str] = None
    summary_auto: Optional[str] = None # Basic summary from ContentExtractionPlugin
    extraction_meta: Optional[FileExtractionMetadata] = None
    content_extraction_error: Optional[str] = None

    # From ImageAnalysisPlugin (if applicable)
    # This would be a list of analysis results for each image found *within* this file_path
    image_analysis_results: Optional[List[Dict[str, Any]]] = field(default_factory=list) # List of ImageAnalysisResult as dicts
    ocr_text_from_images: Optional[str] = None # Combined OCR text from all images in this file

    # From HashGenerationPlugin (if run on this specific file, could be redundant with ingestion_details.original_hash)
    # This might be more for on-demand hashing results rather than primary file data.
    # For now, let's assume hashes from ingestion are primary. Specific hash runs can add to a different field.
    # specific_hashes_run: Optional[FileHashDetail] = None

    # From AI analysis (lcas_ai_wrapper_plugin)
    # This is the direct, potentially nested, output from the AI wrapper.
    ai_analysis_raw: Optional[Dict[str, Any]] = None
    # Key insights/tags extracted from ai_analysis_raw for easier access:
    ai_summary: Optional[str] = None
    ai_tags: List[str] = field(default_factory=list)
    ai_suggested_category: Optional[str] = None
    ai_key_entities: List[Dict[str, Any]] = field(default_factory=list) # e.g. [{"text": "John Doe", "type": "PERSON"}]
    ai_overall_confidence: Optional[float] = None

    # From TimelineAnalysisPlugin
    # List of events *extracted from this specific file's content*.
    # The global timeline is a separate artifact.
    timeline_events_extracted: List[Dict[str, Any]] = field(default_factory=list) # List of TimelineEvent as dicts

    # From EvidenceCategorizationPlugin
    # This is the *assigned* category after that plugin runs.
    assigned_category_folder_name: Optional[str] = None
    categorization_reason: Optional[str] = None

    # From PatternDiscoveryPlugin
    # List of patterns *this specific file* is directly part of.
    # Global patterns and theories are separate artifacts.
    associated_patterns: List[Dict[str, Any]] = field(default_factory=list) # List of Pattern as dicts

    # From EvidenceScoringPlugin
    evidence_scores: Optional[Dict[str, Any]] = field(default_factory=dict) # Populated by EvidenceScoringPlugin

    # Other dynamic metadata or scores
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    error_log: List[str] = field(default_factory=list) # Log of errors encountered for this file specifically

    def __post_init__(self):
        if self.file_path and not self.file_name:
            self.file_name = Path(self.file_path).name
        if self.content and not self.summary_auto: # Basic fallback if content exists but no summary
            self.summary_auto = self.content[:250] + "..." if len(self.content) > 250 else self.content


# Example of how a plugin might update/use this:
# def some_plugin_analyze(data: Any):
#     processed_files: Dict[str, FileAnalysisData] = data.get("processed_files", {})
#     for file_path, file_data_model_instance in processed_files.items():
#         # Read from file_data_model_instance.content
#         # Update file_data_model_instance.ai_summary = "New summary"
#     return {"processed_files_output": processed_files} # Return the updated structure
