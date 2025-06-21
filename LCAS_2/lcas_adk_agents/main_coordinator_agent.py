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

        pass # Rely on system environment variables if .env is not present
except ImportError:
    # dotenv is not installed, which is fine if env vars are set system-wide.
    # print("dotenv library not found. Relying on system environment variables.")
    pass

# Define the root agent for the Legal Case Analysis System (LCAS)
# This will be the main coordinator agent.
# Initially, it will be very simple. We will add tools, sub-agents,
# and more complex instructions progressively.

# Determine if GOOGLE_GENAI_USE_VERTEXAI is set and True
# The value from os.environ will be a string 'True' or 'False' if set.
USE_VERTEX_AI_STR = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "FALSE").upper()
USE_VERTEX_AI = USE_VERTEX_AI_STR == "TRUE"

# Choose model configuration based on whether Vertex AI is used
if USE_VERTEX_AI:
    # For Vertex AI, the model name is usually just the model identifier.
    # Authentication is handled via gcloud application-default credentials.
    # Make sure GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION are set in .env
    MODEL_ID = "gemini-1.5-flash-001" # Or "gemini-1.5-pro-001" when available and configured
    print(f"ADK Agent configured to use Vertex AI model: {MODEL_ID}")
    if not os.environ.get("GOOGLE_CLOUD_PROJECT") or not os.environ.get("GOOGLE_CLOUD_LOCATION"):
        print("WARNING: GOOGLE_GENAI_USE_VERTEXAI is TRUE, but GOOGLE_CLOUD_PROJECT or GOOGLE_CLOUD_LOCATION is not set.")
        print("Please set them in your .env file or environment.")
else:
    # For Google AI Studio, model name is often prefixed, e.g., "models/gemini-1.5-pro-latest"
    # ADK handles the "models/" prefix internally if you provide the base model name.
    # Authentication uses GOOGLE_API_KEY.
    MODEL_ID = "gemini-1.5-flash-001" # Or "gemini-1.5-pro-001" etc.
    # MODEL_ID = "gemini-pro" # A common one for general tasks, but 1.5 Flash is newer
    print(f"ADK Agent configured to use Google AI Studio model: {MODEL_ID}")
    if not os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY") == "YOUR_GOOGLE_AI_STUDIO_API_KEY_HERE":
        print("WARNING: GOOGLE_GENAI_USE_VERTEXAI is FALSE, but GOOGLE_API_KEY is not set or is using the placeholder.")
        print("Please set GOOGLE_API_KEY in your .env file or environment.")


# Define the root agent
# This is the agent that ADK will discover if you run `adk web` or `adk run lcas_adk_agents.main_coordinator_agent`
# from the parent directory (LCAS_2).
# The variable holding the root agent must be globally accessible in this module.
root_agent = Agent(
    name="LCAS_Main_Coordinator",
    model=MODEL_ID, # ADK will handle Google AI Studio vs Vertex AI based on env vars
    description="The main coordinating agent for the Legal Case Analysis System v2 (LCAS_2). It will delegate tasks to specialized sub-agents.",
    instruction="You are the main coordinator for LCAS_2, a system designed to analyze legal cases. "
                "Your primary role is to understand user requests related to a legal case "
                "and delegate tasks to appropriate specialist sub-agents (to be added later). "
                "For now, acknowledge the user's request and state that your capabilities are under development.",
    # tools=[], # No tools for the root agent initially, it will delegate
    # sub_agents=[], # Sub-agents will be added in later steps
    # output_key="main_coordinator_output", # Optional: to save its direct output to state
)

# To make it runnable with `adk run lcas_adk_agents.main_coordinator_agent` or discoverable by `adk web`,
# ensure the agent instance is assigned to a global variable (like `root_agent` above).
# The ADK CLI looks for such global `Agent` instances.

print(f"Defined ADK Agent: {getattr(root_agent, 'name', 'Unnamed Agent')}")

# Example of how you might run it programmatically (for testing within Python, not for adk cli)
# if __name__ == '__main__':
#     import asyncio
#     from google.adk.runners import Runner
#     from google.adk.sessions import InMemorySessionService
#     from google.genai.types import Content, Part

#     async def main():
#         session_service = InMemorySessionService()
#         runner = Runner(
#             agent=root_agent,
#             app_name="lcas2_test_app",
#             session_service=session_service
#         )
#         session_id = await session_service.create_session(app_name="lcas2_test_app", user_id="test_user")

#         user_query = "Start a new case analysis for me."
#         print(f"\nSending query to agent: {user_query}")
#         user_content = Content(parts=[Part(text=user_query)])

#         async for event in runner.run_async(user_id="test_user", session_id=session_id, new_message=user_content):
#             if event.is_final_response():
#                 if event.content and event.content.parts:
#                     print(f"Agent Response: {event.content.parts[0].text}")
#                 break
#         await session_service.delete_session(app_name="lcas2_test_app", user_id="test_user", session_id=session_id)

#     asyncio.run(main()