"""任务相关 API。"""

import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile

from app.api.deps import (
    get_pipeline_runner,
    get_result_store,
    get_step_service,
    get_task_service,
    get_timeout_worker,
)
from app.api.schemas import (
    CreateTaskResponse,
    TaskDetailResponse,
    TaskListResponse,
    TaskReportResponse,
    TaskStepsListResponse,
    TaskStepResponse,
    TaskSummary,
)
from app.document.enrich import enrich_sections_with_snapshot
from app.document.markdown_parser import parse_markdown_sections
from app.config import get_settings
from app.tasks.models import TaskQualityWarnings, TaskRecord, TaskStatus
from app.tasks.pipeline_runner import PipelineTaskRunner
from app.tasks.result_store import TaskResultStore
from app.tasks.step_service import TaskStepService
from app.tasks.task_service import TaskService
from app.tasks.timeout_worker import TimeoutWorker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])

ALLOWED_EXTENSIONS = {".md", ".markdown", ".txt"}


def _to_summary(task: TaskRecord) -> TaskSummary:
    should_warn = False
    alert_level = "none"
    if task.quality_warnings:
        should_warn = task.quality_warnings.should_warn_user
        alert_level = task.quality_warnings.alert_level
    return TaskSummary(
        task_no=task.task_no,
        task_type=task.task_type,
        status=task.status,
        progress=task.progress,
        current_step=task.current_step,
        step_message=task.step_message,
        source_file=task.source_file,
        should_warn_user=should_warn,
        alert_level=alert_level,
        created_at=task.created_at,
        updated_at=task.updated_at,
        finished_at=task.finished_at,
    )


def _to_detail(task: TaskRecord, result_store: TaskResultStore) -> TaskDetailResponse:
    return TaskDetailResponse(
        **task.model_dump(),
        has_report=result_store.exists(task.task_no),
    )


def _run_pipeline_background(
    task_no: str,
    file_path: Path,
    document_title: str | None,
    runner: PipelineTaskRunner,
    task_service: TaskService,
) -> None:
    task = task_service.get(task_no)
    if not task:
        logger.error("后台任务找不到 task_no=%s", task_no)
        return

    try:
        content = file_path.read_text(encoding="utf-8")
        sections = enrich_sections_with_snapshot(parse_markdown_sections(content))
        suffix = file_path.suffix.lstrip(".") or "unknown"
        runner.run_full(
            sections,
            task=task,
            source_file=file_path.name,
            document_title=document_title,
            source_type=suffix,
        )
    except Exception:
        logger.exception("任务 %s 流水线执行失败", task_no)


@router.get("", response_model=TaskListResponse)
def list_tasks(
    limit: int = Query(default=20, ge=1, le=100),
    task_service: TaskService = Depends(get_task_service),
) -> TaskListResponse:
    tasks = task_service.list_tasks(limit=limit)
    items = [_to_summary(task) for task in tasks]
    return TaskListResponse(total=len(items), items=items)


@router.get("/{task_no}", response_model=TaskDetailResponse)
def get_task(
    task_no: str,
    task_service: TaskService = Depends(get_task_service),
    result_store: TaskResultStore = Depends(get_result_store),
    timeout_worker: TimeoutWorker = Depends(get_timeout_worker),
) -> TaskDetailResponse:
    timeout_worker.scan_task(task_no)
    task = task_service.get(task_no)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_no}")
    return _to_detail(task, result_store)


@router.get("/{task_no}/steps", response_model=TaskStepsListResponse)
def get_task_steps(
    task_no: str,
    task_service: TaskService = Depends(get_task_service),
    step_service: TaskStepService = Depends(get_step_service),
    timeout_worker: TimeoutWorker = Depends(get_timeout_worker),
) -> TaskStepsListResponse:
    timeout_worker.scan_task(task_no)
    task = task_service.get(task_no)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_no}")
    steps = step_service.list_steps(task_no)
    return TaskStepsListResponse(
        task_no=task_no,
        items=[TaskStepResponse(**step.model_dump()) for step in steps],
    )


@router.get("/{task_no}/quality-warnings", response_model=TaskQualityWarnings | None)
def get_quality_warnings(
    task_no: str,
    task_service: TaskService = Depends(get_task_service),
) -> TaskQualityWarnings | None:
    task = task_service.get(task_no)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_no}")
    return task.quality_warnings


@router.get("/{task_no}/report", response_model=TaskReportResponse)
def get_task_report(
    task_no: str,
    task_service: TaskService = Depends(get_task_service),
    result_store: TaskResultStore = Depends(get_result_store),
) -> TaskReportResponse:
    task = task_service.get(task_no)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_no}")

    payload = result_store.get(task_no)
    if not payload:
        raise HTTPException(
            status_code=404,
            detail=f"任务报告尚未就绪（当前状态: {task.status}）",
        )
    return TaskReportResponse(**payload)


@router.post("/run", response_model=CreateTaskResponse, status_code=202)
async def run_task(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    title: str | None = None,
    task_service: TaskService = Depends(get_task_service),
    runner: PipelineTaskRunner = Depends(get_pipeline_runner),
) -> CreateTaskResponse:
    settings = get_settings()
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {suffix}，仅支持 {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    upload_dir = settings.upload_storage_dir
    upload_dir.mkdir(parents=True, exist_ok=True)

    task = task_service.create(
        task_type="full",
        source_file=file.filename,
        config={"document_title": title},
    )
    task_service.update_status(
        task,
        TaskStatus.UPLOADED,
        progress=5,
        current_step="upload",
        step_message="文件已上传，等待分析",
    )

    saved_path = upload_dir / f"{task.task_no}{suffix}"
    content = await file.read()
    saved_path.write_bytes(content)

    background_tasks.add_task(
        _run_pipeline_background,
        task.task_no,
        saved_path,
        title,
        runner,
        task_service,
    )

    return CreateTaskResponse(
        task_no=task.task_no,
        status=TaskStatus.ANALYZING.value,
        message="任务已提交，请通过 GET /api/tasks/{task_no} 轮询状态",
    )


@router.post("/timeout-scan")
def scan_timeouts(
    timeout_worker: TimeoutWorker = Depends(get_timeout_worker),
) -> dict:
    """扫描全部 running 步骤是否超时（供 cron 或运维调用）。"""
    affected = timeout_worker.scan_all()
    return {"scanned": True, "affected_tasks": affected, "count": len(affected)}
