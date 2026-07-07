"""将流水线结果拆分为独立 JSON 文件写入输出目录。"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class PipelineResultExporter:
    """每次运行输出一个文件夹，各阶段结果独立成文件。"""

    FILE_EXTRACT = "extract.json"
    FILE_ANALYZE = "analyze.json"
    FILE_REQUIREMENTS = "requirements.json"
    FILE_PARSE_QUALITY = "parse_quality.json"
    FILE_CASE_QUALITY = "case_quality.json"
    FILE_TEST_CASES = "test_cases.json"
    FILE_MANIFEST = "manifest.json"
    FILE_COMPLETENESS = "completeness.json"

    def export(
        self,
        output_dir: Path,
        *,
        task_no: str,
        task_status: str,
        source_file: Optional[str] = None,
        extract: Any,
        analyze: Any,
        requirements: list[Any],
        parse_quality: Any,
        case_quality: Any,
        cases: Any,
        completeness: Any = None,
        quality_warnings: Any = None,
    ) -> Path:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        self._write_json(output_dir / self.FILE_EXTRACT, extract)
        self._write_json(output_dir / self.FILE_ANALYZE, analyze)
        self._write_json(
            output_dir / self.FILE_REQUIREMENTS,
            [item.model_dump() if hasattr(item, "model_dump") else item for item in requirements],
        )
        self._write_json(output_dir / self.FILE_PARSE_QUALITY, parse_quality)
        self._write_json(output_dir / self.FILE_CASE_QUALITY, case_quality)
        self._write_json(output_dir / self.FILE_TEST_CASES, cases)

        if completeness is not None:
            self._write_json(output_dir / self.FILE_COMPLETENESS, completeness)

        test_case_count = 0
        if hasattr(cases, "test_cases"):
            test_case_count = len(cases.test_cases)
        elif isinstance(cases, dict):
            test_case_count = len(cases.get("test_cases", []))

        manifest = {
            "task_no": task_no,
            "task_status": task_status,
            "source_file": source_file,
            "exported_at": datetime.now().isoformat(),
            "files": {
                "extract": self.FILE_EXTRACT,
                "analyze": self.FILE_ANALYZE,
                "requirements": self.FILE_REQUIREMENTS,
                "parse_quality": self.FILE_PARSE_QUALITY,
                "case_quality": self.FILE_CASE_QUALITY,
                "test_cases": self.FILE_TEST_CASES,
            },
            "stats": {
                "requirement_count": len(requirements),
                "issue_count": len(analyze.issues) if hasattr(analyze, "issues") else len(analyze.get("issues", [])),
                "test_case_count": test_case_count,
            },
            "quality_warnings": (
                quality_warnings.model_dump(mode="json")
                if quality_warnings is not None and hasattr(quality_warnings, "model_dump")
                else quality_warnings
            ),
        }
        if completeness is not None:
            manifest["files"]["completeness"] = self.FILE_COMPLETENESS

        self._write_json(output_dir / self.FILE_MANIFEST, manifest)
        return output_dir

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        if hasattr(data, "model_dump"):
            payload = data.model_dump()
        else:
            payload = data
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_manifest(self, output_dir: Path) -> Optional[dict[str, Any]]:
        path = Path(output_dir) / self.FILE_MANIFEST
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def load_combined_report(self, output_dir: Path) -> Optional[dict[str, Any]]:
        """从文件夹组装完整报告（供 API / 兼容旧逻辑）。"""
        output_dir = Path(output_dir)
        manifest = self.load_manifest(output_dir)
        if not manifest:
            return None

        def read(name: str) -> Any:
            path = output_dir / name
            if not path.exists():
                return None
            return json.loads(path.read_text(encoding="utf-8"))

        files = manifest.get("files", {})
        return {
            "task_no": manifest.get("task_no"),
            "task_status": manifest.get("task_status"),
            "quality_warnings": manifest.get("quality_warnings"),
            "extract": read(files.get("extract", self.FILE_EXTRACT)),
            "completeness": read(files.get("completeness", self.FILE_COMPLETENESS)),
            "requirements": read(files.get("requirements", self.FILE_REQUIREMENTS)),
            "analyze": read(files.get("analyze", self.FILE_ANALYZE)),
            "parse_quality": read(files.get("parse_quality", self.FILE_PARSE_QUALITY)),
            "case_quality": read(files.get("case_quality", self.FILE_CASE_QUALITY)),
            "cases": read(files.get("test_cases", self.FILE_TEST_CASES)),
        }
