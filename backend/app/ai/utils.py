"""AI 模块工具函数。"""

import json
import re
from typing import Any, Optional

import jsonschema

from app.ai.models import DocumentSectionInput
from app.ai.schemas import CASES_SCHEMA, ISSUES_SCHEMA


def parse_json_content(raw: str) -> dict[str, Any]:
    """从 LLM 返回文本中解析 JSON，兼容 markdown 代码块包裹。"""
    text = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence_match:
        text = fence_match.group(1).strip()
    return json.loads(text)


def sections_to_json(sections: list[DocumentSectionInput]) -> str:
    return json.dumps(
        [s.model_dump() for s in sections],
        ensure_ascii=False,
        indent=2,
    )


def items_to_json(items: list[Any]) -> str:
    return json.dumps(
        [item.model_dump() for item in items],
        ensure_ascii=False,
        indent=2,
    )


def validate_issues_schema(data: dict[str, Any]) -> None:
    jsonschema.validate(instance=data, schema=ISSUES_SCHEMA)


def validate_cases_schema(data: dict[str, Any]) -> None:
    jsonschema.validate(instance=data, schema=CASES_SCHEMA)


def build_retry_prompt(original_user: str, last_raw: Optional[str], error: str) -> str:
    return (
        f"{original_user}\n\n"
        "---\n"
        "你上一次的输出未通过 JSON Schema 校验，请修正后重新输出。\n"
        f"校验错误：{error}\n"
        f"上次输出：\n{last_raw or '(空)'}\n"
        "请仅返回修正后的合法 JSON，不要包含其他说明文字。"
    )
