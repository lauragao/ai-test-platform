"""Prompt 模板目录。"""

from . import case_generation, requirement_analysis, requirement_extract

PROMPT_MODULES = {
    "extract_requirements": requirement_extract,
    "analyze_requirements": requirement_analysis,
    "generate_test_cases": case_generation,
}

__all__ = [
    "requirement_extract",
    "requirement_analysis",
    "case_generation",
    "PROMPT_MODULES",
]
