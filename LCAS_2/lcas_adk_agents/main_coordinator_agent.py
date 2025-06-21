# LCAS_2/lcas_adk_agents/main_coordinator_agent.py
from google.adk.agents import Agent
import os

# Assuming data_models.py, file_processing_agent.py, and content_extraction_agent.py
# are in the same directory or the package structure is set up correctly via __init__.py
try:
    from .file_processing_agent import file_processing_agent
    from .content_extraction_agent import content_extraction_agent
    # from .data_models import FileAnalysisData # Not directly used by root agent, but good to ensure it's importable
except ImportError:
    # Fallback for potential direct execution/testing, though ADK usually runs as a module
    from file_processing_agent import file_processing_agent
    from content_extraction_agent import content_extraction_agent
    # from data_models import FileAnalysisData


# --- Environment Variable Loading (Preserve existing logic) ---
try:
    from dotenv import load_dotenv
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        # print(f"Loaded .env file from: {dotenv_path}")
    else:
        # print(f".env file not found at: {dotenv_path}. Relying on system environment variables.")
        pass
except ImportError:
    # print("dotenv library not found. Relying on system environment variables.")
    pass

USE_VERTEX_AI_STR = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "FALSE").upper()
USE_VERTEX_AI = USE_VERTEX_AI_STR == "TRUE"

MODEL_ID = "gemini-1.5-flash-001" # Default starting model

if USE_VERTEX_AI:
    print(f"ADK Root Agent configured to use Vertex AI model: {MODEL_ID}")
    if not os.environ.get("GOOGLE_CLOUD_PROJECT") or not os.environ.get("GOOGLE_CLOUD_LOCATION"):
        print("WARNING: GOOGLE_GENAI_USE_VERTEXAI is TRUE, but GOOGLE_CLOUD_PROJECT or GOOGLE_CLOUD_LOCATION is not set.")
else:
    print(f"ADK Root Agent configured to use Google AI Studio model: {MODEL_ID}")
    if not os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY") == "YOUR_GOOGLE_AI_STUDIO_API_KEY_HERE":
        print("WARNING: GOOGLE_GENAI_USE_VERTEXAI is FALSE, but GOOGLE_API_KEY is not set or is using the placeholder.")
# --- End of Preserved Environment Logic ---


# Define the root agent
root_agent = Agent(
    name="LCAS_Main_Coordinator",
    model=MODEL_ID,
    description="The main coordinating agent for LCAS_2. Delegates tasks to specialized sub-agents for file processing, analysis, and reporting.",
    instruction="You are the main coordinator for LCAS_2, a system designed to analyze legal cases. "
                "Your primary role is to understand user requests and delegate tasks to appropriate specialist sub-agents. "
                "Key tasks and delegations:\n"
                "- If the user wants to add or ingest new files, or if files are newly uploaded and need initial processing, "
                "  delegate to the 'FileProcessingAgent'. Clearly state which file path(s) it should process. "
                "  (Example user query: 'Process /path/to/document.pdf')\n"
                "- If the user wants to extract text content from an already ingested file (identified by its file_id), "
                "  delegate to the 'ContentExtractionAgent'. Clearly state which file_id needs content extraction. "
                "  (Example user query: 'Extract text from file_id abc123xyz')\n"
                "- For other analysis tasks (summarization, scoring, pattern discovery - to be implemented later), "
                "  you will delegate to other specialist agents. For now, if such a request is made, state that the capability is coming soon.\n"
                "When delegating, make sure to provide the sub-agent with any necessary information from the user's request or the session state. "
                "After a sub-agent completes its task, acknowledge its completion. "
                "If you don't understand the request or cannot delegate, inform the user.",
    tools=[], # Root agent primarily delegates, may not need its own tools initially.
    sub_agents=[
        file_processing_agent,
        content_extraction_agent
        # Other agents like EvidenceAnalyzerAgent, CaseStrategistAgent, ReportGeneratorAgent will be added here later.
    ],
    # output_key="main_coordinator_output", # Optional
)

print(f"Defined ADK Root Agent: {getattr(root_agent, 'name', 'Unnamed Agent')} with sub-agents: {[sa.name for sa in root_agent.sub_agents]}")
