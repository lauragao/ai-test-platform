"""文档解析相关工具。"""

from .enrich import enrich_section_with_snapshot, enrich_sections_with_snapshot
from .section_snapshot import (
    SourceSnapshot,
    build_source_snapshot,
    compute_document_parse_confidence,
    compute_section_parse_confidence,
    normalize_for_match,
)

__all__ = [
    "SourceSnapshot",
    "build_source_snapshot",
    "compute_section_parse_confidence",
    "compute_document_parse_confidence",
    "normalize_for_match",
    "enrich_section_with_snapshot",
    "enrich_sections_with_snapshot",
]
