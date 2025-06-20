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

# Assuming these classes are available in the execution context or can be imported
# from lcas_main import FileAnalysis (or use Dict[str, Any] for processed_files values)
# from timeline_builder_plugin import Timeline, TimelineEvent

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
    # behavioral, financial, temporal, communication, legal_process, etc.
    pattern_type: str
    title: str
    description: str
    evidence_files: List[str] = field(default_factory=list)
    confidence_score: float = 0.0  # 0.0 to 1.0
    legal_significance: str = ""
    # e.g., "Supports claim of X", "Contradicts Y's testimony"
    potential_arguments: List[str] = field(default_factory=list)
    # List of {'event_title': ..., 'event_date': ...}
    supporting_events: List[Dict[str, Any]] = field(default_factory=list)
    strength_indicators: List[str] = field(
        default_factory=list)  # Specific phrases or data points
    recommended_actions: List[str] = field(
        default_factory=list)  # e.g., "Subpoena records for Z"
    related_patterns: List[str] = field(
        default_factory=list)  # IDs of other patterns
    raw_matches: List[Dict[str, Any]] = field(
        default_factory=list)  # Snippets or specific matches


@dataclass
class LegalTheory:
    """Represents a potential legal theory or argument"""
    theory_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    theory_name: str
    legal_basis: str = ""  # Placeholder for statutes, case law
    description: str = ""
    supporting_patterns: List[str] = field(
        default_factory=list)  # List of Pattern IDs
    evidence_strength: float = 0.0  # 0.0 to 1.0
    likelihood_of_success: float = 0.0  # Rough estimate
    required_evidence_elements: List[str] = field(
        default_factory=list)  # Key elements to prove
    available_evidence_for_elements: Dict[str, List[str]] = field(
        default_factory=dict)  # Element -> List of evidence snippets/files
    missing_evidence_for_elements: Dict[str, str] = field(
        default_factory=dict)  # Element -> Description of what's missing
    strategic_value: str = ""
    implementation_steps: List[str] = field(
        default_factory=list)  # High-level steps
    counter_arguments_to_anticipate: List[str] = field(default_factory=list)


