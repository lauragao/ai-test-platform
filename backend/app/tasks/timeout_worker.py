"""检测 running 步骤是否超时并标记任务 failed。"""

from datetime import datetime
from typing import Optional

from app.tasks.models import TaskStatus, TaskStepStatus
from app.tasks.step_service import TaskStepService
from app.tasks.task_service import TaskService


class TimeoutWorker:
    """轮询 Worker：扫描 running 步骤是否超过 timeout_seconds。"""

    def __init__(self, task_service: TaskService, step_service: TaskStepService):
        self.task_service = task_service
        self.step_service = step_service

    def scan_all(self) -> list[str]:
        """扫描全部任务，返回被标记失败或超时的 task_no 列表。"""
        affected: list[str] = []
        for path in self.step_service.storage_dir.glob("*.steps.json"):
            task_no = path.name.replace(".steps.json", "")
            if self.scan_task(task_no):
                affected.append(task_no)
        return affected

    def scan_task(self, task_no: str) -> bool:
        """扫描单个任务；若处理了超时步骤返回 True。"""
        task = self.task_service.get(task_no)
        if not task:
            return False
        if task.status in (TaskStatus.FAILED.value, TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value):
            return False

        running = self.step_service.get_running_step(task_no)
        if not running or not running.started_at:
            return False

        elapsed = (datetime.now() - running.started_at).total_seconds()
        if elapsed <= running.timeout_seconds:
            return False

        self.step_service.mark_timeout(task_no, running.id)
        if running.retry_count < running.max_retry:
            self.task_service.update_status(
                task,
                task.status,
                step_message=(
                    f"步骤 [{running.step_name}] 超时，可重试 "
                    f"({running.retry_count + 1}/{running.max_retry})"
                ),
            )
            return True

        self.task_service.fail_task(
            task,
            error_code="step_timeout",
            error_message=(
                f"步骤 [{running.step_name}] 超时且已达最大重试 {running.max_retry}"
            ),
        )
        return True
