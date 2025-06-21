# LCAS_2/lcas_adk_agents/main_coordinator_agent.py
from google.adk.agents import Agent
import os

# Attempt to load environment variables from a .env file in the same directory
# This is useful for local development to keep API keys out of the code.
# For production, environment variables should be set in the deployment environment.
try:
    from dotenv import load_dotenv
    # Assuming the .env file is in the 'lcas_adk_agents' directory,
    # and this script is also in that directory.
    # If running 'adk web' from the parent 'LCAS_2' directory,
    # ADK's built-in dotenv handling might pick up .env from LCAS_2/ or LCAS_2/lcas_adk_agents/
    # Explicitly loading it here ensures it's loaded if this module is imported directly.
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        # print(f"Loaded .env file from: {dotenv_path}")
    else:
        # print(f".env file not found at: {dotenv_path}. Relying on system environment variables.")
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

#     asyncio.run(main())
