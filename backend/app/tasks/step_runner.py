"""带超时与重试的步骤执行器。"""

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, Callable, Optional, TypeVar

from app.ai.ai_service import AiServiceError
from app.tasks.exceptions import MaxRetriesExceededError, TaskExecutionError, TaskStepTimeoutError
from app.tasks.models import TaskRecord, TaskStatus
from app.tasks.step_policy import RETRIABLE_ERROR_CODES, resolve_step_policy
from app.tasks.step_service import TaskStepService
from app.tasks.task_service import TaskService

logger = logging.getLogger(__name__)

T = TypeVar("T")


class PipelineStepRunner:
    """为流水线各步骤提供 timeout / max_retry 执行语义。"""

    def __init__(self, task_service: TaskService, step_service: TaskStepService):
        self.task_service = task_service
        self.step_service = step_service

    def run_step(
        self,
        task: TaskRecord,
        step_name: str,
        callback: Callable[[], T],
        *,
        task_status: TaskStatus | None = None,
        progress: Optional[int] = None,
        step_message: Optional[str] = None,
        input_snapshot: Optional[dict[str, Any]] = None,
    ) -> T:
        policy = resolve_step_policy(step_name, task.config, task_timeout_seconds=task.timeout_seconds)
        last_error = "未知错误"
        last_code = "pipeline_failed"

        for attempt in range(policy.max_retry + 1):
            step = self.step_service.begin(
                task.task_no,
                step_name,
                policy,
                attempt=attempt,
                input_snapshot=input_snapshot,
            )
            if task_status is not None:
                self.task_service.update_status(
                    task,
                    task_status,
                    progress=progress,
                    current_step=step_name,
                    step_message=step_message or f"执行步骤 {step_name}",
                )

            try:
                result = self._invoke_with_timeout(callback, policy.timeout_seconds, step_name)
                output_snapshot = None
                if hasattr(result, "model_dump"):
                    output_snapshot = {"summary": getattr(result, "summary", None)}
                self.step_service.succeed(task.task_no, step.id, output_snapshot=output_snapshot)
                return result
            except TaskStepTimeoutError as exc:
                last_code = exc.error_code
                last_error = str(exc)
                self.step_service.fail(
                    task.task_no,
                    step.id,
                    error_code=last_code,
                    error_message=last_error,
                    status="timeout",
                )
                logger.warning("步骤超时 task=%s step=%s attempt=%d", task.task_no, step_name, attempt)
            except AiServiceError as exc:
                last_code = getattr(exc, "error_code", None) or "pipeline_failed"
                last_error = str(exc)
                self.step_service.fail(
                    task.task_no,
                    step.id,
                    error_code=last_code,
                    error_message=last_error,
                )
            except TaskExecutionError as exc:
                last_code = exc.error_code
                last_error = str(exc)
                self.step_service.fail(
                    task.task_no,
                    step.id,
                    error_code=last_code,
                    error_message=last_error,
                )
            except Exception as exc:
                last_code = "pipeline_failed"
                last_error = str(exc)
                self.step_service.fail(
                    task.task_no,
                    step.id,
                    error_code=last_code,
                    error_message=last_error,
                )
                logger.exception("步骤异常 task=%s step=%s", task.task_no, step_name)

            if attempt < policy.max_retry and last_code in RETRIABLE_ERROR_CODES:
                task.retry_count = attempt + 1
                self.task_service.save(task)
                continue

            final_code = "max_retries_exceeded" if attempt >= policy.max_retry else last_code
            final_message = (
                f"步骤 [{step_name}] 已达最大重试 {policy.max_retry}：{last_error}"
                if attempt >= policy.max_retry
                else last_error
            )
            self.task_service.fail_task(task, error_code=final_code, error_message=final_message)
            if attempt >= policy.max_retry:
                raise MaxRetriesExceededError(step_name, policy.max_retry, last_error) from None
            raise TaskExecutionError(final_message, error_code=final_code)

        raise TaskExecutionError(last_error, error_code=last_code)

    @staticmethod
    def _invoke_with_timeout(callback: Callable[[], T], timeout_seconds: int, step_name: str) -> T:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(callback)
            try:
                return future.result(timeout=timeout_seconds)
            except FuturesTimeoutError as exc:
                raise TaskStepTimeoutError(step_name, timeout_seconds) from exc
