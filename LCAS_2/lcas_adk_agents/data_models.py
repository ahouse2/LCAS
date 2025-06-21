# LCAS_2/lcas_adk_agents/data_models.py
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class FileIngestionDetail:
    original_filename: str
    preserved_filename: Optional[str] = None # Could be <hash>_<original_filename>
    preservation_path_conceptual: Optional[str] = None # e.g., cases/<case_id>/preserved/<file_id>/
    ingestion_timestamp: Optional[str] = None
    file_hash_sha256: Optional[str] = None
    file_type_mime: Optional[str] = None
    file_type_extension: Optional[str] = None
    file_size_bytes: Optional[int] = None

@dataclass
class FileExtractionMetadata:
    ocr_performed: bool = False
    text_extraction_method: Optional[str] = None # e.g., "tika", "pypdf", "custom_ocr"
    transcription_method: Optional[str] = None # e.g., "whisper_api_v1"
    metadata_extraction_method: Optional[str] = None # e.g., "exiftool", "email_parser_v2"

@dataclass
class AIScore:
    score_name: str
    score_value: Optional[float] = None
    confidence: Optional[float] = None
    rationale: Optional[str] = None
    model_used: Optional[str] = None # e.g., gemini-1.5-pro, custom_heuristic_v1

@dataclass
class IdentifiedEntity:
    text: str
    type: str # e.g., PERSON, ORG, DATE, LOCATION, LEGAL_STATUTE
    offset_start: Optional[int] = None
    offset_end: Optional[int] = None
    source_sentences: List[str] = field(default_factory=list)

@dataclass
class TimelineEvent:
    event_date_str: str # Could be a range or approximate
    event_description: str
    source_document_ids: List[str] = field(default_factory=list) # List of file_ids
    source_excerpts: List[str] = field(default_factory=list)
    relevance_to_case_theory: Optional[str] = None
    event_id: Optional[str] = None # Optional unique ID for the event itself

@dataclass
class DiscoveredPattern:
    pattern_id: str
    pattern_name: str
    description: str
    supporting_file_ids: List[str] = field(default_factory=list)
    related_entities: List[str] = field(default_factory=list)
    significance_score: Optional[float] = None # How impactful this pattern might be
    contextual_summary: Optional[str] = None

@dataclass
class FileAnalysisData:
    # Core Identifiers & Ingestion Details
    file_id: str  # Unique ID, typically SHA256 hash of content
    ingestion_details: FileIngestionDetail

    # Content Extraction
    extracted_text_content: Optional[str] = None
    extracted_metadata_os: Optional[Dict[str, Any]] = field(default_factory=dict) # OS-level metadata like ctime, mtime
    extracted_metadata_filetype: Optional[Dict[str, Any]] = field(default_factory=dict) # E.g., EXIF, email headers, PDF metadata
    extraction_meta: FileExtractionMetadata = field(default_factory=FileExtractionMetadata)

    # AI Analysis Results
    summary_short: Optional[str] = None # AI-generated
    summary_long: Optional[str] = None  # AI-generated, more detailed
    identified_entities: List[IdentifiedEntity] = field(default_factory=list)
    key_phrases_extracted: List[str] = field(default_factory=list) # AI-extracted
    sentiment: Optional[AIScore] = None # Overall sentiment of the document w.r.t case theory
    relevance_to_case_theory: Optional[AIScore] = None
    custom_tags: List[str] = field(default_factory=list) # User or AI assigned tags/categories

    # Scoring
    scores: Dict[str, AIScore] = field(default_factory=dict) # e.g., "admissibility", "prejudicial_effect", "completeness"
                                                       # Each key would be a score name, value is AIScore object

    # Relations & Context (can be populated by later stage agents)
    timeline_events_contained: List[TimelineEvent] = field(default_factory=list) # Events found *within* this file
    linked_document_ids: Dict[str, str] = field(default_factory=dict) # key: linked_file_id, value: reason/type of link
    part_of_patterns: List[str] = field(default_factory=list) # List of pattern_ids this file contributes to

    # Processing Status
    processing_status: str = "pending_ingestion" # e.g., pending_ingestion, ingested, text_extracted, analyzed, error
    processing_log: List[str] = field(default_factory=list) # Chronological log of processing steps/errors for this file
    agent_contributions: Dict[str, str] = field(default_factory=dict) # Tracks which agent performed which major step

    # For GUI interaction or user notes
    user_notes: Optional[str] = None
    is_flagged: bool = False

    def add_processing_log(self, message: str, agent_name: Optional[str] = None):
        import datetime
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        log_entry = f"{timestamp} - {agent_name if agent_name else 'System'}: {message}"
        self.processing_log.append(log_entry)

    def update_status(self, new_status: str, agent_name: Optional[str] = None, message: Optional[str] = None):
        self.processing_status = new_status
        log_message = f"Status changed to '{new_status}'."
        if message:
            log_message += f" Details: {message}"
        self.add_processing_log(log_message, agent_name)
        if agent_name:
            self.agent_contributions[agent_name] = new_status
