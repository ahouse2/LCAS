#!/usr/bin/env python3
"""
Timeline Builder Plugin for LCAS
Creates comprehensive timelines for legal arguments and case narrative
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import json

logger = logging.getLogger(__name__)

@dataclass
class TimelineEvent:
    """Represents a single event in the timeline"""
    date: str  # ISO format or best approximation
    date_confidence: float  # 0.0 to 1.0
    title: str
    description: str
    source_files: List[str]
    category: str  # Which legal argument this supports
    event_type: str  # communication, financial, legal, abuse, etc.
    participants: List[str]
    evidence_strength: float  # How strong this evidence is
    legal_significance: str
    supporting_documents: List[str]
    tags: List[str]

@dataclass
class Timeline:
    """Complete timeline for a legal argument"""
    argument_name: str
    timeline_id: str
    events: List[TimelineEvent]
    date_range: Tuple[str, str]  # Start and end dates
    total_events: int
    strength_score: float  # Overall timeline strength
    narrative_summary: str
    key_patterns: List[str]
    critical_periods: List[Dict[str, Any]]

class TimelineBuilderPlugin:
    """Plugin for building comprehensive legal timelines"""
    
    def __init__(self, config, ai_service=None):
        self.config = config
        self.ai_service = ai_service
        self.date_patterns = self._initialize_date_patterns()
        self.legal_argument_timelines = defaultdict(list)
    
    def _initialize_date_patterns(self) -> List[Dict[str, Any]]:
        """Initialize regex patterns for date extraction"""
        return [
            {
                'pattern': r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b',
                'format': 'MM/DD/YYYY',
                'confidence': 0.9
            },
            {
                'pattern': r'\b(\d{1,2})-(\d{1,2})-(\d{4})\b',
                'format': 'MM-DD-YYYY',
                'confidence': 0.9
            },
            {
                'pattern': r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b',
                'format': 'YYYY-MM-DD',
                'confidence': 0.95
            },
            {
                'pattern': r'\b([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})\b',
                'format': 'Month DD, YYYY',
                'confidence': 0.85
            },
            {
                'pattern': r'\b(\d{1,2})/(\d{1,2})/(\d{2})\b',
                'format': 'MM/DD/YY',
                'confidence': 0.7
            },
            {
                'pattern': r'\b(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})\b',
                'format': 'DD Month YYYY',
                'confidence': 0.8
            }
        ]
    
    async def build_timelines_for_case(self, processed_files: Dict[str, Any]) -> Dict[str, Timeline]:
        """Build comprehensive timelines for all legal arguments"""
        logger.info("Building case timelines...")
        
        # Extract all temporal events from files
        all_events = []
        for file_path, file_analysis in processed_files.items():
            events = await self._extract_events_from_file(file_path, file_analysis)
            all_events.extend(events)
        
        # Group events by legal argument
        argument_events = self._group_events_by_argument(all_events)
        
        # Build timeline for each argument
        timelines = {}
        for argument, events in argument_events.items():
            timeline = await self._build_argument_timeline(argument, events)
            timelines[argument] = timeline
        
        # Create master timeline
        timelines['MASTER_TIMELINE'] = await self._build_master_timeline(all_events)
        
        # Generate timeline visualizations
        await self._generate_timeline_visualizations(timelines)
        
        return timelines
    
    async def _extract_events_from_file(self, file_path: str, file_analysis: Dict[str, Any]) -> List[TimelineEvent]:
        """Extract timeline events from a single file"""
        events = []
        
        try:
            content = file_analysis.get('content', '')
            if not content:
                return events
            
            # Extract date mentions
            date_mentions = self._extract_dates_from_content(content)
            
            # Use AI to identify significant events
            if self.ai_service:
                ai_events = await self._ai_extract_timeline_events(content, file_analysis)
                events.extend(ai_events)
            
            # Extract events from specific patterns
            pattern_events = self._extract_pattern_based_events(content, file_analysis, date_mentions)
            events.extend(pattern_events)
            
            # Add file metadata as events if relevant
            metadata_events = self._extract_metadata_events(file_path, file_analysis)
            events.extend(metadata_events)
            
        except Exception as e:
            logger.error(f"Error extracting timeline events from {file_path}: {e}")
        
        return events
    
    def _extract_dates_from_content(self, content: str) -> List[Dict[str, Any]]:
        """Extract all date mentions from content"""
        date_mentions = []
        
        for pattern_info in self.date_patterns:
            pattern = pattern_info['pattern']
            matches = re.finditer(pattern, content, re.IGNORECASE)
            
            for match in matches:
                try:
                    date_str = match.group()
                    context_start = max(0, match.start() - 100)
                    context_end = min(len(content), match.end() + 100)
                    context = content[context_start:context_end]
                    
                    # Try to parse the date
                    parsed_date = self._parse_date(date_str, pattern_info['format'])
                    
                    if parsed_date:
                        date_mentions.append({
                            'raw_date': date_str,
                            'parsed_date': parsed_date,
                            'confidence': pattern_info['confidence'],
                            'context': context,
                            'position': match.start()
                        })
                        
                except Exception as e:
                    logger.debug(f"Error parsing date {match.group()}: {e}")
                    continue
        
        return date_mentions
    
    def _parse_date(self, date_str: str, format_hint: str) -> Optional[str]:
        """Parse date string into ISO format"""
        try:
            # Handle different formats
            if format_hint == 'MM/DD/YYYY':
                dt = datetime.strptime(date_str, '%m/%d/%Y')
            elif format_hint == 'MM-DD-YYYY':
                dt = datetime.strptime(date_str, '%m-%d-%Y')
            elif format_hint == 'YYYY-MM-DD':
                dt = datetime.strptime(date_str, '%Y-%m-%d')
            elif format_hint == 'MM/DD/YY':
                dt = datetime.strptime(date_str, '%m/%d/%y')
                # Handle 2-digit years
                if dt.year < 50:
                    dt = dt.replace(year=dt.year + 2000)
                elif dt.year < 100:
                    dt = dt.replace(year=dt.year + 1900)
            elif format_hint == 'Month DD, YYYY':
                dt = datetime.strptime(date_str, '%B %d, %Y')
            else:
                # Try various formats
                formats = ['%B %d, %Y', '%b %d, %Y', '%d %B %Y', '%d %b %Y']
                dt = None
                for fmt in formats:
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        break
                    except:
                        continue
                
                if not dt:
                    return None
            
            return dt.strftime('%Y-%m-%d')
            
        except Exception as e:
            logger.debug(f"Error parsing date {date_str}: {e}")
            return None
    
    async def _ai_extract_timeline_events(self, content: str, file_analysis: Dict[str, Any]) -> List[TimelineEvent]:
        """Use AI to extract timeline events from content"""
        if not self.ai_service:
            return []
        
        try:
            # Create AI prompt for timeline extraction
            prompt = f"""
