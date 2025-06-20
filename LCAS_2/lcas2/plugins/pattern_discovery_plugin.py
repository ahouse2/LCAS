#!/usr/bin/env python3
"""
Pattern Discovery Plugin for LCAS
Discovers hidden patterns, connections, and potential legal theories
Designed to help self-represented litigants find powerful arguments they might miss
"""

import logging
import json
import uuid
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict, field
from collections import defaultdict, Counter
from datetime import datetime
import re
from pathlib import Path

from lcas2.core import AnalysisPlugin, LCASCore, LCASConfig # Adjusted import

logger = logging.getLogger(__name__)


@dataclass
class PatternConfigItem:
    keywords: List[str]
    description_template: str = "Pattern of '{sub_pattern_name}' detected."
    default_confidence_boost: float = 0.05  # Additive to base confidence
    base_confidence: float = 0.5  # Starting confidence if any keyword matches
    # Future: add fields like 'negation_keywords', 'proximity_rules'


@dataclass
class PatternGroupConfig:
    group_type: str
    sub_patterns: Dict[str, PatternConfigItem]  # sub_pattern_name -> config


@dataclass
class Pattern:
    """Represents a discovered pattern"""
    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pattern_type: str # behavioral, financial, temporal, communication, legal_process, etc.
    title: str
    description: str
    evidence_files: List[str] = field(default_factory=list)
    confidence_score: float = 0.0  # 0.0 to 1.0
    legal_significance: str = ""
    potential_arguments: List[str] = field(default_factory=list) # e.g., "Supports claim of X", "Contradicts Y's testimony"
    supporting_events: List[Dict[str, Any]] = field(default_factory=list) # List of {'event_title': ..., 'event_date': ...}
    strength_indicators: List[str] = field(default_factory=list)  # Specific phrases or data points
    recommended_actions: List[str] = field(default_factory=list)  # e.g., "Subpoena records for Z"
    related_patterns: List[str] = field(default_factory=list)  # IDs of other patterns
    raw_matches: List[Dict[str, Any]] = field(default_factory=list)  # Snippets or specific matches


@dataclass
class LegalTheory:
    """Represents a potential legal theory or argument"""
    theory_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    theory_name: str
    legal_basis: str = ""  # Placeholder for statutes, case law
    description: str = ""
    supporting_patterns: List[str] = field(default_factory=list)  # List of Pattern IDs
    evidence_strength: float = 0.0  # 0.0 to 1.0
    likelihood_of_success: float = 0.0  # Rough estimate
    required_evidence_elements: List[str] = field(default_factory=list)  # Key elements to prove
    available_evidence_for_elements: Dict[str, List[str]] = field(default_factory=dict)  # Element -> List of evidence snippets/files
    missing_evidence_for_elements: Dict[str, str] = field(default_factory=dict)  # Element -> Description of what's missing
    strategic_value: str = ""
    implementation_steps: List[str] = field(default_factory=list)  # High-level steps
    counter_arguments_to_anticipate: List[str] = field(default_factory=list)


