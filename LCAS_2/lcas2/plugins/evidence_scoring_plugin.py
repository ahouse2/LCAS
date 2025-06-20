#!/usr/bin/env python3
"""
Evidence Scoring Plugin for LCAS
Assigns scores to evidence based on various legal criteria using AI.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import asyncio
import json # Added for robust parsing and example formatting
import re # For parsing JSON from AI response
from dataclasses import dataclass, asdict, field
import tkinter as tk # For UI elements

from lcas2.core import AnalysisPlugin, LCASCore, LCASConfig, UIPlugin # Added UIPlugin
from lcas2.core.data_models import FileAnalysisData

logger = logging.getLogger(__name__)

@dataclass
class ScoreDetail:
    score: float
    justification: str
    parameters_used: Optional[Dict[str, Any]] = None
    error: Optional[str] = None # For capturing errors during scoring attempt for this specific type

class EvidenceScoringPlugin(AnalysisPlugin, UIPlugin): # Added UIPlugin to class signature
    """
    Assigns scores to evidence files based on criteria like relevance, admissibility, etc.,
    primarily using AI assistance.
    """

    @property
    def name(self) -> str: return "Evidence Scoring"
    @property
    def version(self) -> str: return "0.1.1" # Version updated from subtask 44
    @property
    def description(self) -> str: return "Scores evidence on relevance, admissibility, etc., using AI and refined prompts."
    @property
    def dependencies(self) -> List[str]:
        return ["lcas_ai_wrapper_plugin", "Content Extraction"]

    async def initialize(self, core_app: LCASCore) -> bool:
        self.core = core_app
        self.logger = core_app.logger.getChild(self.name)
        self.ai_service = None
        # Ensure ai_wrapper_plugin_name is available in config
        ai_wrapper_name = getattr(self.core.config, 'ai_wrapper_plugin_name', 'lcas_ai_wrapper_plugin')
        loaded_ai_wrapper = self.core.plugin_manager.loaded_plugins.get(ai_wrapper_name) # Use .get for safety
        if loaded_ai_wrapper:
            if hasattr(loaded_ai_wrapper, 'ai_foundation') and loaded_ai_wrapper.ai_foundation:
                 self.ai_service = loaded_ai_wrapper.ai_foundation
                 self.logger.info("Successfully accessed AI Foundation service.")
            else: self.logger.warning(f"AI Wrapper '{ai_wrapper_name}' loaded, but AI Foundation attribute unavailable.")
        else: self.logger.warning(f"AI Wrapper plugin '{ai_wrapper_name}' not loaded. Scoring will be limited.")
        self.logger.info(f"{self.name} initialized.")
        return True

    async def cleanup(self) -> None:
        self.logger.info(f"{self.name} cleaned up.")
        pass

    async def _get_ai_score(self, fad_instance: FileAnalysisData, score_type: str, case_context_details: Dict[str, Any]) -> ScoreDetail:
        """Generates a specific score for a file using AI, with refined prompts for Gemini and JSON output."""

        if not self.ai_service or not hasattr(self.ai_service, 'execute_custom_prompt'):
            self.logger.error(f"AI service or execute_custom_prompt method not available for scoring '{score_type}'.")
            return ScoreDetail(score=-1.0, justification="AI service method unavailable.", error="AI service method missing")

        # AI service enabled check is now implicitly handled by execute_custom_prompt's provider selection logic.
        # No need for: if not hasattr(self.ai_service, 'config') or not self.ai_service.config.enabled:

        text_for_scoring = fad_instance.content or fad_instance.summary_auto or fad_instance.ai_summary or fad_instance.ocr_text_from_images or ""
        if not text_for_scoring.strip():
            self.logger.info(f"No substantial text content available for scoring '{score_type}' in file {fad_instance.file_name}.")
            return ScoreDetail(score=0.0, justification="No text content for analysis.")

        case_type_str = str(case_context_details.get('case_type','general'))
        jurisdiction_str = str(case_context_details.get('jurisdiction','US Federal'))
        key_allegations_str = "; ".join(case_context_details.get('key_allegations',[])) if isinstance(case_context_details.get('key_allegations'), list) else str(case_context_details.get('key_allegations','N/A'))
        legal_theories_str = "; ".join(case_context_details.get('legal_theories',[])) if isinstance(case_context_details.get('legal_theories'), list) else str(case_context_details.get('legal_theories','N/A'))
        user_scenario_str = str(case_context_details.get('user_scenario_details', 'No specific user scenario provided.'))

        system_prompt = f"You are an AI legal analyst. Your task is to evaluate a piece of evidence based on the provided text and case context. The case is a '{case_type_str}' matter in '{jurisdiction_str}'. Respond ONLY with a single, valid JSON object as specified."

        user_prompt = ""
        json_output_example = {"score": 0.5, "justification": "Your brief justification (1-3 sentences)."}
        json_output_schema_description = f"Respond ONLY with a single JSON object with two keys: 'score' (a float between 0.0 and 1.0) and 'justification' (a brief string explaining the score). Example: {json.dumps(json_output_example)}"


        if score_type == "relevance":
            system_prompt = f"You are an AI legal analyst specializing in assessing evidence relevance for a '{case_type_str}' case in '{jurisdiction_str}'. Provide your analysis in the specified JSON format."
            user_prompt = f"""
