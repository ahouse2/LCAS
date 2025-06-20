#!/usr/bin/env python3
"""
Enhanced LCAS AI Foundation Plugin - Production Ready
Includes rate limiting, user configurability, and generalized legal analysis
"""

import os
import json
import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Any, Optional, Union, Callable
from pathlib import Path
import time
from datetime import datetime

# Core dependencies with better error handling
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import requests
    import httpx
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class AIConfigSettings:
    """User-configurable AI settings"""
    # Provider preferences
    preferred_provider: str = "openai"  # openai, anthropic, local
    fallback_providers: List[str] = field(default_factory=lambda: ["anthropic", "local"])
    
    # Analysis depth and quality
    analysis_depth: str = "standard"  # basic, standard, comprehensive
    confidence_threshold: float = 0.6
    enable_multi_agent: bool = True
    enable_cross_validation: bool = False  # Multiple agents validate findings
    
    # Legal analysis customization
    case_type: str = "general"  # general, family_law, personal_injury, business, etc.
    jurisdiction: str = "US_Federal"  # US_Federal, California, NewYork, etc.
    legal_standards: List[str] = field(default_factory=list)  # Custom legal standards to apply
    
    # Processing options
    max_content_length: int = 50000  # characters
    batch_processing: bool = True
    parallel_agents: bool = True
    cache_results: bool = True
    
    # Output customization
    include_citations: bool = True
    generate_summaries: bool = True
    legal_memo_format: bool = False
    confidence_explanations: bool = True

