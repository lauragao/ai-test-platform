"""按 RunType 与输入规模路由到不同模型。"""

from typing import Any

from app.ai.model_profiles import ModelProfile, ModelTaskCategory
from app.ai.models import RunType
from app.config import Settings


# 各分类的设计推荐（文档 / UI 展示用）
CATEGORY_RECOMMENDATIONS: dict[ModelTaskCategory, dict[str, str]] = {
    ModelTaskCategory.COMPLEX_ANALYSIS: {
        "task": "复杂需求分析（extract / analyze）",
        "models": "GPT-4-turbo / Kimi",
        "reason": "理解能力强，能处理复杂逻辑与矛盾检测",
    },
    ModelTaskCategory.CASE_GENERATION: {
        "task": "测试用例生成",
        "models": "GPT-4o / 智谱 GLM-4",
        "reason": "结构化输出稳定，质量与成本平衡",
    },
    ModelTaskCategory.FORMAT_LIGHT: {
        "task": "格式转换 / 完备性自检",
        "models": "GPT-3.5-turbo",
        "reason": "JSON 格式化与目录对照，成本低、速度快",
    },
    ModelTaskCategory.LONG_CONTEXT: {
        "task": "大规模文档抽取",
        "models": "Kimi (32k) / 通义千问",
        "reason": "支持超长上下文，避免截断遗漏",
    },
    ModelTaskCategory.DEFAULT: {
        "task": "默认",
        "models": "AI_MODEL 环境变量",
        "reason": "单模型模式或未配置分类模型时的回退",
    },
}

RUN_TYPE_DEFAULT_CATEGORY: dict[RunType, ModelTaskCategory] = {
    RunType.EXTRACT_REQUIREMENTS: ModelTaskCategory.COMPLEX_ANALYSIS,
    RunType.CHECK_REQUIREMENT_COMPLETENESS: ModelTaskCategory.FORMAT_LIGHT,
    RunType.ANALYZE_REQUIREMENTS: ModelTaskCategory.COMPLEX_ANALYSIS,
    RunType.GENERATE_CASES: ModelTaskCategory.CASE_GENERATION,
}


def estimate_sections_char_count(sections: list[Any]) -> int:
    total = 0
    for section in sections:
        content = getattr(section, "content", None) or ""
        title = getattr(section, "title", None) or ""
        total += len(content) + len(title)
    return total


class ModelRouter:
    """根据任务类型与输入规模为每次 AI 调用选择 ModelProfile。"""

    def __init__(self, settings: Settings):
        self.settings = settings

    def resolve(
        self,
        run_type: RunType,
        *,
        input_char_count: int = 0,
    ) -> ModelProfile:
        if not self.settings.ai_multi_model_enabled:
            return self._default_profile()

        category = self._pick_category(run_type, input_char_count)
        return self._profile_for(category)

    def list_routing_table(self) -> list[dict[str, Any]]:
        """返回当前配置下的路由表（供 API / 调试）。"""
        rows: list[dict[str, Any]] = []
        for run_type, default_cat in RUN_TYPE_DEFAULT_CATEGORY.items():
            profile = self.resolve(run_type, input_char_count=0)
            long_profile = None
            if run_type == RunType.EXTRACT_REQUIREMENTS:
                long_profile = self.resolve(
                    run_type,
                    input_char_count=self.settings.ai_long_context_threshold_chars,
                )
            rec = CATEGORY_RECOMMENDATIONS.get(
                default_cat, CATEGORY_RECOMMENDATIONS[ModelTaskCategory.DEFAULT]
            )
            rows.append(
                {
                    "run_type": run_type.value,
                    "default_category": default_cat.value,
                    "resolved_model": profile.model,
                    "resolved_base_url": profile.base_url,
                    "long_context_model": long_profile.model if long_profile else None,
                    "long_context_threshold_chars": self.settings.ai_long_context_threshold_chars,
                    "recommended": rec,
                }
            )
        return rows

    def _pick_category(
        self,
        run_type: RunType,
        input_char_count: int,
    ) -> ModelTaskCategory:
        if (
            run_type == RunType.EXTRACT_REQUIREMENTS
            and input_char_count >= self.settings.ai_long_context_threshold_chars
        ):
            return ModelTaskCategory.LONG_CONTEXT
        return RUN_TYPE_DEFAULT_CATEGORY.get(run_type, ModelTaskCategory.DEFAULT)

    def _profile_for(self, category: ModelTaskCategory) -> ModelProfile:
        field_map = {
            ModelTaskCategory.COMPLEX_ANALYSIS: (
                self.settings.ai_model_complex,
                self.settings.ai_base_url_complex,
                self.settings.ai_api_key_complex,
            ),
            ModelTaskCategory.CASE_GENERATION: (
                self.settings.ai_model_cases,
                self.settings.ai_base_url_cases,
                self.settings.ai_api_key_cases,
            ),
            ModelTaskCategory.FORMAT_LIGHT: (
                self.settings.ai_model_light,
                self.settings.ai_base_url_light,
                self.settings.ai_api_key_light,
            ),
            ModelTaskCategory.LONG_CONTEXT: (
                self.settings.ai_model_long,
                self.settings.ai_base_url_long,
                self.settings.ai_api_key_long,
            ),
        }
        model, base_url, api_key = field_map.get(category, ("", "", ""))
        return ModelProfile(
            model=model or self.settings.ai_model,
            base_url=base_url or self.settings.ai_base_url,
            api_key=api_key or self.settings.ai_api_key,
            category=category,
            label=category.value,
        )

    def _default_profile(self) -> ModelProfile:
        return ModelProfile(
            model=self.settings.ai_model,
            base_url=self.settings.ai_base_url,
            api_key=self.settings.ai_api_key,
            category=ModelTaskCategory.DEFAULT,
            label="default",
        )
