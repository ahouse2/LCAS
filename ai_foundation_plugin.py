#!/usr/bin/env python3
"""
LCAS AI Foundation Plugin - Complete Vertical Slice
Modular AI integration supporting OpenAI, Local Models, and Multi-Agent coordination
"""

import os
import json
import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Union, Callable
from pathlib import Path
import time
from datetime import datetime

# Core dependencies
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI not available - install with: pip install openai")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logging.warning("Anthropic not available - install with: pip install anthropic")

try:
    import requests
    import httpx
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False
    logging.warning("HTTP clients not available - install with: pip install requests httpx")

logger = logging.getLogger(__name__)

@dataclass
class AIAnalysisResult:
    """Standardized AI analysis result structure"""
    agent_name: str
    content_analyzed: str
    analysis_type: str
    confidence_score: float
    findings: Dict[str, Any]
    entities_found: List[Dict[str, Any]]
    tags: List[str]
    legal_significance: str
    probative_value: float
    relevance_score: float
    processing_time: float
    metadata: Dict[str, Any]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result

@dataclass
class AIProviderConfig:
    """Configuration for AI providers"""
    provider_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: str = "gpt-4"
    temperature: float = 0.1
    max_tokens: int = 4000
    timeout: int = 60
    max_retries: int = 3
    enabled: bool = True
    cost_per_token: float = 0.0001  # Rough estimate for tracking

