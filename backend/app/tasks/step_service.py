"""任务步骤持久化（MVP 文件型）。"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.tasks.models import TaskStepRecord, TaskStepStatus
from app.tasks.step_policy import StepPolicy


class TaskStepService:
    def __init__(self, storage_dir: str | Path):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def list_steps(self, task_no: str) -> list[TaskStepRecord]:
        return self._load(task_no)

    def get_running_step(self, task_no: str) -> Optional[TaskStepRecord]:
        for step in reversed(self._load(task_no)):
            if step.status == TaskStepStatus.RUNNING.value:
                return step
        return None

    def begin(
        self,
        task_no: str,
        step_name: str,
        policy: StepPolicy,
        *,
        attempt: int = 0,
        input_snapshot: Optional[dict] = None,
    ) -> TaskStepRecord:
        steps = self._load(task_no)
        now = datetime.now()
        step = TaskStepRecord(
            id=len(steps) + 1,
            task_no=task_no,
            step_name=step_name,
            step_order=len(steps) + 1,
            status=TaskStepStatus.RUNNING.value,
            retry_count=attempt,
            max_retry=policy.max_retry,
            timeout_seconds=policy.timeout_seconds,
            input_snapshot=input_snapshot,
            started_at=now,
            created_at=now,
            updated_at=now,
        )
        steps.append(step)
        self._save(task_no, steps)
        return step

    def succeed(
        self,
        task_no: str,
        step_id: int,
        *,
        output_snapshot: Optional[dict] = None,
    ) -> TaskStepRecord:
        step = self._update_step(
            task_no,
            step_id,
            status=TaskStepStatus.SUCCESS.value,
            output_snapshot=output_snapshot,
        )
        return step

    def fail(
        self,
        task_no: str,
        step_id: int,
        *,
        error_code: str,
        error_message: str,
        status: str = TaskStepStatus.FAILED.value,
    ) -> TaskStepRecord:
        return self._update_step(
            task_no,
            step_id,
            status=status,
            error_code=error_code,
            error_message=error_message,
        )

    def mark_timeout(self, task_no: str, step_id: int) -> TaskStepRecord:
        step = self._get_step(task_no, step_id)
        return self.fail(
            task_no,
            step_id,
            error_code="step_timeout",
            error_message=f"步骤 [{step.step_name}] 执行超过 {step.timeout_seconds}s",
            status=TaskStepStatus.TIMEOUT.value,
        )

    def reset_steps(self, task_no: str) -> None:
        path = self._path(task_no)
        if path.exists():
            path.unlink()

    def _update_step(
        self,
        task_no: str,
        step_id: int,
        *,
        status: str,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        output_snapshot: Optional[dict] = None,
    ) -> TaskStepRecord:
        steps = self._load(task_no)
        now = datetime.now()
        for index, step in enumerate(steps):
            if step.id != step_id:
                continue
            finished_at = now
            duration_ms = None
            if step.started_at:
                duration_ms = int((finished_at - step.started_at).total_seconds() * 1000)
            updated = step.model_copy(
                update={
                    "status": status,
                    "error_code": error_code,
                    "error_message": error_message,
                    "output_snapshot": output_snapshot,
                    "finished_at": finished_at,
                    "duration_ms": duration_ms,
                    "updated_at": now,
                }
            )
            steps[index] = updated
            self._save(task_no, steps)
            return updated
        raise KeyError(f"step_id={step_id} not found for task {task_no}")

    def _get_step(self, task_no: str, step_id: int) -> TaskStepRecord:
        for step in self._load(task_no):
            if step.id == step_id:
                return step
        raise KeyError(f"step_id={step_id} not found for task {task_no}")

    def _path(self, task_no: str) -> Path:
        return self.storage_dir / f"{task_no}.steps.json"

    def _load(self, task_no: str) -> list[TaskStepRecord]:
        path = self._path(task_no)
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return [TaskStepRecord.model_validate(item) for item in data]

    def _save(self, task_no: str, steps: list[TaskStepRecord]) -> None:
        path = self._path(task_no)
        payload = [step.model_dump(mode="json") for step in steps]
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
