#!/usr/bin/env python3
"""
AI Integration Module for LCAS
Supports OpenAI-compatible APIs for enhanced legal analysis
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Union
import httpx
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class AIConfig:
    """Configuration for AI services"""
    provider: str = "openai"  # openai, anthropic, claude, local, custom
    api_key: str = ""
    model: str = "gpt-4"
    base_url: str = ""
    temperature: float = 0.1
    max_tokens: int = 4000
    timeout: int = 60
    max_retries: int = 3
    enabled: bool = False

@dataclass
class AIResponse:
    """Response from AI service"""
    content: str
    usage: Dict[str, int]
    model: str
    success: bool
    error: Optional[str] = None

class BaseAIProvider(ABC):
    """Abstract base class for AI providers"""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.client = None
        self._setup_client()
    
    @abstractmethod
    def _setup_client(self):
        """Setup the HTTP client for the provider"""
        pass
    
    @abstractmethod
    async def _make_request(self, messages: List[Dict[str, str]], **kwargs) -> AIResponse:
        """Make request to AI provider"""
        pass
    
    async def generate_completion(self, prompt: str, system_prompt: str = None, **kwargs) -> AIResponse:
        """Generate completion from prompt"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        return await self._make_request(messages, **kwargs)
    
    async def analyze_legal_content(self, content: str, analysis_type: str) -> AIResponse:
        """Analyze legal content with specialized prompts"""
        prompts = {
            "summary": self._get_summary_prompt(),
            "categorization": self._get_categorization_prompt(),
            "scoring": self._get_scoring_prompt(),
            "entity_extraction": self._get_entity_extraction_prompt(),
            "timeline": self._get_timeline_prompt()
        }
        
        if analysis_type not in prompts:
            return AIResponse("", {}, "", False, f"Unknown analysis type: {analysis_type}")
        
        system_prompt = prompts[analysis_type]["system"]
        user_prompt = prompts[analysis_type]["user"].format(content=content)
        
        return await self.generate_completion(user_prompt, system_prompt)
    
    def _get_summary_prompt(self) -> Dict[str, str]:
        """Get prompts for document summarization"""
        return {
            "system": """You are a legal document analysis expert. Your task is to create concise, accurate summaries of legal documents that capture the key facts, legal issues, and relevance to potential court arguments. Focus on probative value and admissibility concerns.""",
            "user": """Analyze this legal document and provide a structured summary:

Document Content:
{content}

Please provide:
1. Document Type: (e.g., email, court filing, financial record)
2. Key Facts: (bullet points of main factual content)
3. Legal Relevance: (how this might be used in court)
4. Potential Issues: (admissibility concerns, authentication needs)
5. Summary: (2-3 sentence overview)

Format your response as JSON with these exact keys: document_type, key_facts, legal_relevance, potential_issues, summary"""
        }
    
    def _get_categorization_prompt(self) -> Dict[str, str]:
        """Get prompts for document categorization"""
        return {
            "system": """You are a legal case organization expert. You categorize legal documents into specific folders based on their content and relevance to different legal arguments. You must be precise and consider the specific legal theories being pursued.""",
            "user": """Categorize this document into the most appropriate folder based on its content:

Document Content:
{content}

Available Categories:
- CASE_SUMMARIES_AND_RELATED_DOCS (authorities, analysis, statutes)
- CONSTITUTIONAL_VIOLATIONS (due process, peremptory challenge issues)
- ELECTRONIC_ABUSE (surveillance, hacking, privacy violations)
- FRAUD_ON_THE_COURT (evidence manipulation, perjury, ex parte communications)
- NON_DISCLOSURE_FC2107_FC2122 (financial disclosure violations)
- PD065288_COURT_RECORD_DOCS (official court documents)
- POST_TRIAL_ABUSE (continued violations after judgment)
- TEXT_MESSAGES (communications evidence)
- FOR_HUMAN_REVIEW (unclear or multiple categories)

Respond with JSON: {{"category": "folder_name", "confidence": 0.0-1.0, "reasoning": "explanation", "alternative_categories": ["alt1", "alt2"]}}"""
        }
    
    def _get_scoring_prompt(self) -> Dict[str, str]:
        """Get prompts for legal scoring"""
        return {
            "system": """You are a legal evidence evaluation expert. You assess the probative value, prejudicial impact, relevance, and admissibility of evidence for court proceedings. Consider Federal Rules of Evidence and California Evidence Code.""",
            "user": """Evaluate this evidence for court use:

Document Content:
{content}

Score each factor from 0.0 to 1.0:

1. Probative Value: How strongly does this prove or disprove a material fact?
2. Prejudicial Value: How likely is this to unfairly influence a jury? (higher = more prejudicial)
3. Relevance: How directly related is this to the legal issues?
4. Admissibility: How likely is this to be admitted as evidence?

Consider: authentication requirements, hearsay rules, privilege, Rule 403 balancing.

Respond with JSON: {{"probative_value": 0.0, "prejudicial_value": 0.0, "relevance": 0.0, "admissibility": 0.0, "overall_impact": 0.0, "reasoning": "detailed explanation"}}"""
        }
    
    def _get_entity_extraction_prompt(self) -> Dict[str, str]:
        """Get prompts for entity extraction"""
        return {
            "system": """You are a legal document entity extraction expert. Extract key entities that are relevant for legal analysis: people, organizations, dates, locations, financial amounts, legal concepts, and document references.""",
            "user": """Extract key entities from this legal document:

Document Content:
{content}

Extract:
- People: (names, roles, relationships)
- Organizations: (companies, law firms, courts)
- Dates: (important dates with context)
- Financial: (amounts, accounts, transactions)
- Legal: (case numbers, statutes, legal concepts)
- Communications: (email addresses, phone numbers)

Respond with JSON: {{"people": [], "organizations": [], "dates": [], "financial": [], "legal": [], "communications": [], "other": []}}"""
        }
    
    def _get_timeline_prompt(self) -> Dict[str, str]:
        """Get prompts for timeline extraction"""
        return {
            "system": """You are a legal timeline analysis expert. Extract chronological events from legal documents to build case timelines. Focus on actionable events, not just document dates.""",
            "user": """Extract timeline events from this document:

Document Content:
{content}

For each event, provide:
- Date (exact or approximate)
- Event description
- Participants
- Significance to the case

Respond with JSON: {{"events": [{{"date": "YYYY-MM-DD or estimate", "description": "what happened", "participants": ["who"], "significance": "why important"}}]}}"""
        }