Analyze this legal document and extract ALL chronological events that could be relevant in a divorce/family court case.

Document Category: {file_analysis.get('category', 'Unknown')}
Document Content: {content[:3000]}

For each event you identify, consider:
1. What happened (action, communication, incident, etc.)
2. When it happened (exact date/time if available, or approximate)
3. Who was involved
4. Why it's legally significant (abuse, financial misconduct, custody issues, etc.)
5. How strong this evidence is

Focus on events that show patterns of:
- Abuse, coercion, control
- Financial hiding or misconduct  
- Parental fitness issues
- Violations of agreements or court orders
- Communication patterns showing intent or state of mind

Extract events even if dates are approximate or contextual (like "last week" or "after the hearing").

Return as JSON array with this format:
[{{
  "date": "YYYY-MM-DD or approximate",
  "date_confidence": 0.0-1.0,
  "title": "Brief event title",
  "description": "Detailed description",
  "event_type": "abuse|financial|custody|legal|communication",
  "participants": ["person1", "person2"],
  "legal_significance": "Why this matters legally",
  "evidence_strength": 0.0-1.0
}}]
"""
            
            response = await self.ai_service.provider.generate_completion(
                prompt,
                "You are an expert legal timeline analyst specializing in family court cases."
            )
            
            if response.success:
                try:
                    events_data = json.loads(response.content)
                    events = []
                    
                    for event_data in events_data:
                        event = TimelineEvent(
                            date=event_data.get('date', ''),
                            date_confidence=event_data.get('date_confidence', 0.5),
                            title=event_data.get('title', ''),
                            description=event_data.get('description', ''),
                            source_files=[file_analysis.get('original_path', '')],
                            category=file_analysis.get('category', ''),
                            event_type=event_data.get('event_type', 'unknown'),
                            participants=event_data.get('participants', []),
                            evidence_strength=event_data.get('evidence_strength', 0.5),
                            legal_significance=event_data.get('legal_significance', ''),
                            supporting_documents=[file_analysis.get('original_name', '')],
                            tags=[]
                        )
                        events.append(event)
                    
                    return events
                    
                except json.JSONDecodeError:
                    logger.warning("AI returned invalid JSON for timeline extraction")
                    return []
            
        except Exception as e:
            logger.error(f"AI timeline extraction failed: {e}")
        
        return []
    
    def _extract_pattern_based_events(self, content: str, file_analysis: Dict[str, Any], date_mentions: List[Dict[str, Any]]) -> List[TimelineEvent]:
        """Extract events based on known patterns and keywords"""
        events = []
        
        # Define event patterns
        event_patterns = {
            'abuse': [
                r'(threatened|intimidated|scared|hit|pushed|grabbed|hurt)',
                r'(called me|said I was|told me I)',
                r'(wouldn\'t let me|prevented me|stopped me)'
            ],
            'financial': [
                r'(transferred|withdrew|deposited|spent|hid|moved)\s+\$?\d+',
                r'(opened|closed|emptied)\s+(account|investment)',
                r'(cryptocurrency|bitcoin|coinbase|trading)'
            ],
            'custody': [
                r'(pick up|drop off|visitation|custody|parenting time)',
                r'(school|doctor|emergency|sick)',
                r'(wouldn\'t return|kept|took)\s+(kids|children)'
            ],
            'legal': [
                r'(filed|served|court|hearing|judge|attorney)',
                r'(motion|petition|order|subpoena|discovery)',
                r'(violation|contempt|compliance)'
            ],
            'communication': [
                r'(text|email|call|message|voicemail)',
                r'(sent|received|replied|forwarded)',
                r'(blocked|deleted|screenshot)'
            ]
        }
        
        # Look for events around each date mention
        for date_info in date_mentions:
            context = date_info['context'].lower()
            
            for event_type, patterns in event_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, context, re.IGNORECASE):
                        # Extract more context around the match
                        event_context = self._extract_event_context(content, date_info['position'])
                        
                        event = TimelineEvent(
                            date=date_info['parsed_date'],
                            date_confidence=date_info['confidence'],
                            title=f"{event_type.title()} Event",
                            description=event_context,
                            source_files=[file_analysis.get('original_path', '')],
                            category=file_analysis.get('category', ''),
                            event_type=event_type,
                            participants=self._extract_participants(event_context),
                            evidence_strength=self._calculate_evidence_strength(event_context, event_type),
                            legal_significance=f"Evidence of {event_type} behavior/activity",
                            supporting_documents=[file_analysis.get('original_name', '')],
                            tags=[event_type, 'pattern-detected']
                        )
                        events.append(event)
                        break
        
        return events
    
    def _extract_metadata_events(self, file_path: str, file_analysis: Dict[str, Any]) -> List[TimelineEvent]:
        """Extract events from file metadata"""
        events = []
        
        try:
            # File creation event
            if file_analysis.get('created_date'):
                created_event = TimelineEvent(
                    date=file_analysis['created_date'].strftime('%Y-%m-%d'),
                    date_confidence=0.9,
                    title=f"Document Created: {file_analysis.get('original_name', '')}",
                    description=f"File created: {file_analysis.get('file_type', 'Unknown')} document",
                    source_files=[file_path],
                    category=file_analysis.get('category', ''),
                    event_type='document',
                    participants=[],
                    evidence_strength=0.3,
                    legal_significance="Document creation timestamp",
                    supporting_documents=[file_analysis.get('original_name', '')],
                    tags=['metadata', 'document-creation']
                )
                events.append(created_event)
            
            # File modification event
            if file_analysis.get('modified_date') and file_analysis.get('created_date'):
                if file_analysis['modified_date'] != file_analysis['created_date']:
                    modified_event = TimelineEvent(
                        date=file_analysis['modified_date'].strftime('%Y-%m-%d'),
                        date_confidence=0.9,
                        title=f"Document Modified: {file_analysis.get('original_name', '')}",
                        description=f"File last modified: {file_analysis.get('file_type', 'Unknown')} document",
                        source_files=[file_path],
                        category=file_analysis.get('category', ''),
                        event_type='document',
                        participants=[],
                        evidence_strength=0.4,
                        legal_significance="Document modification timestamp - may indicate tampering or updates",
                        supporting_documents=[file_analysis.get('original_name', '')],
                        tags=['metadata', 'document-modification']
                    )
                    events.append(modified_event)
                    
        except Exception as e:
            logger.error(f"Error extracting metadata events from {file_path}: {e}")
        
        return events
    
    def _extract_event_context(self, content: str, position: int, context_size: int = 200) -> str:
        """Extract context around a specific position in content"""
        start = max(0, position - context_size)
        end = min(len(content), position + context_size)
        return content[start:end].strip()
    
    def _extract_participants(self, text: str) -> List[str]:
        """Extract participant names from text"""
        participants = []
        
        # Common name patterns in legal documents
        name_patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # First Last
            r'\b(Mr|Mrs|Ms|Dr)\.?\s+[A-Z][a-z]+\b',  # Title Name
            r'\b(plaintiff|defendant|petitioner|respondent)\b'  # Legal roles
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            participants.extend([match.strip() for match in matches if match.strip()])
        
        # Remove duplicates and common words
        common_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'by'}
        participants = list(set([p for p in participants if p.lower() not in common_words]))
        
        return participants[:5]  # Limit to 5 participants
    
    def _calculate_evidence_strength(self, context: str, event_type: str) -> float:
        """Calculate evidence strength based on context and type"""
        strength = 0.5  # Base strength
        
        # Increase strength for specific indicators
        strength_indicators = {
            'abuse': ['police', 'hospital', 'injury', 'threat', 'fear'],
            'financial': ['bank', 'account', 'transfer', 'amount', 'receipt'],
            'custody': ['school', 'pickup', 'overnight', 'parenting'],
            'legal': ['court', 'filed', 'served', 'order', 'hearing'],
            'communication': ['screenshot', 'forwarded', 'timestamp', 'sender']
        }
        
        if event_type in strength_indicators:
            for indicator in strength_indicators[event_type]:
                if indicator in context.lower():
                    strength += 0.1
        
        # Decrease strength for uncertainty words
        uncertainty_words = ['maybe', 'might', 'could', 'possibly', 'perhaps']
        for word in uncertainty_words:
            if word in context.lower():
                strength -= 0.1
        
        return max(0.1, min(1.0, strength))
    
    def _group_events_by_argument(self, events: List[TimelineEvent]) -> Dict[str, List[TimelineEvent]]:
        """Group events by legal argument category"""
        argument_events = defaultdict(list)
        
        for event in events:
            # Map to primary legal arguments
            category = event.category
            if 'FRAUD_ON_THE_COURT' in category:
                argument_events['Fraud on the Court'].append(event)
            elif 'CONSTITUTIONAL_VIOLATIONS' in category:
                argument_events['Constitutional Violations'].append(event)
            elif 'ELECTRONIC_ABUSE' in category:
                argument_events['Electronic Abuse'].append(event)
            elif 'NON_DISCLOSURE' in category:
                argument_events['Financial Non-Disclosure'].append(event)
            elif 'TEXT_MESSAGES' in category:
                argument_events['Communications Evidence'].append(event)
            elif 'POST_TRIAL_ABUSE' in category:
                argument_events['Post-Trial Violations'].append(event)
            else:
                argument_events['General Evidence'].append(event)
        
        return dict(argument_events)
    
    async def _build_argument_timeline(self, argument_name: str, events: List[TimelineEvent]) -> Timeline:
        """Build a comprehensive timeline for a specific legal argument"""
        if not events:
            return Timeline(
                argument_name=argument_name,
                timeline_id=f"timeline_{argument_name.lower().replace(' ', '_')}",
                events=[],
                date_range=('', ''),
                total_events=0,
                strength_score=0.0,
                narrative_summary="No events found for this argument.",
                key_patterns=[],
                critical_periods=[]
            )
        
        # Sort events by date
        sorted_events = sorted(events, key=lambda e: e.date if e.date else '9999-12-31')
        
        # Calculate date range
        valid_dates = [e.date for e in sorted_events if e.date and e.date != '9999-12-31']
        date_range = (valid_dates[0], valid_dates[-1]) if valid_dates else ('', '')
        
        # Calculate overall strength
        strength_score = sum(e.evidence_strength for e in events) / len(events)
        
        # Generate narrative summary using AI
        narrative_summary = await self._generate_timeline_narrative(argument_name, sorted_events)
        
        # Identify key patterns
        key_patterns = self._identify_timeline_patterns(sorted_events)
        
        # Identify critical periods
        critical_periods = self._identify_critical_periods(sorted_events)
        
        return Timeline(
            argument_name=argument_name,
            timeline_id=f"timeline_{argument_name.lower().replace(' ', '_')}",
            events=sorted_events,
            date_range=date_range,
            total_events=len(events),
            strength_score=strength_score,
            narrative_summary=narrative_summary,
            key_patterns=key_patterns,
            critical_periods=critical_periods
        )
    
    async def _build_master_timeline(self, all_events: List[TimelineEvent]) -> Timeline:
        """Build master timeline combining all events"""
        return await self._build_argument_timeline("Master Timeline", all_events)
    
    async def _generate_timeline_narrative(self, argument_name: str, events: List[TimelineEvent]) -> str:
        """Generate AI-powered narrative summary of timeline"""
        if not self.ai_service or not events:
            return f"Timeline for {argument_name} contains {len(events)} events."
        
        try:
            # Prepare events summary for AI
            events_summary = []
            for event in events[:20]:  # Limit to prevent token overflow
                events_summary.append({
                    'date': event.date,
                    'title': event.title,
                    'type': event.event_type,
                    'significance': event.legal_significance
                })
            
            prompt = f"""
