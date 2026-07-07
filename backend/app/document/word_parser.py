"""Word (.docx) 文档解析，转为章节结构。"""

from io import BytesIO

import mammoth

from app.ai.models import DocumentSectionInput
from app.document.markdown_parser import parse_markdown_sections


def parse_docx_sections(content: bytes) -> list[DocumentSectionInput]:
    """将 .docx 转为 Markdown 后按标题切分章节。"""
    result = mammoth.convert_to_markdown(BytesIO(content))
    markdown = result.value or ""
    if result.messages:
        # mammoth 警告不影响主流程，仅在有内容时继续
        pass
    if not markdown.strip():
        raise ValueError("Word 文档解析结果为空，请确认文件未损坏")
    return parse_markdown_sections(markdown)
