"""任务关联文档章节持久化。"""

import json
from pathlib import Path
from typing import Optional

from app.ai.models import DocumentSectionInput


class DocumentStore:
    def __init__(self, storage_dir: str | Path):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def task_dir(self, task_no: str) -> Path:
        return self.storage_dir / task_no

    def sections_path(self, task_no: str) -> Path:
        return self.task_dir(task_no) / "sections.json"

    def save_sections(self, task_no: str, sections: list[DocumentSectionInput]) -> Path:
        path = self.sections_path(task_no)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [section.model_dump() for section in sections]
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def get_sections(self, task_no: str) -> Optional[list[DocumentSectionInput]]:
        path = self.sections_path(task_no)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return [DocumentSectionInput.model_validate(item) for item in data]

    def exists(self, task_no: str) -> bool:
        return self.sections_path(task_no).exists()