@dataclass
class LegalPromptTemplates:
    """Customizable legal analysis prompt templates"""
    case_type: str = "general"
    
    def get_document_analysis_prompt(self, case_context: Dict[str, Any] = None) -> str:
        """Get document analysis prompt based on case type"""
        base_prompt = f"""You are a legal document analysis expert specializing in {self.case_type} cases."

Your task is to analyze legal documents and extract key information for evidence organization.

Case Context: {json.dumps(case_context or {}, indent=2)}

For each document, provide a JSON response with:
{{
  "document_type": "string - type of document",
  "key_parties": ["list of people/entities mentioned"],
  "important_dates": ["list of significant dates"],
  "financial_amounts": ["list of monetary amounts"],
  "legal_significance": "explanation of legal relevance",
  "evidence_category": "suggested category for organization",
  "key_facts": ["list of important factual assertions"],
  "potential_issues": ["list of potential legal issues or concerns"],
  "authentication_needs": ["what's needed to authenticate this document"],
  "probative_value": 0.0-1.0,
  "relevance_score": 0.0-1.0,
  "confidence": 0.0-1.0,
  "summary": "concise summary of document contents",
  "case_specific_insights": ["insights specific to this case type and context"]
}}

Focus on {self._get_case_specific_focus()}.
"""
        return base_prompt
    
    def get_legal_analysis_prompt(self, case_context: Dict[str, Any] = None) -> str:
        """Get legal analysis prompt based on case type and jurisdiction"""
        jurisdiction_rules = self._get_jurisdiction_specific_rules(case_context)
        
        prompt = f"""You are a legal analysis expert specializing in {self.case_type} with expertise in {jurisdiction_rules.get('jurisdiction', 'general')} law."

Your task is to evaluate evidence for legal proceedings.

Case Context: {json.dumps(case_context or {}, indent=2)}

Applicable Legal Standards:
{self._format_legal_standards(jurisdiction_rules)}

For each piece of evidence, provide:
{{
  "admissibility_analysis": "detailed analysis under applicable evidence rules",
  "probative_value": 0.0-1.0,
  "prejudicial_impact": 0.0-1.0,
  "authentication_requirements": ["what's needed to authenticate"],
  "foundation_elements": ["required foundation elements"],
  "hearsay_analysis": "hearsay concerns and exceptions if applicable",
  "relevance_analysis": "relevance under applicable legal standards",
  "strategic_value": "high|medium|low with explanation",
  "legal_theory_support": {{"theory_name": relevance_score}},
  "recommended_use": "strategic recommendations for using this evidence",
  "potential_objections": ["likely opposing objections"],
  "counter_arguments": ["how to address potential objections"],
  "confidence": 0.0-1.0,
  "case_specific_analysis": "analysis specific to this case type and context"
}}

Apply {self.case_type} legal standards and consider {jurisdiction_rules.get('jurisdiction', 'general')} procedural rules.
"""
        return prompt
    
    def get_pattern_discovery_prompt(self, case_context: Dict[str, Any] = None) -> str:
        """Get pattern discovery prompt based on case type"""
        pattern_types = self._get_case_specific_patterns()
        
        prompt = f"""You are a pattern discovery expert specializing in {self.case_type} cases."

Your task is to identify patterns, inconsistencies, and connections across evidence.

Case Context: {json.dumps(case_context or {}, indent=2)}

Look for these {self.case_type}-specific patterns:
{self._format_pattern_types(pattern_types)}

For pattern analysis, provide:
{{
  "patterns_detected": [
    {{
      "pattern_type": "string",
      "description": "detailed description",
      "supporting_evidence": ["list of supporting evidence"],
      "strength": 0.0-1.0,
      "legal_significance": "why this pattern matters legally"
    }}
  ],
  "timeline_analysis": "chronological pattern analysis",
  "inconsistencies_found": ["list of contradictions or inconsistencies"],
  "relationship_mapping": {{"entity1": ["related_entities"]}},
  "behavioral_indicators": ["concerning behavior patterns"],
  "escalation_patterns": "evidence of escalation or progression",
  "corroborating_evidence": ["evidence that supports the patterns"],
  "missing_evidence": ["what additional evidence would strengthen patterns"],
  "strategic_implications": "how these patterns impact legal strategy",
  "confidence": 0.0-1.0,
  "case_specific_patterns": "patterns specific to this case type"
}}

Focus on patterns that are legally significant for {self.case_type} cases.
"""
        return prompt
    
    def _get_case_specific_focus(self) -> str:
        """Get focus areas based on case type"""
        focus_map = {
            "family_law": "financial disclosure, child welfare, domestic relations, asset division, custody factors",
            "personal_injury": "causation, damages, liability, medical records, accident reconstruction",
            "business": "contract performance, breach analysis, financial damages, corporate governance", 
            "criminal": "constitutional violations, evidence admissibility, witness credibility, procedural compliance",
            "employment": "discrimination patterns, workplace policies, performance records, wage compliance",
            "general": "legal relevance, factual accuracy, evidentiary value, procedural compliance"
        }
        return focus_map.get(self.case_type, focus_map["general"])
    
    def _get_jurisdiction_specific_rules(self, case_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get jurisdiction-specific legal rules"""
        jurisdiction = case_context.get('jurisdiction', 'US_Federal') if case_context else 'US_Federal'
        
        rules_map = {
            "US_Federal": {
                "jurisdiction": "Federal",
                "evidence_rules": "Federal Rules of Evidence",
                "key_rules": ["Rule 401 (Relevance)", "Rule 403 (Prejudice vs Probative)", "Rule 702 (Expert Testimony)"]
            },
            "California": {
                "jurisdiction": "California",
                "evidence_rules": "California Evidence Code",
                "key_rules": ["Section 210 (Relevance)", "Section 352 (Prejudice vs Probative)", "Family Code 2107/2122 (Financial Disclosure)"]
            },
            "NewYork": {
                "jurisdiction": "New York", 
                "evidence_rules": "New York Rules of Evidence",
                "key_rules": ["Rule 4.01 (Relevance)", "Rule 4.03 (Prejudice vs Probative)"]
            }
        }
        
        return rules_map.get(jurisdiction, rules_map["US_Federal"])
    
    def _format_legal_standards(self, jurisdiction_rules: Dict[str, Any]) -> str:
        """Format legal standards for prompt"""
        standards = []
        for rule in jurisdiction_rules.get("key_rules", []):
            standards.append(f"- {rule}")
        return "\n".join(standards)
    
    def _get_case_specific_patterns(self) -> List[Dict[str, Any]]:
        """Get pattern types specific to case type"""
        pattern_map = {
            "family_law": [
                {"type": "financial_concealment", "indicators": ["hidden accounts", "crypto transactions", "unreported income"]},
                {"type": "abuse_escalation", "indicators": ["increasing frequency", "severity progression", "isolation tactics"]},
                {"type": "parental_alienation", "indicators": ["child coaching", "access interference", "negative messaging"]}
            ],
            "personal_injury": [
                {"type": "causation_chain", "indicators": ["temporal relationship", "medical progression", "activity limitations"]},
                {"type": "pre_existing_conditions", "indicators": ["prior treatment", "similar symptoms", "medical history"]}
            ],
            "business": [
                {"type": "breach_patterns", "indicators": ["performance failures", "timing issues", "communication gaps"]},
                {"type": "financial_irregularities", "indicators": ["unusual transactions", "accounting discrepancies", "cash flow issues"]}
            ],
            "general": [
                {"type": "credibility_issues", "indicators": ["inconsistent statements", "contradictory evidence", "timing problems"]},
                {"type": "procedural_violations", "indicators": ["missed deadlines", "improper service", "discovery abuse"]}
            ]
        }
        
        return pattern_map.get(self.case_type, pattern_map["general"])
    
    def _format_pattern_types(self, pattern_types: List[Dict[str, Any]]) -> str:
        """Format pattern types for prompt"""
        formatted = []
        for pattern in pattern_types:
            indicators = ", ".join(pattern["indicators"])
            formatted.append(f"- {pattern['type']}: {indicators}")
        return "\n".join(formatted)

class EnhancedAIRateLimiter:
    """Advanced rate limiting with dynamic adjustment and graceful degradation"""
    
    def __init__(self, config):
        self.config = config
        self.request_history = []
        self.token_history = []
        self.cost_history = []
        self.error_history = []
        
        # Dynamic rate adjustment
        self.current_rate_multiplier = 1.0
        self.consecutive_errors = 0
        self.last_error_time = 0
        
        # Graceful degradation settings
        self.degradation_mode = False
        self.degraded_until = 0
        
        # Usage tracking
        self.session_stats = {
            'total_requests': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
            'errors': 0,
            'rate_limit_hits': 0
        }
    
    async def check_and_wait_if_needed(self) -> bool:
        """Check rate limits and wait if necessary, return False if should skip AI"""
        now = time.time()
        
        # Clean old history
        self._clean_old_records(now)
        
        # Check if in degradation mode
        if self.degradation_mode and now < self.degraded_until:
            if self.config.pause_on_limit:
                wait_time = self.degraded_until - now
                logger.info(f"AI in degradation mode, waiting {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)
                self.degradation_mode = False
            else:
                logger.info("AI disabled due to rate limits")
                return False
        
        # Calculate current limits with dynamic adjustment
        effective_rpm = int(self.config.max_requests_per_minute * self.current_rate_multiplier)
        effective_tph = int(self.config.max_tokens_per_hour * self.current_rate_multiplier)
        effective_cph = self.config.max_cost_per_hour * self.current_rate_multiplier
        
        # Check request rate
        recent_requests = len([r for r in self.request_history if now - r < 60])
        if recent_requests >= effective_rpm:
            await self._handle_rate_limit("requests per minute", 60)
            return False
        
        # Check token usage
        recent_tokens = sum(t['tokens'] for t in self.token_history if now - t['timestamp'] < 3600)
        if recent_tokens >= effective_tph:
            await self._handle_rate_limit("tokens per hour", 3600)
            return False
        
        # Check cost usage
        recent_cost = sum(c['cost'] for c in self.cost_history if now - c['timestamp'] < 3600)
        if recent_cost >= effective_cph:
            await self._handle_rate_limit("cost per hour", 3600)
            return False
        
        return True
    
    async def record_request(self, tokens_used: int, cost: float, success: bool = True):
        """Record API usage and adjust rates dynamically"""
        now = time.time()
        
        # Record usage
        self.request_history.append(now)
        self.token_history.append({'timestamp': now, 'tokens': tokens_used})
        self.cost_history.append({'timestamp': now, 'cost': cost})
        
        # Update session stats
        self.session_stats['total_requests'] += 1
        self.session_stats['total_tokens'] += tokens_used
        self.session_stats['total_cost'] += cost
        
        if success:
            # Success - gradually increase rate if we've been conservative'
            self.consecutive_errors = 0
            if self.current_rate_multiplier < 1.0:
                self.current_rate_multiplier = min(1.0, self.current_rate_multiplier + 0.1)
        else:
            # Error - record and potentially decrease rate
            self.error_history.append(now)
            self.session_stats['errors'] += 1
            self.consecutive_errors += 1
            self.last_error_time = now
            
            # Decrease rate after multiple consecutive errors
            if self.consecutive_errors >= 3:
                self.current_rate_multiplier = max(0.3, self.current_rate_multiplier * 0.7)
                logger.warning(f"AI rate limited due to errors, reduced to {self.current_rate_multiplier:.1%} of normal rate")
    
    async def _handle_rate_limit(self, limit_type: str, window_seconds: int):
        """Handle rate limit with adaptive backoff"""
        self.session_stats['rate_limit_hits'] += 1
        logger.warning(f"AI rate limit hit: {limit_type}")
        
        if self.config.pause_on_limit:
            # Calculate adaptive backoff time
            base_backoff = min(window_seconds * 0.1, 60)  # Max 1 minute base
            backoff_time = base_backoff * (1.5 ** min(self.consecutive_errors, 5))  # Exponential up to 5 errors
            backoff_time = min(backoff_time, self.config.max_backoff_seconds)
            
            self.degradation_mode = True
            self.degraded_until = time.time() + backoff_time
            
            logger.info(f"AI paused for {backoff_time:.1f} seconds due to {limit_type} limit")
        else:
            self.degradation_mode = True
            self.degraded_until = time.time() + 300  # 5 minute cooldown
    
    def _clean_old_records(self, now: float):
        """Clean up old usage records"""
        # Keep last hour for tokens/cost
        self.token_history = [t for t in self.token_history if now - t['timestamp'] < 3600]
        self.cost_history = [c for c in self.cost_history if now - c['timestamp'] < 3600]
    def _clean_old_records(self, now: float):
        
        # Keep last minute for requests
        self.request_history = [r for r in self.request_history if now - r < 60]
        
        # Keep last hour for errors
        self.error_history = [e for e in self.error_history if now - e < 3600]
    
def get_usage_stats(self) -> Dict[str, Any]:
        """Get comprehensive usage statistics"""
        now = time.time()
        self._clean_old_records(now)
        
        recent_requests = len([r for r in self.request_history if now - r < 60])
        recent_tokens = sum(t['tokens'] for t in self.token_history if now - t['timestamp'] < 3600)
        recent_cost = sum(c['cost'] for c in self.cost_history if now - c['timestamp'] < 3600)
        recent_errors = len([e for e in self.error_history if now - e < 3600])
        
        return {
            'session_totals': self.session_stats,
            'current_usage': {
                'requests_last_minute': recent_requests,
                'tokens_last_hour': recent_tokens,
                'cost_last_hour': recent_cost,
                'errors_last_hour': recent_errors
            },
            'rate_status': {
                'current_multiplier': self.current_rate_multiplier,
                'degradation_mode': self.degradation_mode,
                'consecutive_errors': self.consecutive_errors
            },
            'limits': {
                'max_requests_per_minute': self.config.max_requests_per_minute,
                'max_tokens_per_hour': self.config.max_tokens_per_hour,
                'max_cost_per_hour': self.config.max_cost_per_hour
            }
        }

class ConfigurableAIProvider(ABC):
    """Enhanced AI provider interface with configurability"""
    
    def __init__(self, config, user_settings: AIConfigSettings):
        self.config = config
        self.user_settings = user_settings
        self.total_tokens_used = 0
        self.total_cost = 0.0
        self.success_count = 0
        self.error_count = 0
        self.prompt_templates = LegalPromptTemplates(case_type=user_settings.case_type)
    
    @abstractmethod
    async def analyze_content(self, content: str, analysis_type: str, 
                            context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze content with specified analysis type"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        pass
    
    def get_analysis_prompt(self, analysis_type: str, context: Dict[str, Any] = None) -> str:
        """Get appropriate prompt based on analysis type and user settings"""
        if analysis_type == "document_intelligence":
            return self.prompt_templates.get_document_analysis_prompt(context)
        elif analysis_type == "legal_analysis":
            return self.prompt_templates.get_legal_analysis_prompt(context)
        elif analysis_type == "pattern_discovery":
            return self.prompt_templates.get_pattern_discovery_prompt(context)
        else:
            return "Analyze the provided content and provide structured insights."
    
    def estimate_cost(self, content_length: int, analysis_type: str) -> float:
        """Estimate cost for analysis"""
        # Rough token estimation (1 token ≈ 4 characters)
        estimated_tokens = content_length // 4
        
        # Add prompt overhead
        prompt_overhead = {
            "document_intelligence": 500,
            "legal_analysis": 800,
            "pattern_discovery": 600
        }
        estimated_tokens += prompt_overhead.get(analysis_type, 400)
        
        # Add response tokens (estimated)
        estimated_tokens += 1000
        
        return estimated_tokens * self.config.cost_per_token
    
    def should_analyze(self, content: str, analysis_type: str) -> bool:
        """Determine if content should be analyzed based on user settings"""
        if len(content) > self.user_settings.max_content_length:
            logger.info(f"Content too long ({len(content)} chars), truncating")
            return True  # Will truncate in analyze_content
        
        estimated_cost = self.estimate_cost(len(content), analysis_type)
        if estimated_cost > 1.0:  # More than $1 per file
            logger.warning(f"High estimated cost (${estimated_cost:.2f}) for {analysis_type}")
            # Could add user confirmation here in future
        
        return True

class EnhancedOpenAIProvider(ConfigurableAIProvider):
    """Enhanced OpenAI provider with configurability and error handling"""
    
    def __init__(self, config, user_settings: AIConfigSettings):
        super().__init__(config, user_settings)
        if OPENAI_AVAILABLE and config.api_key:
            self.client = openai.AsyncOpenAI(
                api_key=config.api_key,
                base_url=config.base_url,
                timeout=config.timeout
            )
        else:
            self.client = None
    
    def is_available(self) -> bool:
        return OPENAI_AVAILABLE and self.config.api_key and self.config.enabled and self.client is not None
    
    async def analyze_content(self, content: str, analysis_type: str, 
                            context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Enhanced content analysis with configurability"""
        if not self.is_available():
            raise ValueError("OpenAI provider not available")
        
        try:
            # Truncate content if needed
            if len(content) > self.user_settings.max_content_length:
                content = content[:self.user_settings.max_content_length] + "\n[Content truncated due to length limits]"
            
            # Get appropriate prompt
            system_prompt = self.get_analysis_prompt(analysis_type, context)
            
            # Prepare messages
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add context if provided
            if context:
                context_msg = f"Additional Context: {json.dumps(context, indent=2)}\n\n"
                content = context_msg + content
            
            messages.append({"role": "user", "content": content})
            
            # Adjust model and parameters based on user settings
            model = self._select_model()
            temperature = self._get_temperature()
            max_tokens = self._get_max_tokens(analysis_type)
            
            # Make API call with retry logic
            response = await self._make_api_call_with_retry(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Track usage
            tokens_used = response.usage.total_tokens if response.usage else 0
            self.total_tokens_used += tokens_used
            cost = tokens_used * self.config.cost_per_token
            self.total_cost += cost
            self.success_count += 1
            
            return {
                "response": response.choices[0].message.content,
                "tokens_used": tokens_used,
                "cost": cost,
                "model": model,
                "provider": "openai",
                "analysis_type": analysis_type,
                "success": True
            }
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def _select_model(self) -> str:
        """Select appropriate model based on user settings"""
        if self.user_settings.analysis_depth == "comprehensive":
            return "gpt-4"  # Best quality
        elif self.user_settings.analysis_depth == "standard":
            return self.config.model or "gpt-4"
        else:  # basic
            return "gpt-3.5-turbo"  # Faster, cheaper
    
    def _get_temperature(self) -> float:
        """Get temperature based on analysis type"""
        # Legal analysis should be more deterministic
        temp_map = {
            "document_intelligence": 0.1,
            "legal_analysis": 0.05,  # Very deterministic for legal analysis
            "pattern_discovery": 0.2   # Slightly more creative for pattern finding
        }
        return temp_map.get("default", self.config.temperature)
    
    def _get_max_tokens(self, analysis_type: str) -> int:
        """Get max tokens based on analysis type and user settings"""
        base_tokens = {
            "document_intelligence": 2000,
            "legal_analysis": 3000,
            "pattern_discovery": 2500
        }
        
        base = base_tokens.get(analysis_type, 2000)
        
        if self.user_settings.analysis_depth == "comprehensive":
            return int(base * 1.5)
        elif self.user_settings.analysis_depth == "basic":
            return int(base * 0.7)
        else:
            return base
    
    async def _make_api_call_with_retry(self, **kwargs) -> Any:
        """Make API call with exponential backoff retry"""
        for attempt in range(self.config.max_retries):
            try:
                response = await self.client.chat.completions.create(**kwargs)
                return response
            except openai.RateLimitError as e:
                if attempt < self.config.max_retries - 1:
                    wait_time = (2 ** attempt) * 1.0  # Exponential backoff
                    logger.warning(f"Rate limit hit, waiting {wait_time}s before retry {attempt + 1}")
                    await asyncio.sleep(wait_time)
                else:
                    raise
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    wait_time = (2 ** attempt) * 0.5
                    logger.warning(f"API error {e}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise

class EnhancedAnthropicProvider(ConfigurableAIProvider):
    """Enhanced Anthropic provider with configurability"""
    
    def __init__(self, config, user_settings: AIConfigSettings):
        super().__init__(config, user_settings)
        if ANTHROPIC_AVAILABLE and config.api_key:
            self.client = anthropic.AsyncAnthropic(api_key=config.api_key)
        else:
            self.client = None
    
    def is_available(self) -> bool:
        return ANTHROPIC_AVAILABLE and self.config.api_key and self.config.enabled and self.client is not None
    
    async def analyze_content(self, content: str, analysis_type: str, 
                            context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Enhanced Anthropic content analysis"""
        if not self.is_available():
            raise ValueError("Anthropic provider not available")
        
        try:
            # Truncate content if needed
            if len(content) > self.user_settings.max_content_length:
                content = content[:self.user_settings.max_content_length] + "\n[Content truncated]"
            
            # Get prompt and construct message
            system_prompt = self.get_analysis_prompt(analysis_type, context)
            
            if context:
                context_str = f"Context: {json.dumps(context, indent=2)}\n\n"
                content = context_str + content
            
            full_prompt = system_prompt + "\n\nContent to analyze:\n" + content
            
            # Select model based on user settings
            model = self._select_model()
            max_tokens = self._get_max_tokens(analysis_type)
            
            # Make API call
            response = await self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=self._get_temperature(),
                messages=[{"role": "user", "content": full_prompt}]
            )
            
            # Track usage (approximate for Anthropic)
            tokens_used = len(full_prompt.split()) * 1.3  # Rough estimate
            cost = tokens_used * 0.00001  # Rough cost estimate
            self.total_tokens_used += int(tokens_used)
            self.total_cost += cost
            self.success_count += 1
            
            return {
                "response": response.content[0].text,
                "tokens_used": int(tokens_used),
                "cost": cost,
                "model": model,
                "provider": "anthropic",
                "analysis_type": analysis_type,
                "success": True
            }
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Anthropic API error: {e}")
            raise
    
    def _select_model(self) -> str:
        """Select Anthropic model based on user settings"""
        if self.user_settings.analysis_depth == "comprehensive":
            return "claude-4-opus-20240229"
        elif self.user_settings.analysis_depth == "standard":
            return self.config.model or "claude-3-sonnet-20240229"
        else:
            return "claude-3-haiku-20240307"
    
    def _get_temperature(self) -> float:
        """Get temperature for Anthropic"""
        return 0.1  # Anthropic works well with low temperature for structured tasks
    
    def _get_max_tokens(self, analysis_type: str) -> int:
        """Get max tokens for Anthropic"""
        base_tokens = {
            "document_intelligence": 2000,
            "legal_analysis": 3000,
            "pattern_discovery": 2500
        }
        
        base = base_tokens.get(analysis_type, 2000)
        
        if self.user_settings.analysis_depth == "comprehensive":
            return int(base * 1.5)
        elif self.user_settings.analysis_depth == "basic":
            return int(base * 0.7)
        else:
            return base

class EnhancedLocalModelProvider(ConfigurableAIProvider):
    """Enhanced local model provider with better configurability"""
    
    def __init__(self, config, user_settings: AIConfigSettings):
        super().__init__(config, user_settings)
        self.base_url = config.base_url or "http://localhost:11434"
        self.available = None  # Cache availability check
    
    def is_available(self) -> bool:
        """Check if local model is available (cached)"""
        if self.available is None:
            self.available = self._check_availability()
        return self.available and self.config.enabled
    
    def _check_availability(self) -> bool:
        """Actually check if local model server is running"""
        if not HTTP_AVAILABLE:
            return False
        
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    async def analyze_content(self, content: str, analysis_type: str, 
                            context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Enhanced local model analysis"""
        if not self.is_available():
            raise ValueError("Local model provider not available")
        
        try:
            # Truncate content if needed
            if len(content) > self.user_settings.max_content_length:
                content = content[:self.user_settings.max_content_length] + "\n[Content truncated]"
            
            # Get prompt
            system_prompt = self.get_analysis_prompt(analysis_type, context)
            
            if context:
                context_str = f"Context: {json.dumps(context, indent=2)}\n\n"
                content = context_str + content
            
            full_prompt = system_prompt + "\n\nContent to analyze:\n" + content
            
            # Select model based on availability and user settings
            model = await self._select_best_model()
            
            # Make API call
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {
                            "temperature": self._get_temperature(),
                            "num_predict": self._get_max_tokens(analysis_type)
                        }
                    }
                )
                
                if response.status_code != 200:
                    raise Exception(f"Local model API error: {response.status_code}")
                
                result = response.json()
                
                self.success_count += 1
                
                return {
                    "response": result.get("response", ""),
                    "tokens_used": 0,  # Local models don't report usage
                    "cost": 0.0,  # No cost for local models
                    "model": model,
                    "provider": "local",
                    "analysis_type": analysis_type,
                    "success": True
                }
                
        except Exception as e:
            self.error_count += 1
            logger.error(f"Local model API error: {e}")
            raise
    
    async def _select_best_model(self) -> str:
        """Select best available local model"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]
                    
                    # Prefer legal/analysis models if available
                    preferred_models = [
                        "llama2:13b", "llama2:7b", "mistral:7b", "codellama:13b"
                    ]
                    
                    for preferred in preferred_models:
                        if any(preferred in name for name in model_names):
                            return preferred
                    
                    # Fall back to any available model
                    if model_names:
                        return model_names[0]
        except:
            pass
        
        return self.config.model or "llama2"
    
    def _get_temperature(self) -> float:
        """Get temperature for local model"""
        return 0.1  # Low temperature for structured analysis
    
    def _get_max_tokens(self, analysis_type: str) -> int:
        """Get max tokens for local model"""
        # Local models often have smaller context windows
        base_tokens = {
            "document_intelligence": 1000,
            "legal_analysis": 1500,
            "pattern_discovery": 1200
        }
        
        return base_tokens.get(analysis_type, 1000)

class GoogleAIProvider(ConfigurableAIProvider):
    """Google AI provider using OpenAI-compatible interface"""

    def __init__(self, config, user_settings: AIConfigSettings):
        super().__init__(config, user_settings)
        # Ensure openai library is available, as we're using its interface
        if OPENAI_AVAILABLE and config.api_key:
            self.client = openai.AsyncOpenAI(
                api_key=config.api_key, # This will be the Google AI API Key
                base_url=config.base_url, # Should be "https://generativelanguage.googleapis.com/v1beta/models"
                timeout=config.timeout
            )
        else:
            self.client = None

    def is_available(self) -> bool:
        return OPENAI_AVAILABLE and self.config.api_key and self.config.enabled and self.client is not None and "generativelanguage.googleapis.com" in self.config.base_url

    async def analyze_content(self, content: str, analysis_type: str,
                            context: Dict[str, Any] = None) -> Dict[str, Any]:
        if not self.is_available():
            raise ValueError("Google AI provider not available or not configured correctly (check base_url).")

        try:
            if len(content) > self.user_settings.max_content_length:
                content = content[:self.user_settings.max_content_length] + "\n[Content truncated due to length limits]"

            system_prompt = self.get_analysis_prompt(analysis_type, context)
            messages = [{"role": "system", "content": system_prompt}]

            if context:
                context_msg = f"Additional Context: {json.dumps(context, indent=2)}\n\n"
                content = context_msg + content
            messages.append({"role": "user", "content": content})

            model = self._select_model() # This will just use config.model
            temperature = self._get_temperature()
            max_tokens = self._get_max_tokens(analysis_type)

            response = await self._make_api_call_with_retry(
                messages=messages,
                model=model, # User will set this to a Gemini model name
                temperature=temperature,
                max_tokens=max_tokens
                # Ensure no OpenAI specific params like 'response_format' are passed if not supported
            )

            tokens_used = response.usage.total_tokens if response.usage else 0 # This might need adjustment if Google's response differs
            self.total_tokens_used += tokens_used
            cost = tokens_used * self.config.cost_per_token # Placeholder cost
            self.total_cost += cost
            self.success_count += 1

            return {
                "response": response.choices[0].message.content,
                "tokens_used": tokens_used,
                "cost": cost,
                "model": model,
                "provider": "google",
                "analysis_type": analysis_type,
                "success": True
            }
        except Exception as e:
            self.error_count += 1
            logger.error(f"Google AI API error: {e}", exc_info=True)
            # Check for specific Google API errors if possible
            if "API key not valid" in str(e): # This is a guess, error messages might differ
                logger.error("Google AI API key may be invalid or missing.")
            raise

    def _select_model(self) -> str:
        # For Google AI, model is directly specified in config.model by user
        # e.g., "gemini-1.5-pro-latest" or "models/gemini-1.5-pro-latest"
        if not self.config.model:
            logger.warning("Google AI model not specified in config, defaulting to 'gemini-pro'")
            return "gemini-pro"
        return self.config.model

    def _get_temperature(self) -> float:
        return self.config.temperature

    def _get_max_tokens(self, analysis_type: str) -> int:
        base_tokens = {"document_intelligence": 2000, "legal_analysis": 3000, "pattern_discovery": 2500}
        base = base_tokens.get(analysis_type, 2000)
        if self.user_settings.analysis_depth == "comprehensive": return int(base * 1.5)
        elif self.user_settings.analysis_depth == "basic": return int(base * 0.7)
        return base

    async def _make_api_call_with_retry(self, **kwargs) -> Any:
        # This uses the openai.RateLimitError, which might not be directly applicable
        # if Google's rate limits behave differently via the OpenAI library shim.
        # This might need refinement based on actual Google API error responses.
        for attempt in range(self.config.max_retries):
            try:
                response = await self.client.chat.completions.create(**kwargs)
                return response
            except openai.RateLimitError as e: # Check if Google errors map to this
                if attempt < self.config.max_retries - 1:
                    wait_time = (2 ** attempt) * 1.0
                    logger.warning(f"Google AI rate limit hit (or error mapped to it), waiting {wait_time}s before retry {attempt + 1}")
                    await asyncio.sleep(wait_time)
                else:
                    raise
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    wait_time = (2 ** attempt) * 0.5
                    logger.warning(f"Google AI API error '{e}', retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise

class EnhancedAIFoundationPlugin:
    """Production-ready AI Foundation Plugin with comprehensive configurability"""
    
    def __init__(self, config_path: str = "config/ai_config.json"):
        self.config_path = config_path
        self.providers = {}
        self.agents = {}
        self.user_settings = AIConfigSettings()
        self.rate_limiter = None
        
        # Load configuration
        self.load_configuration()
        
        # Initialize rate limiter
        if hasattr(self.config, 'ai_rate_limits'):
            self.rate_limiter = EnhancedAIRateLimiter(self.config.ai_rate_limits)
        
        # Initialize providers
        self.initialize_providers()
        
        # Initialize agents
        self.initialize_agents()
    
    def load_configuration(self):
        """Load comprehensive AI configuration"""
        if Path(self.config_path).exists():
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
            
            # Load user settings
            if 'user_settings' in config_data:
                self.user_settings = AIConfigSettings(**config_data['user_settings'])
            
            self.config = type('Config', (), config_data)()
        else:
            # Create comprehensive default configuration
            self.config = self.create_default_config()
            self.save_configuration()
    
    def create_default_config(self) -> Any:
        """Create comprehensive default configuration"""
        config_dict = {
            "providers": {
                "openai": {
                    "provider_name": "openai",
                    "api_key": "",  # User must add
                    "model": "gpt-4",
                    "temperature": 0.1,
                    "max_tokens": 4000,
                    "timeout": 60,
                    "max_retries": 3,
                    "enabled": True,
                    "cost_per_token": 0.00003  # GPT-4 pricing (approximate)
                },
                "anthropic": {
                    "provider_name": "anthropic",
                    "api_key": "",  # User must add
                    "model": "claude-3-sonnet-20240229",
                    "temperature": 0.1,
                    "max_tokens": 4000,
                    "timeout": 60,
                    "max_retries": 3,
                    "enabled": False,  # Disabled by default
                    "cost_per_token": 0.00001  # Approximate
                },
                "local": {
                    "provider_name": "local",
                    "base_url": "http://localhost:11434",
                    "model": "llama2",
                    "temperature": 0.1,
                    "max_tokens": 2000,
                    "timeout": 120,
                    "max_retries": 2,
                    "enabled": False,  # Disabled by default
                    "cost_per_token": 0.0  # No cost for local
                },
                "google": {
                    "provider_name": "google",
                    "api_key": "",  # User must add their Google AI API Key
                    "model": "gemini-1.5-pro-latest", # Default model, user can change
                    "base_url": "https://generativelanguage.googleapis.com/v1beta/models", # OpenAI-compatible endpoint for Gemini
                    "temperature": 0.1,
                    "max_tokens": 4000, # Default, should be adjusted based on model
                    "timeout": 60,
                    "max_retries": 3,
                    "enabled": False, # Default to disabled
                    "cost_per_token": 0.000002  # Placeholder: e.g., Gemini 1.5 Pro input pricing, user should verify/update
                }
            },
            "user_settings": {
                "preferred_provider": "openai",
                "fallback_providers": ["anthropic", "local"],
                "analysis_depth": "standard",
                "confidence_threshold": 0.6,
                "enable_multi_agent": True,
                "enable_cross_validation": False,
                "case_type": "general",
                "jurisdiction": "US_Federal",
                "legal_standards": [],
                "max_content_length": 50000,
                "batch_processing": True,
                "parallel_agents": True,
                "cache_results": True,
                "include_citations": True,
                "generate_summaries": True,
                "legal_memo_format": False,
                "confidence_explanations": True
            },
            "ai_rate_limits": {
                "max_requests_per_minute": 20,
                "max_tokens_per_hour": 100000,
                "max_cost_per_hour": 10.0,
                "initial_backoff_seconds": 1.0,
                "max_backoff_seconds": 300.0,
                "backoff_multiplier": 2.0,
                "pause_on_limit": True,
                "retry_failed_requests": True,
                "max_retries": 3,
                "track_usage": True,
                "usage_log_file": "ai_usage.log"
            },
            "agents": {
                "document_intelligence": {
                    "enabled": True,
                    "provider": "openai",
                    "analysis_type": "document_intelligence",
                    "priority": 1
                },
                "legal_analysis": {
                    "enabled": True,
                    "provider": "openai", 
                    "analysis_type": "legal_analysis",
                    "priority": 2
                },
                "pattern_discovery": {
                    "enabled": False,  # Disabled by default (resource intensive)
                    "provider": "openai",
                    "analysis_type": "pattern_discovery",
                    "priority": 3
                }
            },
            "settings": {
                "max_concurrent_agents": 3,
                "enable_caching": True,
                "log_level": "INFO",
                "auto_fallback": True,
                "quality_threshold": 0.7
            }
        }
        
        return type('Config', (), config_dict)()
    
    def save_configuration(self):
        """Save current configuration to file"""
        config_dict = {
            "providers": self.config.providers,
            "user_settings": asdict(self.user_settings),
            "ai_rate_limits": self.config.ai_rate_limits,
            "agents": self.config.agents,
            "settings": self.config.settings
        }
        
        Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def update_user_settings(self, **kwargs):
        """Update user settings and reinitialize if needed"""
        updated = False
        for key, value in kwargs.items():
            if hasattr(self.user_settings, key):
                setattr(self.user_settings, key, value)
                updated = True
        
        if updated:
            # Reinitialize providers with new settings
            self.initialize_providers()
            # Save updated config
            self.save_configuration()
            logger.info("User settings updated and providers reinitialized")
    
    def initialize_providers(self):
        """Initialize AI providers with user settings"""
        self.providers = {}
        
        for provider_name, provider_config in self.config.providers.items():
            config_obj = type('ProviderConfig', (), provider_config)()
            
            try:
                if provider_name == "openai":
                    self.providers[provider_name] = EnhancedOpenAIProvider(config_obj, self.user_settings)
                elif provider_name == "anthropic":
                    self.providers[provider_name] = EnhancedAnthropicProvider(config_obj, self.user_settings)
                elif provider_name == "local":
                    self.providers[provider_name] = EnhancedLocalModelProvider(config_obj, self.user_settings)
                elif provider_name == "google":
                    self.providers[provider_name] = GoogleAIProvider(config_obj, self.user_settings)
                    
                logger.info(f"Provider {provider_name}: {'✓' if self.providers[provider_name].is_available() else '✗'}")
            except Exception as e:
                logger.error(f"Failed to initialize provider {provider_name}: {e}")
    
    def initialize_agents(self):
        """Initialize AI agents with prioritization"""
        self.agents = {}
        
        # Sort agents by priority
        agent_configs = sorted(
            self.config.agents.items(), 
            key=lambda x: x[1].get('priority', 999)
        )
        
        for agent_name, agent_config in agent_configs:
            if agent_config['enabled']:
                provider_name = agent_config['provider']
                
                if provider_name in self.providers and self.providers[provider_name].is_available():
                    self.agents[agent_name] = {
                        'provider': self.providers[provider_name],
                        'config': agent_config,
                        'analysis_type': agent_config['analysis_type']
                    }
                    logger.info(f"Agent {agent_name}: ✓ (via {provider_name})")
                else:
                    # Try fallback providers
                    for fallback_provider in self.user_settings.fallback_providers:
                        if (fallback_provider in self.providers and 
                            self.providers[fallback_provider].is_available()):
                            self.agents[agent_name] = {
                                'provider': self.providers[fallback_provider],
                                'config': agent_config,
                                'analysis_type': agent_config['analysis_type']
                            }
                            logger.info(f"Agent {agent_name}: ✓ (via {fallback_provider} fallback)")
                            break
                    else:
                        logger.warning(f"Agent {agent_name}: ✗ (no available providers)")
    
    async def analyze_file_content(self, content: str, file_path: str = "", 
                                 context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Enhanced file content analysis with rate limiting and fallbacks"""
        results = {}
        
        # Check rate limits first
        if self.rate_limiter and not await self.rate_limiter.check_and_wait_if_needed():
            logger.warning(f"Rate limited - skipping AI analysis for {file_path}")
            return {"rate_limited": True, "message": "AI analysis skipped due to rate limits"}
        
        # Determine which agents to run
        agents_to_run = self._select_agents_for_analysis(content, context)
        
        if self.user_settings.parallel_agents and len(agents_to_run) > 1:
            # Run agents in parallel
            tasks = []
            for agent_name in agents_to_run:
                if agent_name in self.agents:
                    task = self._run_single_agent(agent_name, content, file_path, context)
                    tasks.append((agent_name, task))
            
            # Execute tasks
            for agent_name, task in tasks:
                try:
                    result = await task
                    results[agent_name] = result
                except Exception as e:
                    logger.error(f"Agent {agent_name} failed: {e}")
                    results[agent_name] = {"error": str(e), "success": False}
        else:
            # Run agents sequentially
            for agent_name in agents_to_run:
                if agent_name in self.agents:
                    try:
                        result = await self._run_single_agent(agent_name, content, file_path, context)
                        results[agent_name] = result
                        
                        # Check if we should continue based on quality
                        if (result.get('success', False) and 
                            result.get('confidence', 0) < self.config.settings.get('quality_threshold', 0.7)):
                            logger.info(f"Low quality result from {agent_name}, trying next agent")
                            continue
                            
                    except Exception as e:
                        logger.error(f"Agent {agent_name} failed: {e}")
                        results[agent_name] = {"error": str(e), "success": False}
        
        return results
    
    def _select_agents_for_analysis(self, content: str, context: Dict[str, Any] = None) -> List[str]:
        """Select which agents should analyze the content"""
        agents_to_run = []
        
        # Always run document intelligence first
        if "document_intelligence" in self.agents:
            agents_to_run.append("document_intelligence")
        
        # Add legal analysis if enabled
        if ("legal_analysis" in self.agents and 
            self.user_settings.analysis_depth in ["standard", "comprehensive"]):
            agents_to_run.append("legal_analysis")
        
        # Add pattern discovery for comprehensive analysis
        if ("pattern_discovery" in self.agents and 
            self.user_settings.analysis_depth == "comprehensive"):
            agents_to_run.append("pattern_discovery")
        
        return agents_to_run
    
    async def _run_single_agent(self, agent_name: str, content: str, 
                              file_path: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run a single agent with error handling and usage tracking"""
        agent = self.agents[agent_name]
        provider = agent['provider']
        analysis_type = agent['analysis_type']
        
        start_time = time.time()
        
        try:
            # Check if content should be analyzed
            if not provider.should_analyze(content, analysis_type):
                return {
                    "skipped": True,
                    "reason": "Content filtering",
                    "success": False
                }
            
            # Perform analysis
            result = await provider.analyze_content(content, analysis_type, context)
            
            # Parse and enhance result
            enhanced_result = self._parse_ai_response(result, agent_name, file_path)
            enhanced_result['processing_time'] = time.time() - start_time
            
            # Record usage with rate limiter
            if self.rate_limiter:
                await self.rate_limiter.record_request(
                    tokens_used=result.get('tokens_used', 0),
                    cost=result.get('cost', 0.0),
                    success=result.get('success', True)
                )
            
            return enhanced_result
            
        except Exception as e:
            # Record failed request
            if self.rate_limiter:
                await self.rate_limiter.record_request(0, 0.0, success=False)
            
            error_result = {
                "error": str(e),
                "success": False,
                "agent_name": agent_name,
                "analysis_type": analysis_type,
                "processing_time": time.time() - start_time
            }
            
            logger.error(f"Agent {agent_name} failed for {file_path}: {e}")
            return error_result
    
    def _parse_ai_response(self, raw_result: Dict[str, Any], agent_name: str, 
                          file_path: str) -> Dict[str, Any]:
        """Parse and structure AI response"""
        response_text = raw_result.get('response', '')
        
        # Try to extract JSON from response
        structured_data = {}
        try:
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                structured_data = json.loads(json_match.group())
        except:
            # If JSON parsing fails, create basic structure
            structured_data = {
                "summary": response_text[:500] if response_text else "No response",
                "full_response": response_text,
                "structured": False
            }
        
        # Enhance with metadata
        result = {
            "agent_name": agent_name,
            "analysis_type": raw_result.get('analysis_type', 'unknown'),
            "confidence_score": self._extract_confidence(structured_data),
            "findings": structured_data,
            "entities_found": self._extract_entities(structured_data),
            "tags": self._extract_tags(structured_data),
            "legal_significance": structured_data.get('legal_significance', ''),
            "probative_value": self._extract_numeric_value(structured_data, 'probative_value'),
            "relevance_score": self._extract_numeric_value(structured_data, 'relevance_score'),
            "processing_time": 0.0,  # Will be set by caller
            "metadata": {
                "file_path": file_path,
                "provider": raw_result.get('provider', 'unknown'),
                "model": raw_result.get('model', 'unknown'),
                "tokens_used": raw_result.get('tokens_used', 0),
                "cost": raw_result.get('cost', 0.0),
                "user_settings": {
                    "analysis_depth": self.user_settings.analysis_depth,
                    "case_type": self.user_settings.case_type,
                    "jurisdiction": self.user_settings.jurisdiction
                }
            },
            "timestamp": datetime.now().isoformat(),
            "success": raw_result.get('success', True)
        }
        
        return result
    
    def _extract_confidence(self, data: Dict[str, Any]) -> float:
        """Extract confidence score from AI response"""
        for key in ['confidence', 'confidence_score', 'certainty']:
            if key in data:
                try:
                    return float(data[key])
                except:
                    pass
        
        # Default confidence based on structure quality
        if data.get('structured', True):
            return 0.7
        else:
            return 0.4
    
    def _extract_entities(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract entities from AI response"""
        entities = []
        
        # Look for various entity fields
        entity_fields = ['key_parties', 'entities', 'people', 'organizations']
        for field in entity_fields:
            if field in data and isinstance(data[field], list):
                for entity in data[field]:
                    if isinstance(entity, str):
                        entities.append({"type": field, "value": entity, "confidence": 0.8})
                    elif isinstance(entity, dict):
                        entities.append(entity)
        
        # Look for financial amounts
        if 'financial_amounts' in data and isinstance(data['financial_amounts'], list):
            for amount in data['financial_amounts']:
                entities.append({"type": "money", "value": amount, "confidence": 0.9})
        
        # Look for dates
        if 'important_dates' in data and isinstance(data['important_dates'], list):
            for date in data['important_dates']:
                entities.append({"type": "date", "value": date, "confidence": 0.8})
        
        return entities
    
    def _extract_tags(self, data: Dict[str, Any]) -> List[str]:
        """Extract tags from AI response"""
        tags = []
        
        # Extract from various fields
        if 'evidence_category' in data:
            tags.append(data['evidence_category'])
        
        if 'document_type' in data:
            tags.append(data['document_type'])
        
        if 'legal_theory_support' in data and isinstance(data['legal_theory_support'], dict):
            tags.extend(data['legal_theory_support'].keys())
        
        if 'key_facts' in data and isinstance(data['key_facts'], list):
            tags.append('factual_evidence')
        
        # Add confidence-based tags
        confidence = self._extract_confidence(data)
        if confidence > 0.8:
            tags.append('high_confidence')
        elif confidence < 0.5:
            tags.append('low_confidence')
        
        # Add case-type specific tags
        tags.append(f"case_type_{self.user_settings.case_type}")
        
        return list(set(tags))  # Remove duplicates
    
    def _extract_numeric_value(self, data: Dict[str, Any], key: str) -> float:
        """Extract numeric value from AI response"""
        if key in data:
            try:
                return float(data[key])
            except:
                pass
        
        # Default values based on key type
        defaults = {
            'probative_value': 0.5,
            'relevance_score': 0.5,
            'prejudicial_impact': 0.1,
            'admissibility_score': 0.7
        }
        
        return defaults.get(key, 0.0)
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive status of AI system"""
        status = {
            "providers": {},
            "agents": {},
            "rate_limiter": {},
            "user_settings": asdict(self.user_settings),
            "system_health": "healthy"
        }
        
        # Provider status
        for name, provider in self.providers.items():
            status["providers"][name] = {
                "available": provider.is_available(),
                "enabled": provider.config.enabled,
                "model": provider.config.model,
                "total_requests": provider.success_count + provider.error_count,
                "success_rate": provider.success_count / max(provider.success_count + provider.error_count, 1),
                "total_tokens": provider.total_tokens_used,
                "total_cost": provider.total_cost
            }
        
        # Agent status
        for name, agent in self.agents.items():
            provider_name = agent['config']['provider']
            status["agents"][name] = {
                "enabled": True,
                "provider": provider_name,
                "provider_available": agent['provider'].is_available(),
                "analysis_type": agent['analysis_type'],
                "priority": agent['config'].get('priority', 999)
            }
        
        # Rate limiter status
        if self.rate_limiter:
            status["rate_limiter"] = self.rate_limiter.get_usage_stats()
        
        # System health assessment
        available_providers = sum(1 for p in status["providers"].values() if p["available"])
        available_agents = sum(1 for a in status["agents"].values() if a["provider_available"])
        
        if available_providers == 0:
            status["system_health"] = "critical"
        elif available_agents < len(self.agents) / 2:
            status["system_health"] = "degraded"
        elif self.rate_limiter and self.rate_limiter.degradation_mode:
            status["system_health"] = "rate_limited"
        
        return status
 
    def generate_usage_report(self) -> str:
        """Generate comprehensive usage report"""
        status = self.get_comprehensive_status()
        
        report = f"""# AI Foundation Plugin Usage Report"

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
System Health: {status['system_health'].upper()}

## Provider Performance
"""
        
        for provider_name, provider_data in status["providers"].items():
            availability = "✓" if provider_data["available"] else "✗"
            report += f"""
### {provider_name.title()} {availability}
- **Model**: {provider_data['model']}
- **Total Requests**: {provider_data['total_requests']}
- **Success Rate**: {provider_data['success_rate']:.1%}
- **Tokens Used**: {provider_data['total_tokens']:,}
- **Total Cost**: ${provider_data['total_cost']:.2f}
"""
        
        report += "\n## Agent Status\n"
        for agent_name, agent_data in status["agents"].items():
            availability = "✓" if agent_data["provider_available"] else "✗"
            report += f"- **{agent_name}** {availability} (via {agent_data['provider']})\n"
        
        if status["rate_limiter"]:
            rl = status["rate_limiter"]
            report += f"""
## Rate Limiting Status
- **Current Rate Multiplier**: {rl['rate_status']['current_multiplier']:.1%}
- **Requests (last minute)**: {rl['current_usage']['requests_last_minute']}/{rl['limits']['max_requests_per_minute']}
- **Tokens (last hour)**: {rl['current_usage']['tokens_last_hour']:,}/{rl['limits']['max_tokens_per_hour']:,}
- **Cost (last hour)**: ${rl['current_usage']['cost_last_hour']:.2f}/${rl['limits']['max_cost_per_hour']:.2f}
- **Rate Limit Hits**: {rl['session_totals']['rate_limit_hits']}
"""
        
        report += f"""
## Current Configuration
- **Preferred Provider**: {status['user_settings']['preferred_provider']}
- **Analysis Depth**: {status['user_settings']['analysis_depth']}
- **Case Type**: {status['user_settings']['case_type']}
- **Jurisdiction**: {status['user_settings']['jurisdiction']}
- **Multi-Agent**: {"Enabled" if status['user_settings']['enable_multi_agent'] else "Disabled"}
- **Parallel Processing**: {"Enabled" if status['user_settings']['parallel_agents'] else "Disabled"}

## Recommendations
"""
        
        # Generate recommendations based on status
        if status["system_health"] == "critical":
            report += "- **CRITICAL**: No AI providers available. Check API keys and network connectivity.\n"
        elif status["system_health"] == "degraded":
            report += "- **WARNING**: Some AI agents unavailable. Consider enabling fallback providers.\n"
        elif status["system_health"] == "rate_limited":
            report += "- **INFO**: Currently rate limited. Consider upgrading API limits or enabling local models.\n"
        
        # Cost optimization recommendations
        total_cost = sum(p["total_cost"] for p in status["providers"].values())
        if total_cost > 50:
            report += f"- **COST**: High usage (${total_cost:.2f}). Consider using local models for basic analysis.\n"
        
        return report
    
    def export_configuration(self, file_path: str = None) -> str:
        """Export current configuration for sharing/backup"""
        if file_path is None:
            file_path = f"lcas_ai_config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        config_export = {
            "version": "2.0",
            "export_date": datetime.now().isoformat(),
            "user_settings": asdict(self.user_settings),
            "provider_settings": {
                name: {k: v for k, v in config.items() if k != 'api_key'}  # Don't export API keys'
                for name, config in self.config.providers.items()
            },
            "agent_settings": self.config.agents,
            "rate_limit_settings": self.config.ai_rate_limits
        }
        
        with open(file_path, 'w') as f:
            json.dump(config_export, f, indent=2)
        
        logger.info(f"Configuration exported to {file_path}")
        return file_path
    
    def import_configuration(self, file_path: str):
        """Import configuration from backup/sharing"""
        with open(file_path, 'r') as f:
            config_import = json.load(f)
        
        if config_import.get('version') != "2.0":
            logger.warning("Configuration version mismatch - some settings may not import correctly")
        
        # Import user settings
        if 'user_settings' in config_import:
            self.user_settings = AIConfigSettings(**config_import['user_settings'])
        
        # Import other settings (preserving existing API keys)
        if 'provider_settings' in config_import:
            for provider_name, settings in config_import['provider_settings'].items():
                if provider_name in self.config.providers:
                    # Preserve existing API key
                    api_key = self.config.providers[provider_name].get('api_key', '')
                    self.config.providers[provider_name].update(settings)
                    if api_key:
                        self.config.providers[provider_name]['api_key'] = api_key
        
        # Reinitialize with new settings
        self.initialize_providers()
        self.initialize_agents()
        self.save_configuration()
        
        logger.info(f"Configuration imported from {file_path}")

# Factory function for LCAS integration
        feat/ai-integration-fix

        feat/ai-integration-fix

        feat/ai-integration-fix

        feat/ai-integration-fix

        feat/ai-integration-fix

      feat/ai-integration-fix
        main
        main
        main
        main
        main
def create_enhanced_ai_plugin(lcas_config) -> "EnhancedAIFoundationPlugin":
    """Factory function to create enhanced AI plugin for LCAS"""
    
    # Extract AI configuration from LCAS config if available
    config_path = getattr(lcas_config, 'ai_config_path', 'config/ai_config.json')
    
    # Create the enhanced plugin
    ai_plugin = EnhancedAIFoundationPlugin(config_path)
    
    # Update user settings based on LCAS config
    if hasattr(lcas_config, 'case_theory'):
        ai_plugin.update_user_settings(
            case_type=lcas_config.case_theory.case_type,
            analysis_depth=getattr(lcas_config, 'ai_analysis_depth', 'standard'),
            confidence_threshold=getattr(lcas_config, 'ai_confidence_threshold', 0.6)
        )
    
    logger.info("Enhanced AI Foundation Plugin created and configured for LCAS")
    return ai_plugin

    def create_enhanced_ai_plugin(lcas_config) -> EnhancedAIFoundationPlugin:
        """Factory function to create enhanced AI plugin for LCAS"""

        # Extract AI configuration from LCAS config if available
        config_path = getattr(lcas_config, 'ai_config_path', 'config/ai_config.json')

        # Create the enhanced plugin
        ai_plugin = EnhancedAIFoundationPlugin(config_path)

        # Update user settings based on LCAS config
        if hasattr(lcas_config, 'case_theory'):
            ai_plugin.update_user_settings(
                case_type=lcas_config.case_theory.case_type,
                analysis_depth=getattr(lcas_config, 'ai_analysis_depth', 'standard'),
                confidence_threshold=getattr(lcas_config, 'ai_confidence_threshold', 0.6)
            )

        logger.info("Enhanced AI Foundation Plugin created and configured for LCAS")
        return ai_plugin
        main

# Backward compatibility
def create_ai_plugin(lcas_config):
    """Backward compatible factory function"""
    return create_enhanced_ai_plugin(lcas_config)

# Example usage and testing
if __name__ == "__main__":
    async def test_enhanced_plugin():
        """Test the enhanced AI plugin functionality"""
        print("Testing Enhanced AI Foundation Plugin...")
        
        # Create plugin with default settings
        plugin = EnhancedAIFoundationPlugin()
        
        # Display status
        status = plugin.get_comprehensive_status()
        print(f"\nSystem Health: {status['system_health']}")
        
        # Show provider availability
        print("\nProvider Status:")
        for name, data in status['providers'].items():
            print(f"  {name}: {'✓' if data['available'] else '✗'} ({data['model']})")
        
        # Show agent status
        print("\nAgent Status:")
        for name, data in status['agents'].items():
            print(f"  {name}: {'✓' if data['provider_available'] else '✗'} via {data['provider']}")
        
        # Test configuration updates
        print("\nTesting configuration updates...")
        plugin.update_user_settings(
            case_type="family_law",
            analysis_depth="comprehensive",
            jurisdiction="California"
        )
        print("  ✓ Settings updated")
        
        # Test analysis if providers available
        available_providers = [name for name, data in status['providers'].items() if data['available']]
        
        if available_providers:
            print(f"\nTesting analysis with {available_providers[0]}...")
            
            test_content = """
            Email from John to Mary dated March 15, 2023.
            Subject: Financial Disclosure Issues
            
            Mary, I've been reviewing our financial statements and noticed some '
            discrepancies in the cryptocurrency accounts. The Bitcoin wallet 
            shows a balance of $75,000 but the disclosed amount was only $25,000.
            We need to address this before the court hearing next week.
            
            Also, I found evidence that contradicts the testimony given about 
            the domestic violence incident on February 10th. The security camera 
            footage shows a different sequence of events.
            
            Please review the attached bank statements showing the offshore 
            account transfers that weren't included in the FC-2107 disclosure.'
            """
            
            try:
                results = await plugin.analyze_file_content(
                    content=test_content,
                    file_path="test_email.txt",
                    context={
                        "case_type": "family_law",
                        "legal_theories": ["Financial Non-Disclosure", "Fraud on Court"],
                        "jurisdiction": "California"
                    }
                )
                
                print("Analysis Results:")
                for agent_name, result in results.items():
                    if result.get('success', False):
                        print(f"  {agent_name}:")
                        print(f"    Confidence: {result.get('confidence_score', 0):.2f}")
                        print(f"    Entities Found: {len(result.get('entities_found', []))}")
                        print(f"    Tags: {', '.join(result.get('tags', [])[:3])}")
                        print(f"    Cost: ${result.get('metadata', {}).get('cost', 0):.4f}")
                    else:
                        print(f"  {agent_name}: Failed - {result.get('error', 'Unknown error')}")
                        
            except Exception as e:
                print(f"  Analysis failed: {e}")
        else:
            print("\nNo AI providers available for testing")
            print("To enable AI analysis:")
            print("1. Add OpenAI API key to config/ai_config.json")
            print("2. Or set up local model with Ollama")
            print("3. Or add Anthropic API key")
        
        # Generate usage report
        print("\nGenerating usage report...")
        report = plugin.generate_usage_report()
        print("  ✓ Report generated (see below)")
        
        print("\n" + "="*60)
        print(report)
        
        # Test configuration export
        print("\nTesting configuration export...")
        export_path = plugin.export_configuration()
        print(f"  ✓ Configuration exported to {export_path}")
    
    # Run test
    asyncio.run(test_enhanced_plugin()
)