Create a coherent narrative summary for this legal timeline:

Argument: {argument_name}
Events: {json.dumps(events_summary, indent=2)}

Write a compelling narrative that:
1. Shows the progression of events over time
2. Highlights patterns of behavior
3. Connects events to legal significance
4. Identifies escalation or changes in behavior
5. Emphasizes the strongest evidence

Focus on how this timeline supports the legal argument. Write in a clear, factual tone suitable for legal proceedings.
Maximum 3 paragraphs.
"""
            
            response = await self.ai_service.provider.generate_completion(
                prompt,
                "You are a legal analyst specializing in case narrative development."
            )
            
            if response.success:
                return response.content.strip()
                
        except Exception as e:
            logger.error(f"Error generating timeline narrative: {e}")
        
        return f"Timeline for {argument_name} spans {len(events)} events from {events[0].date if events else 'unknown'} to {events[-1].date if events else 'unknown'}."
    
    def _identify_timeline_patterns(self, events: List[TimelineEvent]) -> List[str]:
        """Identify patterns in the timeline"""
        patterns = []
        
        if not events:
            return patterns
        
        # Frequency patterns
        event_types = [e.event_type for e in events]
        type_counts = {t: event_types.count(t) for t in set(event_types)}
        
        for event_type, count in type_counts.items():
            if count >= 3:
                patterns.append(f"Repeated {event_type} events ({count} occurrences)")
        
        # Escalation patterns
        abuse_events = [e for e in events if e.event_type == 'abuse']
        if len(abuse_events) >= 2:
            strength_trend = [e.evidence_strength for e in abuse_events]
            if strength_trend[-1] > strength_trend[0]:
                patterns.append("Escalating pattern of abuse over time")
        
        # Temporal clustering
        dates = [e.date for e in events if e.date]
        if len(dates) >= 3:
            date_objects = []
            for date_str in dates:
                try:
                    date_objects.append(datetime.strptime(date_str, '%Y-%m-%d'))
                except:
                    continue
            
            if len(date_objects) >= 3:
                # Look for clusters of activity
                clusters = self._find_date_clusters(date_objects)
                for cluster in clusters:
                    if len(cluster) >= 3:
                        patterns.append(f"Cluster of {len(cluster)} events around {cluster[0].strftime('%B %Y')}")
        
        return patterns
    
    def _find_date_clusters(self, dates: List[datetime], max_gap_days: int = 30) -> List[List[datetime]]:
        """Find clusters of dates within a specified gap"""
        if not dates:
            return []
        
        sorted_dates = sorted(dates)
        clusters = []
        current_cluster = [sorted_dates[0]]
        
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i-1]).days <= max_gap_days:
                current_cluster.append(sorted_dates[i])
            else:
                if len(current_cluster) >= 2:
                    clusters.append(current_cluster)
                current_cluster = [sorted_dates[i]]
        
        if len(current_cluster) >= 2:
            clusters.append(current_cluster)
        
        return clusters
    
    def _identify_critical_periods(self, events: List[TimelineEvent]) -> List[Dict[str, Any]]:
        """Identify critical periods in the timeline"""
        critical_periods = []
        
        if not events:
            return critical_periods
        
        # Group events by month
        monthly_events = defaultdict(list)
        for event in events:
            if event.date:
                try:
                    date_obj = datetime.strptime(event.date, '%Y-%m-%d')
                    month_key = date_obj.strftime('%Y-%m')
                    monthly_events[month_key].append(event)
                except:
                    continue
        
        # Identify months with high activity or high-strength events
        for month, month_events in monthly_events.items():
            if len(month_events) >= 3:  # High activity
                avg_strength = sum(e.evidence_strength for e in month_events) / len(month_events)
                critical_periods.append({
                    'period': month,
                    'event_count': len(month_events),
                    'average_strength': avg_strength,
                    'reason': 'High activity period',
                    'events': [e.title for e in month_events]
                })
            elif any(e.evidence_strength >= 0.8 for e in month_events):  # High strength events
                critical_periods.append({
                    'period': month,
                    'event_count': len(month_events),
                    'average_strength': sum(e.evidence_strength for e in month_events) / len(month_events),
                    'reason': 'High-strength evidence period',
                    'events': [e.title for e in month_events if e.evidence_strength >= 0.8]
                })
        
        return critical_periods
    
    async def _generate_timeline_visualizations(self, timelines: Dict[str, Timeline]) -> None:
        """Generate visual representations of timelines"""
        try:
            # Create timeline visualization data
            viz_data = {}
            
            for timeline_name, timeline in timelines.items():
                if not timeline.events:
                    continue
                
                # Prepare data for visualization
                viz_events = []
                for event in timeline.events:
                    if event.date:
                        viz_events.append({
                            'date': event.date,
                            'title': event.title,
                            'type': event.event_type,
                            'strength': event.evidence_strength,
                            'description': event.description[:100] + '...' if len(event.description) > 100 else event.description
                        })
                
                viz_data[timeline_name] = {
                    'events': viz_events,
                    'date_range': timeline.date_range,
                    'strength_score': timeline.strength_score,
                    'patterns': timeline.key_patterns,
                    'critical_periods': timeline.critical_periods
                }
            
            # Save visualization data
            viz_file = Path(self.config.target_directory) / "10_VISUALIZATIONS_AND_REPORTS" / "timeline_data.json"
            viz_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(viz_file, 'w', encoding='utf-8') as f:
                json.dump(viz_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Timeline visualization data saved to {viz_file}")
            
        except Exception as e:
            logger.error(f"Error generating timeline visualizations: {e}")
    
    def save_timelines(self, timelines: Dict[str, Timeline], output_dir: Path) -> None:
        """Save timelines to files"""
        timeline_dir = output_dir / "TIMELINES"
        timeline_dir.mkdir(parents=True, exist_ok=True)
        
        for timeline_name, timeline in timelines.items():
            # Save detailed timeline
            timeline_file = timeline_dir / f"{timeline.timeline_id}.json"
            with open(timeline_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(timeline), f, indent=2, ensure_ascii=False, default=str)
            
            # Save human-readable timeline
            readable_file = timeline_dir / f"{timeline.timeline_id}_readable.md"
            with open(readable_file, 'w', encoding='utf-8') as f:
                f.write(f"# {timeline.argument_name}\n\n")
                f.write(f"**Date Range:** {timeline.date_range[0]} to {timeline.date_range[1]}\n")
                f.write(f"**Total Events:** {timeline.total_events}\n")
                f.write(f"**Strength Score:** {timeline.strength_score:.2f}\n\n")
                
                f.write("## Narrative Summary\n\n")
                f.write(timeline.narrative_summary + "\n\n")
                
                if timeline.key_patterns:
                    f.write("## Key Patterns\n\n")
                    for pattern in timeline.key_patterns:
                        f.write(f"- {pattern}\n")
                    f.write("\n")
                
                if timeline.critical_periods:
                    f.write("## Critical Periods\n\n")
                    for period in timeline.critical_periods:
                        f.write(f"### {period['period']}\n")
                        f.write(f"- **Event Count:** {period['event_count']}\n")
                        f.write(f"- **Average Strength:** {period['average_strength']:.2f}\n")
                        f.write(f"- **Reason:** {period['reason']}\n\n")
                
                f.write("## Timeline Events\n\n")
                for event in timeline.events:
                    f.write(f"### {event.date} - {event.title}\n")
                    f.write(f"**Type:** {event.event_type}\n")
                    f.write(f"**Strength:** {event.evidence_strength:.2f}\n")
                    f.write(f"**Description:** {event.description}\n")
                    f.write(f"**Legal Significance:** {event.legal_significance}\n")
                    if event.participants:
                        f.write(f"**Participants:** {', '.join(event.participants)}\n")
                    f.write("\n")
        
        logger.info(f"Timelines saved to {timeline_dir}")

# Integration with main LCAS system
class TimelineIntegration:
    """Integrates timeline building into the main LCAS workflow"""
    
    def __init__(self, config, ai_service=None):
        self.timeline_builder = TimelineBuilderPlugin(config, ai_service)
    
    async def process_timelines(self, processed_files: Dict[str, Any], output_dir: Path) -> Dict[str, Timeline]:
        """Process timelines as part of main LCAS workflow"""
        logger.info("Building comprehensive case timelines...")
        
        # Build timelines
        timelines = await self.timeline_builder.build_timelines_for_case(processed_files)
        
        # Save timelines
        self.timeline_builder.save_timelines(timelines, output_dir)
        
        # Generate summary report
        self._generate_timeline_summary_report(timelines, output_dir)
        
        return timelines
    
    def _generate_timeline_summary_report(self, timelines: Dict[str, Timeline], output_dir: Path) -> None:
        """Generate summary report of all timelines"""
        reports_dir = output_dir / "10_VISUALIZATIONS_AND_REPORTS"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = reports_dir / "timeline_summary_report.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# Timeline Analysis Summary Report\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Overview\n\n")
            total_events = sum(t.total_events for t in timelines.values())
            f.write(f"- **Total Timelines:** {len(timelines)}\n")
            f.write(f"- **Total Events:** {total_events}\n")
            f.write(f"- **Average Timeline Strength:** {sum(t.strength_score for t in timelines.values()) / len(timelines):.2f}\n\n")
            
            f.write("## Timeline Summaries\n\n")
            for timeline_name, timeline in timelines.items():
                f.write(f"### {timeline_name}\n")
                f.write(f"- **Events:** {timeline.total_events}\n")
                f.write(f"- **Date Range:** {timeline.date_range[0]} to {timeline.date_range[1]}\n")
                f.write(f"- **Strength Score:** {timeline.strength_score:.2f}\n")
                f.write(f"- **Key Patterns:** {len(timeline.key_patterns)}\n")
                f.write(f"- **Critical Periods:** {len(timeline.critical_periods)}\n\n")
                
                if timeline.narrative_summary:
                    f.write(f"**Summary:** {timeline.narrative_summary[:200]}...\n\n")
        
        logger.info(f"Timeline summary report saved to {report_file}")