class OpenAIProvider(BaseAIProvider):
    """OpenAI API provider"""
    
    def _setup_client(self):
        """Setup OpenAI client"""
        base_url = self.config.base_url or "https://api.openai.com/v1"
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            },
            timeout=self.config.timeout
        )
    
    async def _make_request(self, messages: List[Dict[str, str]], **kwargs) -> AIResponse:
        """Make request to OpenAI API"""
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens)
        }
        
        for attempt in range(self.config.max_retries):
            try:
                response = await self.client.post("/chat/completions", json=payload)
                response.raise_for_status()
                
                data = response.json()
                
                return AIResponse(
                    content=data["choices"][0]["message"]["content"],
                    usage=data.get("usage", {}),
                    model=data.get("model", self.config.model),
                    success=True
                )
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error (attempt {attempt + 1}): {e}")
                if attempt == self.config.max_retries - 1:
                    return AIResponse("", {}, "", False, f"HTTP error: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except Exception as e:
                logger.error(f"Request error (attempt {attempt + 1}): {e}")
                if attempt == self.config.max_retries - 1:
                    return AIResponse("", {}, "", False, f"Request error: {e}")
                await asyncio.sleep(2 ** attempt)

class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude API provider"""
    
    def _setup_client(self):
        """Setup Anthropic client"""
        base_url = self.config.base_url or "https://api.anthropic.com"
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "x-api-key": self.config.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            },
            timeout=self.config.timeout
        )
    
    async def _make_request(self, messages: List[Dict[str, str]], **kwargs) -> AIResponse:
        """Make request to Anthropic API"""
        # Convert OpenAI format to Anthropic format
        system_msg = ""
        user_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append(msg)
        
        payload = {
            "model": self.config.model,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "messages": user_messages
        }
        
        if system_msg:
            payload["system"] = system_msg
        
        for attempt in range(self.config.max_retries):
            try:
                response = await self.client.post("/v1/messages", json=payload)
                response.raise_for_status()
                
                data = response.json()
                
                return AIResponse(
                    content=data["content"][0]["text"],
                    usage=data.get("usage", {}),
                    model=data.get("model", self.config.model),
                    success=True
                )
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error (attempt {attempt + 1}): {e}")
                if attempt == self.config.max_retries - 1:
                    return AIResponse("", {}, "", False, f"HTTP error: {e}")
                await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                logger.error(f"Request error (attempt {attempt + 1}): {e}")
                if attempt == self.config.max_retries - 1:
                    return AIResponse("", {}, "", False, f"Request error: {e}")
                await asyncio.sleep(2 ** attempt)

class CustomProvider(BaseAIProvider):
    """Custom OpenAI-compatible API provider"""
    
    def _setup_client(self):
        """Setup custom API client"""
        self.client = httpx.AsyncClient(
            base_url=self.config.base_url,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            },
            timeout=self.config.timeout
        )
    
    async def _make_request(self, messages: List[Dict[str, str]], **kwargs) -> AIResponse:
        """Make request to custom OpenAI-compatible API"""
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens)
        }
        
        for attempt in range(self.config.max_retries):
            try:
                response = await self.client.post("/v1/chat/completions", json=payload)
                response.raise_for_status()
                
                data = response.json()
                
                return AIResponse(
                    content=data["choices"][0]["message"]["content"],
                    usage=data.get("usage", {}),
                    model=data.get("model", self.config.model),
                    success=True
                )
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error (attempt {attempt + 1}): {e}")
                if attempt == self.config.max_retries - 1:
                    return AIResponse("", {}, "", False, f"HTTP error: {e}")
                await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                logger.error(f"Request error (attempt {attempt + 1}): {e}")
                if attempt == self.config.max_retries - 1:
                    return AIResponse("", {}, "", False, f"Request error: {e}")
                await asyncio.sleep(2 ** attempt)

class AIService:
    """Main AI service that manages different providers"""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.provider = None
        self._setup_provider()
    
    def _setup_provider(self):
        """Setup the appropriate AI provider"""
        if not self.config.enabled:
            logger.info("AI service disabled")
            return
        
        provider_map = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "claude": AnthropicProvider,
            "custom": CustomProvider
        }
        
        if self.config.provider in provider_map:
            self.provider = provider_map[self.config.provider](self.config)
            logger.info(f"AI provider initialized: {self.config.provider}")
        else:
            logger.error(f"Unknown AI provider: {self.config.provider}")
    
    async def is_available(self) -> bool:
        """Check if AI service is available"""
        return self.config.enabled and self.provider is not None
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to AI service"""
        if not await self.is_available():
            return {"success": False, "error": "AI service not available"}
        
        try:
            response = await self.provider.generate_completion(
                "Test message. Please respond with 'Connection successful.'",
                "You are a test assistant. Respond briefly to test messages."
            )
            
            return {
                "success": response.success,
                "error": response.error,
                "model": response.model,
                "response": response.content[:100] if response.content else ""
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def summarize_document(self, content: str) -> Dict[str, Any]:
        """Generate document summary using AI"""
        if not await self.is_available():
            return {"success": False, "error": "AI service not available"}
        
        try:
            response = await self.provider.analyze_legal_content(content, "summary")
            
            if response.success:
                try:
                    parsed_response = json.loads(response.content)
                    return {
                        "success": True,
                        "summary": parsed_response,
                        "usage": response.usage
                    }
                except json.JSONDecodeError:
                    # Fallback to plain text summary
                    return {
                        "success": True,
                        "summary": {"summary": response.content},
                        "usage": response.usage
                    }
            else:
                return {"success": False, "error": response.error}
                
        except Exception as e:
            logger.error(f"Document summarization failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def categorize_document(self, content: str, folder_structure: Dict[str, List[str]]) -> Dict[str, Any]:
        """Categorize document using AI"""
        if not await self.is_available():
            return {"success": False, "error": "AI service not available"}
        
        try:
            # Include folder structure in the prompt
            categories_text = "\n".join([f"- {cat}" for cat in folder_structure.keys()])
            enhanced_content = f"Available categories:\n{categories_text}\n\nDocument to categorize:\n{content}"
            
            response = await self.provider.analyze_legal_content(enhanced_content, "categorization")
            
            if response.success:
                try:
                    parsed_response = json.loads(response.content)
                    return {
                        "success": True,
                        "categorization": parsed_response,
                        "usage": response.usage
                    }
                except json.JSONDecodeError:
                    return {"success": False, "error": "Invalid JSON response from AI"}
            else:
                return {"success": False, "error": response.error}
                
        except Exception as e:
            logger.error(f"Document categorization failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def score_evidence(self, content: str, category: str) -> Dict[str, Any]:
        """Score evidence using AI"""
        if not await self.is_available():
            return {"success": False, "error": "AI service not available"}
        
        try:
            enhanced_content = f"Document category: {category}\n\nDocument content:\n{content}"
            response = await self.provider.analyze_legal_content(enhanced_content, "scoring")
            
            if response.success:
                try:
                    parsed_response = json.loads(response.content)
                    return {
                        "success": True,
                        "scoring": parsed_response,
                        "usage": response.usage
                    }
                except json.JSONDecodeError:
                    return {"success": False, "error": "Invalid JSON response from AI"}
            else:
                return {"success": False, "error": response.error}
                
        except Exception as e:
            logger.error(f"Evidence scoring failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def extract_entities(self, content: str) -> Dict[str, Any]:
        """Extract entities using AI"""
        if not await self.is_available():
            return {"success": False, "error": "AI service not available"}
        
        try:
            response = await self.provider.analyze_legal_content(content, "entity_extraction")
            
            if response.success:
                try:
                    parsed_response = json.loads(response.content)
                    return {
                        "success": True,
                        "entities": parsed_response,
                        "usage": response.usage
                    }
                except json.JSONDecodeError:
                    return {"success": False, "error": "Invalid JSON response from AI"}
            else:
                return {"success": False, "error": response.error}
                
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def extract_timeline_events(self, content: str) -> Dict[str, Any]:
        """Extract timeline events using AI"""
        if not await self.is_available():
            return {"success": False, "error": "AI service not available"}
        
        try:
            response = await self.provider.analyze_legal_content(content, "timeline")
            
            if response.success:
                try:
                    parsed_response = json.loads(response.content)
                    return {
                        "success": True,
                        "timeline": parsed_response,
                        "usage": response.usage
                    }
                except json.JSONDecodeError:
                    return {"success": False, "error": "Invalid JSON response from AI"}
            else:
                return {"success": False, "error": response.error}
                
        except Exception as e:
            logger.error(f"Timeline extraction failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def generate_case_analysis(self, all_documents: List[Dict[str, Any]], case_context: str) -> Dict[str, Any]:
        """Generate comprehensive case analysis"""
        if not await self.is_available():
            return {"success": False, "error": "AI service not available"}
        
        try:
            # Prepare summary of all documents
            doc_summaries = []
            for doc in all_documents[:50]:  # Limit to prevent token overflow
                doc_summaries.append({
                    "file": doc.get("original_name", "Unknown"),
                    "category": doc.get("category", "Unknown"),
                    "summary": doc.get("summary", "")[:200]  # Truncate summaries
                })
            
            analysis_prompt = f"""
Case Context: {case_context}

Document Summaries: {json.dumps(doc_summaries, indent=2)}

Please provide a comprehensive legal case analysis including:
1. Case Overview: Summary of the overall legal situation
2. Strength Assessment: Evaluate the strength of different arguments
3. Key Evidence: Identify the most important pieces of evidence
4. Potential Challenges: Areas that need attention or additional evidence
5. Strategic Recommendations: Advice for proceeding with the case
6. Timeline Significance: Important chronological patterns

Format as JSON with these exact keys: case_overview, strength_assessment, key_evidence, potential_challenges, strategic_recommendations, timeline_significance
"""
            
            response = await self.provider.generate_completion(
                analysis_prompt,
                "You are an expert legal analyst specializing in case strategy and evidence evaluation."
            )
            
            if response.success:
                try:
                    parsed_response = json.loads(response.content)
                    return {
                        "success": True,
                        "analysis": parsed_response,
                        "usage": response.usage
                    }
                except json.JSONDecodeError:
                    return {
                        "success": True,
                        "analysis": {"case_overview": response.content},
                        "usage": response.usage
                    }
            else:
                return {"success": False, "error": response.error}
                
        except Exception as e:
            logger.error(f"Case analysis failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def close(self):
        """Close AI service connections"""
        if self.provider and self.provider.client:
            await self.provider.client.aclose()

# ================================
# AI-Enhanced LCAS Plugin
# ================================

class AIEnhancedLCASPlugin:
    """Plugin that integrates AI capabilities into LCAS"""
    
    def __init__(self, ai_config: AIConfig):
        self.ai_service = AIService(ai_config)
        self.usage_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "total_tokens": 0
        }
    
    async def enhance_file_analysis(self, file_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance file analysis with AI insights"""
        if not file_analysis.get("content"):
            return file_analysis
        
        try:
            # Generate AI summary
            if not file_analysis.get("summary"):
                summary_result = await self.ai_service.summarize_document(file_analysis["content"])
                if summary_result["success"]:
                    file_analysis["ai_summary"] = summary_result["summary"]
                    self._update_usage_stats(summary_result.get("usage", {}))
            
            # AI-powered categorization
            if not file_analysis.get("category") or file_analysis["category"] == "09_FOR_HUMAN_REVIEW":
                cat_result = await self.ai_service.categorize_document(
                    file_analysis["content"], 
                    self._get_folder_structure()
                )
                if cat_result["success"]:
                    file_analysis["ai_categorization"] = cat_result["categorization"]
                    self._update_usage_stats(cat_result.get("usage", {}))
            
            # AI evidence scoring
            if file_analysis.get("category"):
                score_result = await self.ai_service.score_evidence(
                    file_analysis["content"],
                    file_analysis["category"]
                )
                if score_result["success"]:
                    file_analysis["ai_scores"] = score_result["scoring"]
                    self._update_usage_stats(score_result.get("usage", {}))
            
            # Entity extraction
            entity_result = await self.ai_service.extract_entities(file_analysis["content"])
            if entity_result["success"]:
                file_analysis["ai_entities"] = entity_result["entities"]
                self._update_usage_stats(entity_result.get("usage", {}))
            
            # Timeline extraction
            timeline_result = await self.ai_service.extract_timeline_events(file_analysis["content"])
            if timeline_result["success"]:
                file_analysis["ai_timeline"] = timeline_result["timeline"]
                self._update_usage_stats(timeline_result.get("usage", {}))
            
            self.usage_stats["successful_requests"] += 1
            
        except Exception as e:
            logger.error(f"AI enhancement failed: {e}")
            file_analysis["ai_error"] = str(e)
        
        self.usage_stats["total_requests"] += 1
        return file_analysis
    
    async def generate_final_case_report(self, all_documents: List[Dict[str, Any]], case_context: str) -> Dict[str, Any]:
        """Generate AI-powered final case analysis report"""
        try:
            analysis_result = await self.ai_service.generate_case_analysis(all_documents, case_context)
            
            if analysis_result["success"]:
                self._update_usage_stats(analysis_result.get("usage", {}))
                return {
                    "success": True,
                    "report": analysis_result["analysis"],
                    "usage_stats": self.usage_stats.copy()
                }
            else:
                return {"success": False, "error": analysis_result["error"]}
                
        except Exception as e:
            logger.error(f"Final case report generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_folder_structure(self) -> Dict[str, List[str]]:
        """Get the standard LCAS folder structure"""
        return {
            "01_CASE_SUMMARIES_AND_RELATED_DOCS": ["AUTHORITIES", "DETAILED_ANALYSIS_OF_ARGUMENTS", "STATUTES"],
            "02_CONSTITUTIONAL_VIOLATIONS": ["PEREMPTORY_CHALLENGE"],
            "03_ELECTRONIC_ABUSE": [],
            "04_FRAUD_ON_THE_COURT": [
                "ATTORNEY_MISCONDUCT_MARK", "CURATED_TEXT_RECORD", "EVIDENCE_MANIPULATION",
                "EVIDENCE_OF_SOBRIETY", "EX_PARTE_COMMUNICATIONS", "JUDICIAL_MISCONDUCT",
                "NULL_AGREEMENT", "PHYSICAL_ASSAULTS_AND_COERCIVE_CONTROL"
            ],
            "05_NON_DISCLOSURE_FC2107_FC2122": [],
            "06_PD065288_COURT_RECORD_DOCS": [],
            "07_POST_TRIAL_ABUSE": [],
            "08_TEXT_MESSAGES": [
                "SHANE_TO_FRIENDS", "SHANE_TO_KATHLEEN_MCCABE", "SHANE_TO_LISA",
                "SHANE_TO_MARK_ZUCKER", "SHANE_TO_RHONDA_ZUCKER"
            ],
            "09_FOR_HUMAN_REVIEW": []
        }
    
    def _update_usage_stats(self, usage: Dict[str, int]):
        """Update usage statistics"""
        if "total_tokens" in usage:
            self.usage_stats["total_tokens"] += usage["total_tokens"]
        elif "prompt_tokens" in usage and "completion_tokens" in usage:
            self.usage_stats["total_tokens"] += usage["prompt_tokens"] + usage["completion_tokens"]
    
    async def close(self):
        """Close AI service"""
        await self.ai_service.close()
    
    def get_usage_report(self) -> Dict[str, Any]:
        """Get AI usage statistics"""
        return {
            "total_requests": self.usage_stats["total_requests"],
            "successful_requests": self.usage_stats["successful_requests"],
            "success_rate": (
                self.usage_stats["successful_requests"] / max(self.usage_stats["total_requests"], 1)
            ) * 100,
            "total_tokens_used": self.usage_stats["total_tokens"],
            "average_tokens_per_request": (
                self.usage_stats["total_tokens"] / max(self.usage_stats["successful_requests"], 1)
            )
        }

# Example usage
async def main():
    """Example of using the AI integration"""
    # Configure AI
    ai_config = AIConfig(
        provider="openai",
        api_key="your-api-key-here",
        model="gpt-4",
        enabled=True
    )
    
    # Create AI plugin
    ai_plugin = AIEnhancedLCASPlugin(ai_config)
    
    # Test connection
    ai_service = AIService(ai_config)
    connection_test = await ai_service.test_connection()
    print(f"Connection test: {connection_test}")
    
    # Example file analysis enhancement
    sample_file_analysis = {
        "original_name": "sample_document.pdf",
        "content": "This is a sample legal document content for testing AI integration...",
        "category": ""
    }
    
    enhanced_analysis = await ai_plugin.enhance_file_analysis(sample_file_analysis)
    print(f"Enhanced analysis keys: {list(enhanced_analysis.keys())}")
    
    # Get usage report
    usage_report = ai_plugin.get_usage_report()
    print(f"AI Usage Report: {usage_report}")
    
    # Clean up
    await ai_plugin.close()
    await ai_service.close()

if __name__ == "__main__":
    asyncio.run(main())
            "