#!/usr/bin/env python3
"""LCAS AI Wrapper Plugin. Integrates EnhancedAIFoundationPlugin."""
import logging; from typing import Dict, List, Any, Optional; from pathlib import Path; import asyncio
from dataclasses import asdict # Added asdict for output
from lcas2.core import AnalysisPlugin, LCASCore, LCASConfig, CaseTheoryConfig
from lcas2.core.data_models import FileAnalysisData # Import the model
from .ai_integration_plugin import EnhancedAIFoundationPlugin, AIConfigSettings

logger = logging.getLogger(__name__)
class LCASAIWrapperPlugin(AnalysisPlugin):
    def __init__(self):
        self.ai_foundation: Optional[EnhancedAIFoundationPlugin] = None
        self.lcas_core: Optional[LCASCore] = None
    @property
    def name(self) -> str: return "lcas_ai_wrapper_plugin" # Keep original name for now if other plugins depend on it
    @property
    def version(self) -> str: return "1.2.0" # Updated
    @property
    def description(self) -> str: return "Integrates AI analysis, populating FileAnalysisData objects."
    @property
    def dependencies(self) -> List[str]: return ["Content Extraction"]

    async def initialize(self, core_app: LCASCore) -> bool:
        self.lcas_core = core_app
        self.logger = core_app.logger.getChild(self.name)
        self.logger.info(f"{self.name}: Initializing...")
        try:
            # Ensure config path for AI foundation is absolute relative to project root
            project_root = Path(__file__).resolve().parent.parent.parent # LCAS_2
            ai_conf_path_str = getattr(self.lcas_core.config, ai_config_path, config/ai_config.json)

            abs_ai_cfg_path = ai_conf_path_str
            if not Path(ai_conf_path_str).is_absolute():
                abs_ai_cfg_path = str((project_root / ai_conf_path_str).resolve())

            self.ai_foundation = EnhancedAIFoundationPlugin(config_path=abs_ai_cfg_path)
            if not self.ai_foundation or not self.ai_foundation.config: # Check if config loaded
                self.logger.error(f"{self.name}: AI Foundation config failed to load from {abs_ai_cfg_path}.")
                return False
            self._sync_ai_user_settings()
            self.logger.info(f"{self.name}: Initialized successfully with AI config: {abs_ai_cfg_path}.")
            return True
        except Exception as e:
            self.logger.error(f"{self.name}: Error during initialization: {e}", exc_info=True)
            return False

    def _sync_ai_user_settings(self):
        if not self.ai_foundation or not self.lcas_core or not hasattr(self.lcas_core, config): return
        lcas_conf = self.lcas_core.config
        updates = {}
        # Sync relevant LCASConfig settings to AIConfigSettings
        if hasattr(lcas_conf, case_theory) and hasattr(lcas_conf.case_theory, case_type):
            updates[case_type] = lcas_conf.case_theory.case_type
        if hasattr(lcas_conf, ai_analysis_depth):
            updates[analysis_depth] = lcas_conf.ai_analysis_depth
        if hasattr(lcas_conf, ai_confidence_threshold):
            updates[confidence_threshold] = lcas_conf.ai_confidence_threshold

        if updates and hasattr(self.ai_foundation, update_user_settings):
            self.ai_foundation.update_user_settings(**updates)
            self.logger.info(f"AI user settings synced with LCASConfig: {updates}")

    async def cleanup(self) -> None:
        self.logger.info(f"{self.name}: Cleaning up.")
        self.ai_foundation = None
        self.lcas_core = None

    async def analyze(self, data: Any) -> Dict[str, Any]:
        if not self.ai_foundation:
            return {"plugin":self.name, "status":"error", "success": False, "error": "AI Foundation not initialized"}
        self._sync_ai_user_settings() # Ensure settings are current before analysis

        processed_files_input: Dict[str, Any] = data.get("processed_files", {}) # Expects dicts that can be FileAnalysisData
        if not processed_files_input:
            return {"plugin":self.name, "status":"no_data", "success": False, "error": "No processed_files data provided."}

        output_fad_dict: Dict[str, FileAnalysisData] = {} # To store FAD instances
        files_analyzed_count = 0
        files_failed_ai = 0

        for file_path_str, file_data_dict_or_obj in processed_files_input.items():
            fad_instance: Optional[FileAnalysisData] = None
            if isinstance(file_data_dict_or_obj, FileAnalysisData):
                fad_instance = file_data_dict_or_obj
            elif isinstance(file_data_dict_or_obj, dict):
                try:
                    fad_instance = FileAnalysisData(**file_data_dict_or_obj)
                except TypeError as te:
                    self.logger.warning(f"Could not cast dict to FileAnalysisData for {file_path_str}: {te}, skipping AI.")
                    continue
            else:
                self.logger.warning(f"Unexpected data type for file {file_path_str} in processed_files. Expected dict or FileAnalysisData, got {type(file_data_dict_or_obj)}. Skipping AI.")
                continue

            output_fad_dict[file_path_str] = fad_instance # Add to output dict

            content_to_analyze = fad_instance.content if fad_instance.content else fad_instance.summary_auto
            if not content_to_analyze:
                self.logger.debug(f"No content for AI in {file_path_str}, skipping AI for this file.")
                continue

            self.logger.info(f"{self.name}: AI analyzing {file_path_str}")
            try:
                runtime_context = {
                    "lcas_case_name": self.lcas_core.config.case_name if self.lcas_core and hasattr(self.lcas_core.config, case_name) else "Unknown Case",
                    "lcas_case_type": self.lcas_core.config.case_theory.case_type if self.lcas_core and hasattr(self.lcas_core.config, case_theory) else "general"
                }

                # This call returns a dict like: {"document_intelligence": {...}, "legal_analysis": {...}} or error dict
                raw_ai_output = await self.ai_foundation.analyze_file_content(
                    content=content_to_analyze, file_path=file_path_str, context=runtime_context)

                fad_instance.ai_analysis_raw = raw_ai_output

                if isinstance(raw_ai_output, dict) and raw_ai_output.get("success", True): # Assume success if not explicitly false
                    # Extract some common fields for easier access
                    doc_intel_findings = raw_ai_output.get("document_intelligence", {}).get("findings", {}) # Example path
                    if isinstance(doc_intel_findings, dict) and doc_intel_findings.get("summary"):
                        fad_instance.ai_summary = doc_intel_findings["summary"]

                    all_tags = set(fad_instance.ai_tags or [])
                    for agent_key, agent_result in raw_ai_output.items(): # Iterate through agent results
                        if isinstance(agent_result, dict):
                            # Tags might be at top level of agent result or nested in findings
                            current_tags = agent_result.get("tags", [])
                            if isinstance(current_tags, list): all_tags.update(current_tags)

                            findings = agent_result.get("findings", {})
                            if isinstance(findings, dict):
                                current_findings_tags = findings.get("tags", [])
                                if isinstance(current_findings_tags, list): all_tags.update(current_findings_tags)

                                if isinstance(findings.get("evidence_category"),str):
                                    fad_instance.ai_suggested_category = findings.get("evidence_category")

                                key_entities = findings.get("key_entities", findings.get("entities", []))
                                if isinstance(key_entities, list): fad_instance.ai_key_entities.extend(key_entities)

                    fad_instance.ai_tags = list(all_tags)
                    files_analyzed_count +=1
                else: # AI analysis for this file failed or returned unexpected structure
                     error_detail = raw_ai_output.get("error", "Unknown AI analysis error") if isinstance(raw_ai_output, dict) else "Malformed AI response"
                     fad_instance.error_log.append(f"AI Analysis Error: {error_detail}")
                     files_failed_ai +=1

            except Exception as e:
                self.logger.error(f"{self.name}: AI analysis system error for {file_path_str}: {e}", exc_info=True)
                fad_instance.error_log.append(f"AI Analysis System Error: {e}")
                files_failed_ai +=1

        return {"plugin": self.name,
                "status": "completed" if files_failed_ai == 0 else "completed_with_errors",
                "success": True, # Plugin itself succeeded in its job of orchestration
                "summary": {"files_ai_analyzed": files_analyzed_count, "files_ai_failed": files_failed_ai},
                "processed_files_output": {k: asdict(v) for k,v in output_fad_dict.items()}
               }
