"""文件型记忆服务。

迁移自旧工具 `memory_manager.py`。MVP 阶段可用于本地记录术语、偏好、
生成历史和歧义决策；产品化后可替换为数据库实现。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class MemoryService:
    MEMORY_DIR = ".memory"
    FILES = {
        "project_context": "project-context.json",
        "terminology": "terminology.json",
        "generation_history": "generation-history.json",
        "user_preferences": "user-preferences.json",
        "ambiguity_decisions": "ambiguity-decisions.json",
    }

    def __init__(self, project_path: str | Path):
        self.project_path = Path(project_path)
        self.memory_path = self.project_path / self.MEMORY_DIR

    def init(
        self,
        *,
        requirements_dir: str = "requirements",
        output_dir: str = "test-docs",
    ) -> Path:
        self.memory_path.mkdir(parents=True, exist_ok=True)

        self._write_if_missing(
            "project_context",
            {
                "project_name": self.project_path.name,
                "initialized_at": datetime.now().isoformat(),
                "requirements_dir": requirements_dir,
                "output_dir": output_dir,
            },
        )
        self._write_if_missing("terminology", {"domain_terms": {}, "module_abbreviations": {}})
        self._write_if_missing("generation_history", {"generations": []})
        self._write_if_missing(
            "user_preferences",
            {
                "last_output_formats": ["excel", "xmind", "traceability"],
                "default_output_dir": output_dir,
                "show_samples_in_preview": True,
                "auto_confirm_parsing": False,
                "ambiguity_handling": "ask",
                "priority_distribution": {
                    "p0_min": 10,
                    "p0_max": 15,
                    "warn_on_imbalance": True,
                },
                "default_tag": None,
                "step_granularity": "normal",
                "title_style": None,
                "updated_at": None,
            },
        )
        self._write_if_missing("ambiguity_decisions", {"decisions": []})
        return self.memory_path

    def read(self, memory_type: str) -> dict[str, Any]:
        path = self._file_path(memory_type)
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def update(self, memory_type: str, data: dict[str, Any], *, merge: bool = True) -> dict[str, Any]:
        path = self._file_path(memory_type)
        if merge and path.exists():
            existing = self.read(memory_type)
            data = self._deep_merge(existing, data)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data

    def add_generation_record(self, record: dict[str, Any]) -> dict[str, Any]:
        history = self.read("generation_history") or {"generations": []}
        record = {**record, "date": datetime.now().isoformat()}
        history.setdefault("generations", []).append(record)
        return self.update("generation_history", history, merge=False)

    def set_preference(self, key: str, value: Any) -> dict[str, Any]:
        preferences = self.read("user_preferences")
        preferences[key] = value
        preferences["updated_at"] = datetime.now().isoformat()
        return self.update("user_preferences", preferences, merge=False)

    def add_ambiguity_decision(self, decision: dict[str, Any]) -> dict[str, Any]:
        data = self.read("ambiguity_decisions") or {"decisions": []}
        data.setdefault("decisions", []).append({**decision, "date": datetime.now().isoformat()})
        return self.update("ambiguity_decisions", data, merge=False)

    def find_similar_ambiguity(self, ambiguity_type: str, context: str) -> dict[str, Any] | None:
        data = self.read("ambiguity_decisions")
        for decision in reversed(data.get("decisions", [])):
            if decision.get("type") != ambiguity_type:
                continue
            if context.lower() in str(decision.get("context", "")).lower():
                return decision
        return None

    def _write_if_missing(self, memory_type: str, data: dict[str, Any]) -> None:
        path = self._file_path(memory_type)
        if not path.exists():
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _file_path(self, memory_type: str) -> Path:
        if memory_type not in self.FILES:
            raise ValueError(f"未知记忆类型: {memory_type}")
        return self.memory_path / self.FILES[memory_type]

    @classmethod
    def _deep_merge(cls, base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                cls._deep_merge(base[key], value)
            else:
                base[key] = value
        return base
