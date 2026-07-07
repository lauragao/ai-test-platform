"""Markdown / TXT 简易章节解析（MVP）。"""

import re

from app.ai.models import DocumentSectionInput


def parse_markdown_sections(content: str) -> list[DocumentSectionInput]:
    """将 Markdown 按标题切分为章节。"""
    sections: list[DocumentSectionInput] = []
    current_title: str | None = None
    current_level = 1
    current_lines: list[str] = []
    sec_idx = 0

    def flush() -> None:
        nonlocal sec_idx
        text = "\n".join(current_lines).strip()
        if not text and not current_title:
            return
        sec_idx += 1
        sections.append(
            DocumentSectionInput(
                section_id=f"sec_{sec_idx:03d}",
                title=current_title,
                level=current_level,
                content=text or (current_title or ""),
            )
        )

    for line in content.splitlines():
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush()
            current_level = len(heading.group(1))
            current_title = heading.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    flush()

    if not sections:
        sections.append(
            DocumentSectionInput(
                section_id="sec_001",
                title="全文",
                level=1,
                content=content.strip(),
            )
        )
    return sections
