"""任务与质量告警数据模型，对齐 nb_test_tasks.quality_warnings。"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    CREATED = "created"
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    ANALYZING = "analyzing"
    ANALYSIS_COMPLETED = "analysis_completed"
    GENERATING_CASES = "generating_cases"
    CASE_COMPLETED = "case_completed"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class TaskErrorCode(str, Enum):
    STEP_TIMEOUT = "step_timeout"
    AI_CALL_TIMEOUT = "ai_call_timeout"
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"
    PIPELINE_FAILED = "pipeline_failed"
    VALIDATION_FAILED = "validation_failed"


class QualityWarningItem(BaseModel):
    """单条质量告警，供任务详情页展示。"""

    warning_type: str = Field(
        description="告警类型：parse_quality / case_coverage / requirement_quote 等"
    )
    level: str = Field(description="info | warning | critical")
    message: str
    metrics: dict[str, Any] = Field(default_factory=dict)


class TaskQualityWarnings(BaseModel):
    """写入 nb_test_tasks.quality_warnings 的结构化 JSON。"""

    items: list[QualityWarningItem] = Field(default_factory=list)
    alert_level: str = Field(default="none")
    should_warn_user: bool = False
    updated_at: datetime = Field(default_factory=datetime.now)

    def add_item(self, item: QualityWarningItem) -> None:
        self.items.append(item)
        self._escalate(item.level)

    def _escalate(self, level: str) -> None:
        rank = {"none": 0, "info": 1, "warning": 2, "critical": 3}
        if rank.get(level, 0) > rank.get(self.alert_level, 0):
            self.alert_level = level
        if level in ("warning", "critical"):
            self.should_warn_user = True


class TaskStepRecord(BaseModel):
    """对应 nb_test_task_steps（MVP 文件持久化）。"""

    id: int
    task_no: str
    step_name: str
    step_order: int
    status: str = TaskStepStatus.PENDING.value
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retry: int = 3
    timeout_seconds: int = 180
    input_snapshot: Optional[dict[str, Any]] = None
    output_snapshot: Optional[dict[str, Any]] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class TaskRecord(BaseModel):
    """对应 nb_test_tasks（MVP 文件持久化）。"""

    id: Optional[int] = None
    document_id: Optional[int] = None
    task_no: str
    task_type: str = "full"
    status: str = TaskStatus.CREATED.value
    progress: int = 0
    current_step: Optional[str] = None
    step_message: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retry: int = 3
    timeout_seconds: int = 180
    config: dict[str, Any] = Field(default_factory=dict)
    quality_warnings: Optional[TaskQualityWarnings] = None
    source_file: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
