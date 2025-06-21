#!/usr/bin/env python3
"""
Pattern Discovery Plugin for LCAS
Discovers hidden patterns, connections, and potential legal theories
Designed to help self-represented litigants find powerful arguments they might miss
"""

import logging
import json
import uuid
# import numpy as np # Confirmed not used
from typing import Dict, List, Any, Optional, Tuple, Set, Union # Added Union
from dataclasses import dataclass, asdict, field, fields # Added fields
from collections import defaultdict, Counter
from datetime import datetime
import re
from pathlib import Path

from lcas2.core import AnalysisPlugin, LCASCore, LCASConfig
from lcas2.core.data_models import FileAnalysisData # Ensure this is used if consuming FADs

logger = logging.getLogger(__name__)

@dataclass
class PatternConfigItem:
    keywords: List[str] = field(default_factory=list) # Ensure default factory for lists
    description_template: str = "Pattern of ''{sub_pattern_name}'' detected."
    default_confidence_boost: float = 0.05
    base_confidence: float = 0.5
@dataclass
class PatternGroupConfig:
    group_type: str
    sub_patterns: Dict[str, PatternConfigItem] = field(default_factory=dict) # Default factory
@dataclass
class Pattern:
    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pattern_type: str = "Unknown"; title: str = "Untitled"; description: str = "N/A" # Defaults
    evidence_files: List[str] = field(default_factory=list)
    confidence_score: float = 0.0; legal_significance: str = ""
    potential_arguments: List[str] = field(default_factory=list)
    supporting_events: List[Dict[str, Any]] = field(default_factory=list)
    strength_indicators: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    related_patterns: List[str] = field(default_factory=list)
    raw_matches: List[Dict[str, Any]] = field(default_factory=list)
@dataclass
class LegalTheory:
    theory_id: str = field(default_factory=lambda: str(uuid.uuid4())); theory_name: str = "Unnamed Theory" # Default
    legal_basis: str = ""; description: str = ""
    supporting_patterns: List[str] = field(default_factory=list)
    evidence_strength: float = 0.0; likelihood_of_success: float = 0.0
    required_evidence_elements: List[str] = field(default_factory=list)
    available_evidence_for_elements: Dict[str, List[str]] = field(default_factory=dict)
    missing_evidence_for_elements: Dict[str, str] = field(default_factory=dict)
    strategic_value: str = ""; implementation_steps: List[str] = field(default_factory=list)
    counter_arguments_to_anticipate: List[str] = field(default_factory=list)

