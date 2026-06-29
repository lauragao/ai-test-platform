"""AI 模块：统一封装 LLM 调用与 Prompt 编排。"""

from .ai_service import AiService, AiServiceError
from .models import (
    AnalyzeRequirementsResult,
    DocumentSectionInput,
    ExtractRequirementsResult,
    GenerateTestCasesResult,
    RequirementIssue,
    RequirementItem,
    RunType,
    TestCaseItem,
)

__all__ = [
    "AiService",
    "AiServiceError",
    "RunType",
    "DocumentSectionInput",
    "RequirementItem",
    "RequirementIssue",
    "TestCaseItem",
    "ExtractRequirementsResult",
    "AnalyzeRequirementsResult",
    "GenerateTestCasesResult",
]
