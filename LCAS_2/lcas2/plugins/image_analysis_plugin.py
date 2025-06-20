#!/usr/bin/env python3
"""
AI Image Analysis Plugin for LCAS
Deep visual analysis for evidence discovery and pattern recognition
"""

import base64
import io
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import json # Added
import re # Added
from dataclasses import dataclass, asdict, field
import asyncio
# import tkinter as tk # For UI elements - import within method

from lcas2.core import AnalysisPlugin, LCASCore, UIPlugin # Added UIPlugin
from lcas2.core.data_models import FileAnalysisData, FileExtractionMetadata

Image = None; ImageEnhance = None; fitz = None; cv2 = None; np = None; pytesseract = None
logger = logging.getLogger(__name__)

@dataclass
class ImageAnalysisResultData:
    """Result from analysis of a single image within a file"""
    image_sub_id: str
    original_file_path: str
    visual_description: str = ""
    text_content: str = ""
    evidence_type_classification: str = "unknown_image_type" # Matched to new prompt
    abuse_indicators: List[str] = field(default_factory=list)
    financial_evidence: List[str] = field(default_factory=list)
    communication_evidence: List[str] = field(default_factory=list)
    timestamp_info: List[str] = field(default_factory=list)
    image_metadata: Dict[str, Any] = field(default_factory=dict)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    significant_elements_observed: List[str] = field(default_factory=list) # New from prompt
    document_type_guess_if_scan: str = "N/A" # New from prompt
    contextual_relevance_notes: str = "" # New from prompt
    analysis_error: Optional[str] = None

