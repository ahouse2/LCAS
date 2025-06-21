"""
Content Extraction Plugin for LCAS
Handles extraction of text content from various file formats
"""
import logging; from pathlib import Path; from typing import Dict, Any, Optional, List, Tuple; import asyncio; import tkinter as tk # Added tk for create_ui
from dataclasses import asdict # Added asdict for output
from lcas2.core import AnalysisPlugin, LCASCore
from lcas2.core.data_models import FileAnalysisData, FileExtractionMetadata # Import the model

logger = logging.getLogger(__name__)
class ContentExtractionPlugin(AnalysisPlugin):
    @property
    def name(self) -> str: return "Content Extraction"
    @property
    def version(self) -> str: return "1.1.0" # Version update
    @property
    def description(self) -> str: return "Extracts text and basic metadata, populating FileAnalysisData objects."
    @property
    def dependencies(self) -> List[str]: return []

    async def initialize(self, core_app: LCASCore) -> bool:
        self.core = core_app; self.logger = core_app.logger.getChild(self.name)
        self.supported_types = {.txt: self._extract_text, .rtf: self._extract_rtf, .pdf: self._extract_pdf, .docx: self._extract_docx, .doc: self._extract_doc, .xlsx: self._extract_excel, .xls: self._extract_excel, .csv: self._extract_csv, .eml: self._extract_email, .msg: self._extract_msg }
        self.libraries = {}; await asyncio.to_thread(self._import_optional_libraries)
        self.logger.info(f"{self.name} initialized. Optional libraries: {list(self.libraries.keys())}"); return True
    async def cleanup(self) -> None: self.logger.info(f"{self.name} cleaned up.")

    def _import_optional_libraries(self): # Sync method
        try: import PyPDF2; self.libraries[PyPDF2] = PyPDF2
        except ImportError: self.logger.warning("PyPDF2 not available for basic PDF metadata.")
        try: import pdfplumber; self.libraries[pdfplumber] = pdfplumber;
        except ImportError: self.logger.warning("pdfplumber not available for PDF text extraction.")
        try: import docx; self.libraries[docx] = docx; # python-docx
        except ImportError: self.logger.warning("python-docx not available for .docx files.")
        try: import openpyxl; self.libraries[openpyxl] = openpyxl;
        except ImportError: self.logger.warning("openpyxl not available for .xlsx files.")
        try: import pandas as pd; self.libraries[pandas] = pd;
        except ImportError: self.logger.warning("pandas not available for .csv/.xls files.")
        try: import email; import email.policy; self.libraries[email] = email; self.libraries[email.policy] = email.policy
        except ImportError: self.logger.warning("email library not available for .eml files.")
        try: import extract_msg; self.libraries[extract_msg] = extract_msg;
        except ImportError: self.logger.warning("extract_msg library not available for .msg files.")
        # For .doc, textract might be an option but has external dependencies (antiword, etc.)
        # For now, .doc extraction will be minimal or rely on user having textract and its deps installed.


    def _extract_content_for_file_sync(self, file_path: Path) -> FileAnalysisData:
        fad = FileAnalysisData(file_path=str(file_path)) # file_name is auto-populated by __post_init__
        fad.extraction_meta = FileExtractionMetadata()

        extension = file_path.suffix.lower()
        content = None
        metadata_dict : Dict[str, Any] = {"format_detected": extension[1:].upper() if extension else "Unknown"}

        try:
            if extension in self.supported_types:
                content, meta_update = self.supported_types[extension](file_path)
                metadata_dict.update(meta_update)
                fad.content = content
                if content:
                    fad.summary_auto = self._generate_basic_summary(content)
                    metadata_dict[word_count] = len(content.split())
                    metadata_dict[character_count] = len(content)
            else:
                fad.content_extraction_error = f"Unsupported file type: {extension}"
                self.logger.warning(f"Unsupported file type: {file_path}")
        except Exception as e:
            fad.content_extraction_error = str(e)
            self.logger.error(f"Error extracting content from {file_path}: {e}", exc_info=True)

        fad.extraction_meta = FileExtractionMetadata(**metadata_dict)
        return fad

    async def analyze(self, data: Any) -> Dict[str, Any]:
        source_dir_str = data.get("source_directory", self.core.config.source_directory if self.core and hasattr(self.core, config) else None)
        if not source_dir_str: return {"plugin": self.name, "status": "error", "success": False, "error": "Source directory not provided."}

        source_dir = Path(source_dir_str)
        if not await asyncio.to_thread(source_dir.is_dir): # Check dir async
             return {"plugin": self.name, "status": "error", "success": False, "error": f"Source dir not found: {source_dir}"}

        self.logger.info(f"Starting content extraction from: {source_dir}")
        output_processed_files: Dict[str, FileAnalysisData] = {}
        files_extracted_content = 0; files_failed = 0

        # Gather file paths asynchronously to avoid blocking if dir is huge
        all_file_paths = await asyncio.to_thread(lambda: [p for p in source_dir.rglob("*") if p.is_file()])

        tasks = [asyncio.to_thread(self._extract_content_for_file_sync, fp) for fp in all_file_paths]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        for res_or_exc in results_list:
            if isinstance(res_or_exc, FileAnalysisData):
                output_processed_files[res_or_exc.file_path] = res_or_exc
                if res_or_exc.content or res_or_exc.ocr_text_from_images: # Count if any text was found
                    files_extracted_content += 1
                elif res_or_exc.content_extraction_error : files_failed += 1
                # If no content and no error, it might be an empty file or unsupported type handled gracefully
            elif isinstance(res_or_exc, Exception):
                self.logger.error(f"Unhandled exception during extraction task: {res_or_exc}", exc_info=res_or_exc); files_failed += 1
            else: self.logger.error(f"Unknown result type from extraction: {type(res_or_exc)}"); files_failed +=1

        self.logger.info(f"Content extraction complete. Extracted text from: {files_extracted_content} files. Failed/No content: {files_failed} files.")
        return {"plugin": self.name, "status": "completed" if files_failed == 0 else "completed_with_errors",
                "success": True,
                "summary": {"total_files_processed": len(all_file_paths), "successful_extractions": files_extracted_content, "extraction_errors": files_failed},
                "processed_files_output": {k: asdict(v) for k, v in output_processed_files.items()}
               }

    def _extract_text(self, file_path: Path) -> Tuple[Optional[str], Dict[str, Any]]:
        try:
            with open(file_path, r, encoding=utf-8, errors=ignore) as f: content = f.read()
            return content, {"extraction_method": "standard_text_read"}
        except Exception as e: self.logger.error(f"TXT extract error {file_path}: {e}"); return None, {"error": str(e)}
    def _extract_rtf(self, file_path: Path) -> Tuple[Optional[str], Dict[str, Any]]: return self._extract_text(file_path)

    def _extract_pdf(self, file_path: Path) -> Tuple[Optional[str], Dict[str, Any]]:
        text_content = ""
        page_count = 0
        meta = {"extraction_method": "none"}
        if pdfplumber in self.libraries:
            try:
                with self.libraries[pdfplumber].open(file_path) as pdf:
                    page_count = len(pdf.pages)
                    for page in pdf.pages: text_content += (page.extract_text() or "") + "\n"
                meta["extraction_method"] = "pdfplumber"
            except Exception as e: self.logger.error(f"pdfplumber error {file_path}: {e}"); text_content = "" # Reset if failed

        if not text_content and PyPDF2 in self.libraries: # Fallback or for metadata
            try:
                with open(file_path, rb) as f:
                    reader = self.libraries[PyPDF2].PdfReader(f)
                    page_count = len(reader.pages)
                    if not text_content: # Only use PyPDF2 for text if pdfplumber failed
                        for i in range(page_count): text_content += (reader.pages[i].extract_text() or "") + "\n"
                        meta["extraction_method"] = "PyPDF2_fallback" if meta["extraction_method"] == "pdfplumber" else "PyPDF2"
            except Exception as e: self.logger.error(f"PyPDF2 error {file_path}: {e}")
        meta["page_count"] = page_count
        return text_content, meta

    def _extract_docx(self, file_path: Path) -> Tuple[Optional[str], Dict[str, Any]]:
        if docx in self.libraries:
            try:
                doc = self.libraries[docx].Document(file_path)
                return "\n".join([para.text for para in doc.paragraphs]), {"extraction_method": "python-docx"}
            except Exception as e: self.logger.error(f"DOCX extract error {file_path}: {e}"); return None, {"error": str(e)}
        return None, {"error":"python-docx not available"}
    def _extract_doc(self, file_path: Path) -> Tuple[Optional[str], Dict[str, Any]]:
        # Consider using textract or antiword via subprocess if available and allowed
        self.logger.warning(f".doc file {file_path} - basic extraction attempt, may miss content. Consider converting to .docx.")
        try: # Extremely basic, likely fails for complex .doc
            with open(file_path, rb) as f: content = f.read().decode(latin-1, errors=ignore)
            return content, {"extraction_method": "basic_binary_decode", "warning": "Legacy .doc format, extraction may be incomplete."}
        except Exception as e: return None, {"error": str(e), "warning": "Legacy .doc format."}

    def _extract_excel(self, file_path: Path) -> Tuple[Optional[str], Dict[str, Any]]:
        all_text = []
        if openpyxl in self.libraries and file_path.suffix.lower() == .xlsx:
            try:
                workbook = self.libraries[openpyxl].load_workbook(file_path, read_only=True, data_only=True)
                for sheet_name in workbook.sheetnames:
                    all_text.append(f"Sheet: {sheet_name}\n")
                    sheet = workbook[sheet_name]
                    for row in sheet.iter_rows():
                        row_text = [str(cell.value) if cell.value is not None else "" for cell in row]
                        all_text.append(", ".join(row_text))
                return "\n".join(all_text), {"extraction_method": "openpyxl"}
            except Exception as e: self.logger.error(f"XLSX (openpyxl) extract error {file_path}: {e}"); return None, {"error": str(e)}
        elif pandas in self.libraries: # Fallback for .xls or if openpyxl fails for .xlsx
             try:
                excel_file = self.libraries[pandas].ExcelFile(file_path)
                for sheet_name in excel_file.sheet_names:
                    all_text.append(f"Sheet: {sheet_name}\n")
                    df = excel_file.parse(sheet_name)
                    all_text.append(df.to_string())
                return "\n".join(all_text), {"extraction_method": "pandas"}
             except Exception as e: self.logger.error(f"Excel (pandas) extract error {file_path}: {e}"); return None, {"error": str(e)}
        return None, {"error":"No suitable Excel library (openpyxl/pandas) available."}

    def _extract_csv(self, file_path: Path) -> Tuple[Optional[str], Dict[str, Any]]:
        if pandas in self.libraries:
            try:
                df = self.libraries[pandas].read_csv(file_path)
                return df.to_string(), {"extraction_method": "pandas"}
            except Exception as e: self.logger.error(f"CSV extract error {file_path}: {e}"); return None, {"error": str(e)}
        return self._extract_text(file_path) # Fallback to plain text

    def _extract_email(self, file_path: Path) -> Tuple[Optional[str], Dict[str, Any]]:
        if email in self.libraries:
            try:
                with open(file_path, rb) as f: msg = self.libraries[email].message_from_binary_file(f, policy=self.libraries[email.policy].default)
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if part.get_payload(decode=True) and content_type == text/plain: body += part.get_payload(decode=True).decode(errors=ignore) + "\n"
                else:
                    if msg.get_payload(decode=True): body = msg.get_payload(decode=True).decode(errors=ignore)
                headers = "\n".join([f"{k}: {v}" for k,v in msg.items()])
                return f"Headers:\n{headers}\n\nBody:\n{body}", {"extraction_method": "email_lib"}
            except Exception as e: self.logger.error(f"EML extract error {file_path}: {e}"); return None, {"error": str(e)}
        return None, {"error":"email library not available."}

    def _extract_msg(self, file_path: Path) -> Tuple[Optional[str], Dict[str, Any]]:
        if extract_msg in self.libraries:
            try:
                msg = self.libraries[extract_msg].Message(file_path)
                return f"From: {msg.sender}\nTo: {msg.to}\nSubject: {msg.subject}\nDate: {msg.date}\n\nBody:\n{msg.body}", {"extraction_method": "extract_msg"}
            except Exception as e: self.logger.error(f"MSG extract error {file_path}: {e}"); return None, {"error": str(e)}
        return None, {"error":"extract_msg library not available."}

    def _generate_basic_summary(self, content: str, max_len: int = 500) -> str:
        if not content: return ""
        # Simple first N chars summary
        return content[:max_len] + "..." if len(content) > max_len else content

    def create_ui_elements(self, parent_widget) -> List[tk.Widget]:
        from tkinter import ttk # Local import for UI method
        frame = ttk.Frame(parent_widget); frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(frame, text=f"{self.name}: Extracts text content from files. Output used by other plugins.").pack(side=tk.LEFT, padx=2)
        return [frame]
