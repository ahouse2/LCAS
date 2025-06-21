# LCAS_2/lcas_adk_agents/content_extraction_agent.py
import os
from typing import Dict, Any, Optional
from pathlib import Path

from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from google.adk.tools import tool # Required for the @tool decorator


# Assuming data_models.py is in the same directory or the package structure is set up correctly
try:
    from .data_models import FileAnalysisData # Assuming it's in the same ADK agents package
except ImportError:
    # Fallback for potential direct execution/testing, though ADK usually runs as a module
    from data_models import FileAnalysisData


# Placeholder for actual text extraction logic.
# In a full implementation, this would import from a refactored utility
# or directly from the existing content_extraction_plugin if structured appropriately.
def _placeholder_perform_text_extraction(filepath_str: str, mime_type: Optional[str], original_filename: str) -> Dict[str, Any]:
    """
    Placeholder for the actual text extraction logic.
    This function would call into the refactored text extraction utilities
    derived from the original content_extraction_plugin.py.
    """
    print(f"CONCEPTUAL_EXTRACTION: Attempting to extract text from {original_filename} (path: {filepath_str}, mime: {mime_type})")
    # Simulate extraction based on type
    if mime_type == "text/plain":
        return {"text_content": f"This is simulated plain text from {original_filename}.", "ocr_performed": False, "extraction_method": "simulated_text"}
    elif mime_type == "application/pdf":
        return {"text_content": f"This is simulated PDF text from {original_filename}. OCR might have been used.", "ocr_performed": True, "extraction_method": "simulated_pdf_ocr"}
    elif mime_type and "image" in mime_type: # Check if mime_type is not None
        return {"text_content": f"Simulated OCR text from image {original_filename}.", "ocr_performed": True, "extraction_method": "simulated_image_ocr"}
    else:
        return {"text_content": "", "ocr_performed": False, "extraction_method": "simulated_unknown_type", "error": f"Unsupported file type for simulation: {mime_type}"}

@tool
def tool_extract_file_content(file_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Extracts text content from a file identified by file_id, using its metadata
    stored in session_state. Updates the FileAnalysisData object.
    """
    agent_name = tool_context.agent_name
    tool_name = "tool_extract_file_content" # Define tool name for logging
    tool_context.add_log_entry(f"'{agent_name}' invoking '{tool_name}' for file_id: {file_id}", tool_name)

    if "processed_files_data" not in tool_context.state or file_id not in tool_context.state["processed_files_data"]:
        error_msg = f"FileAnalysisData not found in session state for file_id: {file_id}"
        tool_context.add_log_entry(error_msg, agent_name)
        return {"status": "error", "file_id": file_id, "message": error_msg}

    # Retrieve as dict, then convert to FAD object if necessary
    fad_data = tool_context.state["processed_files_data"][file_id]
    if isinstance(fad_data, FileAnalysisData):
        fad = fad_data # It's already an object
    elif isinstance(fad_data, dict):
        try:
            fad = FileAnalysisData(**fad_data)
        except TypeError as te:
            error_msg = f"Could not instantiate FileAnalysisData for {file_id} from dict: {te}"
            tool_context.add_log_entry(error_msg, agent_name)
            return {"status": "error", "file_id": file_id, "message": error_msg}
    else:
        error_msg = f"Invalid data type for file_id {file_id} in session_state: {type(fad_data)}"
        tool_context.add_log_entry(error_msg, agent_name)
        return {"status": "error", "file_id": file_id, "message": error_msg}


    # Conceptual: Use the (conceptual) preserved path for extraction
    # In a real system, this path would point to the securely stored file.
    # For this ADK agent, we rely on ingestion_details having enough info.
    if not fad.ingestion_details:
        error_msg = f"Ingestion details not found for file_id: {file_id}."
        tool_context.add_log_entry(error_msg, agent_name)
        fad.update_status("extraction_error", agent_name, error_msg)
        tool_context.state["processed_files_data"][file_id] = fad # Save updated FAD object
        return {"status": "error", "file_id": file_id, "message": error_msg}

    # The actual file path for extraction might be the original_filepath if not using preserved copies in ADK context
    # For this conceptual tool, we'll use original_filename and mime_type from ingestion_details.
    # The `conceptual_filepath_str` isn't strictly necessary if we're not reading a file system here.
    original_filename = fad.ingestion_details.original_filename
    mime_type = fad.ingestion_details.file_type_mime

    try:
        tool_context.add_log_entry(f"Attempting content extraction for {original_filename} (ID: {file_id})", agent_name)

        extraction_result = _placeholder_perform_text_extraction(
            filepath_str=fad.file_id, # Pass file_id as a stand-in for path if not using real FS
            mime_type=mime_type,
            original_filename=original_filename
        )

        if "error" in extraction_result:
            error_msg = f"Extraction failed for {file_id}: {extraction_result['error']}"
            fad.update_status("extraction_error", agent_name, error_msg)
            tool_context.add_log_entry(error_msg, agent_name)
        else:
            fad.extracted_text_content = extraction_result.get("text_content")
            if fad.extraction_meta: # Ensure extraction_meta exists
                fad.extraction_meta.ocr_performed = extraction_result.get("ocr_performed", False)
                fad.extraction_meta.text_extraction_method = extraction_result.get("extraction_method")
            else: # Should have been created by FileAnalysisData default_factory
                fad.extraction_meta = {"ocr_performed": extraction_result.get("ocr_performed", False), "text_extraction_method": extraction_result.get("extraction_method")} # type: ignore
            fad.update_status("text_extracted", agent_name, "Content extraction successful.")
            tool_context.add_log_entry(f"Content extraction successful for {file_id}.", agent_name)

        tool_context.state["processed_files_data"][file_id] = fad

        return {"status": "success", "file_id": file_id, "message": f"Content extraction completed for {file_id}."}

    except Exception as e:
        error_msg = f"Error during content extraction for {file_id}: {str(e)}"
        tool_context.add_log_entry(error_msg, agent_name)
        fad.update_status("extraction_error", agent_name, error_msg)
        tool_context.state["processed_files_data"][file_id] = fad
        return {"status": "error", "file_id": file_id, "message": error_msg}

# Define the ContentExtractionAgent
content_extraction_agent = Agent(
    name="ContentExtractionAgent",
    model=os.environ.get("ADK_DEFAULT_MODEL", "gemini-1.5-flash-001"),
    description="Extracts text and metadata content from various file types. Can perform OCR if needed.",
    instruction="You are the Content Extraction Agent. For a given file_id that has been ingested, "
                "use 'tool_extract_file_content' to extract its textual content. "
                "This tool will update the session state with the extracted information directly into the FileAnalysisData object for that file_id.",
    tools=[tool_extract_file_content],
)

# print(f"Defined ADK Agent: {getattr(content_extraction_agent, 'name', 'Unnamed ContentExtractionAgent')}")
