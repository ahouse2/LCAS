#!/usr/bin/env python3
"""
LCAS AI Wrapper Plugin
Integrates the EnhancedAIFoundationPlugin into the LCAS plugin system.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path # Added for path resolution

from lcas2.core import AnalysisPlugin, LCASCore, LCASConfig, CaseTheoryConfig # Updated import
from .ai_integration_plugin import EnhancedAIFoundationPlugin, AIConfigSettings

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
        return "1.1.0" # Version updated

    @property
    def description(self) -> str:
        return "Integrates advanced AI analysis capabilities using settings from LCASConfig and ai_config.json."

    @property
    def dependencies(self) -> List[str]:
        # Informational; actual dependencies are managed by the project environment.
        return ["openai", "anthropic", "httpx", "requests"] # httpx and requests are for local models if used

    async def initialize(self, core_app: LCASCore) -> bool:
        """Initialize the plugin and the wrapped AI foundation plugin."""
        self.lcas_core = core_app
        logger.info(f"{self.name}: Initializing...")
        try:
            # Determine the absolute path for ai_config.json
            # ai_config_path in LCASConfig is relative to project root.
            project_root = Path(__file__).parent.parent.parent # Assumes this plugin is in LCAS_2/lcas2/plugins
            ai_conf_path_str = self.lcas_core.config.ai_config_path
            absolute_ai_config_path = project_root / ai_conf_path_str

            logger.info(f"{self.name}: Loading AI Foundation with config: {absolute_ai_config_path}")

            self.ai_foundation = EnhancedAIFoundationPlugin(config_path=str(absolute_ai_config_path))

            if not self.ai_foundation.config: # Check if underlying config loaded
                logger.error(f"{self.name}: Failed to load AI foundation's internal configuration from {absolute_ai_config_path}.")
                return False

            # Synchronize AI foundation's user_settings with LCASConfig
            self._sync_ai_user_settings()

            status = self.ai_foundation.get_comprehensive_status()
            available_providers = [p for p, s in status.get("providers", {}).items() if s.get("available")]
            if not available_providers:
                logger.warning(f"{self.name}: No AI providers seem to be available/configured in '{absolute_ai_config_path}'. Ensure API keys are set.")
            else:
                logger.info(f"{self.name}: Available AI providers: {available_providers}")

            logger.info(f"{self.name}: Initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"{self.name}: Error during initialization: {e}", exc_info=True)
            return False

    def _sync_ai_user_settings(self):
        """Synchronizes AIFoundationPlugin's user_settings with LCASCore's config."""
        if not self.ai_foundation or not self.lcas_core:
            return

        lcas_conf = self.lcas_core.config
        ai_user_settings_updates = {}

        if hasattr(lcas_conf, 'case_theory') and isinstance(lcas_conf.case_theory, CaseTheoryConfig):
            ai_user_settings_updates['case_type'] = lcas_conf.case_theory.case_type

        if hasattr(lcas_conf, 'ai_analysis_depth'):
            ai_user_settings_updates['analysis_depth'] = lcas_conf.ai_analysis_depth

        if hasattr(lcas_conf, 'ai_confidence_threshold'):
            ai_user_settings_updates['confidence_threshold'] = lcas_conf.ai_confidence_threshold

        # Add any other relevant mappings here
        # Example: if LCASConfig had a 'jurisdiction' field for AI
        # if hasattr(lcas_conf, 'jurisdiction_for_ai'):
        #    ai_user_settings_updates['jurisdiction'] = lcas_conf.jurisdiction_for_ai

        if ai_user_settings_updates:
            self.ai_foundation.update_user_settings(**ai_user_settings_updates)
            logger.info(f"{self.name}: Synchronized AI Foundation user_settings: {ai_user_settings_updates}")


    async def cleanup(self) -> None:
        """Cleanup resources."""
        logger.info(f"{self.name}: Cleaning up.")
        self.ai_foundation = None # Allow GC
        self.lcas_core = None

    async def analyze(self, data: Any) -> Dict[str, Any]:
        """
        Perform AI analysis on the provided data.
        'data' is expected to be a dictionary potentially containing:
        - 'file_content': The text content of the file to analyze.
        - 'file_path': The path to the file being analyzed.
        - 'text_to_analyze': Alternative to file_content for direct text.
        - 'analysis_type': Specific type of analysis for AI (e.g., 'document_summary', 'legal_theory_check').
                           If not provided, EnhancedAIFoundationPlugin might run its default agent sequence.
        - 'case_context': Optional dictionary with runtime case-specific context.
        """
        if not self.ai_foundation:
            logger.error(f"{self.name}: AI Foundation not initialized.")
            return {"error": "AI Foundation not initialized", "success": False}

        # Ensure settings are fresh if config could change dynamically (e.g. via GUI)
        self._sync_ai_user_settings()

        content_to_analyze = data.get("file_content", data.get("text_to_analyze"))
        file_path = data.get("file_path", "unknown_source")
        # analysis_task_type = data.get("analysis_type") # For more granular control in future

        if content_to_analyze is None: # Check for None explicitly, as empty string might be valid
            logger.warning(f"{self.name}: No content provided for AI analysis (file_path: {file_path}).")
            return {"error": "No content (file_content or text_to_analyze) provided.", "file_path": file_path, "success": False}

        # Prepare runtime context for AI
        lcas_conf = self.lcas_core.config
        runtime_context = data.get("case_context", {})
        if lcas_conf:
            runtime_context.setdefault("lcas_case_name", lcas_conf.case_name)
            runtime_context.setdefault("lcas_case_type", lcas_conf.case_theory.case_type)
            # Add other details from lcas_conf.case_theory if they are relevant at runtime

        logger.info(f"{self.name}: Analyzing content for: {file_path} with AI.")
        logger.debug(f"{self.name}: AI User Settings: {self.ai_foundation.user_settings}")
        logger.debug(f"{self.name}: Runtime Context for AI: {runtime_context}")


        try:
            # EnhancedAIFoundationPlugin.analyze_file_content runs multiple agents.
            # If a more specific agent call is needed, the 'data' dict would need to specify that,
            # and this wrapper would need logic to call the specific agent method on ai_foundation.
            # For now, using the general analyze_file_content which runs configured agents.
            ai_results = await self.ai_foundation.analyze_file_content(
                content=content_to_analyze,
                file_path=file_path,
                context=runtime_context
            )

            if ai_results.get("rate_limited"):
                logger.warning(f"{self.name}: AI analysis for {file_path} was skipped due to rate limits: {ai_results.get('message')}")
                return {"status": "skipped_rate_limited", "message": ai_results.get("message"), "file_path": file_path, "success": False}

            final_result = {
                "status": "success",
                "file_path": file_path,
                "provider_results": ai_results, # Contains results from each agent ran by EnhancedAIFoundationPlugin
                "summary": "AI analysis performed.", # Generic summary, can be improved
                "success": True
            }

            # Attempt to extract a more specific summary, e.g., from document_intelligence agent
            if isinstance(ai_results, dict):
                doc_intel_res = ai_results.get("document_intelligence", {}).get("findings", {})
                if isinstance(doc_intel_res, dict) and "summary" in doc_intel_res:
                    final_result["summary"] = doc_intel_res["summary"]
                elif isinstance(doc_intel_res, str) and doc_intel_res: # If findings itself is a string summary
                    final_result["summary"] = doc_intel_res[:500] # Truncate if too long

            return final_result

        except Exception as e:
            logger.error(f"{self.name}: Error during AI analysis for {file_path}: {e}", exc_info=True)
            return {"error": str(e), "file_path": file_path, "success": False}
