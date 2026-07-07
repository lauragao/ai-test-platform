"""上传文件与文档解析辅助。"""

from pathlib import Path

from app.ai.models import DocumentSectionInput
from app.document.document_parser import parse_document_file, supported_extensions
from app.document.enrich import enrich_sections_with_snapshot


def find_upload_file(task_no: str, upload_dir: Path) -> Path | None:
    for ext in sorted(supported_extensions()):
        candidate = upload_dir / f"{task_no}{ext}"
        if candidate.exists():
            return candidate
    return None


def load_and_parse_upload(file_path: Path) -> list[DocumentSectionInput]:
    sections = parse_document_file(file_path)
    return enrich_sections_with_snapshot(sections)