class PatternDiscoveryPlugin(AnalysisPlugin):
    @property
    def name(self) -> str: return "Pattern Discovery"
    @property
    def version(self) -> str: return "2.2.1" # Incremented for prompt refinements
    @property
    def description(self) -> str: return "Discovers patterns, suggests theories using keywords & AI with refined prompts for JSON."
    @property
    def dependencies(self) -> List[str]: return ["lcas_ai_wrapper_plugin", "Content Extraction", "Timeline Analysis"]

    async def initialize(self, core_app: LCASCore) -> bool:
        self.core = core_app; self.logger = core_app.logger.getChild(self.name); self.lcas_config = core_app.config
        self.ai_service = None
        ai_wrapper_name = getattr(self.lcas_config, 'ai_wrapper_plugin_name', 'lcas_ai_wrapper_plugin')
        loaded_ai_wrapper = self.core.plugin_manager.loaded_plugins.get(ai_wrapper_name)
        if loaded_ai_wrapper:
            if hasattr(loaded_ai_wrapper, 'ai_foundation') and loaded_ai_wrapper.ai_foundation:
                self.ai_service = loaded_ai_wrapper.ai_foundation
                self.logger.info("PatternDiscovery: AI Foundation service accessed.")
            else: self.logger.warning("PatternDiscovery: AI Wrapper loaded, but AI Foundation attribute unavailable.")
        else: self.logger.warning(f"PatternDiscovery: AI Wrapper plugin '{ai_wrapper_name}' not loaded. AI features limited.")

        default_rules_file = "pattern_discovery_rules.json"; plugin_dir = Path(__file__).parent
        cfg_path_str = getattr(self.lcas_config, 'pattern_discovery_config_path', None)

        path_to_load = None
        if cfg_path_str:
            cfg_path_obj = Path(cfg_path_str)
            if cfg_path_obj.is_absolute(): path_to_load = cfg_path_obj
            # Use core.project_root if core is available and has project_root, otherwise assume relative to plugin dir's parent for safety
            elif hasattr(self.core, 'project_root') and self.core.project_root:
                 path_to_load = (self.core.project_root / cfg_path_str).resolve()
            else: # Fallback if project_root isn't available for some reason during early init
                 path_to_load = (plugin_dir.parent.parent / cfg_path_str).resolve()
        else: path_to_load = (plugin_dir / default_rules_file).resolve()

        self.logger.info(f"PatternDiscovery: Attempting to load pattern rules from: {path_to_load}")
        self.pattern_configs = self._load_pattern_configurations(str(path_to_load))

        self.discovered_patterns: List[Pattern] = []; self.potential_theories: List[LegalTheory] = []
        self.logger.info(f"{self.name} initialized."); return True

    async def cleanup(self) -> None: self.logger.info(f"{self.name} cleaned up."); self.ai_service = None

    def _load_pattern_configurations(self, config_path_str: Optional[str]) -> Dict[str, PatternGroupConfig]:
        configs: Dict[str, PatternGroupConfig] = {}
        if config_path_str and Path(config_path_str).exists():
            try:
                with open(config_path_str, 'r', encoding='utf-8') as f: raw_configs = json.load(f)
                for group_type, group_data in raw_configs.items():
                    if not isinstance(group_data, dict): continue
                    sub_patterns_dict = {sp_name: PatternConfigItem(**sp_data) for sp_name, sp_data in group_data.get('sub_patterns', {}).items() if isinstance(sp_data, dict)}
                    if sub_patterns_dict: configs[group_type] = PatternGroupConfig(group_type=group_type, sub_patterns=sub_patterns_dict)
                self.logger.info(f"Loaded {len(configs)} pattern groups from {config_path_str}")
            except Exception as e: self.logger.error(f"Error loading pattern configs from {config_path_str}: {e}. Using defaults.", exc_info=True); configs = {}
        else: self.logger.info(f"Pattern config file '{config_path_str}' not found or path is None. Using defaults.")
        if not configs:
            configs["Default_Abuse_Indicators"] = PatternGroupConfig(group_type="Abuse Indicators", sub_patterns={'PhysicalAbuseKeywords': PatternConfigItem(keywords=['hit', 'punched', 'assaulted', 'bruise'], description_template="Direct mentions of physical violence.")})
            configs["Default_Financial_Indicators"] = PatternGroupConfig(group_type="Financial Indicators", sub_patterns={'HiddenAssetKeywords': PatternConfigItem(keywords=['undisclosed account', 'secret investment', 'offshore transfer'], description_template="Potential hidden assets based on keywords.")})
            self.logger.info(f"Loaded {len(configs)} internal default pattern groups.")
        return configs

    async def analyze(self, data: Any) -> Dict[str, Any]:
        self.logger.info(f"Starting pattern discovery for case: {data.get('case_name', 'Unknown')}")
        self.discovered_patterns = []; self.potential_theories = []

        processed_files_input_any: Any = data.get("processed_files", {})
        if not isinstance(processed_files_input_any, dict):
             self.logger.error(f"Expected 'processed_files' to be a Dict, got {type(processed_files_input_any)}.")
             return {"plugin": self.name, "status": "error", "success": False, "message": "Invalid 'processed_files' format."}
        processed_files_input: Dict[str, Any] = processed_files_input_any

        timelines_data_any = data.get("timelines")
        timelines_data: Optional[Dict[str,Any]] = None
        if isinstance(timelines_data_any, dict): timelines_data = timelines_data_any

        target_dir_str = data.get("target_directory", self.lcas_config.target_directory if self.lcas_config and self.lcas_config.target_directory else str(self.core.project_root / "analysis_results_patterns"))

        Path(target_dir_str).mkdir(parents=True, exist_ok=True)
        if not processed_files_input: self.logger.warning("No 'processed_files' data for pattern discovery."); return {"plugin": self.name, "status": "no_data", "success": False, "message": "No FileAnalysisData."}

        processed_fad_instances: Dict[str, FileAnalysisData] = {}

        for file_path_str, fad_object_or_dict in processed_files_input.items():
            fad_instance: Optional[FileAnalysisData] = None
            if isinstance(fad_object_or_dict, FileAnalysisData): fad_instance = fad_object_or_dict
            elif isinstance(fad_object_or_dict, dict):
                try: fad_instance = FileAnalysisData(**fad_object_or_dict)
                except TypeError as te: self.logger.warning(f"Cannot cast dict to FileAnalysisData for {file_path_str} in PatternDiscovery: {te}"); continue
            if not fad_instance: continue
            processed_fad_instances[file_path_str] = fad_instance

            texts_to_search_in_fad: List[Tuple[str, str]] = []
            if fad_instance.content: texts_to_search_in_fad.append(("main_content", fad_instance.content))
            if fad_instance.summary_auto: texts_to_search_in_fad.append(("summary_auto", fad_instance.summary_auto))
            if fad_instance.ai_summary: texts_to_search_in_fad.append(("ai_summary", fad_instance.ai_summary))
            if fad_instance.ocr_text_from_images: texts_to_search_in_fad.append(("ocr_text_from_images", fad_instance.ocr_text_from_images))

            if isinstance(fad_instance.ai_analysis_raw, dict):
                for agent_name, agent_result in fad_instance.ai_analysis_raw.items():
                    if isinstance(agent_result, dict) and isinstance(agent_result.get('findings'), dict):
                        agent_summary = agent_result['findings'].get('summary')
                        if isinstance(agent_summary, str): texts_to_search_in_fad.append((f"{agent_name}_summary", agent_summary))

            if texts_to_search_in_fad:
                doc_patterns = await self._analyze_file_content_for_patterns(file_path_str, texts_to_search_in_fad, fad_instance)
                for p in doc_patterns: self._add_pattern(p)

        if timelines_data and isinstance(timelines_data.get("events"), list):
            timeline_patterns = await self._analyze_timeline_for_patterns("main_timeline", timelines_data)
            for p in timeline_patterns: self._add_pattern(p)

        self._refine_and_correlate_patterns()

        case_context_for_ai = {
            "lcas_case_type": self.lcas_config.case_theory.case_type if self.lcas_config.case_theory else "general",
            "lcas_jurisdiction": getattr(self.lcas_config.case_theory, 'jurisdiction', getattr(self.lcas_config, 'jurisdiction', "US_Federal")),
            "lcas_primary_objective": self.lcas_config.case_theory.primary_objective if self.lcas_config.case_theory else "",
            "lcas_key_questions": self.lcas_config.case_theory.key_questions if self.lcas_config.case_theory else []
        }
        await self._synthesize_legal_theories(case_context_for_ai)

        self.save_discovery_report(target_dir_str, data.get("case_name", "UnknownCase"))

        return {"plugin": self.name, "status": "completed", "success": True,
                "summary": {"discovered_patterns_count": len(self.discovered_patterns), "potential_theories_count": len(self.potential_theories)},
                "report_path_root": str(Path(target_dir_str) / "REPORTS_LCAS" / "PATTERN_DISCOVERY"),
                "potential_theories_output_list_of_dicts": [asdict(t) for t in self.potential_theories],
                "discovered_patterns_output_list_of_dicts": [asdict(p) for p in self.discovered_patterns],
                "processed_files_output": {k:asdict(v) for k,v in processed_fad_instances.items()}
               }

    def _get_text_snippet(self, text: str, keyword_match_obj: re.Match, window_size: int = 100) -> str:
        start_index = max(0, keyword_match_obj.start() - window_size); end_index = min(len(text), keyword_match_obj.end() + window_size)
        return f"{'...' if start_index > 0 else ''}{text[start_index:end_index]}{'...' if end_index < len(text) else ''}"

    async def _analyze_file_content_for_patterns(self, file_path_str: str, texts_tuples: List[Tuple[str, str]], fad_instance: FileAnalysisData) -> List[Pattern]:
        file_patterns: List[Pattern] = []; file_path_obj = Path(file_path_str)
        for text_source_name, text_content in texts_tuples:
            if not text_content or not isinstance(text_content, str): continue
            for group_type, group_config in self.pattern_configs.items():
                for sub_pattern_name, item_config in group_config.sub_patterns.items():
                    current_matches, matched_keywords_in_subpattern = [], set()
                    for keyword in item_config.keywords:
                        try: compiled_regex = re.compile(r'\b' + re.escape(str(keyword)) + r'\b', re.IGNORECASE)
                        except re.error as e: self.logger.warning(f"Regex error for '{keyword}': {e}"); continue
                        for match_obj in compiled_regex.finditer(text_content):
                            snippet = self._get_text_snippet(text_content, match_obj); current_matches.append({"keyword": match_obj.group(0), "snippet": snippet, "source_text_type": text_source_name, "sub_pattern_name": sub_pattern_name}); matched_keywords_in_subpattern.add(str(keyword).lower())
                    if current_matches:
                        title = f"{group_config.group_type.replace('_', ' ').title()}: {sub_pattern_name.replace('_', ' ').title()}"
                        description = item_config.description_template.format(sub_pattern_name=sub_pattern_name.replace('_', ' ')) + f" Identified in '{file_path_obj.name}' from '{text_source_name}' based on keywords: '{', '.join(list(matched_keywords_in_subpattern)[:3])}'."
                        confidence = min(1.0, item_config.base_confidence + (item_config.default_confidence_boost * len(matched_keywords_in_subpattern)))
                        file_cat = fad_instance.assigned_category_folder_name or "General"
                        new_pattern = Pattern(pattern_type=group_config.group_type, title=title, description=description, evidence_files=[file_path_str], confidence_score=confidence, legal_significance=f"May indicate {group_config.group_type} relevant to {file_cat}.", potential_arguments=[file_cat], strength_indicators=[f"Distinct keywords: {len(matched_keywords_in_subpattern)}", f"Total matches: {len(current_matches)}"], raw_matches=current_matches)
                        if self.ai_service and hasattr(self.ai_service, 'config') and self.ai_service.config.enabled:
                            ai_call_context = {"lcas_case_type": self.lcas_config.case_theory.case_type if self.lcas_config.case_theory else "general",
                                               "lcas_jurisdiction": getattr(self.lcas_config.case_theory, 'jurisdiction', getattr(self.lcas_config, 'jurisdiction', "US_Federal"))}
                            ai_analysis = await self._ai_analyze_pattern_context(new_pattern, text_content, ai_call_context)
                            if ai_analysis and isinstance(ai_analysis.get('ai_confidence'), (float,int)) and ai_analysis['ai_confidence'] > 0:
                                new_pattern.description += f"\nAI Review: {ai_analysis.get('ai_description', '')}"
                                new_pattern.confidence_score = min(1.0, (new_pattern.confidence_score + ai_analysis['ai_confidence']) / 2)
                                new_pattern.legal_significance = ai_analysis.get('ai_legal_significance', new_pattern.legal_significance)
                        file_patterns.append(new_pattern)
        if file_patterns: fad_instance.associated_patterns.extend([asdict(p) for p in file_patterns])
        return file_patterns

    async def _ai_analyze_pattern_context(self, pattern: Pattern, full_text_context: str, case_context_for_ai: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.ai_service or not hasattr(self.ai_service, 'execute_custom_prompt'): self.logger.error("AI service or method missing for pattern context."); return None

        snippets_for_ai = "\n".join([f"- '{m.get('keyword','N/A')}': {m.get('snippet','N/A')}" for m in pattern.raw_matches[:3]])
        system_prompt_text = f"You are a legal analyst AI. Analyze the significance of a pre-identified text pattern within a specific case context ({case_context_for_ai.get('lcas_case_type', 'general')}, {case_context_for_ai.get('lcas_jurisdiction', 'US_Federal')}). Respond ONLY in the specified JSON format."
        json_output_example_context = {"ai_description": "Refined pattern description based on context.", "ai_confidence": 0.75, "ai_legal_significance": "Legal implication here."}
        user_prompt_text = f"""
**Identified Pattern:** Title: "{pattern.title}", Type: "{pattern.pattern_type}", Initial Description: "{pattern.description}", Keyword Matches: {snippets_for_ai}
**Full Text Snippet (source of pattern, max 1000 chars):** "{full_text_context[:1000]}"
**Overall Case Context:** {json.dumps(case_context_for_ai, indent=2)}
**Your Task:** Refine description, estimate confidence (0.0-1.0) of relevance and significance, and state legal significance.
Respond ONLY with a single JSON object matching this schema: {json.dumps(json_output_example_context)}
"""
        try:
            ai_response_data = await self.ai_service.execute_custom_prompt(system_prompt=system_prompt_text, user_prompt=user_prompt_text, context_for_ai_run={"task": "pattern_context_analysis"})
            if ai_response_data and ai_response_data.get("success"):
                response_content = ai_response_data.get("response", ""); match = re.search(r'\{[\s\S]*?\}', response_content, re.DOTALL) # More robust JSON finding
                if match: return json.loads(match.group(0))
                else: self.logger.error(f"Pattern context AI JSON error: {response_content}"); return {"ai_description": "AI response not valid JSON.", "ai_confidence": 0.1, "ai_legal_significance": "Response format error."}
            else: self.logger.error(f"Pattern context AI task failed: {ai_response_data.get('error', '') if ai_response_data else 'No AI resp'}"); return None
        except Exception as e: self.logger.error(f"Exception in AI pattern context: {e}", exc_info=True); return None

    async def _ai_synthesize_theories_via_ai(self, case_context_for_ai: Dict[str, Any]):
        if not self.ai_service or not hasattr(self.ai_service, 'execute_custom_prompt'): self.logger.error("AI service or method missing for theory synthesis."); return
        if not self.discovered_patterns: self.logger.info("No patterns for AI theory synthesis."); return

        pattern_summary = [{"id": p.pattern_id, "title": p.title, "type": p.pattern_type, "confidence": f"{p.confidence_score:.2f}", "description_snippet": p.description[:100]} for p in self.discovered_patterns if p.confidence_score >= 0.6][:10]
        if not pattern_summary: self.logger.info("No high-confidence patterns for AI theory synthesis."); return

        system_prompt_text = f"You are a legal strategy AI. Based on discovered text patterns from evidence and case context ({case_context_for_ai.get('lcas_case_type','general')}, {case_context_for_ai.get('lcas_jurisdiction','US_Federal')}), suggest potential legal theories. Respond ONLY in the specified JSON array format."
        json_theory_example = [{"theory_name": "Example Theory Name", "description": "How patterns support it.", "supporting_pattern_ids": ["id1"], "evidence_strength_assessment": "Medium", "key_evidence_elements_to_prove": ["Element A"], "potential_strategic_value": "Value proposition."}]
        user_prompt_text = f"""
**Discovered Patterns (High Confidence):** {json.dumps(pattern_summary, indent=2)}
**Overall Case Context:** {json.dumps(case_context_for_ai, indent=2)}
**Your Task:** Suggest 1-3 potential legal theories. For each, provide: theory_name, description, supporting_pattern_ids (list), evidence_strength_assessment (High/Medium/Low), key_evidence_elements_to_prove (list), potential_strategic_value.
Respond ONLY with a JSON array of theory objects. Example: {json.dumps(json_theory_example)}
If no strong theories are apparent from the provided patterns, return an empty array [].
"""
        try:
            ai_response_data = await self.ai_service.execute_custom_prompt(system_prompt=system_prompt_text, user_prompt=user_prompt_text, context_for_ai_run={"task": "theory_synthesis"})
            if ai_response_data and ai_response_data.get("success"):
                response_content = ai_response_data.get("response", "").strip(); match = re.search(r'\[[\s\S]*?\]', response_content, re.DOTALL)
                if match:
                    json_str = match.group(0); ai_theories = json.loads(json_str)
                    valid_theory_keys = {f.name for f in fields(LegalTheory)}
                    for theory_data in ai_theories:
                        if isinstance(theory_data, dict) and 'theory_name' in theory_data and 'supporting_pattern_ids' in theory_data:
                            filtered_data = {k:v for k,v in theory_data.items() if k in valid_theory_keys}
                            strength_str = filtered_data.pop("evidence_strength_assessment", "Low")
                            strength_map = {"high": 0.8, "medium": 0.5, "low": 0.2}; filtered_data['evidence_strength'] = strength_map.get(strength_str.lower(), 0.3)
                            new_theory = LegalTheory(**filtered_data)
                            self._add_theory(new_theory) # _add_theory handles duplicates
                else: self.logger.error(f"Theory AI response not JSON array: {response_content}")
            else: self.logger.error(f"Theory AI task failed: {ai_response_data.get('error', '') if ai_response_data else 'No AI resp'}")
        except Exception as e: self.logger.error(f"Exception in AI theory synthesis: {e}", exc_info=True)

    async def _analyze_timeline_for_patterns(self, timeline_name: str, timeline_data: Dict[str, Any]) -> List[Pattern]:
        events = timeline_data.get("events", [])
        if not events or len(events) < 3: return []
        event_type_counts = Counter(evt.get("event_type", "unknown") for evt in events)
        timeline_patterns_found = []
        for event_type, count in event_type_counts.items():
            if count >= 3:
                relevant_events = [evt for evt in events if evt.get("event_type") == event_type]
                try: relevant_events.sort(key=lambda x: datetime.fromisoformat(x['date'].replace('Z', '')))
                except: pass
                first_event_date = relevant_events[0].get('date','Unknown'); last_event_date = relevant_events[-1].get('date','Unknown')
                pattern = Pattern(pattern_type="Temporal Event Cluster", title=f"Cluster of '{event_type}' Events", description=f"{count} events of type '{event_type}' occurred between {first_event_date} and {last_event_date}.", evidence_files=list(set(Path(evt['source_file_path']).name for evt in relevant_events if 'source_file_path' in evt)), confidence_score=0.6 + min(0.4, count * 0.05), legal_significance=f"Repeated '{event_type}' occurrences may indicate a sustained activity or issue.", supporting_events=[{"date":evt.get('date'), "description":evt.get('description')[:50]+"..."} for evt in relevant_events[:5]])
                timeline_patterns_found.append(pattern)
        return timeline_patterns_found

    def _refine_and_correlate_patterns(self):
        unique_patterns: Dict[Tuple[str,str], Pattern] = {}
        for p in self.discovered_patterns:
            key = (p.pattern_type, p.title)
            if key not in unique_patterns: unique_patterns[key] = p
            else:
                existing_p = unique_patterns[key]
                existing_p.evidence_files = sorted(list(set(existing_p.evidence_files + p.evidence_files)))
                existing_p.raw_matches.extend(p.raw_matches)
                existing_p.confidence_score = min(1.0, max(existing_p.confidence_score, p.confidence_score) + 0.05 * (len(p.evidence_files) > 0)) # Boost for corroboration
        self.discovered_patterns = list(unique_patterns.values())
        self.logger.info(f"Refined patterns. Count: {len(self.discovered_patterns)}")

    async def _synthesize_legal_theories(self, case_context_for_ai: Dict[str,Any]):
        for pattern in self.discovered_patterns:
            if "financial" in pattern.pattern_type.lower() and pattern.confidence_score > 0.6:
                theory = LegalTheory(theory_name=f"Potential Financial Misconduct related to {pattern.title}", description=f"Pattern '{pattern.title}' (confidence: {pattern.confidence_score:.2f}) suggests possible financial issues.", supporting_patterns=[pattern.pattern_id], evidence_strength=pattern.confidence_score)
                self._add_theory(theory)
        if self.ai_service and hasattr(self.ai_service, 'config') and self.ai_service.config.enabled and self.discovered_patterns:
            await self._ai_synthesize_theories_via_ai(case_context_for_ai)
        else: self.logger.info("Using only rule-based theory synthesis or AI service unavailable/no patterns.")

    def _add_pattern(self, pattern: Pattern): self.discovered_patterns.append(pattern)
    def _add_theory(self, theory: LegalTheory):
        if not any(t.theory_name.lower() == theory.theory_name.lower() for t in self.potential_theories):
            self.potential_theories.append(theory)

    def save_discovery_report(self, output_dir_path_str: str, case_name: str):
        report_dir = Path(output_dir_path_str) / "REPORTS_LCAS" / "PATTERN_DISCOVERY"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file_path = report_dir / f"{case_name}_PatternDiscoveryData.json"
        report_data = {
            "case_name": case_name, "report_generated_at": datetime.now().isoformat(),
            "plugin_version": self.version,
            "summary": {"discovered_patterns_count": len(self.discovered_patterns), "potential_theories_count": len(self.potential_theories)},
            "discovered_patterns": [asdict(p) for p in self.discovered_patterns],
            "potential_legal_theories": [asdict(t) for t in self.potential_theories]
        }
        try:
            with open(report_file_path, 'w', encoding='utf-8') as f: json.dump(report_data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Pattern discovery report saved to: {report_file_path}")
        except Exception as e: self.logger.error(f"Error saving pattern discovery report to {report_file_path}: {e}", exc_info=True)
