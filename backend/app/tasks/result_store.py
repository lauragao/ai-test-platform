"""任务流水线结果持久化（按任务号分文件夹，各阶段独立 JSON）。"""

import json
from pathlib import Path
from typing import Any, Optional

from app.tasks.result_exporter import PipelineResultExporter


class TaskResultStore:
    def __init__(self, storage_dir: str | Path):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.exporter = PipelineResultExporter()

    def output_dir(self, task_no: str) -> Path:
        return self.storage_dir / task_no

    def save(
        self,
        task_no: str,
        payload: dict[str, Any],
        *,
        split: bool = True,
    ) -> Path:
        """保存结果。默认拆分为文件夹内多个 JSON 文件。"""
        if split:
            return self.exporter.export(
                self.output_dir(task_no),
                task_no=task_no,
                task_status=payload.get("task_status", ""),
                source_file=payload.get("source_file"),
                extract=payload["extract"],
                analyze=payload["analyze"],
                requirements=payload["requirements"],
                parse_quality=payload["parse_quality"],
                case_quality=payload["case_quality"],
                cases=payload["cases"],
                completeness=payload.get("completeness"),
                quality_warnings=payload.get("quality_warnings"),
            )

        path = self.storage_dir / f"{task_no}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def save_pipeline(
        self,
        task_no: str,
        *,
        task_status: str,
        source_file: Optional[str],
        extract: Any,
        analyze: Any,
        requirements: list[Any],
        parse_quality: Any,
        case_quality: Any,
        cases: Any,
        completeness: Any = None,
        quality_warnings: Any = None,
    ) -> Path:
        return self.exporter.export(
            self.output_dir(task_no),
            task_no=task_no,
            task_status=task_status,
            source_file=source_file,
            extract=extract,
            analyze=analyze,
            requirements=requirements,
            parse_quality=parse_quality,
            case_quality=case_quality,
            cases=cases,
            completeness=completeness,
            quality_warnings=quality_warnings,
        )

    def get(self, task_no: str) -> Optional[dict[str, Any]]:
        folder = self.output_dir(task_no)
        if folder.exists() and (folder / PipelineResultExporter.FILE_MANIFEST).exists():
            return self.exporter.load_combined_report(folder)

        legacy = self.storage_dir / f"{task_no}.json"
        if legacy.exists():
            return json.loads(legacy.read_text(encoding="utf-8"))
        return None

    def exists(self, task_no: str) -> bool:
        folder = self.output_dir(task_no)
        if (folder / PipelineResultExporter.FILE_MANIFEST).exists():
            return True
        return (self.storage_dir / f"{task_no}.json").exists()
