#!/usr/bin/env python3
"""
AI Image Analysis Plugin for LCAS
Deep visual analysis for evidence discovery and pattern recognition
"""

import base64
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import json
from dataclasses import dataclass
from PIL import Image, ImageEnhance
import fitz  # PyMuPDF for PDF image extraction
import cv2
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class ImageAnalysisResult:
    """Result from image analysis"""
    file_path: str
    image_count: int
    visual_description: str
    text_content: str  # OCR results
    evidence_type: str  # screenshot, document, photo, etc.
    abuse_indicators: List[str]
    financial_evidence: List[str]
    communication_evidence: List[str]
    timestamp_info: List[str]
    metadata: Dict[str, Any]
    confidence_scores: Dict[str, float]

class ImageAnalysisPlugin:
    """Plugin for comprehensive image analysis in legal evidence"""
    
    def __init__(self, config, ai_service=None):
        self.config = config
        self.ai_service = ai_service
        self._setup_dependencies()
    
    def _setup_dependencies(self):
        """Setup required libraries for image processing"""
        self.libraries = {}
        
        # OCR capability
        try:
            import pytesseract
            self.libraries['pytesseract'] = pytesseract
        except ImportError:
            logger.warning("pytesseract not available - OCR will be limited")
        
        # Advanced image processing
        try:
            import cv2
            self.libraries['cv2'] = cv2
        except ImportError:
            logger.warning("opencv not available - advanced image processing disabled")
        
        # PDF image extraction
        try:
            import fitz  # PyMuPDF
            self.libraries['fitz'] = fitz
        except ImportError:
            logger.warning("PyMuPDF not available - PDF image extraction disabled")
    
    async def analyze_file_images(self, file_path: Path, file_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze all images in a file for legal evidence"""
        try:
            images = self._extract_images_from_file(file_path)
            
            if not images:
                return file_analysis
            
            # Analyze each image
            image_analyses = []
            for i, (image_data, image_info) in enumerate(images):
                analysis = await self._analyze_single_image(
                    image_data, 
                    f"{file_path.stem}_image_{i}",
                    image_info
                )
                image_analyses.append(analysis)
            
            # Aggregate results
            file_analysis['image_analysis'] = self._aggregate_image_analysis(image_analyses)
            file_analysis['has_images'] = True
            file_analysis['image_count'] = len(images)
            
            # Update file categorization based on image content
            file_analysis = self._update_categorization_from_images(file_analysis)
            
            return file_analysis
            
        except Exception as e:
            logger.error(f"Image analysis failed for {file_path}: {e}")
            file_analysis['image_analysis_error'] = str(e)
            return file_analysis
    
    def _extract_images_from_file(self, file_path: Path) -> List[Tuple[bytes, Dict[str, Any]]]:
        """Extract images from various file types"""
        images = []
        file_ext = file_path.suffix.lower()
        
        try:
            if file_ext == '.pdf':
                images = self._extract_from_pdf(file_path)
            elif file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']:
                images = self._extract_from_image_file(file_path)
            elif file_ext in ['.docx']:
                images = self._extract_from_docx(file_path)
            # Add more file types as needed
            
        except Exception as e:
            logger.error(f"Error extracting images from {file_path}: {e}")
        
        return images
    
    def _extract_from_pdf(self, file_path: Path) -> List[Tuple[bytes, Dict[str, Any]]]:
        """Extract images from PDF files"""
        images = []
        
        if 'fitz' not in self.libraries:
            return images
        
        try:
            pdf_doc = self.libraries['fitz'].open(file_path)
            
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    pix = self.libraries['fitz'].Pixmap(pdf_doc, xref)
                    
                    if pix.n - pix.alpha < 4:  # GRAY or RGB
                        img_data = pix.tobytes("png")
                        img_info = {
                            'source': 'PDF',
                            'page': page_num + 1,
                            'index': img_index,
                            'width': pix.width,
                            'height': pix.height
                        }
                        images.append((img_data, img_info))
                    
                    pix = None
            
            pdf_doc.close()
            
        except Exception as e:
            logger.error(f"Error extracting from PDF {file_path}: {e}")
        
        return images
    
    def _extract_from_image_file(self, file_path: Path) -> List[Tuple[bytes, Dict[str, Any]]]:
        """Extract from standalone image files"""
        try:
            with open(file_path, 'rb') as f:
                img_data = f.read()
            
            # Get image info
            with Image.open(file_path) as img:
                img_info = {
                    'source': 'Image File',
                    'format': img.format,
                    'width': img.width,
                    'height': img.height,
                    'mode': img.mode
                }
            
            return [(img_data, img_info)]
            
        except Exception as e:
            logger.error(f"Error reading image file {file_path}: {e}")
            return []
    
    def _extract_from_docx(self, file_path: Path) -> List[Tuple[bytes, Dict[str, Any]]]:
        """Extract images from DOCX files"""
        images = []
        
        try:
            import zipfile
            from xml.etree import ElementTree
            
            with zipfile.ZipFile(file_path, 'r') as docx:
                # Look for images in media folder
                media_files = [f for f in docx.namelist() if f.startswith('word/media/')]
                
                for media_file in media_files:
                    if any(media_file.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
                        img_data = docx.read(media_file)
                        img_info = {
                            'source': 'DOCX',
                            'filename': media_file.split('/')[-1]
                        }
                        images.append((img_data, img_info))
        
        except Exception as e:
            logger.error(f"Error extracting from DOCX {file_path}: {e}")
        
        return images
    
    async def _analyze_single_image(self, image_data: bytes, image_name: str, image_info: Dict[str, Any]) -> ImageAnalysisResult:
        """Analyze a single image for legal evidence"""
        try:
            # Convert to PIL Image for processing
            image = Image.open(io.BytesIO(image_data))
            
            # Enhance image quality if needed
            enhanced_image = self._enhance_image_quality(image)
            
            # OCR text extraction
            text_content = self._extract_text_from_image(enhanced_image)
            
            # AI-powered visual analysis
            visual_analysis = await self._ai_visual_analysis(image_data, text_content)
            
            # Pattern recognition for abuse indicators
            abuse_indicators = self._detect_abuse_patterns(text_content, visual_analysis)
            
            # Financial evidence detection
            financial_evidence = self._detect_financial_evidence(text_content, visual_analysis)
            
            # Communication evidence detection
            communication_evidence = self._detect_communication_evidence(text_content, visual_analysis)
            
            # Timestamp extraction
            timestamp_info = self._extract_timestamps(text_content, image_info)
            
            return ImageAnalysisResult(
                file_path=image_name,
                image_count=1,
                visual_description=visual_analysis.get('description', ''),
                text_content=text_content,
                evidence_type=visual_analysis.get('evidence_type', 'unknown'),
                abuse_indicators=abuse_indicators,
                financial_evidence=financial_evidence,
                communication_evidence=communication_evidence,
                timestamp_info=timestamp_info,
                metadata=image_info,
                confidence_scores=visual_analysis.get('confidence_scores', {})
            )
            
        except Exception as e:
            logger.error(f"Error analyzing image {image_name}: {e}")
            return ImageAnalysisResult(
                file_path=image_name,
                image_count=0,
                visual_description="Analysis failed",
                text_content="",
                evidence_type="error",
                abuse_indicators=[],
                financial_evidence=[],
                communication_evidence=[],
                timestamp_info=[],
                metadata={},
                confidence_scores={}
            )
    
    def _enhance_image_quality(self, image: Image.Image) -> Image.Image:
        """Enhance image quality for better OCR"""
        try:
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Enhance contrast and sharpness
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)
            
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.1)
            
            return image
            
        except Exception as e:
            logger.error(f"Error enhancing image: {e}")
            return image
    
    def _extract_text_from_image(self, image: Image.Image) -> str:
        """Extract text using OCR"""
        if 'pytesseract' not in self.libraries:
            return ""
        
        try:
            # Use pytesseract with optimal settings for screenshots/documents
            custom_config = r'--oem 3 --psm 6'
            text = self.libraries['pytesseract'].image_to_string(image, config=custom_config)
            return text.strip()
            
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""
    
    async def _ai_visual_analysis(self, image_data: bytes, text_content: str) -> Dict[str, Any]:
        """Use AI to analyze image content for legal context"""
        if not self.ai_service:
            return {
                'description': 'AI analysis not available',
                'evidence_type': 'unknown',
                'confidence_scores': {}
            }
        
        try:
            # Encode image for AI analysis
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            analysis_prompt = f"""
Analyze this image in the context of legal evidence for a divorce/family court case. 
Consider patterns of abuse, financial misconduct, custody issues, and communication evidence.

OCR Text Found: {text_content[:1000]}

Please identify:
1. Type of evidence (screenshot, document, photo, financial record, communication, etc.)
2. Visual description of what's shown
3. Potential legal relevance (abuse indicators, financial hiding, parental fitness, etc.)
4. Specific details that might be important in court
5. Confidence levels for your assessments

Focus on patterns that might not be obvious to someone under stress.
Look for signs of coercive control, financial abuse, or custody manipulation.
"""
            
            response = await self.ai_service.provider.generate_completion(
                analysis_prompt,
                "You are an expert in domestic violence patterns and family court evidence analysis."
            )
            
            if response.success:
                try:
                    # Try to parse as JSON, fall back to text analysis
                    analysis = json.loads(response.content)
                except json.JSONDecodeError:
                    analysis = {
                        'description': response.content,
                        'evidence_type': 'document',
                        'confidence_scores': {'overall': 0.7}
                    }
                
                return analysis
            
        except Exception as e:
            logger.error(f"AI visual analysis failed: {e}")
        
        return {
            'description': 'AI analysis failed',
            'evidence_type': 'unknown',
            'confidence_scores': {}
        }
    
    def _detect_abuse_patterns(self, text_content: str, visual_analysis: Dict[str, Any]) -> List[str]:
        """Detect patterns indicative of abuse"""
        abuse_indicators = []
        text_lower = text_content.lower()
        
        # Common abuse pattern keywords
        abuse_keywords = [
            'threatened', 'scared', 'afraid', 'intimidate', 'control',
            'punish', 'hurt', 'hit', 'push', 'shove', 'grab',
            'isolate', 'monitor', 'track', 'follow', 'stalk',
            'take the kids', 'never see them again', 'bad mother',
            'crazy', 'unstable', 'unfit', 'mental', 'therapy',
            'rehab', 'treatment', 'drug', 'alcohol', 'addict'
        ]
        
        # Financial abuse patterns
        financial_abuse_keywords = [
            'hide money', 'secret account', 'transfer', 'spend',
            'credit card', 'debt', 'loan', 'investment', 'crypto',
            'bitcoin', 'cash', 'withdraw', 'deposit'
        ]
        
        # Check for abuse language patterns
        for keyword in abuse_keywords:
            if keyword in text_lower:
                abuse_indicators.append(f"Contains abuse-related language: '{keyword}'")
        
        # Check for financial control patterns
        for keyword in financial_abuse_keywords:
            if keyword in text_lower:
                abuse_indicators.append(f"Financial control indicator: '{keyword}'")
        
        # Check AI analysis for additional patterns
        ai_description = visual_analysis.get('description', '').lower()
        if 'threatening' in ai_description or 'intimidating' in ai_description:
            abuse_indicators.append("AI detected threatening content")
        
        if 'surveillance' in ai_description or 'monitoring' in ai_description:
            abuse_indicators.append("AI detected surveillance/monitoring evidence")
        
        return abuse_indicators
    
    def _detect_financial_evidence(self, text_content: str, visual_analysis: Dict[str, Any]) -> List[str]:
        """Detect financial evidence patterns"""
        financial_evidence = []
        text_lower = text_content.lower()
        
        # Look for financial document indicators
        financial_keywords = [
            'account', 'balance', 'statement', 'transaction',
            'deposit', 'withdrawal', 'transfer', 'payment',
            'bitcoin', 'cryptocurrency', 'coinbase', 'wallet',
            'investment', 'stock', 'bond', 'asset', 'property',
            'income', 'salary', 'wage', 'bonus', 'commission'
        ]
        
        for keyword in financial_keywords:
            if keyword in text_lower:
                financial_evidence.append(f"Financial keyword detected: '{keyword}'")
        
        # Look for dollar amounts
        import re
        dollar_pattern = r'\$[\d,]+\.?\d*'
        dollar_matches = re.findall(dollar_pattern, text_content)
        if dollar_matches:
            financial_evidence.append(f"Dollar amounts found: {', '.join(dollar_matches[:5])}")
        
        # Account numbers pattern
        account_pattern = r'\b\d{4,16}\b'
        if re.search(account_pattern, text_content):
            financial_evidence.append("Potential account numbers detected")
        
        return financial_evidence
    
    def _detect_communication_evidence(self, text_content: str, visual_analysis: Dict[str, Any]) -> List[str]:
        """Detect communication evidence patterns"""
        communication_evidence = []
        
        # Check for messaging app indicators
        messaging_keywords = [
            'imessage', 'text message', 'whatsapp', 'telegram',
            'facebook', 'messenger', 'instagram', 'snapchat',
            'email', 'gmail', 'yahoo', 'outlook'
        ]
        
        text_lower = text_content.lower()
        for keyword in messaging_keywords:
            if keyword in text_lower:
                communication_evidence.append(f"Communication platform: {keyword}")
        
        # Look for phone numbers
        import re
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        if re.search(phone_pattern, text_content):
            communication_evidence.append("Phone numbers detected")
        
        # Look for email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if re.search(email_pattern, text_content):
            communication_evidence.append("Email addresses detected")
        
        # Check AI analysis for communication indicators
        ai_description = visual_analysis.get('description', '').lower()
        if 'screenshot' in ai_description and ('message' in ai_description or 'chat' in ai_description):
            communication_evidence.append("AI detected message screenshot")
        
        return communication_evidence
    
    def _extract_timestamps(self, text_content: str, image_info: Dict[str, Any]) -> List[str]:
        """Extract timestamp information from images"""
        timestamps = []
        
        # Look for date/time patterns in text
        import re
        
        # Various date patterns
        date_patterns = [
            r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',  # MM/DD/YYYY
            r'\b\d{1,2}-\d{1,2}-\d{2,4}\b',  # MM-DD-YYYY
            r'\b\d{4}-\d{1,2}-\d{1,2}\b',    # YYYY-MM-DD
            r'\b[A-Za-z]{3}\s+\d{1,2},?\s+\d{4}\b',  # Jan 1, 2024
        ]
        
        # Time patterns
        time_patterns = [
            r'\b\d{1,2}:\d{2}\s*[AaPp][Mm]\b',  # 12:34 PM
            r'\b\d{1,2}:\d{2}:\d{2}\b',         # 12:34:56
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text_content)
            for match in matches:
                timestamps.append(f"Date found: {match}")
        
        for pattern in time_patterns:
            matches = re.findall(pattern, text_content)
            for match in matches:
                timestamps.append(f"Time found: {match}")
        
        return timestamps
    
    def _aggregate_image_analysis(self, image_analyses: List[ImageAnalysisResult]) -> Dict[str, Any]:
        """Aggregate results from multiple image analyses"""
        if not image_analyses:
            return {}
        
        # Combine all findings
        all_text = "\n".join([analysis.text_content for analysis in image_analyses])
        all_abuse_indicators = []
        all_financial_evidence = []
        all_communication_evidence = []
        all_timestamps = []
        
        for analysis in image_analyses:
            all_abuse_indicators.extend(analysis.abuse_indicators)
            all_financial_evidence.extend(analysis.financial_evidence)
            all_communication_evidence.extend(analysis.communication_evidence)
            all_timestamps.extend(analysis.timestamp_info)
        
        return {
            'total_images': len(image_analyses),
            'combined_text': all_text,
            'abuse_indicators': list(set(all_abuse_indicators)),
            'financial_evidence': list(set(all_financial_evidence)),
            'communication_evidence': list(set(all_communication_evidence)),
            'timestamps': list(set(all_timestamps)),
            'evidence_types': [analysis.evidence_type for analysis in image_analyses]
        }
    
    def _update_categorization_from_images(self, file_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Update file categorization based on image analysis results"""
        if 'image_analysis' not in file_analysis:
            return file_analysis
        
        image_data = file_analysis['image_analysis']
        
        # Boost scores based on image evidence
        if image_data.get('abuse_indicators'):
            if 'FRAUD_ON_THE_COURT' in str(file_analysis.get('category', '')):
                file_analysis['probative_value'] = min(1.0, file_analysis.get('probative_value', 0) + 0.3)
            if 'ELECTRONIC_ABUSE' in str(file_analysis.get('category', '')):
                file_analysis['probative_value'] = min(1.0, file_analysis.get('probative_value', 0) + 0.2)
        
        if image_data.get('financial_evidence'):
            if 'NON_DISCLOSURE' in str(file_analysis.get('category', '')):
                file_analysis['probative_value'] = min(1.0, file_analysis.get('probative_value', 0) + 0.4)
        
        if image_data.get('communication_evidence'):
            if 'TEXT_MESSAGES' in str(file_analysis.get('category', '')):
                file_analysis['probative_value'] = min(1.0, file_analysis.get('probative_value', 0) + 0.2)
        
        return file_analysis