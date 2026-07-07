"""模型路由查询 API。"""

from fastapi import APIRouter, Depends

from app.ai.model_router import CATEGORY_RECOMMENDATIONS, ModelRouter
from app.api.deps import get_app_settings, get_model_router
from app.config import Settings

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/routing")
def get_model_routing(
    router_svc: ModelRouter = Depends(get_model_router),
    settings: Settings = Depends(get_app_settings),
) -> dict:
    """返回当前多模型路由配置与推荐策略。"""
    return {
        "multi_model_enabled": settings.ai_multi_model_enabled,
        "long_context_threshold_chars": settings.ai_long_context_threshold_chars,
        "default_model": settings.ai_model,
        "routing_table": router_svc.list_routing_table(),
        "recommendations": {
            key.value: value for key, value in CATEGORY_RECOMMENDATIONS.items()
        },
    }
