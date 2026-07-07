"""任务结果导出服务。"""

from pathlib import Path
from typing import Literal

from app.ai.models import GenerateTestCasesResult, RequirementItem, TestCaseItem
from app.exporters import ExcelExporter, XmindExporter
from app.tasks.result_store import TaskResultStore

ExportFormat = Literal["xlsx", "xmind"]

FORMAT_EXTENSIONS: dict[ExportFormat, str] = {
    "xlsx": ".xlsx",
    "xmind": ".xmind",
}

FORMAT_FILENAMES: dict[ExportFormat, str] = {
    "xlsx": "test_cases.xlsx",
    "xmind": "test_cases.xmind",
}


class TaskExportService:
    def __init__(self, result_store: TaskResultStore, export_dir: str | Path):
        self.result_store = result_store
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_dir_for(self, task_no: str) -> Path:
        path = self.export_dir / task_no
        path.mkdir(parents=True, exist_ok=True)
        return path

    def export_file_path(self, task_no: str, fmt: ExportFormat) -> Path:
        return self.export_dir_for(task_no) / FORMAT_FILENAMES[fmt]

    def export(
        self,
        task_no: str,
        fmt: ExportFormat,
        *,
        document_title: str | None = None,
    ) -> Path:
        payload = self.result_store.get(task_no)
        if not payload:
            raise FileNotFoundError(f"任务 {task_no} 的报告尚未就绪，无法导出")

        requirements = [
            RequirementItem.model_validate(item) for item in payload.get("requirements", [])
        ]
        cases_payload = payload.get("cases") or {}
        if isinstance(cases_payload, dict) and "test_cases" in cases_payload:
            test_cases = [
                TestCaseItem.model_validate(item) for item in cases_payload["test_cases"]
            ]
        else:
            result = GenerateTestCasesResult.model_validate(cases_payload)
            test_cases = result.test_cases

        output_path = self.export_file_path(task_no, fmt)
        root_title = document_title or f"{task_no} 测试用例"

        if fmt == "xlsx":
            ExcelExporter().export(
                test_cases,
                output_path,
                requirements=requirements,
                include_traceability=True,
            )
        elif fmt == "xmind":
            XmindExporter().export(test_cases, output_path, root_title=root_title)
        else:
            raise ValueError(f"不支持的导出格式: {fmt}")

        return output_path

    def resolve_download_path(self, task_no: str, filename: str) -> Path | None:
        path = self.export_dir_for(task_no) / filename
        if not path.exists() or not path.is_file():
            return None
        resolved = path.resolve()
        export_root = self.export_dir_for(task_no).resolve()
        if export_root not in resolved.parents:
            return None
        return resolved
