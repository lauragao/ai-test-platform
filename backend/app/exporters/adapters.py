"""导出字段适配层。

后端内部使用英文结构字段，Excel/XMind 导出沿用旧工具的中文字段格式。
"""

from typing import Any

from app.ai.models import RequirementItem, TestCaseItem


REGRESSION_NAME_MAP = {
    "SMOKE": "冒烟",
    "CORE": "核心",
    "FULL": "全量",
}


def split_module_path(module: str | None) -> list[str]:
    if not module:
        return ["未分组"]

    for separator in ("/", ">", "｜", "|"):
        if separator in module:
            return [part.strip() for part in module.split(separator) if part.strip()]

    return [module.strip()]


def normalize_steps(case: TestCaseItem) -> list[dict[str, str]]:
    """将 steps + expected_result 转成 XMind 需要的操作/预期结构。"""
    normalized: list[dict[str, str]] = []
    for index, step in enumerate(case.steps, 1):
        expected = case.expected_result if index == len(case.steps) else ""
        normalized.append(
            {
                "操作": step,
                "预期": expected,
            }
        )
    return normalized


def to_legacy_case(case: TestCaseItem) -> dict[str, Any]:
    requirement_ids = ", ".join(case.source_requirement_ids)
    design_methods = ", ".join(case.design_methods)
    risk_notes = "；".join(case.risk_notes)
    remark_parts = [part for part in [case.remark, risk_notes] if part]
    regression_type = case.regression_type or regression_type_from_priority(case.priority)

    return {
        "用例编号": case.case_key,
        "模块": split_module_path(case.module),
        "模块名称": " / ".join(split_module_path(case.module)),
        "用例标题": case.title,
        "优先级": case.priority,
        "关联需求ID": requirement_ids,
        "设计方法": design_methods,
        "前置条件": case.precondition or "",
        "测试步骤": "\n".join(case.steps),
        "步骤": normalize_steps(case),
        "预期结果": case.expected_result,
        "实际结果": "",
        "是否通过": "未执行",
        "回归类型": REGRESSION_NAME_MAP.get(regression_type, regression_type),
        "备注": "；".join(remark_parts),
        "标签": case.tag or "",
    }


def to_legacy_cases(cases: list[TestCaseItem]) -> list[dict[str, Any]]:
    return [to_legacy_case(case) for case in cases]


def to_legacy_requirements(requirements: list[RequirementItem]) -> list[dict[str, Any]]:
    return [
        {
            "id": requirement.req_key,
            "需求ID": requirement.req_key,
            "需求名称": requirement.title,
            "所属模块": requirement.module or "",
        }
        for requirement in requirements
    ]


def regression_type_from_priority(priority: str) -> str:
    normalized = (priority or "").upper()
    if normalized == "P0":
        return "SMOKE"
    if normalized == "P1":
        return "CORE"
    return "FULL"
