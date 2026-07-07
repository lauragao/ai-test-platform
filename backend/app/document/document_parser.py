"""统一文档解析入口：Markdown / TXT / Word。"""

from pathlib import Path

from app.ai.models import DocumentSectionInput
from app.document.markdown_parser import parse_markdown_sections
from app.document.word_parser import parse_docx_sections

TEXT_EXTENSIONS = {".md", ".markdown", ".txt"}
WORD_EXTENSIONS = {".docx"}


def supported_extensions() -> set[str]:
    return TEXT_EXTENSIONS | WORD_EXTENSIONS


def parse_document(content: bytes | str, suffix: str) -> list[DocumentSectionInput]:
    """按文件后缀解析文档为章节列表。"""
    normalized = suffix.lower().lstrip(".")
    if not normalized.startswith("."):
        ext = f".{normalized}"
    else:
        ext = normalized

    if ext in TEXT_EXTENSIONS:
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        return parse_markdown_sections(text)

    if ext in WORD_EXTENSIONS:
        raw = content if isinstance(content, bytes) else content.encode("utf-8")
        return parse_docx_sections(raw)

    raise ValueError(f"不支持的文件类型: {ext}")


def parse_document_file(file_path: Path) -> list[DocumentSectionInput]:
    suffix = file_path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return parse_document(file_path.read_text(encoding="utf-8"), suffix)
    if suffix in WORD_EXTENSIONS:
        return parse_document(file_path.read_bytes(), suffix)
    raise ValueError(f"不支持的文件类型: {suffix}")
