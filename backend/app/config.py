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

    task_default_timeout_seconds: int = 180

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_cors_origins: str = "*"

    @property
    def task_storage_dir(self) -> Path:
        return BACKEND_ROOT / "tmp" / "tasks"

    @property
    def result_storage_dir(self) -> Path:
        return BACKEND_ROOT / "tmp" / "results"

    @property
    def task_step_storage_dir(self) -> Path:
        return BACKEND_ROOT / "tmp" / "task_steps"

    @property
    def upload_storage_dir(self) -> Path:
        return BACKEND_ROOT / "tmp" / "uploads"


@lru_cache
def get_settings() -> Settings:
    return Settings()
