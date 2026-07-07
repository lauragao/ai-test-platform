"""任务相关 API。"""

import logging
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import (
    get_document_store,
    get_export_service,
    get_pipeline_runner,
    get_result_store,
    get_step_service,
    get_task_service,
    get_timeout_worker,
)
from app.api.schemas import (
    CreateTaskResponse,
    DocumentSectionResponse,
    ExportTaskResponse,
    RetryTaskResponse,
    TaskDetailResponse,
    TaskDocumentResponse,
    TaskListResponse,
    TaskReportResponse,
    TaskStepsListResponse,
    TaskStepResponse,
    TaskSummary,
)
from app.api.upload_utils import find_upload_file, load_and_parse_upload
from app.config import get_settings
from app.document.document_parser import supported_extensions
from app.document.document_store import DocumentStore
from app.document.section_snapshot import compute_document_parse_confidence
from app.tasks.export_service import TaskExportService
from app.tasks.models import TaskQualityWarnings, TaskRecord, TaskStatus
from app.tasks.pipeline_runner import PipelineTaskRunner
from app.tasks.result_store import TaskResultStore
from app.tasks.step_service import TaskStepService
from app.tasks.task_service import TaskService
from app.tasks.timeout_worker import TimeoutWorker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])

ALLOWED_EXTENSIONS = supported_extensions()
RETRYABLE_STATUSES = {TaskStatus.FAILED.value, TaskStatus.CANCELLED.value}
ExportFormat = Literal["xlsx", "xmind"]


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
    document_store: DocumentStore,
) -> None:
    task = task_service.get(task_no)
    if not task:
        logger.error("后台任务找不到 task_no=%s", task_no)
        return

    try:
        sections = load_and_parse_upload(file_path)
        document_store.save_sections(task_no, sections)
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


def _load_document_sections(
    task_no: str,
    task: TaskRecord,
    document_store: DocumentStore,
    upload_dir: Path,
) -> list:
    sections = document_store.get_sections(task_no)
    if sections:
        return sections

    upload_file = find_upload_file(task_no, upload_dir)
    if not upload_file:
        return []

    sections = load_and_parse_upload(upload_file)
    document_store.save_sections(task_no, sections)
    return sections


def _to_document_response(
    task: TaskRecord,
    sections: list,
) -> TaskDocumentResponse:
    confidences = [
        section.parse_confidence
        for section in sections
        if section.parse_confidence is not None
    ]
    lengths = [len(section.content) for section in sections]
    doc_confidence = compute_document_parse_confidence(confidences, lengths) if confidences else None

    return TaskDocumentResponse(
        task_no=task.task_no,
        source_file=task.source_file,
        section_count=len(sections),
        document_parse_confidence=doc_confidence,
        sections=[
            DocumentSectionResponse(
                section_id=section.section_id,
                title=section.title,
                level=section.level,
                content=section.content,
                page_start=section.page_start,
                page_end=section.page_end,
                source_snapshot=(
                    section.source_snapshot.model_dump()
                    if section.source_snapshot is not None
                    else None
                ),
                parse_confidence=section.parse_confidence,
            )
            for section in sections
        ],
    )


@router.get("", response_model=TaskListResponse)
def list_tasks(
    limit: int = Query(default=20, ge=1, le=100),
    task_service: TaskService = Depends(get_task_service),
) -> TaskListResponse:
    tasks = task_service.list_tasks(limit=limit)
    items = [_to_summary(task) for task in tasks]
    return TaskListResponse(total=len(items), items=items)


@router.post("/run", response_model=CreateTaskResponse, status_code=202)
async def run_task(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    title: str | None = None,
    task_service: TaskService = Depends(get_task_service),
    runner: PipelineTaskRunner = Depends(get_pipeline_runner),
    document_store: DocumentStore = Depends(get_document_store),
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
        document_store,
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


@router.get("/{task_no}/document", response_model=TaskDocumentResponse)
def get_task_document(
    task_no: str,
    task_service: TaskService = Depends(get_task_service),
    document_store: DocumentStore = Depends(get_document_store),
) -> TaskDocumentResponse:
    settings = get_settings()
    task = task_service.get(task_no)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_no}")

    sections = _load_document_sections(
        task_no,
        task,
        document_store,
        settings.upload_storage_dir,
    )
    if not sections:
        raise HTTPException(
            status_code=404,
            detail="文档章节尚未就绪，请确认任务已上传且原始文件仍存在",
        )
    return _to_document_response(task, sections)


@router.post("/{task_no}/export", response_model=ExportTaskResponse)
def export_task(
    task_no: str,
    fmt: ExportFormat = Query(..., alias="format", description="导出格式：xlsx 或 xmind"),
    task_service: TaskService = Depends(get_task_service),
    export_service: TaskExportService = Depends(get_export_service),
) -> ExportTaskResponse:
    task = task_service.get(task_no)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_no}")

    if task.status not in {
        TaskStatus.CASE_COMPLETED.value,
        TaskStatus.COMPLETED.value,
    }:
        raise HTTPException(
            status_code=400,
            detail=f"任务尚未完成，当前状态: {task.status}，无法导出",
        )

    document_title = task.config.get("document_title") if task.config else None
    try:
        output_path = export_service.export(
            task_no,
            fmt,
            document_title=document_title,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    filename = output_path.name
    return ExportTaskResponse(
        task_no=task_no,
        format=fmt,
        filename=filename,
        download_url=f"/api/tasks/{task_no}/exports/{filename}",
        file_size=output_path.stat().st_size,
    )


@router.get("/{task_no}/exports/{filename}")
def download_export(
    task_no: str,
    filename: str,
    task_service: TaskService = Depends(get_task_service),
    export_service: TaskExportService = Depends(get_export_service),
) -> FileResponse:
    task = task_service.get(task_no)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_no}")

    file_path = export_service.resolve_download_path(task_no, filename)
    if not file_path:
        raise HTTPException(status_code=404, detail=f"导出文件不存在: {filename}")

    media_types = {
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xmind": "application/octet-stream",
    }
    media_type = media_types.get(file_path.suffix.lower(), "application/octet-stream")
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type,
    )


@router.post("/{task_no}/retry", response_model=RetryTaskResponse, status_code=202)
def retry_task(
    task_no: str,
    background_tasks: BackgroundTasks,
    task_service: TaskService = Depends(get_task_service),
    step_service: TaskStepService = Depends(get_step_service),
    runner: PipelineTaskRunner = Depends(get_pipeline_runner),
    document_store: DocumentStore = Depends(get_document_store),
) -> RetryTaskResponse:
    settings = get_settings()
    task = task_service.get(task_no)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_no}")

    if task.status not in RETRYABLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"仅 failed / cancelled 状态可重试，当前状态: {task.status}",
        )

    upload_file = find_upload_file(task_no, settings.upload_storage_dir)
    if not upload_file:
        raise HTTPException(
            status_code=404,
            detail="找不到原始上传文件，无法重试，请重新上传文档",
        )

    step_service.reset_steps(task_no)
    task = task_service.reset_for_retry(task)
    document_title = task.config.get("document_title") if task.config else None

    background_tasks.add_task(
        _run_pipeline_background,
        task.task_no,
        upload_file,
        document_title,
        runner,
        task_service,
        document_store,
    )

    return RetryTaskResponse(
        task_no=task.task_no,
        status=TaskStatus.ANALYZING.value,
        message="任务已重新提交，请通过 GET /api/tasks/{task_no} 轮询状态",
    )
