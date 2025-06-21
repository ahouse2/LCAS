# LCAS_2/lcas_adk_agents/file_processing_agent.py
import os
import hashlib
import datetime
from typing import Dict, Any
from pathlib import Path

from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from google.adk.tools import tool # Required for the @tool decorator

# Assuming data_models.py is in the same directory or the package structure is set up correctly
try:
    from .data_models import FileAnalysisData, FileIngestionDetail
except ImportError:
    # Fallback for potential direct execution/testing, though ADK usually runs as a module
    from data_models import FileAnalysisData, FileIngestionDetail

@tool
def tool_ingest_and_preserve_file(original_filepath_str: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Ingests a file: calculates its hash, records metadata,
    and prepares its FileAnalysisData structure in session_state.
    Actual file copying/preservation is logged as a conceptual step.
    A 'case_id' must be present in the tool_context.state.
    """
    agent_name = tool_context.agent_name
    tool_name = "tool_ingest_and_preserve_file" # Define tool name for logging
    tool_context.add_log_entry(f"'{agent_name}' invoking '{tool_name}' for: {original_filepath_str}", tool_name)

    original_filepath = Path(original_filepath_str)
    file_id = None # Initialize file_id

    if not original_filepath.exists() or not original_filepath.is_file():
        error_msg = f"File not found or is not a file: {original_filepath_str}"
        tool_context.add_log_entry(error_msg, agent_name)
        return {"status": "error", "file_id": None, "message": error_msg}

    try:
        # 1. Calculate File Hash (SHA256) to use as file_id
        hasher = hashlib.sha256()
        with open(original_filepath, 'rb') as f:
            while chunk := f.read(8192): # Read in chunks
                hasher.update(chunk)
        file_id = hasher.hexdigest()
        tool_context.add_log_entry(f"Calculated SHA256 hash ({file_id}) for {original_filepath.name}", agent_name)

        # 2. Get Case ID from session state
        case_id = tool_context.state.get("case_id")
        if not case_id:
            error_msg = "Case ID not found in session state. Cannot ingest file."
            tool_context.add_log_entry(error_msg, agent_name)
            # Still return file_id if calculated, so it can be tracked even if ingestion fails here
            return {"status": "error", "file_id": file_id, "message": error_msg}

        # 3. Conceptual Preservation Path & Details
        preserved_filename = f"{file_id}_{original_filepath.name}"
        # Using a conceptual relative path for the ADK agent's understanding
        conceptual_preservation_dir_str = f"cases/{case_id}/preserved_files/{file_id}"
        conceptual_full_path_str = f"{conceptual_preservation_dir_str}/{preserved_filename}"

        tool_context.add_log_entry(f"Conceptual preservation path for {original_filepath.name} would be: {conceptual_full_path_str}", agent_name)
        tool_context.add_log_entry(f"ACTION_LOG: File '{original_filepath.name}' (ID: {file_id}) conceptually preserved at '{conceptual_full_path_str}'. Actual file system operation deferred to LCAS Core.", agent_name)


        # 4. Gather File Metadata
        file_size_bytes = original_filepath.stat().st_size
        file_type_extension = original_filepath.suffix.lower()
        mime_type_map = {
            ".pdf": "application/pdf", ".txt": "text/plain", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".eml": "message/rfc822",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".csv": "text/csv"
        }
        file_type_mime = mime_type_map.get(file_type_extension, "application/octet-stream")

        ingestion_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

        ingestion_data = FileIngestionDetail(
            original_filename=original_filepath.name,
            preserved_filename=preserved_filename,
            preservation_path_conceptual=conceptual_full_path_str, # Store string path
            ingestion_timestamp=ingestion_ts,
            file_hash_sha256=file_id,
            file_type_mime=file_type_mime,
            file_type_extension=file_type_extension,
            file_size_bytes=file_size_bytes
        )

        # 5. Create/Update FileAnalysisData in session_state
        if "processed_files_data" not in tool_context.state:
            tool_context.state["processed_files_data"] = {}

        # Create a new FAD or update if a placeholder existed (e.g. from a manifest)
        fad = tool_context.state["processed_files_data"].get(file_id)
        if fad and isinstance(fad, dict): # If it's a dict, try to convert to FAD object
            try:
                fad = FileAnalysisData(**fad)
            except TypeError: # If dict can't be cast, create new
                fad = FileAnalysisData(file_id=file_id, ingestion_details=ingestion_data)
        elif not fad: # If no placeholder existed
             fad = FileAnalysisData(file_id=file_id, ingestion_details=ingestion_data)

        # Update ingestion details and status
        fad.ingestion_details = ingestion_data # Overwrite/set ingestion details
        fad.update_status("ingested", agent_name, f"Successfully ingested from {original_filepath_str}")

        tool_context.state["processed_files_data"][file_id] = fad # Store FAD object
        tool_context.add_log_entry(f"FileAnalysisData for {file_id} ({original_filepath.name}) created/updated and stored in session_state.", agent_name)

        # 6. Update uploaded_files_metadata (if it exists from a previous step, e.g. UI upload)
        if "uploaded_files_metadata" in tool_context.state and isinstance(tool_context.state["uploaded_files_metadata"], dict):
            if original_filepath.name in tool_context.state["uploaded_files_metadata"]:
                tool_context.state["uploaded_files_metadata"][original_filepath.name]["status"] = "ingested"
                tool_context.state["uploaded_files_metadata"][original_filepath.name]["file_id"] = file_id
                tool_context.state["uploaded_files_metadata"][original_filepath.name]["ingested_timestamp"] = ingestion_ts


        return {"status": "success", "file_id": file_id, "message": f"File '{original_filepath.name}' ingested successfully as {file_id}."}

    except Exception as e:
        error_msg = f"Error during ingestion of {original_filepath_str}: {str(e)}"
        tool_context.add_log_entry(error_msg, agent_name)

        # Attempt to update FAD with error status if possible
        if file_id and "processed_files_data" in tool_context.state and isinstance(tool_context.state["processed_files_data"], dict):
            fad_entry = tool_context.state["processed_files_data"].get(file_id)
            if isinstance(fad_entry, FileAnalysisData):
                fad_entry.update_status("ingestion_error", agent_name, error_msg)
                fad_entry.add_processing_log(error_msg, agent_name)
            elif isinstance(fad_entry, dict): # If it's still a dict
                 fad_entry["processing_status"] = "ingestion_error"
                 if "processing_log" not in fad_entry or not isinstance(fad_entry["processing_log"], list): fad_entry["processing_log"] = []
                 fad_entry["processing_log"].append(f"{datetime.datetime.now(datetime.timezone.utc).isoformat()} - {agent_name}: {error_msg}")
            else: # No FAD entry yet, create one to log the error
                minimal_ingestion = FileIngestionDetail(original_filename=original_filepath.name, file_hash_sha256=file_id)
                error_fad = FileAnalysisData(file_id=file_id, ingestion_details=minimal_ingestion)
                error_fad.update_status("ingestion_error", agent_name, error_msg)
                tool_context.state["processed_files_data"][file_id] = error_fad

        return {"status": "error", "file_id": file_id, "message": error_msg}

# Define the FileProcessingAgent
file_processing_agent = Agent(
    name="FileProcessingAgent",
    model=os.environ.get("ADK_DEFAULT_MODEL", "gemini-1.5-flash-001"),
    description="Responsible for ingesting files, calculating hashes, extracting basic metadata, and preparing files for deeper analysis.",
    instruction="You are the File Processing Agent. Your job is to take file paths provided by the user or other agents "
                "and use the 'tool_ingest_and_preserve_file' to process them. "
                "Ensure each file is ingested and its FileAnalysisData structure is created and updated in the session state. "
                "If multiple files need processing, invoke the tool for each file path given. "
                "The 'case_id' must be available in session state before you can process files.",
    tools=[tool_ingest_and_preserve_file],
)

# print(f"Defined ADK Agent: {getattr(file_processing_agent, 'name', 'Unnamed FileProcessingAgent')}")