class ImageAnalysisPlugin(AnalysisPlugin, UIPlugin):
    SUPPORTED_FILE_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif', '.docx']
    @property
    def name(self) -> str: return "Image Analysis"
    @property
    def version(self) -> str: return "1.1.1" # Version update
    @property
    def description(self) -> str: return "Extracts images, OCRs, and uses AI for visual analysis (refined prompts)."
    @property
    def dependencies(self) -> List[str]: return ["lcas_ai_wrapper_plugin", "Content Extraction"]

    async def initialize(self, core_app: LCASCore) -> bool:
        self.core = core_app; self.logger = core_app.logger.getChild(self.name); self.ai_service = None
        ai_wrapper_name = getattr(self.core.config, 'ai_wrapper_plugin_name', 'lcas_ai_wrapper_plugin')
        loaded_ai_wrapper = self.core.plugin_manager.loaded_plugins.get(ai_wrapper_name)
        if loaded_ai_wrapper:
            if hasattr(loaded_ai_wrapper, 'ai_foundation') and loaded_ai_wrapper.ai_foundation:
                self.ai_service = loaded_ai_wrapper.ai_foundation
                self.logger.info("AI Foundation service accessed for Image Analysis.")
            else: self.logger.warning("ImageAnalysis: AI Wrapper loaded, but AI Foundation attribute unavailable.")
        else: self.logger.warning(f"ImageAnalysis: AI Wrapper plugin '{ai_wrapper_name}' not loaded. AI visual analysis will be limited.")

        self.libraries = {};
        await asyncio.to_thread(self._setup_dependencies)
        self.logger.info(f"{self.name} initialized. Optional libs: {list(self.libraries.keys())}");
        return True

    def _setup_dependencies(self):
        global Image, ImageEnhance, fitz, cv2, np, pytesseract
        try: from PIL import Image as PILImage, ImageEnhance as PILImageEnhance; Image = PILImage; ImageEnhance = PILImageEnhance; self.libraries['Pillow'] = True;
        except ImportError: self.logger.warning("Pillow (PIL) not available.")
        try: import pytesseract as tsrct; pytesseract = tsrct; self.libraries['pytesseract'] = True;
        except ImportError: self.logger.warning("pytesseract not available.")
        try: import fitz as fz; fitz = fz; self.libraries['PyMuPDF'] = True;
        except ImportError: self.logger.warning("PyMuPDF (fitz) not available.")
        try: import cv2 as c2; cv2 = c2; self.libraries['OpenCV'] = True;
        except ImportError: self.logger.warning("OpenCV (cv2) not available.")
        try: import numpy as nump; np = nump; self.libraries['NumPy'] = True;
        except ImportError: self.logger.warning("Numpy not available.")
        try: import docx; self.libraries['python-docx'] = docx;
        except ImportError: self.logger.warning("python-docx not available for DOCX image extraction.")


    async def cleanup(self) -> None: self.logger.info(f"{self.name} cleaned up.")

    async def analyze(self, data: Any) -> Dict[str, Any]:
        processed_files_input_any: Any = data.get("processed_files", {})
        if not isinstance(processed_files_input_any, dict):
             self.logger.error(f"Expected 'processed_files' to be a Dict, got {type(processed_files_input_any)}.")
             return {"plugin": self.name, "status": "error", "success": False, "message": "Invalid 'processed_files' format."}
        processed_files_input: Dict[str, Any] = processed_files_input_any


        if not processed_files_input: return {"plugin": self.name, "status": "no_data", "success": False, "message": "No 'processed_files' data."}

        self.logger.info(f"Starting image analysis for {len(processed_files_input)} input files.")
        files_with_images_found = 0; total_images_analyzed = 0
        output_fad_dict: Dict[str, FileAnalysisData] = {}

        for original_file_path_str, fad_object_or_dict in processed_files_input.items():
            fad_instance: Optional[FileAnalysisData] = None
            if isinstance(fad_object_or_dict, FileAnalysisData): fad_instance = fad_object_or_dict
            elif isinstance(fad_object_or_dict, dict):
                try: fad_instance = FileAnalysisData(**fad_object_or_dict)
                except TypeError as te: self.logger.warning(f"Cannot cast to FAD for {original_file_path_str}, skipping image analysis: {te}"); continue
            if not fad_instance: continue
            output_fad_dict[original_file_path_str] = fad_instance


            file_path_obj = Path(original_file_path_str)
            if file_path_obj.suffix.lower() not in self.SUPPORTED_FILE_EXTENSIONS: continue

            self.logger.debug(f"Processing for images: {file_path_obj.name}")
            try:
                extracted_images_tuples: List[Tuple[bytes, Dict[str, Any]]] = await asyncio.to_thread(self._extract_images_from_file, file_path_obj)
                if not extracted_images_tuples: continue

                files_with_images_found += 1
                current_file_ocr_texts: List[str] = []
                current_file_image_analysis_results: List[ImageAnalysisResultData] = []

                analysis_tasks = []
                for i, (img_bytes, img_info) in enumerate(extracted_images_tuples):
                    img_sub_id = f"{file_path_obj.stem}_p{img_info.get('page_num',0)}_idx{img_info.get('image_index_on_page',i)}"
                    analysis_tasks.append(self._analyze_single_image(img_bytes, img_sub_id, original_file_path_str, img_info, fad_instance))

                gathered_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
                for res_or_exc in gathered_results:
                    if isinstance(res_or_exc, ImageAnalysisResultData):
                        current_file_image_analysis_results.append(res_or_exc)
                        if res_or_exc.text_content: current_file_ocr_texts.append(res_or_exc.text_content)
                        total_images_analyzed +=1
                    elif isinstance(res_or_exc, Exception): self.logger.error(f"Error analyzing sub-image in {original_file_path_str}: {res_or_exc}", exc_info=res_or_exc)

                if current_file_image_analysis_results: fad_instance.image_analysis_results = [asdict(res) for res in current_file_image_analysis_results]
                if current_file_ocr_texts: fad_instance.ocr_text_from_images = "\n\n--- OCR Page/Image Separator ---\n\n".join(current_file_ocr_texts)
                if not fad_instance.content and fad_instance.ocr_text_from_images:
                    fad_instance.content = fad_instance.ocr_text_from_images
                    fad_instance.extraction_meta = fad_instance.extraction_meta or FileExtractionMetadata();
                    fad_instance.extraction_meta.format_detected = fad_instance.extraction_meta.format_detected or "Image_OCR_Primary"
                    # No 'content_extracted' field on FileAnalysisData
            except Exception as e: self.logger.error(f"Failed image processing for {original_file_path_str}: {e}", exc_info=True); fad_instance.error_log.append(f"ImageAnalysisPlugin Error: {e}")

        return {"plugin": self.name, "status": "completed", "success": True,
                "summary": {"files_with_images_found": files_with_images_found, "total_images_analyzed": total_images_analyzed},
                "processed_files_output": {k:asdict(v) for k,v in output_fad_dict.items()}}

    def _extract_images_from_file(self, file_path: Path) -> List[Tuple[bytes, Dict[str, Any]]]:
        ext = file_path.suffix.lower()
        if ext == '.pdf' and self.libraries.get('PyMuPDF'): return self._extract_from_pdf_fitz(file_path)
        if ext == '.docx' and self.libraries.get('python-docx'): return self._extract_from_docx(file_path)
        if ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif'] and self.libraries.get('Pillow'): return self._extract_from_image_file(file_path)
        return []

    def _extract_from_pdf_fitz(self, file_path: Path) -> List[Tuple[bytes, Dict[str, Any]]]:
        images_data = []
        try:
            doc = fitz.open(file_path) # type: ignore
            for page_num in range(len(doc)):
                image_list = doc.get_page_images(page_num)
                for img_index, img_info in enumerate(image_list):
                    xref = img_info[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_meta = {"source_page": page_num + 1, "image_index_on_page": img_index, "format": base_image["ext"], "width": base_image["width"], "height": base_image["height"]}
                    images_data.append((image_bytes, image_meta))
            doc.close()
        except Exception as e: self.logger.error(f"Error extracting images from PDF {file_path} with PyMuPDF: {e}", exc_info=True)
        return images_data

    def _extract_from_image_file(self, file_path: Path) -> List[Tuple[bytes, Dict[str, Any]]]:
        try:
            with open(file_path, 'rb') as f: image_bytes = f.read()
            img = Image.open(io.BytesIO(image_bytes)) # type: ignore
            image_meta = {"format": img.format, "width": img.width, "height": img.height, "mode": img.mode}
            return [(image_bytes, image_meta)]
        except Exception as e: self.logger.error(f"Error reading image file {file_path}: {e}", exc_info=True); return []

    def _extract_from_docx(self, file_path: Path) -> List[Tuple[bytes, Dict[str, Any]]]:
        images_data = [];
        if not self.libraries.get('python-docx'): return []
        doc = self.libraries['python-docx'].Document(file_path)
        try:
            for i, rel_id in enumerate(doc.part.rels):
                rel = doc.part.rels[rel_id]
                if "image" in rel.target_ref:
                    image_bytes = rel.target_part.blob
                    image_meta = {"source_docx_relation_id": rel_id, "image_index_in_docx": i, "filename": Path(rel.target_ref).name}
                    images_data.append((image_bytes, image_meta))
        except Exception as e: self.logger.error(f"Error extracting images from DOCX {file_path}: {e}", exc_info=True)
        return images_data

    async def _analyze_single_image(self, image_bytes: bytes, image_sub_id: str, original_file_path: str, image_info_meta: Dict[str, Any], fad_context: FileAnalysisData) -> ImageAnalysisResultData:
        text_content = ""; visual_desc = "N/A"; evidence_type_cls = "unknown_image_type"; confidence = {}; sig_elements = []; doc_type_guess = "N/A"; context_notes = ""
        analysis_error_str : Optional[str] = None
        try:
            enhanced_image_pil = await asyncio.to_thread(self._enhance_image_quality_sync_bytes, image_bytes)
            text_content = await asyncio.to_thread(self._perform_ocr_on_image, enhanced_image_pil) if enhanced_image_pil else ""

            ai_analysis_results_dict = {}
            if self.ai_service :
                 case_context_for_ai = {
                    "lcas_case_type": self.core.config.case_theory.case_type if self.core.config.case_theory else "general",
                    "lcas_jurisdiction": getattr(self.core.config.case_theory, 'jurisdiction', "US_Federal") if self.core.config.case_theory else "US_Federal",
                    "lcas_user_scenario_details": getattr(self.core.config.case_theory, 'user_scenario_description', "No specific scenario.") if self.core.config.case_theory else "No specific scenario.",
                    "parent_document_summary": fad_context.summary_auto or fad_context.ai_summary or ""
                 }
                 ai_analysis_results_dict = await self._ai_visual_analysis(image_bytes, text_content[:1000], case_context_for_ai)
                 visual_desc = ai_analysis_results_dict.get('visual_description', visual_desc)
                 evidence_type_cls = ai_analysis_results_dict.get('evidence_type_classification', evidence_type_cls)
                 confidence['overall_visual_analysis_confidence'] = ai_analysis_results_dict.get('overall_confidence', 0.0)
                 sig_elements = ai_analysis_results_dict.get('significant_elements_observed', [])
                 doc_type_guess = ai_analysis_results_dict.get('document_type_guess_if_scan', 'N/A')
                 context_notes = ai_analysis_results_dict.get('contextual_relevance_notes', '')

            else: self.logger.info(f"AI service not available/enabled, skipping AI visual analysis for {image_sub_id}")

            combined_text_for_rules = text_content + "\n" + visual_desc
            abuse_indicators = self._detect_abuse_patterns(combined_text_for_rules, ai_analysis_results_dict)
            financial_evidence = self._detect_financial_evidence(combined_text_for_rules, ai_analysis_results_dict)
            communication_evidence = self._detect_communication_evidence(combined_text_for_rules, ai_analysis_results_dict)
            timestamp_info = self._extract_timestamps(combined_text_for_rules, image_info_meta)

        except Exception as e:
            self.logger.error(f"Error analyzing single image {image_sub_id} from {original_file_path}: {e}", exc_info=True)
            analysis_error_str = str(e)

        return ImageAnalysisResultData(
            image_sub_id=image_sub_id, original_file_path=original_file_path,
            visual_description=visual_desc, text_content=text_content or "",
            evidence_type_classification=evidence_type_cls,
            abuse_indicators=abuse_indicators, financial_evidence=financial_evidence,
            communication_evidence=communication_evidence, timestamp_info=timestamp_info,
            image_metadata=image_info_meta, confidence_scores=confidence,
            significant_elements_observed=sig_elements, document_type_guess_if_scan=doc_type_guess,
            contextual_relevance_notes=context_notes, analysis_error=analysis_error_str
        )

    def _enhance_image_quality_sync_bytes(self, image_bytes: bytes) -> Optional[Any]:
        if not Image or not self.libraries.get('NumPy') or not self.libraries.get('OpenCV'): return None
        try:
            img_array = np.frombuffer(image_bytes, np.uint8) # type: ignore
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR) # type: ignore
            if img is None: self.logger.warning("cv2.imdecode returned None"); return None
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) # type: ignore
            enhanced = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2) # type: ignore
            is_success, buffer = cv2.imencode(".png", enhanced) # type: ignore
            if not is_success: self.logger.warning("cv2.imencode failed"); return None
            return Image.open(io.BytesIO(buffer)) # type: ignore
        except Exception as e: self.logger.error(f"Error enhancing image: {e}"); return None

    def _perform_ocr_on_image(self, image_pil: Any) -> str:
        if not self.libraries.get('pytesseract') or not image_pil : return ""
        try: return pytesseract.image_to_string(image_pil) # type: ignore
        except Exception as e: self.logger.error(f"OCR error: {e}"); return ""

    async def _ai_visual_analysis(self, image_bytes: bytes, ocr_text_snippet: str, case_context_for_ai: Dict[str, Any]) -> Dict[str, Any]:
        """Refined prompt for image visual analysis, expecting structured JSON."""
        if not self.ai_service or not hasattr(self.ai_service, 'execute_custom_prompt'):
            self.logger.error("AI service or execute_custom_prompt NA for visual analysis.")
            return {"visual_description": "AI Service N/A", "evidence_type_classification": "unknown_no_ai", "overall_confidence": 0.0, "error_message": "AI service unavailable"}

        # Image is not directly sent in this text-only prompt; AI infers from context and OCR.
        # For multimodal models, image_bytes would be encoded (e.g. base64) and sent.
        # The prompt is adjusted to reflect this text-only analysis of an image's properties.

        system_prompt = f"You are an AI assistant specialized in analyzing descriptions and OCR text from images to infer their content and potential as legal evidence. The case is a '{case_context_for_ai.get('lcas_case_type', 'general')}' matter in '{case_context_for_ai.get('lcas_jurisdiction', 'US_Federal')}'. Focus on objective visual details suggested by the text and their potential relevance. Respond ONLY with the specified JSON structure."

        json_schema_example = {
            "visual_description": "string (Detailed, objective description of what the image likely contains, based on OCR and context: people, objects, setting, actions, text visible).",
            "evidence_type_classification": "string (e.g., Screenshot of Text Conversation, Scanned Financial Document, Photograph of Event, Photograph of Injury, Diagram, Other).",
            "significant_elements_observed": ["list of strings (Key visual elements that would be relevant if present, inferred from OCR/context, e.g., 'Timestamp on screenshot', 'Signature on document', 'Visible injury on person')."],
            "document_type_guess_if_scan": "string (If OCR suggests a scan/photo of a document, what type? e.g., 'Contract', 'Medical Bill'. Else 'N/A').",
            "contextual_relevance_notes": "string (Brief notes on how this image (based on its inferred content) might be relevant given the OCR text and case context provided by user.)",
            "overall_confidence": "float (0.0-1.0, your confidence in this *inferred* visual analysis based *only* on the provided text information)"
        }
        json_example_str = json.dumps(json_schema_example)

        user_prompt = f"""
**Image Context:**
- Parent Document (if applicable): Summarized as: "{case_context_for_ai.get('parent_document_summary', 'N/A')}"
- Case Type: {case_context_for_ai.get('lcas_case_type', 'general')}
- User Scenario: {case_context_for_ai.get('lcas_user_scenario_details', 'N/A')}

**OCR'd Text Snippet from this specific image (if any, max 1000 chars):**
"{ocr_text_snippet[:1000]}"

**Your Task:**
Based *only* on the OCR'd text (if any) and the general context that this is an image:
1.  Describe what such an image might visually contain.
2.  Classify the type of evidence the image likely represents.
3.  Identify elements that would be legally significant if visually present (inferred from OCR/context).
4.  If OCR suggests a scan/photo of a document, guess the document type.
5.  Briefly note its contextual relevance.
6.  Provide an overall confidence score for your *inferred* analysis based *only* on the provided text information.

Respond ONLY with a single JSON object matching this structure (values are type hints/examples):
{json_example_str}
"""
        try:
            ai_response_data = await self.ai_service.execute_custom_prompt(
                system_prompt=system_prompt, user_prompt=user_prompt,
                context_for_ai_run={"task": "image_visual_analysis_from_text_structured"}
            )
            if ai_response_data and ai_response_data.get("success"):
                response_content = ai_response_data.get("response", "")
                match = re.search(r'\{[\s\S]*?\}', response_content, re.DOTALL)
                if match: return json.loads(match.group(0))
                self.logger.error(f"Image AI JSON error: {response_content}"); return {"visual_description": response_content, "overall_confidence":0.1, "error_parsing": True, "error_message": "AI response not valid JSON" }
            else:
                err_msg = ai_response_data.get('error', 'Unknown AI error') if ai_response_data else 'No AI response'
                self.logger.error(f"Image AI task failed: {err_msg}"); return {"error_message": f"AI task failed: {err_msg}"}
        except Exception as e: self.logger.error(f"Exception in AI visual analysis: {e}", exc_info=True); return {"error_message": f"Exception: {str(e)}"}

    def _detect_abuse_patterns(self, text_content: str, visual_analysis: Dict[str, Any]) -> List[str]: return []
    def _detect_financial_evidence(self, text_content: str, visual_analysis: Dict[str, Any]) -> List[str]: return []
    def _detect_communication_evidence(self, text_content: str, visual_analysis: Dict[str, Any]) -> List[str]: return []
    def _extract_timestamps(self, text_content: str, image_info: Dict[str, Any]) -> List[str]: return []

    def create_ui_elements(self, parent_widget) -> List[Any]:
        try:
            import tkinter as tk_ui
            from tkinter import ttk
        except ImportError:
            self.logger.warning("Tkinter not available for ImageAnalysisPlugin UI.")
            return []

        frame = ttk.Frame(parent_widget); frame.pack(fill=tk_ui.X, padx=5, pady=2)
        label = ttk.Label(frame, text=f"{self.name}: Extracts and analyzes images from files.")
        label.pack(side=tk_ui.LEFT, padx=2)
        return [frame]
