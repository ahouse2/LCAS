"""
Content Extraction Plugin for LCAS
Handles extraction of text content from various file formats
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ContentExtractionPlugin:
    """Plugin for extracting content from various file types"""

    def __init__(self, config):
        self.config = config
        self.supported_types = {
            '.txt': self._extract_text,
            '.rtf': self._extract_rtf,
            '.pdf': self._extract_pdf,
            '.docx': self._extract_docx,
            '.doc': self._extract_doc,
            '.xlsx': self._extract_excel,
            '.xls': self._extract_excel,
            '.csv': self._extract_csv,
            '.eml': self._extract_email,
            '.msg': self._extract_msg
        }

        # Try to import optional libraries
        self._import_optional_libraries()

    def _import_optional_libraries(self):
        """Import optional libraries for enhanced content extraction"""
        self.libraries = {}

        # PDF extraction
        try:
            import PyPDF2
            self.libraries['PyPDF2'] = PyPDF2
        except ImportError:
            logger.warning(
                "PyPDF2 not available - PDF extraction will be limited")

        try:
            import pdfplumber
            self.libraries['pdfplumber'] = pdfplumber
        except ImportError:
            logger.warning(
                "pdfplumber not available - advanced PDF extraction disabled")

        # Word document extraction
        try:
            import docx
            self.libraries['docx'] = docx
        except ImportError:
            logger.warning(
                "python-docx not available - DOCX extraction disabled")

        # Excel extraction
        try:
            import openpyxl
            self.libraries['openpyxl'] = openpyxl
        except ImportError:
            logger.warning(
                "openpyxl not available - Excel extraction disabled")

        try:
            import pandas as pd
            self.libraries['pandas'] = pd
        except ImportError:
            logger.warning("pandas not available - CSV/Excel analysis limited")

        # Email extraction
        try:
            import email
            import email.policy
            self.libraries['email'] = email
        except ImportError:
            logger.warning(
                "email library not available - email extraction disabled")

    def extract_content(self, file_path: Path,
                        file_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract content from a file based on its type"""
        try:
            extension = file_path.suffix.lower()

            if extension in self.supported_types:
                content, metadata = self.supported_types[extension](file_path)
                file_analysis['content'] = content
                file_analysis['extraction_metadata'] = metadata
                file_analysis['content_extracted'] = True

                # Generate basic summary if content was extracted
                if content:
                    file_analysis['summary'] = self._generate_basic_summary(
                        content)
                    file_analysis['word_count'] = len(content.split())
                    file_analysis['character_count'] = len(content)
            else:
                file_analysis['content'] = ""
                file_analysis['extraction_metadata'] = {}
                file_analysis['content_extracted'] = False
                logger.warning(
                    f"Unsupported file type for content extraction: {extension}")

        except Exception as e:
            file_analysis['content'] = ""
            file_analysis['extraction_metadata'] = {}
            file_analysis['content_extracted'] = False
            file_analysis['extraction_error'] = str(e)
            logger.error(f"Error extracting content from {file_path}: {e}")

        return file_analysis

    def _extract_text(self, file_path: Path) -> tuple[str, Dict[str, Any]]:
        """Extract content from plain text files"""
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252', 'ascii']

            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()

                    metadata = {
                        'encoding_used': encoding,
                        'line_count': content.count('\n') + 1
                    }

                    return content, metadata

                except UnicodeDecodeError:
                    continue

            # If all encodings fail, read as binary and decode with
            # errors='ignore'
            with open(file_path, 'rb') as f:
                content = f.read().decode('utf-8', errors='ignore')

            metadata = {
                'encoding_used': 'utf-8 (with errors ignored)',
                'line_count': content.count('\n') + 1
            }

            return content, metadata

        except Exception as e:
            logger.error(f"Error reading text file {file_path}: {e}")
            return "", {"error": str(e)}

    def _extract_rtf(self, file_path: Path) -> tuple[str, Dict[str, Any]]:
        """Extract content from RTF files (basic implementation)"""
        try:
            # For now, treat as text file - in production, use RTF parser
            content, metadata = self._extract_text(file_path)
            metadata['format'] = 'RTF (basic extraction)'
            return content, metadata
        except Exception as e:
            logger.error(f"Error reading RTF file {file_path}: {e}")
            return "", {"error": str(e)}

    def _extract_pdf(self, file_path: Path) -> tuple[str, Dict[str, Any]]:
        """Extract content from PDF files"""
        content = ""
        metadata = {"format": "PDF"}

        # Try pdfplumber first (better for complex layouts)
        if 'pdfplumber' in self.libraries:
            try:
                with self.libraries['pdfplumber'].open(file_path) as pdf:
                    pages_text = []
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            pages_text.append(page_text)

                    content = '\n\n'.join(pages_text)
                    metadata.update({
                        'page_count': len(pdf.pages),
                        'extraction_method': 'pdfplumber'
                    })

                    return content, metadata

            except Exception as e:
                logger.warning(
                    f"pdfplumber extraction failed for {file_path}: {e}")

        # Fall back to PyPDF2
        if 'PyPDF2' in self.libraries:
            try:
                with open(file_path, 'rb') as f:
                    pdf_reader = self.libraries['PyPDF2'].PdfReader(f)
                    pages_text = []

                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            pages_text.append(page_text)

                    content = '\n\n'.join(pages_text)
                    metadata.update({
                        'page_count': len(pdf_reader.pages),
                        'extraction_method': 'PyPDF2'
                    })

                    return content, metadata

            except Exception as e:
                logger.error(f"PyPDF2 extraction failed for {file_path}: {e}")

        # If no PDF library is available
        metadata['error'] = 'No PDF extraction library available'
        return content, metadata

    def _extract_docx(self, file_path: Path) -> tuple[str, Dict[str, Any]]:
        """Extract content from DOCX files"""
        if 'docx' not in self.libraries:
            return "", {"error": "python-docx library not available"}

        try:
            doc = self.libraries['docx'].Document(file_path)
            paragraphs = []

            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    paragraphs.append(paragraph.text)

            content = '\n'.join(paragraphs)

            metadata = {
                'format': 'DOCX',
                'paragraph_count': len(paragraphs),
                'extraction_method': 'python-docx'
            }

            return content, metadata

        except Exception as e:
            logger.error(
                f"Error extracting DOCX content from {file_path}: {e}")
            return "", {"error": str(e)}

    def _extract_doc(self, file_path: Path) -> tuple[str, Dict[str, Any]]:
        """Extract content from legacy DOC files"""
        # Legacy DOC files require specialized libraries (python-docx doesn't support them)
        # For now, return empty content with a note
        metadata = {
            'format': 'DOC (legacy)',
            'error': 'Legacy DOC format extraction not implemented - convert to DOCX'
        }
        return "", metadata

    def _extract_excel(self, file_path: Path) -> tuple[str, Dict[str, Any]]:
        """Extract content from Excel files"""
        if 'pandas' not in self.libraries:
            return "", {
                "error": "pandas library not available for Excel extraction"}

        try:
            # Read all sheets
            excel_data = self.libraries['pandas'].read_excel(
                file_path, sheet_name=None)

            content_parts = []
            sheet_info = {}

            for sheet_name, df in excel_data.items():
                # Convert dataframe to string representation
                sheet_content = f"Sheet: {sheet_name}\n"
                sheet_content += df.to_string(index=False)
                content_parts.append(sheet_content)

                sheet_info[sheet_name] = {
                    'rows': len(df),
                    'columns': len(df.columns),
                    'column_names': list(df.columns)
                }

            content = '\n\n' + '=' * 50 + '\n\n'.join(content_parts)

            metadata = {
                'format': 'Excel',
                'sheet_count': len(excel_data),
                'sheets_info': sheet_info,
                'extraction_method': 'pandas'
            }

            return content, metadata

        except Exception as e:
            logger.error(
                f"Error extracting Excel content from {file_path}: {e}")
            return "", {"error": str(e)}

    def _extract_csv(self, file_path: Path) -> tuple[str, Dict[str, Any]]:
        """Extract content from CSV files"""
        if 'pandas' in self.libraries:
            try:
                df = self.libraries['pandas'].read_csv(file_path)
                content = df.to_string(index=False)

                metadata = {
                    'format': 'CSV',
                    'rows': len(df),
                    'columns': len(df.columns),
                    'column_names': list(df.columns),
                    'extraction_method': 'pandas'
                }

                return content, metadata

            except Exception as e:
                logger.warning(
                    f"Pandas CSV extraction failed for {file_path}: {e}")

        # Fall back to basic text extraction
        return self._extract_text(file_path)

    def _extract_email(self, file_path: Path) -> tuple[str, Dict[str, Any]]:
        """Extract content from EML email files"""
        if 'email' not in self.libraries:
            return "", {"error": "email library not available"}

        try:
            with open(file_path, 'rb') as f:
                msg = self.libraries['email'].message_from_bytes(
                    f.read(),
                    policy=self.libraries['email'].policy.default
                )

            # Extract basic email information
            subject = msg.get('Subject', 'No Subject')
            from_addr = msg.get('From', 'Unknown Sender')
            to_addr = msg.get('To', 'Unknown Recipient')
            date = msg.get('Date', 'Unknown Date')

            # Extract body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_content()
                        break
            else:
                body = msg.get_content()

            # Format content
            content = f"""Subject: {subject}
From: {from_addr}
To: {to_addr}
Date: {date}

{body}"""

            metadata = {
                'format': 'Email (EML)',
                'subject': subject,
                'from': from_addr,
                'to': to_addr,
                'date': date,
                'is_multipart': msg.is_multipart()
            }

            return content, metadata

        except Exception as e:
            logger.error(
                f"Error extracting email content from {file_path}: {e}")
            return "", {"error": str(e)}

    def _extract_msg(self, file_path: Path) -> tuple[str, Dict[str, Any]]:
        """Extract content from MSG Outlook files"""
        # MSG files require specialized libraries (like msg_parser or extract_msg)
        # For now, return empty content with a note
        metadata = {
            'format': 'MSG (Outlook)',
            'error': 'MSG format extraction requires additional library (extract_msg)'
        }
        return "", metadata

    def _generate_basic_summary(self, content: str,
                                max_sentences: int = 3) -> str:
        """Generate a basic summary from content"""
        if not content:
            return ""

        # Simple sentence splitting
        sentences = content.replace('\n', ' ').split('.')
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return content[:200] + "..." if len(content) > 200 else content

        # Take first few sentences
        summary_sentences = sentences[:max_sentences]
        summary = '. '.join(summary_sentences)

        if len(summary) > 500:
            summary = summary[:497] + "..."

        return summary

    def get_installation_requirements(self) -> Dict[str, str]:
        """Return dictionary of optional libraries and their installation commands"""
        return {
            'PyPDF2': 'pip install PyPDF2',
            'pdfplumber': 'pip install pdfplumber',
            'python-docx': 'pip install python-docx',
            'openpyxl': 'pip install openpyxl',
            'pandas': 'pip install pandas',
            'extract_msg': 'pip install extract-msg'
        }