class AIProviderInterface(ABC):
    """Abstract interface for AI providers"""
    
    def __init__(self, config: AIProviderConfig):
        self.config = config
        self.total_tokens_used = 0
        self.total_cost = 0.0
    
    @abstractmethod
    async def analyze_content(self, content: str, analysis_prompt: str, 
                            context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze content using the AI provider"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and configured"""
        pass
    
    def track_usage(self, tokens_used: int):
        """Track token usage and costs"""
        self.total_tokens_used += tokens_used
        self.total_cost += tokens_used * self.config.cost_per_token

class OpenAIProvider(AIProviderInterface):
    """OpenAI API provider implementation"""
    
    def __init__(self, config: AIProviderConfig):
        super().__init__(config)
        if OPENAI_AVAILABLE and config.api_key:
            self.client = openai.AsyncOpenAI(
                api_key=config.api_key,
                base_url=config.base_url
            )
        else:
            self.client = None
    
    def is_available(self) -> bool:
        return OPENAI_AVAILABLE and self.config.api_key and self.config.enabled
    
    async def analyze_content(self, content: str, analysis_prompt: str, 
                            context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze content using OpenAI"""
        if not self.is_available():
            raise ValueError("OpenAI provider not available or not configured")
        
        try:
            # Construct messages
            messages = [
                {"role": "system", "content": analysis_prompt}
            ]
            
            if context:
                context_str = f"Context: {json.dumps(context, indent=2)}\n\n"
                content = context_str + content
            
            messages.append({"role": "user", "content": content})
            
            # Make API call
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout
            )
            
            # Track usage
            tokens_used = response.usage.total_tokens if response.usage else 0
            self.track_usage(tokens_used)
            
            return {
                "response": response.choices[0].message.content,
                "tokens_used": tokens_used,
                "model": self.config.model,
                "provider": "openai"
            }
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

class AnthropicProvider(AIProviderInterface):
    """Anthropic Claude provider implementation"""
    
    def __init__(self, config: AIProviderConfig):
        super().__init__(config)
        if ANTHROPIC_AVAILABLE and config.api_key:
            self.client = anthropic.AsyncAnthropic(api_key=config.api_key)
        else:
            self.client = None
    
    def is_available(self) -> bool:
        return ANTHROPIC_AVAILABLE and self.config.api_key and self.config.enabled
    
    async def analyze_content(self, content: str, analysis_prompt: str, 
                            context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze content using Anthropic Claude"""
        if not self.is_available():
            raise ValueError("Anthropic provider not available or not configured")
        
        try:
            # Construct prompt
            full_prompt = analysis_prompt + "\n\nContent to analyze:\n" + content
            
            if context:
                context_str = f"Context: {json.dumps(context, indent=2)}\n\n"
                full_prompt = context_str + full_prompt
            
            # Make API call
            response = await self.client.messages.create(
                model=self.config.model or "claude-3-sonnet-20240229",
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[{"role": "user", "content": full_prompt}]
            )
            
            # Track usage (approximate)
            tokens_used = len(full_prompt.split()) * 1.3  # Rough estimate
            self.track_usage(int(tokens_used))
            
            return {
                "response": response.content[0].text,
                "tokens_used": int(tokens_used),
                "model": self.config.model,
                "provider": "anthropic"
            }
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

class LocalModelProvider(AIProviderInterface):
    """Local model provider (via HTTP API like Ollama, LM Studio, etc.)"""
    
    def __init__(self, config: AIProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:11434"  # Default Ollama
    
    def is_available(self) -> bool:
        if not HTTP_AVAILABLE or not self.config.enabled:
            return False
        
        # Test connection to local model server
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    async def analyze_content(self, content: str, analysis_prompt: str, 
                            context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze content using local model"""
        if not self.is_available():
            raise ValueError("Local model provider not available")
        
        try:
            # Construct prompt
            full_prompt = analysis_prompt + "\n\nContent to analyze:\n" + content
            
            if context:
                context_str = f"Context: {json.dumps(context, indent=2)}\n\n"
                full_prompt = context_str + full_prompt
            
            # Make API call to local model
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.config.model or "llama2",
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {
                            "temperature": self.config.temperature,
                            "num_predict": self.config.max_tokens
                        }
                    }
                )
                
                if response.status_code != 200:
                    raise Exception(f"Local model API error: {response.status_code}")
                
                result = response.json()
                
                return {
                    "response": result.get("response", ""),
                    "tokens_used": 0,  # Local models don't report usage
                    "model": self.config.model,
                    "provider": "local"
                }
                
        except Exception as e:
            logger.error(f"Local model API error: {e}")
            raise

class AIAgent:
    """Base class for specialized AI agents"""
    
    def __init__(self, name: str, provider: AIProviderInterface, 
                 system_prompt: str, agent_config: Dict[str, Any] = None):
        self.name = name
        self.provider = provider
        self.system_prompt = system_prompt
        self.config = agent_config or {}
        self.results_cache = {}
    
    async def analyze(self, content: str, file_path: str = "", 
                     context: Dict[str, Any] = None) -> AIAnalysisResult:
        """Perform AI analysis on content"""
        start_time = time.time()
        
        try:
            # Get AI response
            ai_response = await self.provider.analyze_content(
                content=content,
                analysis_prompt=self.system_prompt,
                context=context
            )
            
            # Parse AI response
            findings = self._parse_ai_response(ai_response["response"])
            
            # Extract entities and tags
            entities = self._extract_entities(content, findings)
            tags = self._generate_tags(content, findings)
            
            # Calculate scores
            confidence = self._calculate_confidence(findings)
            probative_value = self._calculate_probative_value(findings)
            relevance_score = self._calculate_relevance(findings)
            
            # Create result
            result = AIAnalysisResult(
                agent_name=self.name,
                content_analyzed=content[:500] + "..." if len(content) > 500 else content,
                analysis_type=self.config.get("analysis_type", "general"),
                confidence_score=confidence,
                findings=findings,
                entities_found=entities,
                tags=tags,
                legal_significance=findings.get("legal_significance", ""),
                probative_value=probative_value,
                relevance_score=relevance_score,
                processing_time=time.time() - start_time,
                metadata={
                    "file_path": file_path,
                    "ai_provider": ai_response["provider"],
                    "model": ai_response["model"],
                    "tokens_used": ai_response["tokens_used"]
                },
                timestamp=datetime.now()
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Agent {self.name} analysis failed: {e}")
            # Return error result
            return AIAnalysisResult(
                agent_name=self.name,
                content_analyzed=content[:100] + "...",
                analysis_type="error",
                confidence_score=0.0,
                findings={"error": str(e)},
                entities_found=[],
                tags=["error"],
                legal_significance="Analysis failed",
                probative_value=0.0,
                relevance_score=0.0,
                processing_time=time.time() - start_time,
                metadata={"file_path": file_path, "error": True},
                timestamp=datetime.now()
            )
    
    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response into structured findings"""
        # Try to parse JSON if present
        try:
            # Look for JSON in the response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        # Fallback to text parsing
        return {
            "summary": response[:500],
            "full_response": response,
            "structured": False
        }
    
    def _extract_entities(self, content: str, findings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract entities from content"""
        entities = []
        
        # Basic entity extraction (can be enhanced with spaCy/transformers later)
        import re
        
        # Dates
        date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
        dates = re.findall(date_pattern, content)
        for date in dates:
            entities.append({"type": "date", "value": date, "confidence": 0.8})
        
        # Email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, content)
        for email in emails:
            entities.append({"type": "email", "value": email, "confidence": 0.9})
        
        # Phone numbers
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        phones = re.findall(phone_pattern, content)
        for phone in phones:
            entities.append({"type": "phone", "value": phone, "confidence": 0.7})
        
        # Dollar amounts
        money_pattern = r'\$[\d,]+\.?\d*'
        amounts = re.findall(money_pattern, content)
        for amount in amounts:
            entities.append({"type": "money", "value": amount, "confidence": 0.8})
        
        return entities
    
    def _generate_tags(self, content: str, findings: Dict[str, Any]) -> List[str]:
        """Generate tags for the content"""
        tags = []
        
        # Content-based tags
        content_lower = content.lower()
        
        # Legal concepts
        legal_keywords = {
            "contract": ["contract", "agreement", "terms"],
            "financial": ["money", "payment", "account", "bank"],
            "communication": ["email", "text", "message", "call"],
            "evidence": ["evidence", "proof", "document", "exhibit"],
            "misconduct": ["fraud", "perjury", "misconduct", "violation"]
        }
        
        for tag, keywords in legal_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                tags.append(tag)
        
        # Add findings-based tags
        if findings.get("legal_significance"):
            tags.append("legally_significant")
        
        if findings.get("confidence", 0) > 0.8:
            tags.append("high_confidence")
        
        return list(set(tags))  # Remove duplicates
    
    def _calculate_confidence(self, findings: Dict[str, Any]) -> float:
        """Calculate confidence score from findings"""
        if "confidence" in findings:
            return float(findings["confidence"])
        
        # Default calculation based on findings structure
        if findings.get("structured", False):
            return 0.8
        elif len(findings.get("full_response", "")) > 100:
            return 0.6
        else:
            return 0.3
    
    def _calculate_probative_value(self, findings: Dict[str, Any]) -> float:
        """Calculate probative value from findings"""
        if "probative_value" in findings:
            return float(findings["probative_value"])
        
        # Basic calculation
        legal_sig = findings.get("legal_significance", "").lower()
        if any(term in legal_sig for term in ["strong", "significant", "crucial"]):
            return 0.8
        elif any(term in legal_sig for term in ["relevant", "important", "useful"]):
            return 0.6
        else:
            return 0.4
    
    def _calculate_relevance(self, findings: Dict[str, Any]) -> float:
        """Calculate relevance score from findings"""
        if "relevance_score" in findings:
            return float(findings["relevance_score"])
        
        # Default relevance calculation
        return 0.5

class AIFoundationPlugin:
    """Main AI Foundation Plugin - orchestrates all AI functionality"""
    
    def __init__(self, config_path: str = "config/ai_config.json"):
        self.config_path = config_path
        self.providers = {}
        self.agents = {}
        self.results_storage = {}
        
        # Load configuration
        self.load_configuration()
        
        # Initialize providers
        self.initialize_providers()
        
        # Initialize agents
        self.initialize_agents()
    
    def load_configuration(self):
        """Load AI configuration from file"""
        if Path(self.config_path).exists():
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
        else:
            # Create default configuration
            self.config = self.create_default_config()
            self.save_configuration()
    
    def create_default_config(self) -> Dict[str, Any]:
        """Create default AI configuration"""
        return {
            "providers": {
                "openai": {
                    "provider_name": "openai",
                    "api_key": "",
                    "model": "gpt-4",
                    "temperature": 0.1,
                    "max_tokens": 4000,
                    "enabled": True
                },
                "anthropic": {
                    "provider_name": "anthropic",
                    "api_key": "",
                    "model": "claude-3-sonnet-20240229",
                    "temperature": 0.1,
                    "max_tokens": 4000,
                    "enabled": False
                },
                "local": {
                    "provider_name": "local",
                    "base_url": "http://localhost:11434",
                    "model": "llama2",
                    "temperature": 0.1,
                    "max_tokens": 4000,
                    "enabled": False
                }
            },
            "agents": {
                "document_intelligence": {
                    "enabled": True,
                    "provider": "openai",
                    "analysis_type": "document_analysis"
                },
                "legal_analysis": {
                    "enabled": True,
                    "provider": "openai",
                    "analysis_type": "legal_evaluation"
                },
                "pattern_discovery": {
                    "enabled": False,
                    "provider": "openai",
                    "analysis_type": "pattern_detection"
                }
            },
            "settings": {
                "max_concurrent_agents": 3,
                "enable_caching": True,
                "log_level": "INFO"
            }
        }
    
    def save_configuration(self):
        """Save configuration to file"""
        Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def initialize_providers(self):
        """Initialize AI providers"""
        for provider_name, provider_config in self.config["providers"].items():
            config = AIProviderConfig(**provider_config)
            
            if provider_name == "openai":
                self.providers[provider_name] = OpenAIProvider(config)
            elif provider_name == "anthropic":
                self.providers[provider_name] = AnthropicProvider(config)
            elif provider_name == "local":
                self.providers[provider_name] = LocalModelProvider(config)
        
        logger.info(f"Initialized {len(self.providers)} AI providers")
    
    def initialize_agents(self):
        """Initialize AI agents with their specialized prompts"""
        agent_prompts = {
            "document_intelligence": """You are a legal document intelligence agent specializing in evidence analysis for family law cases.

Your task is to analyze legal documents and extract key information for evidence organization.

For each document, provide a JSON response with:
{
  "document_type": "email|contract|financial_record|text_message|court_document|other",
  "key_parties": ["list of people mentioned"],
  "important_dates": ["list of dates found"],
  "financial_amounts": ["list of money amounts"],
  "legal_significance": "explanation of why this document matters legally",
  "evidence_category": "fraud_on_court|constitutional_violations|financial_nondisclosure|electronic_abuse|text_messages|other",
  "probative_value": 0.0-1.0,
  "relevance_score": 0.0-1.0,
  "confidence": 0.0-1.0,
  "summary": "2-3 sentence summary of document contents"
}

Focus on family law evidence, financial disclosure violations, fraud on the court, and abuse patterns.""",

            "legal_analysis": """You are a legal analysis agent specializing in family law evidence evaluation.

Your expertise includes:
- Rule 403 probative value vs prejudicial impact analysis
- Evidence admissibility under family law rules
- Financial disclosure requirements (FC 2107, FC 2122)
- Constitutional violations in family court proceedings
- Fraud on the court analysis

For each piece of evidence, provide:
{
  "admissibility_analysis": "detailed analysis of admissibility issues",
  "probative_value": 0.0-1.0,
  "prejudicial_impact": 0.0-1.0,
  "rule_403_analysis": "balancing test analysis",
  "legal_theory_support": ["list of legal theories this evidence supports"],
  "authentication_requirements": "what's needed to authenticate this evidence",
  "foundation_elements": ["list of foundation requirements"],
  "strategic_value": "high|medium|low",
  "recommended_use": "how to best use this evidence strategically",
  "confidence": 0.0-1.0
}

Focus on building the strongest possible case within evidence rules.""",

            "pattern_discovery": """You are a pattern discovery agent specializing in detecting abuse, fraud, and misconduct patterns in family law cases.

Look for patterns including:
- Financial fraud and asset hiding
- Abuse escalation patterns
- Electronic surveillance and stalking
- Fraud on the court behaviors
- Timeline inconsistencies
- Contradictory statements

For pattern analysis, provide:
{
  "patterns_detected": ["list of patterns found"],
  "pattern_strength": 0.0-1.0,
  "supporting_evidence": ["list of evidence supporting each pattern"],
  "timeline_analysis": "chronological pattern description",
  "behavioral_indicators": ["list of concerning behaviors identified"],
  "risk_assessment": "assessment of ongoing risk or escalation",
  "corroborating_evidence_needed": ["what additional evidence would strengthen the pattern"],
  "legal_implications": "how these patterns support legal arguments",
  "confidence": 0.0-1.0
}

Focus on identifying actionable patterns that strengthen the legal case."""
        }
        
        # Create agents
        for agent_name, agent_config in self.config["agents"].items():
            if agent_config["enabled"]:
                provider_name = agent_config["provider"]
                if provider_name in self.providers and self.providers[provider_name].is_available():
                    self.agents[agent_name] = AIAgent(
                        name=agent_name,
                        provider=self.providers[provider_name],
                        system_prompt=agent_prompts.get(agent_name, "Analyze the provided content."),
                        agent_config=agent_config
                    )
        
        logger.info(f"Initialized {len(self.agents)} AI agents")
    
    async def analyze_file_content(self, content: str, file_path: str = "", 
                                 agent_names: List[str] = None) -> Dict[str, AIAnalysisResult]:
        """Analyze file content using specified agents"""
        if agent_names is None:
            agent_names = list(self.agents.keys())
        
        results = {}
        
        # Run agents concurrently
        tasks = []
        for agent_name in agent_names:
            if agent_name in self.agents:
                task = self.agents[agent_name].analyze(
                    content=content,
                    file_path=file_path,
                    context={"file_path": file_path}
                )
                tasks.append((agent_name, task))
        
        # Execute tasks
        for agent_name, task in tasks:
            try:
                result = await task
                results[agent_name] = result
                logger.info(f"Agent {agent_name} completed analysis of {file_path}")
            except Exception as e:
                logger.error(f"Agent {agent_name} failed: {e}")
        
        return results
    
    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all AI providers"""
        status = {}
        for name, provider in self.providers.items():
            status[name] = {
                "available": provider.is_available(),
                "enabled": provider.config.enabled,
                "model": provider.config.model,
                "total_tokens_used": provider.total_tokens_used,
                "total_cost": provider.total_cost
            }
        return status
    
    def get_agent_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all AI agents"""
        status = {}
        for name, agent in self.agents.items():
            status[name] = {
                "enabled": True,
                "provider": agent.provider.config.provider_name,
                "provider_available": agent.provider.is_available(),
                "analysis_type": agent.config.get("analysis_type", "general")
            }
        return status
    
    def save_analysis_results(self, results: Dict[str, AIAnalysisResult], 
                            output_path: str):
        """Save analysis results to file"""
        serializable_results = {}
        for agent_name, result in results.items():
            serializable_results[agent_name] = result.to_dict()
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(serializable_results, f, indent=2)

# Plugin integration function for LCAS
def create_ai_plugin(lcas_config) -> AIFoundationPlugin:
    """Factory function to create and configure AI plugin for LCAS"""
    # Extract AI config from LCAS config if available
    config_path = "config/ai_config.json"
    
    # Create the plugin
    ai_plugin = AIFoundationPlugin(config_path)
    
    logger.info("AI Foundation Plugin created and ready for LCAS integration")
    return ai_plugin

# Example usage and testing
if __name__ == "__main__":
    async def test_ai_plugin():
        """Test the AI plugin functionality"""
        print("Testing AI Foundation Plugin...")
        
        # Create plugin
        plugin = AIFoundationPlugin()
        
        # Check provider status
        print("\nProvider Status:")
        for name, status in plugin.get_provider_status().items():
            print(f"  {name}: {'✓' if status['available'] else '✗'} ({status['model']})")
        
        # Check agent status
        print("\nAgent Status:")
        for name, status in plugin.get_agent_status().items():
            print(f"  {name}: {'✓' if status['enabled'] else '✗'} via {status['provider']}")
        
        # Test analysis (if any provider is available)
        available_providers = [name for name, status in plugin.get_provider_status().items() 
                             if status['available']]
        
        if available_providers:
            test_content = """
            This is a test email from Shane to Lisa dated 3/15/2023.
            Shane mentions hiding $50,000 in a crypto account and 
            threatens to file false police reports if Lisa contacts his attorney.
            The email contains evidence of financial non-disclosure and potential fraud.
            """
            
            print(f"\nTesting analysis with {available_providers[0]}...")
            results = await plugin.analyze_file_content(
                content=test_content,
                file_path="test_email.txt"
            )
            
            for agent_name, result in results.items():
                print(f"\n{agent_name} Results:")
                print(f"  Confidence: {result.confidence_score:.2f}")
                print(f"  Probative Value: {result.probative_value:.2f}")
                print(f"  Entities: {len(result.entities_found)}")
                print(f"  Tags: {', '.join(result.tags)}")
        else:
            print("\nNo AI providers available for testing")
            print("Configure OpenAI API key or set up local model to test")
    
    # Run test
    asyncio.run(test_ai_plugin())
