"""AI 模块工具函数。"""

import json
import re
from typing import Any, Optional

import jsonschema

from app.ai.models import DocumentSectionInput, CompletenessCheckResult
from app.ai.schemas import CASES_SCHEMA, COMPLETENESS_SCHEMA, ISSUES_SCHEMA


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


def validate_completeness_schema(data: dict[str, Any]) -> None:
    jsonschema.validate(instance=data, schema=COMPLETENESS_SCHEMA)


def build_document_toc(
    sections: list[DocumentSectionInput],
    document_title: Optional[str] = None,
) -> str:
    """生成文档目录 JSON，供完备性自检使用。"""
    title = document_title
    if not title:
        for section in sections:
            if section.level == 1 and section.title:
                title = section.title
                break
        if not title and sections:
            title = sections[0].title or "未命名文档"
        if not title:
            title = "未命名文档"

    toc = {
        "document_title": title,
        "sections": [
            {
                "section_id": section.section_id,
                "title": section.title,
                "level": section.level,
            }
            for section in sections
        ],
    }
    return json.dumps(toc, ensure_ascii=False, indent=2)


def merge_requirements(
    existing: list[Any],
    additional: list[Any],
) -> list[Any]:
    """合并补抽需求点，并为新增项续编 req_key。"""
    if not additional:
        return list(existing)

    max_num = 0
    for req in existing:
        match = re.match(r"req_(\d+)$", req.req_key)
        if match:
            max_num = max(max_num, int(match.group(1)))

    merged = list(existing)
    for index, req in enumerate(additional, start=1):
        merged.append(req.model_copy(update={"req_key": f"req_{max_num + index:03d}"}))
    return merged


def requirements_to_summary_json(requirements: list[Any]) -> str:
    """精简需求列表，供完备性自检 Prompt 使用。"""
    summary_items = [
        {
            "req_key": req.req_key,
            "section_id": req.section_id,
            "module": req.module,
            "title": req.title,
            "description": req.description,
        }
        for req in requirements
    ]
    return json.dumps(summary_items, ensure_ascii=False, indent=2)


def collect_refill_section_ids(result: CompletenessCheckResult) -> list[str]:
    """从完备性自检结果中收集需补抽的 section_id。"""
    refill_ids = {item.section_id for item in result.sections_to_refill}
    for item in result.coverage_map:
        if item.coverage_status in ("partial", "missing"):
            refill_ids.add(item.section_id)
    return sorted(refill_ids)


def build_retry_prompt(original_user: str, last_raw: Optional[str], error: str) -> str:
    return (
        f"{original_user}\n\n"
        "---\n"
        "你上一次的输出未通过 JSON Schema 校验，请修正后重新输出。\n"
        f"校验错误：{error}\n"
        f"上次输出：\n{last_raw or '(空)'}\n"
        "请仅返回修正后的合法 JSON，不要包含其他说明文字。"
    )