**Document Text Snippet (max 2000 chars):**
"{text_for_scoring[:2000]}"

**Case Context:**
- User Scenario: {user_scenario_str[:1000]}
- Key Allegations: {key_allegations_str[:1000]}
- Primary Legal Theories: {legal_theories_str[:1000]}

**Task:**
Assess the **relevance** of the document snippet to the described case context, allegations, and legal theories.
- A score of 1.0 means highly relevant and directly pertinent.
- A score of 0.0 means not relevant at all.
- Justification should briefly explain why the document is or isn't relevant.

{json_output_schema_description}
"""
        elif score_type == "admissibility_concern":
            system_prompt = f"You are an AI legal analyst flagging potential admissibility concerns for evidence in a '{case_type_str}' case in '{jurisdiction_str}'. Your response must be in the specified JSON format."
            doc_type_info = fad_instance.extraction_meta.format_detected if fad_instance.extraction_meta else 'Unknown'
            user_prompt = f"""
**Document Text Snippet (max 2000 chars):**
"{text_for_scoring[:2000]}"
**Document Type (if known):** {doc_type_info}
**Case Context:**
- User Scenario: {user_scenario_str[:1000]}

**Task:**
Identify potential **admissibility concerns** for this document snippet (e.g., hearsay, authenticity, relevance, prejudice, chain of custody).
- A score of 1.0 indicates VERY HIGH admissibility concerns (likely inadmissible).
- A score of 0.0 indicates LOW to NO admissibility concerns (likely admissible on this front).
- Justification should briefly state the primary concern(s) or why there are none.

