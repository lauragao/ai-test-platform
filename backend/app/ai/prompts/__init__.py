"""Prompt 模板目录。"""

from . import (
    case_generation,
    requirement_analysis,
    requirement_completeness_check,
    requirement_extract,
)

PROMPT_MODULES = {
    "extract_requirements": requirement_extract,
    "check_requirement_completeness": requirement_completeness_check,
    "analyze_requirements": requirement_analysis,
    "generate_test_cases": case_generation,
}

__all__ = [
    "requirement_extract",
    "requirement_completeness_check",
    "requirement_analysis",
    "case_generation",
    "PROMPT_MODULES",
]
