"""OCR sub-package — multi-engine text extraction and field parsing."""

from src.ocr.ocr_engine import OCREngineManager, OCRResult
from src.ocr.field_parser import FieldParser, ParsedDocument

__all__ = ["OCREngineManager", "OCRResult", "FieldParser", "ParsedDocument"]
