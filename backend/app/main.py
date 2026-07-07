"""FastAPI 应用入口。"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.tasks import router as tasks_router
from app.api.schemas import HealthResponse
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="AI 需求分析与测试用例生成平台",
    description="MVP REST API：任务列表、详情、质量告警、分析报告",
    version="0.1.0",
)

origins = ["*"] if settings.api_cors_origins == "*" else [
    origin.strip() for origin in settings.api_cors_origins.split(",") if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks_router, prefix="/api")


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health_check() -> HealthResponse:
    return HealthResponse()
