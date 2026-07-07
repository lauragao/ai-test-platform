"""API 请求/响应模型。"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.tasks.models import TaskQualityWarnings


class TaskSummary(BaseModel):
    task_no: str
    task_type: str
    status: str
    progress: int
    current_step: Optional[str] = None
    step_message: Optional[str] = None
    source_file: Optional[str] = None
    should_warn_user: bool = False
    alert_level: str = "none"
    created_at: datetime
    updated_at: datetime
    finished_at: Optional[datetime] = None


class TaskListResponse(BaseModel):
    total: int
    items: list[TaskSummary]


class TaskDetailResponse(BaseModel):
    id: Optional[int] = None
    task_no: str
    document_id: Optional[int] = None
    task_type: str
    status: str
    progress: int
    current_step: Optional[str] = None
    step_message: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int
    max_retry: int
    timeout_seconds: int = 180
    config: dict[str, Any] = Field(default_factory=dict)
    quality_warnings: Optional[TaskQualityWarnings] = None
    source_file: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    has_report: bool = False


class TaskStepResponse(BaseModel):
    id: int
    task_no: str
    step_name: str
    step_order: int
    status: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int
    max_retry: int
    timeout_seconds: int
    duration_ms: Optional[int] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class TaskStepsListResponse(BaseModel):
    task_no: str
    items: list[TaskStepResponse]


class CreateTaskResponse(BaseModel):
    task_no: str
    status: str
    message: str


class TaskReportResponse(BaseModel):
    task_no: str
    task_status: str
    quality_warnings: Optional[dict[str, Any]] = None
    extract: dict[str, Any]
    completeness: Optional[dict[str, Any]] = None
    requirements: list[dict[str, Any]]
    analyze: dict[str, Any]
    parse_quality: dict[str, Any]
    case_quality: dict[str, Any]
    cases: dict[str, Any]


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "nb-test-platform-api"