class PatternDiscoveryPlugin:
    """Plugin for discovering hidden patterns and legal theories"""

    def __init__(self, config, ai_service=None,
                 pattern_configs_path: Optional[str] = None):
        self.lcas_config = config  # LCASConfig or similar
        self.ai_service = ai_service  # AIService instance
        self.discovered_patterns: List[Pattern] = []
        self.potential_theories: List[LegalTheory] = []

        self.pattern_configs: Dict[str, PatternGroupConfig] = self._load_pattern_configurations(
            pattern_configs_path)

    def _load_pattern_configurations(
            self, config_path: Optional[str]) -> Dict[str, PatternGroupConfig]:
        """
        Loads pattern configurations from external YAML/JSON files or uses defaults.
        This implements part of Vertical Slice 1.1.
        """
        configs: Dict[str, PatternGroupConfig] = {}

        # In a real scenario, you'd load from a file here.
        # For now, we'll use the structure defined in the dataclasses and populate defaults.
        # Example of how you might load if path is provided:
        # if config_path and Path(config_path).exists():
        #     with open(config_path, 'r') as f:
        #         raw_configs = yaml.safe_load(f) # Assuming YAML
        #     for group_type, group_data in raw_configs.items():
        #         sub_patterns_dict = {}
        #         for sp_name, sp_data in group_data.get('sub_patterns', {}).items():
        #             sub_patterns_dict[sp_name] = PatternConfigItem(**sp_data)
        #         configs[group_type] = PatternGroupConfig(group_type=group_type, sub_patterns=sub_patterns_dict)
        #     return configs

        # --- DEFAULT CONFIGURATIONS (Simulating external loading) ---
        configs["abuse"] = PatternGroupConfig(
            group_type="abuse",
            sub_patterns={
                'escalation_indicators': PatternConfigItem(
                    keywords=[
                        'increasingly',
                        'more frequent',
                        'getting worse',
                        'escalating',
                        'never did this before',
                        'first time',
                        'started when',
                        'progressively worse'],
                    description_template="Indicates a worsening or escalating situation related to abuse.",
                    default_confidence_boost=0.1
                ),
                'physical_abuse': PatternConfigItem(
                    keywords=[
                        'hit',
                        'punched',
                        'kicked',
                        'slapped',
                        'choked',
                        'shoved',
                        'pushed',
                        'grabbed',
                        'restrained',
                        'assaulted',
                        'beat',
                        'bruised',
                        'injured'],
                    description_template="Direct mentions of physical violence.",
                    default_confidence_boost=0.2
                ),
                'emotional_verbal_abuse': PatternConfigItem(
                    keywords=[
                        'yelled',
                        'screamed',
                        'insulted',
                        'humiliated',
                        'belittled',
                        'degraded',
                        'gaslighting',
                        'gaslit',
                        'manipulated',
                        'threatened',
                        'intimidated',
                        'scared',
                        'afraid',
                        'worthless',
                        'stupid',
                        'crazy',
                        'unstable',
                        'name-calling'],
                    description_template="Mentions of emotional or verbal abuse tactics.",
                    default_confidence_boost=0.15
                ),
                'isolation_tactics': PatternConfigItem(
                    keywords=[
                        'wouldn\'t let me',
                        'prevented me from',
                        'stopped me from seeing',
                        'blocked me',
                        'cut off contact with family',
                        'monitored my calls',
                        'controlled who I saw'],
                    description_template="Indicates tactics used to isolate the individual.",
                    default_confidence_boost=0.1
                ),
                'financial_abuse_control': PatternConfigItem(
                    keywords=[
                        'took my card',
                        'changed passwords to accounts',
                        'hid money',
                        'secret account',
                        'controlled all spending',
                        'no access to funds',
                        'allowance',
                        'forced me to quit job',
                        'sabotaged my job',
                        'ran up debt in my name'],
                    description_template="Indicates financial control as a form of abuse.",
                    default_confidence_boost=0.15
                ),
                'custody_related_threats_coercion': PatternConfigItem(
                    keywords=[
                        'take the kids',
                        'never see them again',
                        'bad mother',
                        'bad father',
                        'unfit parent',
                        'call CPS',
                        'get full custody',
                        'use children against me',
                        'alienate children'],
                    description_template="Threats or coercion related to child custody.",
                    default_confidence_boost=0.15
                ),
                'technological_abuse': PatternConfigItem(
                    keywords=[
                        'spyware',
                        'stalkerware',
                        'tracking device',
                        'GPS tracker',
                        'monitored my phone',
                        'hacked my account',
                        'changed my passwords',
                        'impersonated me online',
                        'posted private photos',
                        'nonconsensual recording',
                        'cyberstalking',
                        'doxing'],
                    description_template="Use of technology for abusive purposes.",
                    default_confidence_boost=0.15
                )
            }
        )
        configs["financial"] = PatternGroupConfig(
            group_type="financial",
            sub_patterns={
                'hidden_assets_income': PatternConfigItem(
                    keywords=[
                        'undisclosed account',
                        'secret investment',
                        'offshore',
                        'shell company',
                        'cash transactions',
                        'unreported income',
                        'deferred compensation',
                        'crypto wallet',
                        'missing statements',
                        'large unexplained withdrawal',
                        'transfer to unknown'],
                    description_template="Potential indication of hidden assets or income.",
                    default_confidence_boost=0.2
                ),
                'dissipation_of_assets': PatternConfigItem(
                    keywords=[
                        'excessive spending',
                        'gambling losses',
                        'gifts to third parties',
                        'unusual purchases',
                        'selling assets below market value',
                        'transferring property to family'],
                    description_template="Potential dissipation of marital assets.",
                    default_confidence_boost=0.15
                ),
            }
        )
        # ... Add default configs for 'control', 'legal_process', 'communication' similarly ...
        configs["control"] = PatternGroupConfig(group_type="control", sub_patterns={
            'monitoring_surveillance': PatternConfigItem(keywords=['tracked my location', 'read my emails', 'checked my phone'], description_template="Evidence of monitoring/surveillance.")
        })
        configs["legal_process"] = PatternGroupConfig(group_type="legal_process", sub_patterns={
            'procedural_misconduct': PatternConfigItem(keywords=['frivolous filing', 'delay tactics', 'failed to disclose'], description_template="Potential procedural misconduct.")
        })
        configs["communication"] = PatternGroupConfig(group_type="communication", sub_patterns={
            'admission_of_fault_fact': PatternConfigItem(keywords=['I admit', 'my fault', 'I was wrong'], description_template="Admission of fault or fact.")
        })

        logger.info(f"Loaded {len(configs)} pattern configuration groups.")
        return configs

    # The _initialize_*_patterns methods are now effectively replaced by _load_pattern_configurations
    # and the direct use of self.pattern_configs.

    async def discover_patterns_and_theories(
        self,
        processed_files: Dict[str, Any],  # Dict[str, FileAnalysis-like dict]
        # Dict[str, Timeline-like dict]
        timelines: Optional[Dict[str, Any]] = None,
        # Dict[str, ImageAnalysisResult-like dict]
        image_analyses: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Pattern], List[LegalTheory]]:
        logger.info("Starting pattern discovery and legal theory synthesis...")
        self.discovered_patterns = []
        self.potential_theories = []

        all_texts_by_file: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

        for file_path, analysis_data in processed_files.items():
            if analysis_data.get('content'):
                all_texts_by_file[file_path].append(
                    ("main_content", analysis_data['content']))
            if analysis_data.get('summary'):
                all_texts_by_file[file_path].append(
                    ("summary", analysis_data['summary']))

            # Handle AI summary (check if it's dict from AIEnhancedLCASPlugin
            # or simple string)
            ai_summary_data = analysis_data.get('ai_summary')
            if isinstance(ai_summary_data, dict):
                ai_summary_text = str(ai_summary_data.get('summary', ''))
                if ai_summary_text:  # Ensure it's not an empty string
                    all_texts_by_file[file_path].append(
                        ("ai_summary_text", ai_summary_text))
            elif isinstance(ai_summary_data, str) and ai_summary_data:
                all_texts_by_file[file_path].append(
                    ("ai_summary_text", ai_summary_data))

            # Handle image analysis text
            if image_analyses and file_path in image_analyses:
                # This is the value from the image_analyses dict
                img_analysis_parent = image_analyses[file_path]
                # The actual image analysis results might be nested if
                # ImageAnalysisPlugin structures it that way
                actual_img_analysis_data = img_analysis_parent.get(
                    'image_analysis', img_analysis_parent)

                combined_text = actual_img_analysis_data.get('combined_text')
                if combined_text:
                    all_texts_by_file[file_path].append(
                        ("image_ocr_text", combined_text))
                # Fallback if combined_text not present
                elif actual_img_analysis_data.get('text_content'):
                    all_texts_by_file[file_path].append(
                        ("image_ocr_text", actual_img_analysis_data['text_content']))

        for file_path, texts_tuples in all_texts_by_file.items():
            doc_patterns = await self._analyze_file_content_for_patterns(file_path, texts_tuples, processed_files[file_path])
            for p in doc_patterns:
                self._add_pattern(p)

        if timelines:
            for timeline_name, timeline_data_dict in timelines.items():
                timeline_patterns = await self._analyze_timeline_for_patterns(timeline_name, timeline_data_dict)
                for p in timeline_patterns:
                    self._add_pattern(p)

        self._refine_and_correlate_patterns()
        await self._synthesize_legal_theories()

        logger.info(
            f"Discovered {
                len(
                    self.discovered_patterns)} patterns and {
                len(
                    self.potential_theories)} potential theories.")
        return self.discovered_patterns, self.potential_theories

    def _get_text_snippet(
            self, text: str, keyword_match_obj: re.Match, window_size: int = 50) -> str:
        """Extracts a snippet of text around the re.Match object."""
        start_index = max(0, keyword_match_obj.start() - window_size)
        end_index = min(len(text), keyword_match_obj.end() + window_size)
        # Add ellipsis if snippet doesn't start/end at text boundaries
        prefix = "..." if start_index > 0 else ""
        suffix = "..." if end_index < len(text) else ""
        return f"{prefix}{text[start_index:end_index]}{suffix}"

    async def _analyze_file_content_for_patterns(
        self,
        file_path: str,
        texts_tuples: List[Tuple[str, str]],
        file_analysis_data: Dict[str, Any]
    ) -> List[Pattern]:
        """
        Analyzes all text associated with a single file for patterns.
        Updated for Vertical Slice 1.1 to use self.pattern_configs.
        """
        file_patterns: List[Pattern] = []

        for text_source_name, text_content in texts_tuples:
            if not text_content or not isinstance(text_content, str):
                continue

            for group_type, group_config in self.pattern_configs.items():
                for sub_pattern_name, item_config in group_config.sub_patterns.items():
                    current_matches = []
                    matched_keywords_in_subpattern = set()

                    for keyword in item_config.keywords:
                        # Using re.finditer for multiple occurrences and positions
                        # Ensure keyword is treated as a whole word unless it contains wildcards (not handled here yet)
                        # regex_keyword = r'\b' + re.escape(keyword) + r'\b'
                        # For more flexibility, if keywords can be phrases, re.escape is important.
                        # If keywords are single words, \b works well. If they can be phrases, \b might be too restrictive at ends.
                        # Let's assume keywords are meant to be matched as
                        # given.
                        try:
                            # Attempt to compile regex for each keyword to catch invalid regex early
                            # More robust: compile all regexes once at init if
                            # they are complex
                            compiled_regex = re.compile(
                                r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
                        except re.error as e:
                            logger.warning(
                                f"Invalid regex for keyword '{keyword}' in pattern '{sub_pattern_name}': {e}")
                            continue  # Skip this keyword

                        for match_obj in compiled_regex.finditer(text_content):
                            snippet = self._get_text_snippet(
                                text_content, match_obj)  # Pass match_obj
                            current_matches.append({
                                # Get the actual matched text
                                "keyword": match_obj.group(0),
                                "snippet": snippet,
                                "source_text_type": text_source_name,
                                "sub_pattern_name": sub_pattern_name,
                                "start_pos": match_obj.start(),
                                "end_pos": match_obj.end()
                            })
                            matched_keywords_in_subpattern.add(
                                keyword.lower())  # Store the original configured keyword

                    if current_matches:
                        title = f"{
                            group_config.group_type.replace(
                                '_', ' ').title()}: {
                            sub_pattern_name.replace(
                                '_', ' ').title()}"

                        # Use description_template from config
                        description = item_config.description_template.format(
                            sub_pattern_name=sub_pattern_name.replace('_', ' '))
                        description += f" Identified in '{
                            Path(file_path).name}' based on keywords like '{
                            ', '.join(
                                list(matched_keywords_in_subpattern)[
                                    :3])}'."

                        # Confidence: base + boost for number of *distinct*
                        # keywords from the sub_pattern's list that matched.
                        num_distinct_matched_keywords = len(
                            matched_keywords_in_subpattern)
                        confidence = min(1.0, item_config.base_confidence +
                                         (item_config.default_confidence_boost *
                                          num_distinct_matched_keywords))

                        new_pattern = Pattern(
                            pattern_type=group_config.group_type,
                            title=title,
                            description=description,
                            evidence_files=[file_path],
                            confidence_score=confidence,
                            legal_significance=f"May indicate {
                                group_config.group_type} relevant to {
                                file_analysis_data.get(
                                    'category', 'various arguments')}.",
                            potential_arguments=[
                                file_analysis_data.get(
                                    'category',
                                    'General Case File')] if file_analysis_data.get('category') else ['General Case File'],
                            strength_indicators=[
                                f"Distinct keywords matched: {num_distinct_matched_keywords}",
                                f"Total matches: {
                                    len(current_matches)}"],
                            raw_matches=current_matches
                        )

                        if self.ai_service and self.ai_service.config.enabled:
                            ai_analysis = await self._ai_analyze_pattern_context(new_pattern, text_content)
                            if ai_analysis:
                                new_pattern.description += f"\nAI Context: {
                                    ai_analysis.get(
                                        'ai_description', '')}"
                                new_pattern.confidence_score = (
                                    new_pattern.confidence_score + ai_analysis.get(
                                        'ai_confidence', new_pattern.confidence_score)) / 2
                                new_pattern.legal_significance = ai_analysis.get(
                                    'ai_legal_significance', new_pattern.legal_significance)

                        file_patterns.append(new_pattern)

        return file_patterns

    async def _ai_analyze_pattern_context(
            self, pattern: Pattern, full_text_context: str) -> Optional[Dict[str, Any]]:
        if not self.ai_service or not self.ai_service.config.enabled:
            return None

        snippets_for_ai = "\n".join(
            [f"- '{m['keyword']}': {m['snippet']}" for m in pattern.raw_matches[:5]])

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
            response = await self.ai_service.provider.generate_completion(
                prompt,
                system_prompt="You are a legal analyst AI specializing in identifying patterns in evidence for family law cases. Provide concise, structured JSON responses."
            )
            if response.success:
                try:
                    # Attempt to strip markdown ```json ... ``` if present
                    content_to_parse = response.content
                    if content_to_parse.strip().startswith("```json"):
                        content_to_parse = content_to_parse.strip()[7:]
                        if content_to_parse.strip().endswith("```"):
                            content_to_parse = content_to_parse.strip()[:-3]

                    return json.loads(content_to_parse)
                except json.JSONDecodeError:
                    logger.error(
                        f"AI response for pattern analysis was not valid JSON: {
                            response.content}")
                    # Fallback: Try to extract info if it's just plain text
                    return {"ai_description": response.content, "ai_confidence": 0.4,
                            "ai_legal_significance": "AI analysis returned non-JSON content."}
            return None
        except Exception as e:
            logger.error(f"Error during AI pattern context analysis: {e}")
            return None

    async def _analyze_timeline_for_patterns(
            self, timeline_name: str, timeline_data: Dict[str, Any]) -> List[Pattern]:
        timeline_patterns: List[Pattern] = []
        events = timeline_data.get('events', [])
        if not events or len(events) < 2:
            return timeline_patterns

        event_type_counts = Counter(
            event['event_type'] for event in events if event.get('event_type'))

        for et, count in event_type_counts.items():
            if count >= 3:
                related_events = [
                    e for e in events if e.get('event_type') == et]
                try:
                    related_events.sort(
                        key=lambda x: datetime.fromisoformat(
                            x['date'].split(' ')[0].replace(
                                'Z', '')))  # Handle ISO dates robustly
                except (ValueError, TypeError, AttributeError) as e:
                    logger.warning(
                        f"Could not sort events by date for timeline pattern analysis due to date format issues: {e}. Events: {related_events[:2]}")
                    related_events.sort(key=lambda x: x.get('date', ''))

                avg_strength = sum(
                    e.get(
                        'evidence_strength',
                        0.5) for e in related_events) / len(related_events) if related_events else 0

                pattern = Pattern(
                    pattern_type="temporal",
                    title=f"Recurrence of '{et}' Events in {timeline_name}",
                    description=f"{count} events of type '{et}' found in timeline '{timeline_name}'. Average evidence strength of these events: {
                        avg_strength:.2f}.",
                    evidence_files=list(
                        set(
                            f for e_dict in related_events for f_list in [
                                e_dict.get(
                                    'source_files',
                                    []),
                                e_dict.get(
                                    'supporting_documents',
                                    [])] for f in f_list if f)),
                    # Combine and unique
                    confidence_score=min(
                        1.0,
                        0.6 +
                        count *
                        0.05 +
                        avg_strength *
                        0.1),
                    # Factor in avg_strength
                    legal_significance=f"Repeated occurrences of '{et}' (total {count}) may establish a consistent behavior pattern relevant to {timeline_name}.",
                    supporting_events=[{'event_title': e.get('title'), 'event_date': e.get(
                        'date'), 'description_snippet': e.get('description', '')[:100]} for e in related_events[:5]]
                )
                timeline_patterns.append(pattern)

        return timeline_patterns

    def _refine_and_correlate_patterns(self):
        merged_patterns: Dict[Tuple[str, str], Pattern] = {}
        for p in self.discovered_patterns:
            # Key for merging: type + title (could be more sophisticated, e.g.
            # root keywords)
            key = (p.pattern_type, p.title)
            if key not in merged_patterns:
                merged_patterns[key] = p
            else:
                existing_p = merged_patterns[key]
                existing_p.evidence_files.extend(p.evidence_files)
                existing_p.evidence_files = sorted(
                    list(set(existing_p.evidence_files)))

                existing_p.raw_matches.extend(p.raw_matches)
                # Deduplicate raw_matches if necessary, based on snippet & file
                # For now, just extend; could become very large.

                existing_p.supporting_events.extend(p.supporting_events)
                # Deduplicate supporting_events
                seen_events = set()
                unique_supporting_events = []
                for event_dict in existing_p.supporting_events:
                    event_tuple = tuple(sorted(event_dict.items()))
                    if event_tuple not in seen_events:
                        unique_supporting_events.append(event_dict)
                        seen_events.add(event_tuple)
                existing_p.supporting_events = unique_supporting_events

                # Recalculate confidence, e.g., average or max, or more complex
                # logic
                existing_p.confidence_score = max(
                    existing_p.confidence_score,
                    p.confidence_score)  # Or weighted average
                existing_p.description += f"\nAdditional evidence found in: {
                    ', '.join(
                        Path(ef).name for ef in p.evidence_files)}"
                existing_p.strength_indicators.extend(p.strength_indicators)
                existing_p.strength_indicators = sorted(
                    list(set(existing_p.strength_indicators)))

        self.discovered_patterns = list(merged_patterns.values())
        logger.info(
            f"Refined patterns. Count: {len(self.discovered_patterns)}")

    async def _synthesize_legal_theories(self):
        patterns_by_type = defaultdict(list)
        for p in self.discovered_patterns:
            patterns_by_type[p.pattern_type].append(p)

        # --- Rule-based Theory Synthesis ---
        # (Using a simplified version of the earlier logic for brevity, can be expanded)

        # Coercive Control / Domestic Abuse Theory
        abuse_pattern_count = len(patterns_by_type.get('abuse', []))
        control_pattern_count = len(patterns_by_type.get('control', []))
        if abuse_pattern_count >= 1 or control_pattern_count >= 1:  # Lowered threshold for suggestion
            # More specific: sum confidence of relevant patterns
            relevant_patterns_for_abuse_theory = patterns_by_type.get(
                'abuse', []) + patterns_by_type.get('control', [])
            if relevant_patterns_for_abuse_theory:
                supporting_pattern_ids = [
                    p.pattern_id for p in relevant_patterns_for_abuse_theory]
                avg_strength = sum(
                    p.confidence_score for p in relevant_patterns_for_abuse_theory) / len(relevant_patterns_for_abuse_theory)

                theory = LegalTheory(
                    theory_name="Potential Pattern of Coercive Control / Domestic Abuse",
                    description="Evidence suggests a potential pattern of coercive control and/or domestic abuse. This could involve emotional, financial, technological, or other forms of abuse and control. Such patterns can be highly relevant for restraining orders, child custody decisions, and equitable division of assets.",
                    supporting_patterns=supporting_pattern_ids,
                    evidence_strength=avg_strength,
                    required_evidence_elements=[
                        "Specific incidents of abusive/controlling behavior (dates, details)",
                        "Pattern of conduct (not isolated incidents)",
                        "Impact on the victim (fear, financial dependence, etc.)",
                        "Corroborating evidence (texts, emails, photos, witness statements if any)"],
                    strategic_value="Can significantly impact safety planning, custody arrangements, and financial settlements. May be grounds for specific legal remedies like a restraining order or findings of domestic violence which affect custody presumptions.",
                    implementation_steps=[
                        "Organize all supporting patterns and their raw evidence chronologically.",
                        "Draft a detailed declaration outlining each incident and the overall pattern of control/abuse.",
                        "Identify which elements of the legal definition of DV/coercive control are met by the evidence.",
                        "Consider if expert testimony (e.g., DV expert) would be beneficial if resources allow.",
                        "Consult legal aid or a domestic violence advocate for guidance on presenting this in court."]
                )
                self._add_theory(theory)

        # Financial Misconduct / Non-Disclosure Theory
        financial_pattern_count = len(patterns_by_type.get('financial', []))
        if financial_pattern_count >= 1:  # Lowered threshold
            relevant_patterns_for_financial_theory = patterns_by_type.get(
                'financial', [])
            if relevant_patterns_for_financial_theory:
                supporting_pattern_ids = [
                    p.pattern_id for p in relevant_patterns_for_financial_theory]
                avg_strength = sum(p.confidence_score for p in relevant_patterns_for_financial_theory) / len(
                    relevant_patterns_for_financial_theory)

                theory = LegalTheory(
                    theory_name="Potential Financial Misconduct or Non-Disclosure",
                    description="Patterns suggest potential financial misconduct, such as hiding assets, dissipating marital funds, or failing to disclose income/assets accurately. This is crucial for achieving a fair and equitable division of property and for accurate support calculations.",
                    supporting_patterns=supporting_pattern_ids,
                    evidence_strength=avg_strength,
                    required_evidence_elements=[
                        "Proof of undisclosed assets/income (bank statements, tax returns, business records)",
                        "Evidence of asset dissipation (unusual transactions, sales below value)",
                        "Discrepancies in financial declarations vs. actual financials",
                        "Timeline of suspicious financial activities"],
                    strategic_value="Can lead to sanctions for non-disclosure, an unequal division of assets in the wronged party's favor, imputation of income for support, and recovery of dissipated assets or their value.",
                    implementation_steps=[
                        "Issue formal discovery requests (subpoenas, interrogatories, requests for production) for all relevant financial records.",
                        "Carefully compare financial declarations with bank statements and other proof.",
                        "Consider if a forensic accountant is necessary (can be expensive, but powerful).",
                        "File motions to compel disclosure or for sanctions if non-compliance occurs.",
                        "Present clear evidence of discrepancies or hidden assets to the court."]
                )
                self._add_theory(theory)

        # Abuse of Legal Process / Fraud on the Court
        legal_process_patterns = patterns_by_type.get('legal_process', [])
        # Filter for more specific sub-patterns that indicate serious
        # misconduct
        relevant_fotc_patterns = [
            p for p in legal_process_patterns if
            any(
                term in p.title.lower() for term in [
                    'perjury',
                    'false_statements',
                    'evidence_tampering',
                    'procedural_misconduct',
                    'discovery_abuse'])
        ]
        if relevant_fotc_patterns:
            supporting_pattern_ids = [
                p.pattern_id for p in relevant_fotc_patterns]
            avg_strength = sum(p.confidence_score for p in relevant_fotc_patterns) / \
                len(relevant_fotc_patterns) if relevant_fotc_patterns else 0.0

            theory = LegalTheory(
                theory_name="Potential Abuse of Legal Process / Fraud on the Court",
                description="Evidence indicates possible abuse of the legal process or attempts to defraud the court. This could involve submitting false statements, hiding or tampering with evidence, or using litigation for harassment or delay.",
                supporting_patterns=supporting_pattern_ids,
                evidence_strength=avg_strength,
                required_evidence_elements=[
                    "Specific instances of false statements/filings with proof of falsity",
                    "Evidence of intent to deceive the court or harass the other party",
                    "Demonstrable harm or prejudice caused by the misconduct",
                    "Violation of court rules or orders"],
                strategic_value="If proven, can lead to severe sanctions (monetary, striking pleadings, adverse inferences), awards of attorney fees, and can heavily damage the offending party's credibility. In extreme cases, judgments can be set aside.",
                implementation_steps=[
                    "Meticulously document each instance of misconduct with clear, irrefutable proof (e.g., contradictory documents, proof of lies).",
                    "File appropriate motions with the court (e.g., motion for sanctions, motion to strike, request for evidentiary hearing).",
                    "Clearly highlight contradictions and falsehoods in all court filings and oral arguments.",
                    "Adhere strictly to procedural rules when presenting these claims."]
            )
            self._add_theory(theory)

        if self.ai_service and self.ai_service.config.enabled and self.discovered_patterns:
            await self._ai_synthesize_theories()

    async def _ai_synthesize_theories(self):
        if not self.ai_service or not self.ai_service.config.enabled or not self.discovered_patterns:
            return

        pattern_summary_for_ai = []
        for p in self.discovered_patterns[:20]:  # Limit for token count
            pattern_summary_for_ai.append({
                "id": p.pattern_id,
                "title": p.title,
                "type": p.pattern_type,
                # string for strict json
                "confidence": f"{p.confidence_score:.2f}",
                "description_snippet": p.description[:150]
            })

        prompt = f"""
        You are a legal strategy AI for family law cases. Given the following patterns discovered from evidence:
        {json.dumps(pattern_summary_for_ai, indent=2)}

        Please suggest potential legal theories or arguments. For each distinct theory:
        1.  "theory_name": A concise name (e.g., "Financial Non-Disclosure and Dissipation").
        2.  "description": A brief explanation of how the patterns support this theory.
        3.  "supporting_pattern_ids": A list of relevant pattern IDs from the input.
        4.  "evidence_strength": Your estimated strength for this theory (float 0.0-1.0) based on the provided patterns.
        5.  "required_evidence_elements": A list of key legal elements generally needed to prove such a theory in family court.
        6.  "strategic_value": Brief comment on why this theory is important.

        Focus on theories relevant to divorce, custody, domestic violence, and financial disputes.
        Prioritize theories with stronger support from multiple patterns or high-confidence patterns.
        Return ONLY a JSON array of theory objects. Do not include any explanatory text before or after the JSON array.
        Example of one theory object:
        {{
            "theory_name": "Coercive Control Affecting Custody",
            "description": "Patterns of emotional abuse and isolation tactics suggest a coercive control dynamic that could impact the children's best interests.",
            "supporting_pattern_ids": ["pattern_id_1", "pattern_id_3"],
            "evidence_strength": 0.75,
            "required_evidence_elements": ["Pattern of controlling behavior", "Specific incidents", "Impact on victim/children", "Chronology of control"],
            "strategic_value": "Crucial for child safety and determining appropriate custody/visitation."
        }}
        If no strong theories are apparent, return an empty array [].
        """
        try:
            response = await self.ai_service.provider.generate_completion(
                prompt,
                system_prompt="You are a legal strategy AI. Analyze patterns to suggest legal theories for family law cases. Respond ONLY with a valid JSON array of theory objects."
            )
            if response.success:
                content_to_parse = response.content.strip()
                # Check if response is wrapped in markdown json block
                if content_to_parse.startswith("```json"):
                    content_to_parse = content_to_parse[7:]
                    if content_to_parse.endswith("```"):
                        content_to_parse = content_to_parse[:-3]

                # Ensure it's an array
                if not content_to_parse.startswith(
                        "[") or not content_to_parse.endswith("]"):
                    logger.error(
                        f"AI theory synthesis response is not a JSON array: {content_to_parse}")
                    return  # Or attempt to wrap it if it's a single object.

                try:
                    ai_suggested_theories = json.loads(content_to_parse)
                    for suggested_theory_data in ai_suggested_theories:
                        if not isinstance(suggested_theory_data, dict):
                            logger.warning(
                                f"Skipping non-dict item in AI theories: {suggested_theory_data}")
                            continue
                        if 'theory_name' in suggested_theory_data and 'supporting_pattern_ids' in suggested_theory_data:
                            new_theory = LegalTheory(
                                theory_name=suggested_theory_data['theory_name'],
                                description=suggested_theory_data.get(
                                    'description', ''),
                                supporting_patterns=suggested_theory_data['supporting_pattern_ids'],
                                evidence_strength=float(
                                    suggested_theory_data.get(
                                        'evidence_strength', 0.5)),
                                required_evidence_elements=suggested_theory_data.get(
                                    'required_evidence_elements', []),
                                strategic_value=suggested_theory_data.get(
                                    'strategic_value', '')
                            )
                            if not any(t.theory_name.strip().lower() == new_theory.theory_name.strip(
                            ).lower() for t in self.potential_theories):  # Avoid duplicates
                                self._add_theory(new_theory)
                except json.JSONDecodeError as e:
                    logger.error(
                        f"AI response for theory synthesis was not valid JSON after stripping: {e}. Content: {content_to_parse}")
        except Exception as e:
            logger.error(f"Error during AI theory synthesis: {e}")

    def _add_pattern(self, pattern: Pattern):
        self.discovered_patterns.append(pattern)

    def _add_theory(self, theory: LegalTheory):
        self.potential_theories.append(theory)

    def save_discovery_report(self, output_dir_path_str: str):
        output_dir = Path(output_dir_path_str)
        # Use a more specific subdirectory for these reports
        report_dir = output_dir / "REPORTS_LCAS" / "PATTERN_DISCOVERY"
        report_dir.mkdir(parents=True, exist_ok=True)

        patterns_file = report_dir / "discovered_patterns_details.json"
        theories_file = report_dir / "potential_legal_theories_details.json"
        summary_report_file = report_dir / "pattern_discovery_summary.md"

        try:
            with open(patterns_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(p) for p in self.discovered_patterns],
                          f, indent=2, ensure_ascii=False)
            logger.info(f"Discovered patterns saved to {patterns_file}")

            with open(theories_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(t) for t in self.potential_theories],
                          f, indent=2, ensure_ascii=False)
            logger.info(f"Potential legal theories saved to {theories_file}")

            with open(summary_report_file, 'w', encoding='utf-8') as f:
                f.write(
                    f"# Pattern Discovery & Legal Theory Summary Report\n\n")
                f.write(
                    f"*Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                f.write(f"This report summarizes automatically discovered patterns from the provided evidence and suggests potential legal theories or arguments that might be developed.\n\n")

                f.write(
                    f"## Discovered Patterns Summary ({len(self.discovered_patterns)})\n\n")
                if not self.discovered_patterns:
                    f.write(
                        "No significant patterns were automatically discovered based on the current analysis.\n\n")
                else:
                    f.write(
                        "| Pattern Title                      | Type              | Confidence | Evidence Files (Count) | Key Significance                       |\n")
                    f.write(
                        "|------------------------------------|-------------------|------------|------------------------|----------------------------------------|\n")
                    for p in sorted(self.discovered_patterns, key=lambda x: x.confidence_score, reverse=True)[
                            :20]:  # Top 20
                        evidence_count = len(p.evidence_files)
                        f.write(
                            f"| {
                                p.title[
                                    :35]}{
                                '...' if len(
                                    p.title) > 35 else ''} | {
                                p.pattern_type:<17} | {
                                p.confidence_score:<10.2f} | {
                                evidence_count:<22} | {
                                    p.legal_significance[
                                        :38]}{
                                            '...' if len(
                                                p.legal_significance) > 38 else ''} |\n")
                    if len(self.discovered_patterns) > 20:
                        f.write(f"\n*... and {len(self.discovered_patterns) -
                                              20} more patterns. See discovered_patterns_details.json for full list.*\n")
                    f.write("\n**Note:** Refer to `discovered_patterns_details.json` for full details on each pattern, including raw matches and AI analysis if applicable.\n\n")

                f.write(
                    f"## Potential Legal Theories ({len(self.potential_theories)})\n\n")
                if not self.potential_theories:
                    f.write("No specific legal theories were automatically synthesized. This may indicate insufficient linked patterns or require manual review of discovered patterns to build arguments.\n\n")
                else:
                    f.write(
                        "| Theory Name                        | Evidence Strength | Supporting Patterns (Count) | Strategic Value Summary                |\n")
                    f.write(
                        "|------------------------------------|-------------------|---------------------------|----------------------------------------|\n")
                    for t in sorted(
                            self.potential_theories, key=lambda x: x.evidence_strength, reverse=True):
                        patterns_count = len(t.supporting_patterns)
                        f.write(
                            f"| {
                                t.theory_name[
                                    :35]}{
                                '...' if len(
                                    t.theory_name) > 35 else ''} | {
                                t.evidence_strength:<17.2f} | {
                                patterns_count:<25} | {
                                t.strategic_value[
                                    :38]}{
                                        '...' if len(
                                            t.strategic_value) > 38 else ''} |\n")
                    f.write("\n**Note:** Refer to `potential_legal_theories_details.json` for full details on each theory, including required evidence elements and implementation steps.\n\n")

                f.write("---\n\n**Disclaimer:** This is an automated analysis. All discovered patterns and suggested theories require careful manual review, verification, and consultation with legal counsel if possible. This tool is for assistance and does not constitute legal advice.\n")

            logger.info(
                f"Pattern discovery summary report saved to {summary_report_file}")

        except Exception as e:
            logger.error(
                f"Error saving pattern discovery report: {e}",
                exc_info=True)
