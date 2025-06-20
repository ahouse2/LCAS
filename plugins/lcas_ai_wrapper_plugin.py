#!/usr/bin/env python3
"""
LCAS AI Wrapper Plugin
Integrates the EnhancedAIFoundationPlugin into the LCAS plugin system.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional

from lcas.core import AnalysisPlugin, LCASCore
# Assuming it's in the same directory
from plugins.ai_integration_plugin import EnhancedAIFoundationPlugin

logger = logging.getLogger(__name__)


class LCASAIWrapperPlugin(AnalysisPlugin):
    """
    Wrapper plugin to integrate the advanced AI capabilities.
    """

    def __init__(self):
        self.ai_foundation: Optional[EnhancedAIFoundationPlugin] = None
        self.lcas_core: Optional[LCASCore] = None

    @property
    def name(self) -> str:
        return "lcas_ai_wrapper_plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Integrates advanced AI analysis capabilities (OpenAI, Anthropic, Local) into LCAS."

    @property
    def dependencies(self) -> List[str]:
        # These are Python package dependencies, not other LCAS plugins.
        # The actual AI SDKs are handled by ai_integration_plugin.py's imports
        # and the main requirements.txt / setup.py.
        return ["openai", "anthropic", "httpx", "requests"]

    async def initialize(self, core_app: LCASCore) -> bool:
        """Initialize the plugin and the wrapped AI foundation plugin."""
        self.lcas_core = core_app
        logger.info(f"{self.name}: Initializing...")
        try:
            # The EnhancedAIFoundationPlugin loads its own config from 'config/ai_config.json'
            # or creates a default one.
            # We need to ensure that 'config/ai_config.json' is discoverable.
            # For now, we assume 'config/' is in the root directory where LCAS
            # is run.
            self.ai_foundation = EnhancedAIFoundationPlugin(
                config_path="config/ai_config.json")

            if not self.ai_foundation.config:
                logger.error(
                    f"{self.name}: Failed to load AI foundation configuration.")
                return False

            # Check provider availability
            status = self.ai_foundation.get_comprehensive_status()
            available_providers = [p for p, s in status.get(
                "providers", {}).items() if s.get("available")]
            if not available_providers:
                logger.warning(
                    f"{self.name}: No AI providers seem to be available/configured in 'config/ai_config.json'.")
                logger.warning(
                    f"{self.name}: Please ensure API keys are set in 'config/ai_config.json'.")
            else:
                logger.info(
                    f"{self.name}: Available AI providers: {available_providers}")

            logger.info(f"{self.name}: Initialized successfully.")
            return True
        except Exception as e:
            logger.error(
                f"{self.name}: Error during initialization: {e}", exc_info=True)
            return False

    async def cleanup(self) -> None:
        """Cleanup resources."""
        logger.info(f"{self.name}: Cleaning up.")
        self.ai_foundation = None
        self.lcas_core = None

    async def analyze(self, data: Any) -> Dict[str, Any]:
        """
        Perform AI analysis on the provided data.
        'data' is expected to be a dictionary from LCASCore, containing:
        - 'file_content': The text content of the file.
        - 'file_path': The path to the file being analyzed.
        - 'case_context': Optional dictionary with case-specific context.
        """
        if not self.ai_foundation:
            logger.error(f"{self.name}: AI Foundation not initialized.")
            return {"error": "AI Foundation not initialized", "success": False}

        file_content = data.get("file_content")
        file_path = data.get("file_path", "unknown_file")

        # Extract relevant context for the AI plugin
        # The LCASCore config might have case_name, etc.
        # The EnhancedAIFoundationPlugin uses its own user_settings for case_type, jurisdiction
        # We can pass additional runtime context if available
        lcas_config = self.lcas_core.config if self.lcas_core else None
        case_context = {
            "lcas_case_name": lcas_config.case_name if lcas_config else "Unknown Case",
            # Add other relevant details from lcas_config or data if needed
        }

        # Update AI plugin's user settings if they can be derived from LCAS config
        # This is an example; actual mapping might differ based on available
        # config fields
        if lcas_config and hasattr(
                lcas_config, 'case_type_for_ai'):  # Fictional field
            self.ai_foundation.update_user_settings(
                case_type=lcas_config.case_type_for_ai)
        if lcas_config and hasattr(
                lcas_config, 'jurisdiction_for_ai'):  # Fictional field
            self.ai_foundation.update_user_settings(
                jurisdiction=lcas_config.jurisdiction_for_ai)

        logger.info(f"{self.name}: Analyzing file: {file_path} with AI.")

        try:
            # The EnhancedAIFoundationPlugin's analyze_file_content expects:
            # content: str, file_path: str = "", context: Dict[str, Any] = None
            ai_results = await self.ai_foundation.analyze_file_content(
                content=file_content,
                file_path=file_path,
                context=case_context  # Pass LCAS case context to AI plugin
            )

            # Check if rate limited
            if ai_results.get("rate_limited"):
                logger.warning(
                    f"{self.name}: AI analysis for {file_path} was skipped due to rate limits.")
                return {
                    "status": "skipped_rate_limited",
                    "message": ai_results.get("message"),
                    "file_path": file_path,
                    "success": False  # Or True, depending on how LCAS should treat this
                }

            # Adapt the results to a format expected by LCASCore if necessary.
            # For now, assume the raw ai_results are suitable or that consuming plugins/UI can handle them.
            # The EnhancedAIFoundationPlugin already structures its output
            # well.

            # Example: Flatten results from multiple agents if needed, or
            # select primary
            final_result = {
                "status": "success",
                "file_path": file_path,
                # Contains results from each agent (doc_intel, legal_analysis)
                "provider_results": ai_results,
                "summary": "AI analysis performed.",  # Generic summary
                "success": True
            }

            # Potentially extract a top-level summary or key findings if possible
            # This depends on how the GUI or other parts of LCAS expect to consume results.
            # For example, trying to get a summary from the
            # 'document_intelligence' agent:
            doc_intel_res = ai_results.get(
                "document_intelligence", {}).get(
                "findings", {})
            if doc_intel_res and isinstance(
                    doc_intel_res, dict) and "summary" in doc_intel_res:
                final_result["summary"] = doc_intel_res["summary"]
            elif isinstance(doc_intel_res, str):  # If findings itself is a string summary
                final_result["summary"] = doc_intel_res

            return final_result

        except Exception as e:
            logger.error(
                f"{self.name}: Error during AI analysis for {file_path}: {e}", exc_info=True)
            return {"error": str(e), "file_path": file_path, "success": False}

# To ensure PluginManager can find this class by a predictable name:
# The PluginManager converts 'lcas_ai_wrapper_plugin.py' to 'LcasAiWrapperPlugin'
# This class is named LCASAIWrapperPlugin, which should work.
