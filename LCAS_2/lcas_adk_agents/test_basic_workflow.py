# LCAS_2/lcas_adk_agents/test_basic_workflow.py
import asyncio
import os
import uuid
from pathlib import Path

# Setup environment for local testing (in case .env is not automatically picked up by parent runner)
try:
    from dotenv import load_dotenv
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        print(f"Loaded .env file from: {dotenv_path}")
    else:
        print(f"Test script: .env file not found at: {dotenv_path}. Relying on system environment variables.")
except ImportError:
    print("Test script: dotenv library not found. Relying on system environment variables.")


from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

# Assuming ADK agents are correctly imported via __init__.py or direct reference
try:
    from .main_coordinator_agent import root_agent
    from .data_models import FileAnalysisData # To inspect the type
except ImportError: # Fallback for different execution contexts
    from main_coordinator_agent import root_agent
    from data_models import FileAnalysisData

async def run_test():
    print("--- Starting ADK Basic Workflow Test ---")

    # 1. Setup SessionService and Runner
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent, # Our main coordinator
        app_name="lcas2_test_app",
        session_service=session_service
    )
    print(f"Runner initialized with agent: {root_agent.name}")

    # 2. Simulate GUI creating a new case and session
    case_id = str(uuid.uuid4())
    user_id = "test_user_workflow"

    initial_state_dict = {
        "case_id": case_id,
        "case_name": "Test Case - ADK Workflow",
        "case_theory_summary": "This is a test case to verify ADK agent delegation for file processing.",
        "uploaded_files_metadata": {
            "sample_doc1.txt": {"size": 123, "type": "text/plain", "status": "pending_ingestion", "local_path_for_test": "sample_doc1.txt"},
            "sample_image1.png": {"size": 456, "type": "image/png", "status": "pending_ingestion", "local_path_for_test": "sample_image1.png"}
        },
        "processed_files_data": {}, # Initialize as empty dict
        "analysis_pipeline_config": {
            "run_ocr_on_images": True
        },
        "current_analysis_status": "idle",
        "error_messages": []
    }
    session_id = await session_service.create_session(
        app_name="lcas2_test_app",
        user_id=user_id,
        state=initial_state_dict
    )
    print(f"Session created with ID: {session_id}, Case ID: {case_id}")

    # Create dummy files for the ingestion tool to "find"
    Path("sample_doc1.txt").write_text("This is sample document 1. It contains plain text.")
    Path("sample_image1.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\xf8\xff\xff?_\x03\x00\x08\xfc_\xfe\x01<\x9c\xc7\xa0\x00\x00\x00\x00IEND\xaeB`\x82") # Minimal valid PNG

    # 3. Simulate user request to process uploaded files
    # Corrected approach: iterate through the initial state we just set up
    current_session_state = await session_service.get_session_state(app_name="lcas2_test_app", user_id=user_id, session_id=session_id)
    files_to_process_from_gui = current_session_state.get("uploaded_files_metadata", {}).items()


    for original_filename, metadata in files_to_process_from_gui:
        if metadata.get("status") == "pending_ingestion":
            local_path = metadata.get("local_path_for_test", original_filename)

            print(f"\n>>> Simulating GUI request: Process file '{original_filename}' (path: {local_path})")
            user_query_ingest = f"Please ingest and process the new file located at '{local_path}' for case {case_id}."
            user_content_ingest = Content(parts=[Part(text=user_query_ingest)])

            async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=user_content_ingest):
                if event.is_final_response():
                    print(f"<<< Root Agent Final Response (after ingest request for {original_filename}): {event.stringify_content_for_llm()}")
                    break

            current_state_after_ingest = await session_service.get_session_state(app_name="lcas2_test_app", user_id=user_id, session_id=session_id)
            fad_objects = current_state_after_ingest.get("processed_files_data", {})
            found_file_id = None
            for fid, fad_data_item in fad_objects.items():
                current_original_filename = ""
                if isinstance(fad_data_item, FileAnalysisData): # If already an object
                    current_original_filename = fad_data_item.ingestion_details.original_filename if fad_data_item.ingestion_details else ""
                elif isinstance(fad_data_item, dict): # If it's a dict from state
                    current_original_filename = fad_data_item.get("ingestion_details", {}).get("original_filename", "")

                if current_original_filename == original_filename:
                    found_file_id = fid
                    break

            if found_file_id:
                fad_for_status = fad_objects[found_file_id]
                current_status = fad_for_status.processing_status if isinstance(fad_for_status, FileAnalysisData) else fad_for_status.get('processing_status', 'unknown')
                print(f"File '{original_filename}' ingested. File ID: {found_file_id}. Current status: {current_status}")

                print(f"\n>>> Simulating GUI request: Extract content for file_id '{found_file_id}'")
                user_query_extract = f"Extract text content for file {found_file_id}."
                user_content_extract = Content(parts=[Part(text=user_query_extract)])

                async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=user_content_extract):
                    if event.is_final_response():
                        print(f"<<< Root Agent Final Response (after extract request for {found_file_id}): {event.stringify_content_for_llm()}")
                        break
            else:
                print(f"ERROR: Could not find file_id for '{original_filename}' after ingestion attempt.")

    print("\n--- Final Session State Inspection ---")
    final_state = await session_service.get_session_state(app_name="lcas2_test_app", user_id=user_id, session_id=session_id)

    print(f"Case ID: {final_state.get('case_id')}")
    print(f"Status: {final_state.get('current_analysis_status')}")

    print("\nUploaded Files Metadata:")
    for fname, meta in final_state.get("uploaded_files_metadata", {}).items():
        print(f"  - {fname}: Status: {meta.get('status')}, File ID: {meta.get('file_id')}")

    print("\nProcessed Files Data (FileAnalysisData objects):")
    for file_id, fad_item in final_state.get("processed_files_data", {}).items():
        original_name = "N/A"; extracted_text_preview = "N/A"; status = "N/A"

        if isinstance(fad_item, FileAnalysisData):
            original_name = fad_item.ingestion_details.original_filename if fad_item.ingestion_details else "N/A"
            extracted_text_preview = (fad_item.extracted_text_content[:70] + "...") if fad_item.extracted_text_content else "No text extracted"
            status = fad_item.processing_status
        elif isinstance(fad_item, dict):
            original_name = fad_item.get("ingestion_details", {}).get("original_filename", "N/A")
            extracted_text_preview = (fad_item.get("extracted_text_content", "")[:70] + "...") if fad_item.get("extracted_text_content") else "No text extracted"
            status = fad_item.get("processing_status", "N/A")

        print(f"  File ID: {file_id}")
        print(f"    Original Name: {original_name}")
        print(f"    Status: {status}")
        print(f"    Extracted Text Preview: {extracted_text_preview}")

    Path("sample_doc1.txt").unlink(missing_ok=True)
    Path("sample_image1.png").unlink(missing_ok=True)
    print("\nCleaned up dummy files.")

    print("\n--- Test Complete ---")

if __name__ == "__main__":
    asyncio.run(run_test())
