"""任务流水线结果持久化（MVP 文件型）。"""

import json
from pathlib import Path
from typing import Any, Optional


class TaskResultStore:
    def __init__(self, storage_dir: str | Path):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, task_no: str, payload: dict[str, Any]) -> Path:
        path = self.storage_dir / f"{task_no}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def get(self, task_no: str) -> Optional[dict[str, Any]]:
        path = self.storage_dir / f"{task_no}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def exists(self, task_no: str) -> bool:
        return (self.storage_dir / f"{task_no}.json").exists()
