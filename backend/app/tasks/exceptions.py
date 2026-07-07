"""任务步骤相关异常。"""


class TaskExecutionError(Exception):
    def __init__(self, message: str, *, error_code: str = "pipeline_failed"):
        super().__init__(message)
        self.error_code = error_code


class TaskStepTimeoutError(TaskExecutionError):
    def __init__(self, step_name: str, timeout_seconds: int):
        super().__init__(
            f"步骤 [{step_name}] 执行超时（>{timeout_seconds}s）",
            error_code="step_timeout",
        )
        self.step_name = step_name
        self.timeout_seconds = timeout_seconds


class MaxRetriesExceededError(TaskExecutionError):
    def __init__(self, step_name: str, max_retry: int, last_error: str):
        super().__init__(
            f"步骤 [{step_name}] 已达最大重试次数 {max_retry}：{last_error}",
            error_code="max_retries_exceeded",
        )
        self.step_name = step_name
        self.max_retry = max_retry
