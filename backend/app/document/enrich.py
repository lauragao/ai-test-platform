"""为结构化章节附加原文快照。"""

from typing import TYPE_CHECKING

from app.document.section_snapshot import (
    build_source_snapshot,
    compute_section_parse_confidence,
)

if TYPE_CHECKING:
    from app.ai.models import DocumentSectionInput


def enrich_section_with_snapshot(section: "DocumentSectionInput") -> "DocumentSectionInput":
    snapshot = build_source_snapshot(section.content)
    confidence = compute_section_parse_confidence(snapshot)
    return section.model_copy(
        update={"source_snapshot": snapshot, "parse_confidence": confidence}
    )


def enrich_sections_with_snapshot(
    sections: list["DocumentSectionInput"],
) -> list["DocumentSectionInput"]:
    return [enrich_section_with_snapshot(section) for section in sections]
