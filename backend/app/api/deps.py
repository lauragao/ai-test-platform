"""API 依赖注入。"""

from functools import lru_cache

from app.ai.ai_service import AiService
from app.config import Settings, get_settings
from app.tasks.pipeline_runner import PipelineTaskRunner
from app.tasks.result_store import TaskResultStore
from app.tasks.step_service import TaskStepService
from app.tasks.task_service import TaskService
from app.tasks.timeout_worker import TimeoutWorker


@lru_cache
def get_task_service() -> TaskService:
    settings = get_settings()
    return TaskService(settings.task_storage_dir)


@lru_cache
def get_step_service() -> TaskStepService:
    settings = get_settings()
    return TaskStepService(settings.task_step_storage_dir)


@lru_cache
def get_result_store() -> TaskResultStore:
    settings = get_settings()
    return TaskResultStore(settings.result_storage_dir)


@lru_cache
def get_ai_service() -> AiService:
    return AiService()


@lru_cache
def get_pipeline_runner() -> PipelineTaskRunner:
    return PipelineTaskRunner(
        get_ai_service(),
        get_task_service(),
        get_result_store(),
        get_step_service(),
    )


def get_timeout_worker() -> TimeoutWorker:
    return TimeoutWorker(get_task_service(), get_step_service())


def get_app_settings() -> Settings:
    return get_settings()
