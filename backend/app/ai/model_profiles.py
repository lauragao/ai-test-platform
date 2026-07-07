"""多模型配置：按任务类型选择不同 LLM。"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ModelTaskCategory(str, Enum):
    """模型任务分类，对齐设计文档推荐策略。"""

    COMPLEX_ANALYSIS = "complex_analysis"
    """复杂需求分析：GPT-4-turbo / Kimi，理解力强。"""

    CASE_GENERATION = "case_generation"
    """测试用例生成：GPT-4o / 智谱 GLM-4，质量与成本平衡。"""

    FORMAT_LIGHT = "format_light"
    """格式转换 / 轻量反思：GPT-3.5-turbo，低成本快速。"""

    LONG_CONTEXT = "long_context"
    """大规模文档：Kimi 32k / 通义千问，超长上下文。"""

    DEFAULT = "default"
    """未分类或关闭多模型路由时的默认模型。"""


@dataclass(frozen=True)
class ModelProfile:
    """单次 LLM 调用的模型与网关配置。"""

    model: str
    base_url: str
    api_key: str
    category: ModelTaskCategory
    temperature: Optional[float] = None
    label: str = ""

    @property
    def profile_key(self) -> str:
        return f"{self.category.value}:{self.model}@{self.base_url}"
