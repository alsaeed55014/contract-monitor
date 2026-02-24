# src/core/file_translator.py
"""
Professional Multi-Format File Translation Engine
Supports: .docx, .bdf, .jpg/.png/.jpeg, .pdf
Uses: deep_translator (free, no API key), easyocr (free OCR)
Architecture: Extensible handler pattern for future formats (pptx, xlsx)
Author: Alsaeed Alwazzan
"""

import io
import os
import re
import time
import logging
from datetime import datetime
from typing import Callable, Optional, Dict, List, Tuple, Any

# ──────────────────────────────────────────────
# Lazy imports for optional dependencies
# ──────────────────────────────────────────────

def _import_docx():
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor
        return Document, True
    except ImportError:
        return None, False

def _import_easyocr():
    try:
        import easyocr
        return easyocr, True
    except ImportError:
        return None, False

def _import_pdfplumber():
    try:
        import pdfplumber
        return pdfplumber, True
    except ImportError:
        return None, False

def _import_pillow():
    try:
        from PIL import Image
        return Image, True
    except ImportError:
        return None, False

# ──────────────────────────────────────────────
# Translation Service (Free, No API Key)
# ──────────────────────────────────────────────

class TranslationService:
    """Wrapper around deep_translator for chunked, robust translation."""

    SUPPORTED_LANGUAGES = {
        "ar": "العربية (Arabic)",
        "en": "English",
        "fr": "الفرنسية (French)",
        "es": "الإسبانية (Spanish)",
        "de": "الألمانية (German)",
        "tr": "التركية (Turkish)",
        "ur": "الأردية (Urdu)",
        "hi": "الهندية (Hindi)",
        "zh-CN": "الصينية (Chinese)",
        "ja": "اليابانية (Japanese)",
        "ko": "الكورية (Korean)",
        "ru": "الروسية (Russian)",
        "pt": "البرتغالية (Portuguese)",
        "it": "الإيطالية (Italian)",
        "id": "الإندونيسية (Indonesian)",
        "ms": "الملايوية (Malay)",
        "tl": "الفلبينية (Filipino)",
        "bn": "البنغالية (Bengali)",
        "th": "التايلاندية (Thai)",
        "vi": "الفيتنامية (Vietnamese)",
    }

    CHUNK_SIZE = 4000  # Max chars per translation request

    def __init__(self, source_lang: str = "auto", target_lang: str = "ar"):
        from deep_translator import GoogleTranslator
        self.source_lang = source_lang
        self.target_lang = target_lang
        self._translator = GoogleTranslator(source=source_lang, target=target_lang)

    def translate_text(self, text: str, progress_callback: Optional[Callable] = None) -> str:
        """Translate text with chunking for large content."""
        if not text or not text.strip():
            return ""

        # Split into chunks respecting sentence boundaries
        chunks = self._split_into_chunks(text)
        total = len(chunks)
        translated_parts = []

        for i, chunk in enumerate(chunks):
            try:
                result = self._translator.translate(chunk)
                translated_parts.append(result if result else chunk)
            except Exception as e:
                logging.warning(f"Translation chunk {i+1}/{total} failed: {e}")
                translated_parts.append(chunk)  # Keep original on failure

            if progress_callback:
                progress_callback((i + 1) / total, f"ترجمة الجزء {i+1}/{total}")

        return "\n".join(translated_parts)

    def translate_batch(self, texts: List[str], progress_callback: Optional[Callable] = None) -> List[str]:
        """Translate a list of text strings."""
        results = []
        total = len(texts)
        for i, text in enumerate(texts):
            if text and text.strip():
                try:
                    result = self._translator.translate(text)
                    results.append(result if result else text)
                except Exception:
                    results.append(text)
            else:
                results.append(text)

            if progress_callback:
                progress_callback((i + 1) / total, f"ترجمة النص {i+1}/{total}")

        return results

    def _split_into_chunks(self, text: str) -> List[str]:
        """Split text into chunks at sentence boundaries."""
        if len(text) <= self.CHUNK_SIZE:
            return [text]

        chunks = []
        current = ""
        # Split by newlines first, then by sentences
        paragraphs = text.split("\n")

        for para in paragraphs:
            if len(current) + len(para) + 1 <= self.CHUNK_SIZE:
                current += para + "\n"
            else:
                if current:
                    chunks.append(current.strip())
                # If single paragraph > chunk size, split by sentences
                if len(para) > self.CHUNK_SIZE:
                    sentences = re.split(r'(?<=[.!?。؟])\s+', para)
                    sub_chunk = ""
                    for sent in sentences:
                        if len(sub_chunk) + len(sent) + 1 <= self.CHUNK_SIZE:
                            sub_chunk += sent + " "
                        else:
                            if sub_chunk:
                                chunks.append(sub_chunk.strip())
                            # If single sentence > chunk size, force split
                            if len(sent) > self.CHUNK_SIZE:
                                for j in range(0, len(sent), self.CHUNK_SIZE):
                                    chunks.append(sent[j:j + self.CHUNK_SIZE])
                            else:
                                sub_chunk = sent + " "
                    if sub_chunk.strip():
                        chunks.append(sub_chunk.strip())
                    current = ""
                else:
                    current = para + "\n"

        if current.strip():
            chunks.append(current.strip())

        return chunks if chunks else [text]