{json_output_schema_description}
"""
        else:
            self.logger.warning(f"Unknown score_type '{score_type}' requested for AI scoring.")
            return ScoreDetail(score=-1.0, justification=f"Unknown score type: {score_type}", error="Unknown score type")

        try:
            ai_response_data = await self.ai_service.execute_custom_prompt(
                system_prompt=system_prompt, user_prompt=user_prompt,
                context_for_ai_run={"task": f"evidence_scoring_{score_type}"}
            )
            if ai_response_data and ai_response_data.get("success"):
                response_content = ai_response_data.get("response", "")
                try:
                    match = re.search(r'\{[\s\S]*?\}', response_content, re.DOTALL)
                    if match:
                        json_str = match.group(0)
                        score_data = json.loads(json_str)
                        parsed_score = score_data.get("score")
                        final_score = 0.0
                        if isinstance(parsed_score, (float, int)):
                            final_score = max(0.0, min(1.0, float(parsed_score)))
                        else:
                            self.logger.warning(f"AI returned non-numeric score for {score_type} on {fad_instance.file_name}: '{parsed_score}'. Defaulting to 0.")

                        return ScoreDetail(
                            score=final_score,
                            justification=str(score_data.get("justification", "No justification from AI."))
                        )
                    else:
                        self.logger.error(f"No JSON object found in AI response for {score_type} on {fad_instance.file_name}. Response: {response_content}")
                        return ScoreDetail(score=0.0, justification=f"AI response not valid JSON: {response_content[:100]}", error="AI response not valid JSON")
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    self.logger.error(f"AI score parsing error for {score_type} on {fad_instance.file_name}: {e}. Response: {response_content}", exc_info=True)
                    return ScoreDetail(score=0.0, justification=f"AI response parsing error: {response_content[:100]}", error=f"JSON parsing error: {e}")
            else:
                err_msg = ai_response_data.get('error', 'Unknown AI error') if ai_response_data else 'No AI response'
                self.logger.error(f"AI scoring task '{score_type}' failed for {fad_instance.file_name}. Error: {err_msg}")
                return ScoreDetail(score=-1.0, justification=f"AI task failed: {err_msg[:100]}", error=f"AI task failed: {err_msg}")
        except AttributeError as ae:
             self.logger.error(f"AI service method error during scoring for {score_type} on {fad_instance.file_name}: {ae}", exc_info=True)
             return ScoreDetail(score=-1.0, justification=f"AI service method error.", error=str(ae))
        except Exception as e:
            self.logger.error(f"Exception during AI scoring for {score_type} on {fad_instance.file_name}: {e}", exc_info=True)
            return ScoreDetail(score=-1.0, justification=f"Exception during scoring.", error=str(e))


    async def analyze(self, data: Any) -> Dict[str, Any]:
        processed_files_input_any: Any = data.get("processed_files", {})
        if not isinstance(processed_files_input_any, dict):
            self.logger.error(f"Expected 'processed_files' to be a Dict, got {type(processed_files_input_any)}.")
            return {"plugin": self.name, "status": "error", "success": False, "message": "Invalid 'processed_files' format."}
        processed_files_input: Dict[str, Any] = processed_files_input_any

        if not processed_files_input: return {"plugin": self.name, "status": "no_data", "success": False, "message": "No 'processed_files' provided."}

        self.logger.info(f"Starting evidence scoring for {len(processed_files_input)} files.")
        files_scored_count = 0; errors_count = 0
        output_fad_dict: Dict[str, FileAnalysisData] = {}

        case_theory_obj = self.core.config.case_theory if hasattr(self.core.config, 'case_theory') else None
        case_context_details = {
            "case_type": getattr(case_theory_obj, 'case_type', "general") if case_theory_obj else "general",
            "jurisdiction": getattr(self.core.config.case_theory, 'jurisdiction', "US Federal") if case_theory_obj and hasattr(self.core.config.case_theory, 'jurisdiction') else getattr(self.core.config, 'jurisdiction', "US Federal"),
            "key_allegations": getattr(case_theory_obj, 'primary_objective', "") if case_theory_obj else "",
            "legal_theories": getattr(case_theory_obj, 'key_questions', []) if case_theory_obj else [],
            "user_scenario_details": getattr(case_theory_obj, 'user_scenario_description', 'No specific user scenario provided.') if case_theory_obj and hasattr(case_theory_obj, 'user_scenario_description') else 'No specific user scenario provided.'
        }

        score_types_to_generate = ["relevance", "admissibility_concern"]
        for file_path_str, fad_object_or_dict in processed_files_input.items():
            fad_instance: Optional[FileAnalysisData] = None
            if isinstance(fad_object_or_dict, FileAnalysisData): fad_instance = fad_object_or_dict
            elif isinstance(fad_object_or_dict, dict):
                try: fad_instance = FileAnalysisData(**fad_object_or_dict)
                except TypeError as te: self.logger.warning(f"Cannot cast dict to FAD for {file_path_str} for scoring: {te}"); errors_count+=1; continue
            if not fad_instance: errors_count+=1; continue

            output_fad_dict[file_path_str] = fad_instance

            if not hasattr(fad_instance, 'evidence_scores') or not isinstance(fad_instance.evidence_scores, dict):
                fad_instance.evidence_scores = {} # type: ignore

            current_file_had_successful_score = False
            for score_type in score_types_to_generate:
                self.logger.debug(f"Scoring '{score_type}' for file: {fad_instance.file_name}")
                score_detail = await self._get_ai_score(fad_instance, score_type, case_context_details)

                if not isinstance(fad_instance.evidence_scores, dict): fad_instance.evidence_scores = {} # type: ignore

                if score_detail : # score_detail is now always returned
                    fad_instance.evidence_scores[score_type] = asdict(score_detail) # type: ignore
                    if not score_detail.error:
                        current_file_had_successful_score = True
                    else: # An error occurred during this specific scoring attempt
                        errors_count+=1

            if current_file_had_successful_score: files_scored_count +=1

        self.logger.info(f"Evidence scoring complete. Files considered: {len(processed_files_input)}, Files with at least one successful score: {files_scored_count}, Total scoring attempt errors/NAs: {errors_count}.")
        return {"plugin": self.name, "status": "completed" if errors_count == 0 else "completed_with_errors", "success": True,
                "summary": {"files_considered_for_scoring": len(processed_files_input), "files_successfully_scored_at_least_once": files_scored_count, "scoring_errors_or_not_applicable": errors_count, "score_types_applied": score_types_to_generate},
                "processed_files_output": {k:asdict(v) for k,v in output_fad_dict.items()}}

    def create_ui_elements(self, parent_widget) -> List[tk.Widget]:
        try:
            import tkinter # Keep import local to UI method
            from tkinter import ttk
        except ImportError:
            self.logger.warning("Tkinter not available, UI elements for EvidenceScoringPlugin cannot be created.")
            return []

        frame = ttk.Frame(parent_widget); frame.pack(fill=tkinter.X, padx=5, pady=2) # Use tkinter.X
        label = ttk.Label(frame, text=f"{self.name}: Assigns AI-driven scores. Runs in pipeline.")
        label.pack(side=tkinter.LEFT, padx=2) # Use tkinter.LEFT
        return [frame]
