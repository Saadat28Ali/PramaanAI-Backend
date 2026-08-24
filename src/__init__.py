"""DocuNet — document verification: preprocessing, forensics, and OCR."""

from src.config import DocuNetConfig
from src.exceptions import DocuNetError
from src.pipeline import DocuNetPipeline, PipelineResult
from src.protocols import (
    Enhancer,
    FieldExtractor,
    ForensicAnalyzer,
    GlareRemover,
    OCRExtractor,
    QualityChecker,
    Rectifier,
    Serializable,
    TamperClassifierProtocol,
)

__all__ = [
    "DocuNetConfig",
    "DocuNetError",
    "DocuNetPipeline",
    "PipelineResult",
    "Enhancer",
    "FieldExtractor",
    "ForensicAnalyzer",
    "GlareRemover",
    "OCRExtractor",
    "QualityChecker",
    "Rectifier",
    "Serializable",
    "TamperClassifierProtocol",
]

__version__ = "1.0.0"
__author__ = "DocuNet Team"