class PatternDiscoveryPlugin(AnalysisPlugin): # Inherit from AnalysisPlugin
    """Plugin for discovering hidden patterns and legal theories"""

    @property
    def name(self) -> str:
        return "Pattern Discovery"

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def description(self) -> str:
        return "Discovers complex patterns, connections, and suggests legal theories from evidence."

    @property
    def dependencies(self) -> List[str]:
        return ["lcas_ai_wrapper_plugin"]

    async def initialize(self, core_app: LCASCore) -> bool:
        self.core = core_app
        self.logger = core_app.logger.getChild(self.name)
        self.lcas_config: LCASConfig = core_app.config

        self.ai_service: Optional[Any] = None
        if "lcas_ai_wrapper_plugin" in self.core.plugin_manager.loaded_plugins:
            ai_wrapper = self.core.plugin_manager.loaded_plugins["lcas_ai_wrapper_plugin"]
            if hasattr(ai_wrapper, 'ai_foundation') and ai_wrapper.ai_foundation is not None:
                 self.ai_service = ai_wrapper.ai_foundation
                 self.logger.info("Successfully accessed AI Foundation service via wrapper.")
            else:
                self.logger.warning("AI Wrapper plugin is loaded, but AI Foundation service is not available.")
        else:
            self.logger.warning("AI Wrapper plugin not found or not loaded. AI-assisted pattern analysis will be limited.")

        default_pattern_config_filename = "pattern_discovery_rules.json"
        plugin_dir = Path(__file__).parent
        pattern_configs_path_str: Optional[str] = None

        if hasattr(self.lcas_config, 'pattern_discovery_config_path') and self.lcas_config.pattern_discovery_config_path:
            project_root = plugin_dir.parent.parent
            pattern_configs_path = (project_root / self.lcas_config.pattern_discovery_config_path).resolve()
            pattern_configs_path_str = str(pattern_configs_path)
            self.logger.info(f"Attempting to load pattern configurations from LCASConfig specified path: {pattern_configs_path}")
        else:
            pattern_configs_path = (plugin_dir / default_pattern_config_filename).resolve()
            pattern_configs_path_str = str(pattern_configs_path)
            self.logger.info(f"No specific pattern configuration path in LCASConfig. Using default relative to plugin: {pattern_configs_path}")

        self.pattern_configs: Dict[str, PatternGroupConfig] = self._load_pattern_configurations(pattern_configs_path_str)

        self.discovered_patterns: List[Pattern] = []
        self.potential_theories: List[LegalTheory] = []
        self.logger.info(f"{self.name} initialized.")
        return True

    async def cleanup(self) -> None:
        self.logger.info(f"{self.name} cleaned up.")
        self.discovered_patterns = []
        self.potential_theories = []
        self.ai_service = None

    def _load_pattern_configurations(
            self, config_path_str: Optional[str]) -> Dict[str, PatternGroupConfig]:
        configs: Dict[str, PatternGroupConfig] = {}

        if config_path_str and Path(config_path_str).exists():
            try:
                with open(config_path_str, 'r', encoding='utf-8') as f:
                    raw_configs = json.load(f)
                loaded_configs_count = 0
                for group_type, group_data in raw_configs.items():
                    sub_patterns_dict = {}
                    if isinstance(group_data.get('sub_patterns'), dict):
                        for sp_name, sp_data in group_data.get('sub_patterns', {}).items():
                            if isinstance(sp_data, dict):
                                try:
                                    sub_patterns_dict[sp_name] = PatternConfigItem(**sp_data)
                                except TypeError as te:
                                    self.logger.error(f"Type error creating PatternConfigItem for {sp_name} in {group_type}: {te}. Data: {sp_data}")
                        if sub_patterns_dict:
                           configs[group_type] = PatternGroupConfig(group_type=group_type, sub_patterns=sub_patterns_dict)
                           loaded_configs_count +=1
                self.logger.info(f"Successfully loaded {loaded_configs_count} pattern groups from {config_path_str}")
            except Exception as e:
                self.logger.error(f"Error loading pattern configurations from {config_path_str}: {e}. Using internal defaults.", exc_info=True)
                configs = {}
        else:
            self.logger.info(f"Pattern configuration file not found at {config_path_str}. Using internal defaults.")

        if not configs:
            self.logger.info("Populating pattern configurations with internal defaults.")
            configs["abuse"] = PatternGroupConfig(
                group_type="abuse",
                sub_patterns={
                    'escalation_indicators': PatternConfigItem(keywords=['increasingly', 'more frequent', 'getting worse', 'escalating', 'never did this before', 'first time', 'started when', 'progressively worse'], description_template="Indicates a worsening or escalating situation related to abuse.", default_confidence_boost=0.1),
                    'physical_abuse': PatternConfigItem(keywords=['hit', 'punched', 'kicked', 'slapped', 'choked', 'shoved', 'pushed', 'grabbed', 'restrained', 'assaulted', 'beat', 'bruised', 'injured'], description_template="Direct mentions of physical violence.", default_confidence_boost=0.2),
                    'emotional_verbal_abuse': PatternConfigItem(keywords=['yelled', 'screamed', 'insulted', 'humiliated', 'belittled', 'degraded', 'gaslighting', 'gaslit', 'manipulated', 'threatened', 'intimidated', 'scared', 'afraid', 'worthless', 'stupid', 'crazy', 'unstable', 'name-calling'], description_template="Mentions of emotional or verbal abuse tactics.", default_confidence_boost=0.15),
                    'isolation_tactics': PatternConfigItem(keywords=['wouldn\'t let me', 'prevented me from', 'stopped me from seeing', 'blocked me', 'cut off contact with family', 'monitored my calls', 'controlled who I saw'], description_template="Indicates tactics used to isolate the individual.", default_confidence_boost=0.1),
                    'financial_abuse_control': PatternConfigItem(keywords=['took my card', 'changed passwords to accounts', 'hid money', 'secret account', 'controlled all spending', 'no access to funds', 'allowance', 'forced me to quit job', 'sabotaged my job', 'ran up debt in my name'], description_template="Indicates financial control as a form of abuse.", default_confidence_boost=0.15),
                    'custody_related_threats_coercion': PatternConfigItem(keywords=['take the kids', 'never see them again', 'bad mother', 'bad father', 'unfit parent', 'call CPS', 'get full custody', 'use children against me', 'alienate children'], description_template="Threats or coercion related to child custody.", default_confidence_boost=0.15),
                    'technological_abuse': PatternConfigItem(keywords=['spyware', 'stalkerware', 'tracking device', 'GPS tracker', 'monitored my phone', 'hacked my account', 'changed my passwords', 'impersonated me online', 'posted private photos', 'nonconsensual recording', 'cyberstalking', 'doxing'], description_template="Use of technology for abusive purposes.", default_confidence_boost=0.15)
                }
            )
            configs["financial"] = PatternGroupConfig(
                group_type="financial",
                sub_patterns={
                    'hidden_assets_income': PatternConfigItem(keywords=['undisclosed account', 'secret investment', 'offshore', 'shell company', 'cash transactions', 'unreported income', 'deferred compensation', 'crypto wallet', 'missing statements', 'large unexplained withdrawal', 'transfer to unknown'], description_template="Potential indication of hidden assets or income.", default_confidence_boost=0.2),
                    'dissipation_of_assets': PatternConfigItem(keywords=['excessive spending', 'gambling losses', 'gifts to third parties', 'unusual purchases', 'selling assets below market value', 'transferring property to family'], description_template="Potential dissipation of marital assets.", default_confidence_boost=0.15),
                }
            )
            configs["control"] = PatternGroupConfig(group_type="control", sub_patterns={'monitoring_surveillance': PatternConfigItem(keywords=['tracked my location', 'read my emails', 'checked my phone'], description_template="Evidence of monitoring/surveillance.")})
            configs["legal_process"] = PatternGroupConfig(group_type="legal_process", sub_patterns={'procedural_misconduct': PatternConfigItem(keywords=['frivolous filing', 'delay tactics', 'failed to disclose'], description_template="Potential procedural misconduct.")})
            configs["communication"] = PatternGroupConfig(group_type="communication", sub_patterns={'admission_of_fault_fact': PatternConfigItem(keywords=['I admit', 'my fault', 'I was wrong'], description_template="Admission of fault or fact.")})
            self.logger.info(f"Loaded {len(configs)} internal default pattern configuration groups.")
        return configs

    async def analyze(self, data: Any) -> Dict[str, Any]:
        self.logger.info(f"Starting pattern discovery for case: {data.get('case_name', 'Unknown')}")
        self.discovered_patterns = []
        self.potential_theories = []

        processed_files = data.get("processed_files", {})
        timelines = data.get("timelines")
        image_analyses = data.get("image_analyses")
        target_dir_str = data.get("target_directory", self.lcas_config.target_directory if self.lcas_config else "analysis_results_patterns")

        if not Path(target_dir_str).is_dir():
            Path(target_dir_str).mkdir(parents=True, exist_ok=True)

        all_texts_by_file: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        if not processed_files:
            self.logger.warning("No 'processed_files' data provided for pattern discovery.")
            return {"plugin": self.name, "status": "no_data", "success": False, "message": "No processed file data available for analysis.", "discovered_patterns_count": 0, "potential_theories_count": 0}

        for file_path, analysis_data_dict in processed_files.items():
            if not isinstance(analysis_data_dict, dict):
                self.logger.warning(f"Skipping file {file_path} due to unexpected data type for its analysis data: {type(analysis_data_dict)}")
                continue
            if analysis_data_dict.get('content'): all_texts_by_file[file_path].append(("main_content", analysis_data_dict['content']))
            if analysis_data_dict.get('summary'): all_texts_by_file[file_path].append(("summary", analysis_data_dict['summary']))
            ai_results = analysis_data_dict.get('ai_analysis_results', analysis_data_dict.get('provider_results'))
            if isinstance(ai_results, dict):
                for agent_name, agent_result in ai_results.items():
                    if isinstance(agent_result, dict):
                        findings = agent_result.get('findings')
                        if isinstance(findings, dict) and findings.get('summary'): all_texts_by_file[file_path].append((f"{agent_name}_summary", findings['summary']))
                        elif isinstance(findings, str) and findings: all_texts_by_file[file_path].append((f"{agent_name}_findings_text", findings))
                        raw_response = agent_result.get('response', agent_result.get('raw_response'))
                        if isinstance(raw_response, str) and raw_response and len(raw_response) < 20000 : all_texts_by_file[file_path].append((f"{agent_name}_raw_response_snippet", raw_response[:500]))
            if image_analyses and file_path in image_analyses:
                img_analysis_parent = image_analyses[file_path]
                actual_img_analysis_data = img_analysis_parent.get('image_analysis', img_analysis_parent)
                if isinstance(actual_img_analysis_data, dict):
                    combined_text = actual_img_analysis_data.get('combined_text', actual_img_analysis_data.get('text_content'))
                    if combined_text: all_texts_by_file[file_path].append(("image_ocr_text", combined_text))

        for file_path_str, texts_tuples in all_texts_by_file.items():
            current_file_analysis_data = processed_files.get(file_path_str, {})
            doc_patterns = await self._analyze_file_content_for_patterns(file_path_str, texts_tuples, current_file_analysis_data)
            for p in doc_patterns: self._add_pattern(p)

        if timelines:
            for timeline_name, timeline_data_dict in timelines.items():
                if isinstance(timeline_data_dict, dict):
                    timeline_patterns = await self._analyze_timeline_for_patterns(timeline_name, timeline_data_dict)
                    for p in timeline_patterns: self._add_pattern(p)
                else: self.logger.warning(f"Timeline data for '{timeline_name}' is not in expected dict format, skipping.")

        self._refine_and_correlate_patterns()
        await self._synthesize_legal_theories()
        self.logger.info(f"Discovered {len(self.discovered_patterns)} patterns and {len(self.potential_theories)} potential theories.")
        self.save_discovery_report(target_dir_str)

        return {"plugin": self.name, "status": "completed", "success": True, "summary": {"discovered_patterns_count": len(self.discovered_patterns), "potential_theories_count": len(self.potential_theories)}, "report_location": str(Path(target_dir_str) / "REPORTS_LCAS" / "PATTERN_DISCOVERY")}

    def _get_text_snippet(self, text: str, keyword_match_obj: re.Match, window_size: int = 50) -> str:
        start_index = max(0, keyword_match_obj.start() - window_size)
        end_index = min(len(text), keyword_match_obj.end() + window_size)
        prefix = "..." if start_index > 0 else ""
        suffix = "..." if end_index < len(text) else ""
        return f"{prefix}{text[start_index:end_index]}{suffix}"

    async def _analyze_file_content_for_patterns(self, file_path: str, texts_tuples: List[Tuple[str, str]], file_analysis_data: Dict[str, Any]) -> List[Pattern]:
        file_patterns: List[Pattern] = []
        for text_source_name, text_content in texts_tuples:
            if not text_content or not isinstance(text_content, str): continue
            for group_type, group_config in self.pattern_configs.items():
                for sub_pattern_name, item_config in group_config.sub_patterns.items():
                    current_matches, matched_keywords_in_subpattern = [], set()
                    for keyword in item_config.keywords:
                        try:
                            compiled_regex = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
                        except re.error as e: self.logger.warning(f"Invalid regex for keyword '{keyword}' in pattern '{sub_pattern_name}': {e}"); continue
                        for match_obj in compiled_regex.finditer(text_content):
                            snippet = self._get_text_snippet(text_content, match_obj)
                            current_matches.append({"keyword": match_obj.group(0), "snippet": snippet, "source_text_type": text_source_name, "sub_pattern_name": sub_pattern_name, "start_pos": match_obj.start(), "end_pos": match_obj.end()})
                            matched_keywords_in_subpattern.add(keyword.lower())
                    if current_matches:
                        title = f"{group_config.group_type.replace('_', ' ').title()}: {sub_pattern_name.replace('_', ' ').title()}"
                        description = item_config.description_template.format(sub_pattern_name=sub_pattern_name.replace('_', ' ')) + f" Identified in '{Path(file_path).name}' based on keywords like '{', '.join(list(matched_keywords_in_subpattern)[:3])}'."
                        num_distinct_matched_keywords = len(matched_keywords_in_subpattern)
                        confidence = min(1.0, item_config.base_confidence + (item_config.default_confidence_boost * num_distinct_matched_keywords))
                        new_pattern = Pattern(pattern_type=group_config.group_type, title=title, description=description, evidence_files=[file_path], confidence_score=confidence, legal_significance=f"May indicate {group_config.group_type} relevant to {file_analysis_data.get('category', 'various arguments')}.", potential_arguments=[file_analysis_data.get('category', 'General Case File')] if file_analysis_data.get('category') else ['General Case File'], strength_indicators=[f"Distinct keywords matched: {num_distinct_matched_keywords}", f"Total matches: {len(current_matches)}"], raw_matches=current_matches)
                        if self.ai_service and hasattr(self.ai_service, 'config') and self.ai_service.config.enabled: # Check ai_service.config
                            ai_analysis = await self._ai_analyze_pattern_context(new_pattern, text_content)
                            if ai_analysis:
                                new_pattern.description += f"\nAI Context: {ai_analysis.get('ai_description', '')}"
                                new_pattern.confidence_score = (new_pattern.confidence_score + ai_analysis.get('ai_confidence', new_pattern.confidence_score)) / 2
                                new_pattern.legal_significance = ai_analysis.get('ai_legal_significance', new_pattern.legal_significance)
                        file_patterns.append(new_pattern)
        return file_patterns

    async def _ai_analyze_pattern_context(self, pattern: Pattern, full_text_context: str) -> Optional[Dict[str, Any]]:
        if not self.ai_service or not hasattr(self.ai_service, 'config') or not self.ai_service.config.enabled: return None # Check ai_service.config
        snippets_for_ai = "\n".join([f"- '{m['keyword']}': {m['snippet']}" for m in pattern.raw_matches[:5]])
        prompt = f"""
        A potential pattern titled "{pattern.title}" (type: {pattern.pattern_type}) was identified in a legal document.
        Keyword matches found:
        {snippets_for_ai}
        Context: The document relates to a family law case (divorce, custody, domestic violence).
        Full text excerpt (first 1000 chars of source): {full_text_context[:1000]}
        Please analyze this:
        1. Provide a concise "ai_description" (1-2 sentences) of what this pattern likely represents in this specific legal context.
        2. Estimate your "ai_confidence" (a float from 0.0 to 1.0) that this is a significant and correctly identified pattern relevant to the case.
        3. Suggest its potential "ai_legal_significance" in a family law proceeding (e.g., evidence of abuse, hidden assets, parental alienation).
        Respond ONLY in JSON format with the exact keys: "ai_description", "ai_confidence", "ai_legal_significance".
        Example: {{"ai_description": "This seems to indicate repeated instances of verbal intimidation towards the end of the relationship.", "ai_confidence": 0.85, "ai_legal_significance": "Could be used as evidence of emotional abuse affecting custody decisions or supporting a restraining order."}}
        """
        try:
            response = await self.ai_service.provider.generate_completion(prompt, system_prompt="You are a legal analyst AI specializing in identifying patterns in evidence for family law cases. Provide concise, structured JSON responses.")
            if response.success:
                try:
                    content_to_parse = response.content
                    if content_to_parse.strip().startswith("```json"): content_to_parse = content_to_parse.strip()[7:]
                    if content_to_parse.strip().endswith("```"): content_to_parse = content_to_parse.strip()[:-3]
                    return json.loads(content_to_parse)
                except json.JSONDecodeError: logger.error(f"AI response for pattern analysis was not valid JSON: {response.content}"); return {"ai_description": response.content, "ai_confidence": 0.4, "ai_legal_significance": "AI analysis returned non-JSON content."}
            return None
        except Exception as e: logger.error(f"Error during AI pattern context analysis: {e}"); return None

    async def _analyze_timeline_for_patterns(self, timeline_name: str, timeline_data: Dict[str, Any]) -> List[Pattern]:
        timeline_patterns: List[Pattern] = []
        events = timeline_data.get('events', [])
        if not events or len(events) < 2: return timeline_patterns
        event_type_counts = Counter(event['event_type'] for event in events if event.get('event_type'))
        for et, count in event_type_counts.items():
            if count >= 3:
                related_events = [e for e in events if e.get('event_type') == et]
                try: related_events.sort(key=lambda x: datetime.fromisoformat(x['date'].split(' ')[0].replace('Z', '')))
                except (ValueError, TypeError, AttributeError) as e: logger.warning(f"Could not sort events by date for timeline pattern analysis: {e}. Events: {related_events[:2]}"); related_events.sort(key=lambda x: x.get('date', ''))
                avg_strength = sum(e.get('evidence_strength', 0.5) for e in related_events) / len(related_events) if related_events else 0
                pattern = Pattern(pattern_type="temporal", title=f"Recurrence of '{et}' Events in {timeline_name}", description=f"{count} events of type '{et}' found in timeline '{timeline_name}'. Average evidence strength: {avg_strength:.2f}.", evidence_files=list(set(f for e_dict in related_events for f_list in [e_dict.get('source_files', []), e_dict.get('supporting_documents', [])] for f in f_list if f)), confidence_score=min(1.0, 0.6 + count * 0.05 + avg_strength * 0.1), legal_significance=f"Repeated '{et}' occurrences ({count}) may establish consistent behavior relevant to {timeline_name}.", supporting_events=[{'event_title': e.get('title'), 'event_date': e.get('date'), 'description_snippet': e.get('description', '')[:100]} for e in related_events[:5]])
                timeline_patterns.append(pattern)
        return timeline_patterns

    def _refine_and_correlate_patterns(self):
        merged_patterns: Dict[Tuple[str, str], Pattern] = {}
        for p in self.discovered_patterns:
            key = (p.pattern_type, p.title)
            if key not in merged_patterns: merged_patterns[key] = p
            else:
                existing_p = merged_patterns[key]
                existing_p.evidence_files.extend(p.evidence_files); existing_p.evidence_files = sorted(list(set(existing_p.evidence_files)))
                existing_p.raw_matches.extend(p.raw_matches)
                existing_p.supporting_events.extend(p.supporting_events)
                seen_events = set(); unique_supporting_events = []
                for event_dict in existing_p.supporting_events:
                    event_tuple = tuple(sorted(event_dict.items()))
                    if event_tuple not in seen_events: unique_supporting_events.append(event_dict); seen_events.add(event_tuple)
                existing_p.supporting_events = unique_supporting_events
                existing_p.confidence_score = max(existing_p.confidence_score, p.confidence_score)
                existing_p.description += f"\nAdditional evidence in: {', '.join(Path(ef).name for ef in p.evidence_files)}"
                existing_p.strength_indicators.extend(p.strength_indicators); existing_p.strength_indicators = sorted(list(set(existing_p.strength_indicators)))
        self.discovered_patterns = list(merged_patterns.values())
        self.logger.info(f"Refined patterns. Count: {len(self.discovered_patterns)}")

    async def _synthesize_legal_theories(self):
        patterns_by_type = defaultdict(list)
        for p in self.discovered_patterns: patterns_by_type[p.pattern_type].append(p)
        abuse_patterns = patterns_by_type.get('abuse', []) + patterns_by_type.get('control', [])
        if abuse_patterns:
            avg_strength = sum(p.confidence_score for p in abuse_patterns) / len(abuse_patterns)
            self._add_theory(LegalTheory(theory_name="Potential Pattern of Coercive Control / Domestic Abuse", description="Evidence suggests a potential pattern of coercive/abusive behavior.", supporting_patterns=[p.pattern_id for p in abuse_patterns], evidence_strength=avg_strength, required_evidence_elements=["Specific incidents", "Pattern of conduct", "Impact on victim"], strategic_value="Relevant for restraining orders, custody, DV findings.", implementation_steps=["Organize evidence chronologically.", "Draft detailed declaration.", "Consult with DV advocate."]))
        financial_patterns = patterns_by_type.get('financial', [])
        if financial_patterns:
            avg_strength = sum(p.confidence_score for p in financial_patterns) / len(financial_patterns)
            self._add_theory(LegalTheory(theory_name="Potential Financial Misconduct or Non-Disclosure", description="Patterns suggest potential financial misconduct or non-disclosure.", supporting_patterns=[p.pattern_id for p in financial_patterns], evidence_strength=avg_strength, required_evidence_elements=["Proof of undisclosed assets/income", "Evidence of dissipation", "Discrepancies in declarations"], strategic_value="Crucial for asset division and support calculations.", implementation_steps=["Issue discovery for financial records.", "Compare declarations with proof.", "Consider forensic accountant."]))
        legal_process_patterns = [p for p in patterns_by_type.get('legal_process', []) if any(term in p.title.lower() for term in ['perjury', 'false_statements', 'evidence_tampering', 'procedural_misconduct', 'discovery_abuse'])]
        if legal_process_patterns:
            avg_strength = sum(p.confidence_score for p in legal_process_patterns) / len(legal_process_patterns) if legal_process_patterns else 0.0
            self._add_theory(LegalTheory(theory_name="Potential Abuse of Legal Process / Fraud on the Court", description="Evidence indicates possible abuse of legal process or fraud on the court.", supporting_patterns=[p.pattern_id for p in legal_process_patterns], evidence_strength=avg_strength, required_evidence_elements=["False statements/filings with proof", "Intent to deceive/harass", "Harm caused"], strategic_value="Can lead to sanctions, damage credibility.", implementation_steps=["Document misconduct meticulously.", "File appropriate motions (sanctions).", "Highlight falsehoods."]))

        if self.ai_service and hasattr(self.ai_service, 'config') and self.ai_service.config.enabled and self.discovered_patterns: # Check ai_service.config
            await self._ai_synthesize_theories_via_ai() # Renamed method

    async def _ai_synthesize_theories_via_ai(self): # Renamed to avoid conflict
        if not self.ai_service or not hasattr(self.ai_service, 'config') or not self.ai_service.config.enabled or not self.discovered_patterns: return # Check ai_service.config
        pattern_summary_for_ai = [{"id": p.pattern_id, "title": p.title, "type": p.pattern_type, "confidence": f"{p.confidence_score:.2f}", "description_snippet": p.description[:150]} for p in self.discovered_patterns[:20]]
        prompt = f"""You are a legal strategy AI for family law cases. Given patterns: {json.dumps(pattern_summary_for_ai, indent=2)}. Suggest legal theories. For each: "theory_name", "description", "supporting_pattern_ids", "evidence_strength" (float 0.0-1.0), "required_evidence_elements", "strategic_value". Focus on divorce, custody, DV, finance. Prioritize strong support. Respond ONLY in JSON array. Example: [{{"theory_name": "X", "description": "Y", ...}}]. If none, return []."""
        try:
            response = await self.ai_service.provider.generate_completion(prompt, system_prompt="Respond ONLY with valid JSON array of theory objects.")
            if response.success:
                content_to_parse = response.content.strip()
                if content_to_parse.startswith("```json"): content_to_parse = content_to_parse[7:];
                if content_to_parse.endswith("```"): content_to_parse = content_to_parse[:-3]
                if not content_to_parse.startswith("[") or not content_to_parse.endswith("]"): logger.error(f"AI theory response not JSON array: {content_to_parse}"); return
                try:
                    ai_suggested_theories = json.loads(content_to_parse)
                    for suggested_theory_data in ai_suggested_theories:
                        if not isinstance(suggested_theory_data, dict): logger.warning(f"Skipping non-dict item in AI theories: {suggested_theory_data}"); continue
                        if 'theory_name' in suggested_theory_data and 'supporting_pattern_ids' in suggested_theory_data:
                            new_theory = LegalTheory(theory_name=suggested_theory_data['theory_name'], description=suggested_theory_data.get('description', ''), supporting_patterns=suggested_theory_data['supporting_pattern_ids'], evidence_strength=float(suggested_theory_data.get('evidence_strength', 0.5)), required_evidence_elements=suggested_theory_data.get('required_evidence_elements', []), strategic_value=suggested_theory_data.get('strategic_value', ''))
                            if not any(t.theory_name.strip().lower() == new_theory.theory_name.strip().lower() for t in self.potential_theories): self._add_theory(new_theory)
                except json.JSONDecodeError as e: logger.error(f"AI theory JSON decode error: {e}. Content: {content_to_parse}")
        except Exception as e: logger.error(f"Error in AI theory synthesis: {e}")

    def _add_pattern(self, pattern: Pattern): self.discovered_patterns.append(pattern)
    def _add_theory(self, theory: LegalTheory): self.potential_theories.append(theory)

    def save_discovery_report(self, output_dir_path_str: str):
        output_dir = Path(output_dir_path_str)
        report_dir = output_dir / "REPORTS_LCAS" / "PATTERN_DISCOVERY"
        report_dir.mkdir(parents=True, exist_ok=True)
        patterns_file, theories_file, summary_file = report_dir / "patterns.json", report_dir / "theories.json", report_dir / "summary.md"
        try:
            with open(patterns_file, 'w', encoding='utf-8') as f: json.dump([asdict(p) for p in self.discovered_patterns], f, indent=2, ensure_ascii=False)
            self.logger.info(f"Patterns saved: {patterns_file}")
            with open(theories_file, 'w', encoding='utf-8') as f: json.dump([asdict(t) for t in self.potential_theories], f, indent=2, ensure_ascii=False)
            self.logger.info(f"Theories saved: {theories_file}")
            summary_content = f"# Pattern Discovery Report ({datetime.now():%Y-%m-%d %H:%M})\n\n## Patterns ({len(self.discovered_patterns)})\n"
            if self.discovered_patterns: summary_content += "| Title | Type | Confidence | Files | Significance |\n|---|---|---|---|---|\n" + "\n".join([f"| {p.title[:30]}... | {p.pattern_type} | {p.confidence_score:.2f} | {len(p.evidence_files)} | {p.legal_significance[:30]}... |" for p in sorted(self.discovered_patterns, key=lambda x: x.confidence_score, reverse=True)[:20]]) + (f"\n...and {len(self.discovered_patterns)-20} more." if len(self.discovered_patterns)>20 else "") + "\n\n"
            else: summary_content += "No patterns discovered.\n\n"
            summary_content += f"## Legal Theories ({len(self.potential_theories)})\n"
            if self.potential_theories: summary_content += "| Theory | Strength | Patterns | Value |\n|---|---|---|---|\n" + "\n".join([f"| {t.theory_name[:30]}... | {t.evidence_strength:.2f} | {len(t.supporting_patterns)} | {t.strategic_value[:30]}... |" for t in sorted(self.potential_theories, key=lambda x: x.evidence_strength, reverse=True)]) + "\n\n"
            else: summary_content += "No theories synthesized.\n\n"
            summary_content += "**Disclaimer:** Automated analysis. Review carefully. Not legal advice."
            with open(summary_file, 'w', encoding='utf-8') as f: f.write(summary_content)
            self.logger.info(f"Summary report saved: {summary_file}")
        except Exception as e: self.logger.error(f"Error saving discovery report: {e}", exc_info=True)

# Note: UIPlugin aspects (create_ui_elements, run_analysis_ui) would need to be added
# if this plugin is to have a direct UI in the "Plugin Features" tab.
# For now, it's purely an AnalysisPlugin.
>>>>>>> REPLACE
