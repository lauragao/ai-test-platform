"""任务持久化服务（MVP 文件型，后续可替换为 MySQL nb_test_tasks）。"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from app.tasks.models import TaskQualityWarnings, TaskRecord, TaskStatus


class TaskService:
    """管理任务记录与 quality_warnings 写入。"""

    def __init__(self, storage_dir: str | Path):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._id_counter_path = self.storage_dir / ".id_counter"

    def create(
        self,
        *,
        document_id: Optional[int] = None,
        task_type: str = "full",
        source_file: Optional[str] = None,
        config: Optional[dict] = None,
    ) -> TaskRecord:
        task_no = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
        now = datetime.now()
        task = TaskRecord(
            id=self._next_id(),
            document_id=document_id,
            task_no=task_no,
            task_type=task_type,
            status=TaskStatus.CREATED.value,
            progress=0,
            source_file=source_file,
            config=config or {},
            started_at=now,
            created_at=now,
            updated_at=now,
        )
        self.save(task)
        return task

    def get(self, task_no: str) -> Optional[TaskRecord]:
        path = self._task_path(task_no)
        if not path.exists():
            return None
        return TaskRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def save(self, task: TaskRecord) -> TaskRecord:
        task.updated_at = datetime.now()
        path = self._task_path(task.task_no)
        path.write_text(
            json.dumps(task.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return task

    def update_status(
        self,
        task: TaskRecord,
        status: str | TaskStatus,
        *,
        progress: Optional[int] = None,
        current_step: Optional[str] = None,
        step_message: Optional[str] = None,
    ) -> TaskRecord:
        task.status = status.value if isinstance(status, TaskStatus) else status
        if progress is not None:
            task.progress = progress
        if current_step is not None:
            task.current_step = current_step
        if step_message is not None:
            task.step_message = step_message
        return self.save(task)

    def apply_quality_warnings(
        self,
        task: TaskRecord,
        quality_warnings: TaskQualityWarnings,
        *,
        status: str | TaskStatus | None = None,
        progress: Optional[int] = None,
        current_step: Optional[str] = None,
        step_message: Optional[str] = None,
        mark_finished: bool = False,
    ) -> TaskRecord:
        """写入 quality_warnings，供任务详情页展示。"""
        task.quality_warnings = quality_warnings
        if status is not None:
            task.status = status.value if isinstance(status, TaskStatus) else status
        if progress is not None:
            task.progress = progress
        if current_step is not None:
            task.current_step = current_step
        if step_message is not None:
            task.step_message = step_message
        if mark_finished:
            task.finished_at = datetime.now()
        return self.save(task)

    def fail_task(
        self,
        task: TaskRecord,
        *,
        error_code: str,
        error_message: str,
    ) -> TaskRecord:
        task.status = TaskStatus.FAILED.value
        task.error_code = error_code
        task.error_message = error_message
        task.finished_at = datetime.now()
        return self.save(task)

    def list_tasks(self, limit: int = 20) -> list[TaskRecord]:
        tasks: list[TaskRecord] = []
        for path in sorted(
            self.storage_dir.glob("task_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            if path.name.startswith("."):
                continue
            tasks.append(TaskRecord.model_validate(json.loads(path.read_text(encoding="utf-8"))))
            if len(tasks) >= limit:
                break
        return tasks

    def _task_path(self, task_no: str) -> Path:
        return self.storage_dir / f"{task_no}.json"

    def _next_id(self) -> int:
        current = 0
        if self._id_counter_path.exists():
            current = int(self._id_counter_path.read_text(encoding="utf-8").strip() or "0")
        next_id = current + 1
        self._id_counter_path.write_text(str(next_id), encoding="utf-8")
        return next_id
