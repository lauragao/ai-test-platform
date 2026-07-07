"""应用配置，从环境变量加载。"""

from functools import lru_cache

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o-mini"
    ai_temperature: float = 0.2
    ai_max_retries: int = 3
    ai_timeout_seconds: int = 120

    # 多模型混合路由（见 app/ai/model_router.py）
    ai_multi_model_enabled: bool = True
    ai_long_context_threshold_chars: int = 20000

    # 复杂需求分析：GPT-4-turbo / Kimi
    ai_model_complex: str = ""
    ai_base_url_complex: str = ""
    ai_api_key_complex: str = ""

    # 测试用例生成：GPT-4o / 智谱 GLM-4
    ai_model_cases: str = ""
    ai_base_url_cases: str = ""
    ai_api_key_cases: str = ""

    # 格式转换 / 轻量任务：GPT-3.5-turbo
    ai_model_light: str = ""
    ai_base_url_light: str = ""
    ai_api_key_light: str = ""

    # 大规模文档：Kimi 32k / 通义千问
    ai_model_long: str = ""
    ai_base_url_long: str = ""
    ai_api_key_long: str = ""

    task_default_timeout_seconds: int = 180

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_cors_origins: str = "*"

    @property
    def task_storage_dir(self) -> Path:
        return BACKEND_ROOT / "tmp" / "tasks"

    @property
    def result_storage_dir(self) -> Path:
        return BACKEND_ROOT / "tmp" / "outputs"

    @property
    def task_step_storage_dir(self) -> Path:
        return BACKEND_ROOT / "tmp" / "task_steps"

    @property
    def upload_storage_dir(self) -> Path:
        return BACKEND_ROOT / "tmp" / "uploads"

    @property
    def document_storage_dir(self) -> Path:
        return BACKEND_ROOT / "tmp" / "documents"

    @property
    def export_storage_dir(self) -> Path:
        return BACKEND_ROOT / "tmp" / "exports"


@lru_cache
def get_settings() -> Settings:
    return Settings()