# ──────────────────────────────────────────────
# Operation Logger
# ──────────────────────────────────────────────

class OperationLogger:
    """Logs translation operations with timestamps."""

    def __init__(self):
        self.entries: List[Dict[str, Any]] = []

    def log(self, message: str, level: str = "info"):
        self.entries.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": message,
            "level": level,  # info, success, warning, error
        })

    def get_entries(self) -> List[Dict[str, Any]]:
        return self.entries

    def clear(self):
        self.entries.clear()


# ──────────────────────────────────────────────
# Base Handler
# ──────────────────────────────────────────────

class BaseTranslator:
    """Base class for all file type translators."""

    SUPPORTED_EXTENSIONS: List[str] = []

    def __init__(self, service: TranslationService, logger: OperationLogger):
        self.service = service
        self.logger = logger

    def can_handle(self, extension: str) -> bool:
        return extension.lower() in self.SUPPORTED_EXTENSIONS

    def translate(self, file_bytes: bytes, filename: str,
                  progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Returns dict with:
          - original_text: str
          - translated_text: str
          - output_bytes: bytes (translated file)
          - output_filename: str
          - output_mime: str
          - success: bool
          - error: str (if any)
        """
        raise NotImplementedError


# ──────────────────────────────────────────────
# DOCX Translator
# ──────────────────────────────────────────────

class DocxTranslator(BaseTranslator):
    """Translate .docx files while preserving formatting."""

    SUPPORTED_EXTENSIONS = [".docx"]

    def translate(self, file_bytes: bytes, filename: str,
                  progress_callback: Optional[Callable] = None) -> Dict[str, Any]:

        Document, available = _import_docx()
        if not available:
            return self._error("مكتبة python-docx غير مثبتة. pip install python-docx")

        self.logger.log(f"📄 بدء ترجمة ملف Word: {filename}")

        try:
            doc = Document(io.BytesIO(file_bytes))
            original_texts = []
            translatable_runs = []

            # Phase 1: Collect all text from paragraphs
            self.logger.log("📋 استخراج النصوص من المستند...")
            for para in doc.paragraphs:
                for run in para.runs:
                    if run.text and run.text.strip():
                        original_texts.append(run.text)
                        translatable_runs.append(run)

            # Collect text from tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for para in cell.paragraphs:
                            for run in para.runs:
                                if run.text and run.text.strip():
                                    original_texts.append(run.text)
                                    translatable_runs.append(run)

            if not original_texts:
                return self._error("لم يتم العثور على نصوص في الملف")

            total = len(original_texts)
            self.logger.log(f"📊 تم العثور على {total} نص قابل للترجمة")

            # Phase 2: Translate in batches
            self.logger.log("🔄 بدء الترجمة...")
            translated_texts = self.service.translate_batch(
                original_texts,
                progress_callback=progress_callback
            )

            # Phase 3: Replace text while keeping formatting
            self.logger.log("✏️ استبدال النصوص مع الحفاظ على التنسيق...")
            for run, trans in zip(translatable_runs, translated_texts):
                run.text = trans

            # Save translated document
            output = io.BytesIO()
            doc.save(output)
            output.seek(0)

            base_name = os.path.splitext(filename)[0]
            output_filename = f"translated_{base_name}.docx"

            self.logger.log(f"✅ تمت الترجمة بنجاح: {output_filename}", "success")

            return {
                "original_text": "\n".join(original_texts),
                "translated_text": "\n".join(translated_texts),
                "output_bytes": output.read(),
                "output_filename": output_filename,
                "output_mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "success": True,
                "error": None,
                "stats": {"total_texts": total}
            }

        except Exception as e:
            return self._error(f"خطأ في ترجمة ملف Word: {str(e)}")

    def _error(self, msg):
        self.logger.log(f"❌ {msg}", "error")
        return {"success": False, "error": msg, "original_text": "", "translated_text": "",
                "output_bytes": b"", "output_filename": "", "output_mime": ""}


# ──────────────────────────────────────────────
# Image Translator (OCR + Translation)
# ──────────────────────────────────────────────

class ImageTranslator(BaseTranslator):
    """Extract text from images via OCR, then translate."""

    SUPPORTED_EXTENSIONS = [".jpg", ".jpeg", ".png"]

    def translate(self, file_bytes: bytes, filename: str,
                  progress_callback: Optional[Callable] = None) -> Dict[str, Any]:

        easyocr_mod, available = _import_easyocr()
        if not available:
            return self._error("مكتبة easyocr غير مثبتة. pip install easyocr")

        Image, pil_available = _import_pillow()
        if not pil_available:
            return self._error("مكتبة Pillow غير مثبتة. pip install Pillow")

        self.logger.log(f"🖼️ بدء معالجة الصورة: {filename}")

        try:
            # Phase 1: OCR
            self.logger.log("🔍 استخراج النص من الصورة (OCR)...")
            if progress_callback:
                progress_callback(0.1, "جارٍ تحميل نموذج OCR...")

            # Detect languages based on source/target
            ocr_langs = ['en']
            src = self.service.source_lang
            if src == 'auto' or src == 'ar':
                ocr_langs = ['ar', 'en']
            elif src == 'en':
                ocr_langs = ['en']
            else:
                ocr_langs = ['en']  # Default to English

            reader = easyocr_mod.Reader(ocr_langs, gpu=False)

            if progress_callback:
                progress_callback(0.3, "جارٍ قراءة النص من الصورة...")

            # Read image from bytes
            image = Image.open(io.BytesIO(file_bytes))
            import numpy as np
            image_np = np.array(image)

            results = reader.readtext(image_np)

            if not results:
                return self._error("لم يتم العثور على نص في الصورة")

            # Extract text
            extracted_lines = [text for (_, text, conf) in results]
            original_text = "\n".join(extracted_lines)

            self.logger.log(f"📊 تم استخراج {len(extracted_lines)} سطر من الصورة")

            if progress_callback:
                progress_callback(0.5, "جارٍ ترجمة النص المستخرج...")

            # Phase 2: Translate
            self.logger.log("🔄 بدء ترجمة النص المستخرج...")

            def sub_progress(pct, msg):
                if progress_callback:
                    progress_callback(0.5 + pct * 0.5, msg)

            translated_text = self.service.translate_text(original_text, progress_callback=sub_progress)

            # Output as text file
            base_name = os.path.splitext(filename)[0]
            output_filename = f"translated_{base_name}.txt"
            output_content = f"=== النص الأصلي (Original) ===\n\n{original_text}\n\n"
            output_content += f"=== النص المترجم (Translated) ===\n\n{translated_text}\n"

            self.logger.log(f"✅ تمت ترجمة نص الصورة بنجاح: {output_filename}", "success")

            return {
                "original_text": original_text,
                "translated_text": translated_text,
                "output_bytes": output_content.encode("utf-8"),
                "output_filename": output_filename,
                "output_mime": "text/plain",
                "success": True,
                "error": None,
                "stats": {"lines_extracted": len(extracted_lines)}
            }

        except Exception as e:
            return self._error(f"خطأ في معالجة الصورة: {str(e)}")

    def _error(self, msg):
        self.logger.log(f"❌ {msg}", "error")
        return {"success": False, "error": msg, "original_text": "", "translated_text": "",
                "output_bytes": b"", "output_filename": "", "output_mime": ""}


# ──────────────────────────────────────────────
# BDF Font File Translator
# ──────────────────────────────────────────────

class BdfTranslator(BaseTranslator):
    """Translate text properties in BDF font files."""

    SUPPORTED_EXTENSIONS = [".bdf"]

    # BDF properties that contain translatable text
    TRANSLATABLE_KEYS = {
        "FAMILY_NAME", "FONT", "COMMENT", "COPYRIGHT",
        "NOTICE", "FOUNDRY", "FULL_NAME", "WEIGHT_NAME",
        "SLANT", "ADD_STYLE_NAME", "CHARSET_REGISTRY"
    }

    def translate(self, file_bytes: bytes, filename: str,
                  progress_callback: Optional[Callable] = None) -> Dict[str, Any]:

        self.logger.log(f"🔤 بدء ترجمة ملف BDF: {filename}")

        try:
            # Try to decode the file
            try:
                content = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                content = file_bytes.decode("latin-1")

            lines = content.split("\n")
            total_lines = len(lines)
            translated_lines = []
            original_texts = []
            translated_texts = []
            text_count = 0

            self.logger.log(f"📊 الملف يحتوي على {total_lines} سطر")

            for i, line in enumerate(lines):
                stripped = line.strip()

                # Check if the line starts with a translatable property
                translated = False
                for key in self.TRANSLATABLE_KEYS:
                    if stripped.startswith(key + " "):
                        # Extract the value part
                        value = stripped[len(key) + 1:].strip()
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            inner = value[1:-1]
                            if inner and not self._is_technical(inner):
                                try:
                                    trans = self.service.translate_text(inner)
                                    original_texts.append(inner)
                                    translated_texts.append(trans)
                                    translated_lines.append(f'{key} "{trans}"')
                                    text_count += 1
                                    translated = True
                                except Exception:
                                    translated_lines.append(line)
                                    translated = True
                        elif value and not self._is_technical(value):
                            try:
                                trans = self.service.translate_text(value)
                                original_texts.append(value)
                                translated_texts.append(trans)
                                translated_lines.append(f"{key} {trans}")
                                text_count += 1
                                translated = True
                            except Exception:
                                translated_lines.append(line)
                                translated = True
                        break

                if not translated:
                    translated_lines.append(line)

                if progress_callback and i % max(1, total_lines // 20) == 0:
                    progress_callback(i / total_lines, f"معالجة السطر {i}/{total_lines}")

            # Generate output
            output_content = "\n".join(translated_lines)
            base_name = os.path.splitext(filename)[0]
            output_filename = f"translated_{base_name}.bdf"

            self.logger.log(f"✅ تمت ترجمة {text_count} نص في ملف BDF", "success")

            return {
                "original_text": "\n".join(original_texts) if original_texts else "(لا يوجد نصوص قابلة للترجمة)",
                "translated_text": "\n".join(translated_texts) if translated_texts else "(لا يوجد ترجمة)",
                "output_bytes": output_content.encode("utf-8"),
                "output_filename": output_filename,
                "output_mime": "application/octet-stream",
                "success": True,
                "error": None,
                "stats": {"total_lines": total_lines, "translated_properties": text_count}
            }

        except Exception as e:
            return self._error(f"خطأ في ترجمة ملف BDF: {str(e)}")

    def _is_technical(self, text: str) -> bool:
        """Check if text is technical/binary data that shouldn't be translated."""
        # Skip hex patterns, pure numbers, encoding names, etc.
        if re.match(r'^[0-9A-Fa-f\s\-_.]+$', text):
            return True
        if re.match(r'^ISO\d+', text):
            return True
        if len(text) <= 1:
            return True
        return False

    def _error(self, msg):
        self.logger.log(f"❌ {msg}", "error")
        return {"success": False, "error": msg, "original_text": "", "translated_text": "",
                "output_bytes": b"", "output_filename": "", "output_mime": ""}


# ──────────────────────────────────────────────
# PDF Translator (Enhanced from existing)
# ──────────────────────────────────────────────

class PdfTranslator(BaseTranslator):
    """Translate PDF files using pdfplumber for extraction."""

    SUPPORTED_EXTENSIONS = [".pdf"]

    def translate(self, file_bytes: bytes, filename: str,
                  progress_callback: Optional[Callable] = None) -> Dict[str, Any]:

        pdfplumber, available = _import_pdfplumber()
        if not available:
            return self._error("مكتبة pdfplumber غير مثبتة. pip install pdfplumber")

        self.logger.log(f"📑 بدء ترجمة ملف PDF: {filename}")

        try:
            # Phase 1: Extract text
            self.logger.log("📋 استخراج النصوص من PDF...")
            if progress_callback:
                progress_callback(0.1, "جارٍ استخراج النصوص...")

            original_text = ""
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                total_pages = len(pdf.pages)
                for idx, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        original_text += page_text + "\n\n"
                    if progress_callback:
                        progress_callback(0.1 + 0.3 * ((idx + 1) / total_pages),
                                          f"صفحة {idx+1}/{total_pages}")

            if not original_text.strip():
                return self._error("لم يتم العثور على نص في ملف PDF. قد يكون الملف عبارة عن صور.")

            self.logger.log(f"📊 تم استخراج النص ({len(original_text)} حرف)")

            # Phase 2: Translate
            self.logger.log("🔄 بدء الترجمة...")

            def sub_progress(pct, msg):
                if progress_callback:
                    progress_callback(0.4 + pct * 0.6, msg)

            translated_text = self.service.translate_text(original_text, progress_callback=sub_progress)

            # Output as text file
            base_name = os.path.splitext(filename)[0]
            output_filename = f"translated_{base_name}.txt"

            self.logger.log(f"✅ تمت ترجمة PDF بنجاح: {output_filename}", "success")

            return {
                "original_text": original_text,
                "translated_text": translated_text,
                "output_bytes": translated_text.encode("utf-8"),
                "output_filename": output_filename,
                "output_mime": "text/plain",
                "success": True,
                "error": None,
                "stats": {"total_pages": total_pages, "total_chars": len(original_text)}
            }

        except Exception as e:
            return self._error(f"خطأ في ترجمة PDF: {str(e)}")

    def _error(self, msg):
        self.logger.log(f"❌ {msg}", "error")
        return {"success": False, "error": msg, "original_text": "", "translated_text": "",
                "output_bytes": b"", "output_filename": "", "output_mime": ""}


# ──────────────────────────────────────────────
# Main File Translator (Orchestrator)
# ──────────────────────────────────────────────

class FileTranslator:
    """
    Main orchestrator that auto-detects file type and routes to the correct handler.
    
    Usage:
        translator = FileTranslator(source_lang="auto", target_lang="ar")
        result = translator.translate(file_bytes, "resume.docx", progress_callback)
        
    Extensible: Add new handlers by creating a class extending BaseTranslator
    and registering it in the handlers list.
    """

    # All supported file extensions
    SUPPORTED_EXTENSIONS = [".docx", ".bdf", ".jpg", ".jpeg", ".png", ".pdf"]

    # File type descriptions (for UI)
    FILE_TYPE_INFO = {
        ".docx": {"icon": "📄", "name_ar": "ملف Word", "name_en": "Word Document"},
        ".bdf": {"icon": "🔤", "name_ar": "ملف خط BDF", "name_en": "BDF Font File"},
        ".jpg": {"icon": "🖼️", "name_ar": "صورة JPG", "name_en": "JPG Image"},
        ".jpeg": {"icon": "🖼️", "name_ar": "صورة JPEG", "name_en": "JPEG Image"},
        ".png": {"icon": "🖼️", "name_ar": "صورة PNG", "name_en": "PNG Image"},
        ".pdf": {"icon": "📑", "name_ar": "ملف PDF", "name_en": "PDF Document"},
    }

    def __init__(self, source_lang: str = "auto", target_lang: str = "ar"):
        self.service = TranslationService(source_lang=source_lang, target_lang=target_lang)
        self.logger = OperationLogger()

        # Register all handlers
        self._handlers: List[BaseTranslator] = [
            DocxTranslator(self.service, self.logger),
            ImageTranslator(self.service, self.logger),
            BdfTranslator(self.service, self.logger),
            PdfTranslator(self.service, self.logger),
        ]

    def get_file_type(self, filename: str) -> Optional[str]:
        """Detect file extension."""
        _, ext = os.path.splitext(filename)
        return ext.lower() if ext else None

    def get_handler(self, filename: str) -> Optional[BaseTranslator]:
        """Find the appropriate handler for a file."""
        ext = self.get_file_type(filename)
        if not ext:
            return None
        for handler in self._handlers:
            if handler.can_handle(ext):
                return handler
        return None

    def is_supported(self, filename: str) -> bool:
        """Check if a file type is supported."""
        ext = self.get_file_type(filename)
        return ext in self.SUPPORTED_EXTENSIONS

    def translate(self, file_bytes: bytes, filename: str,
                  progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Main translation entry point.
        Auto-detects file type and routes to the correct handler.
        """
        ext = self.get_file_type(filename)
        info = self.FILE_TYPE_INFO.get(ext, {})
        icon = info.get("icon", "📁")
        type_name = info.get("name_ar", ext)

        self.logger.log(f"📂 تم استلام ملف: {filename}")
        self.logger.log(f"{icon} نوع الملف: {type_name}")
        self.logger.log(f"📏 حجم الملف: {self._format_size(len(file_bytes))}")

        handler = self.get_handler(filename)
        if not handler:
            supported = ", ".join(self.SUPPORTED_EXTENSIONS)
            msg = f"نوع الملف '{ext}' غير مدعوم. الأنواع المدعومة: {supported}"
            self.logger.log(f"❌ {msg}", "error")
            return {"success": False, "error": msg}

        start_time = time.time()
        result = handler.translate(file_bytes, filename, progress_callback)
        elapsed = time.time() - start_time

        if result.get("success"):
            self.logger.log(f"⏱️ إجمالي وقت الترجمة: {elapsed:.1f} ثانية", "success")
        else:
            self.logger.log(f"⏱️ فشل بعد: {elapsed:.1f} ثانية", "error")

        return result

    def get_log(self) -> List[Dict]:
        """Get operation log entries."""
        return self.logger.get_entries()

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    @classmethod
    def get_supported_extensions_str(cls) -> str:
        """Get comma-separated list of supported extensions."""
        return ", ".join(cls.SUPPORTED_EXTENSIONS)
