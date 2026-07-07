"""原文快照：评估文档解析质量的基础指标。"""

import re
from typing import Optional

from pydantic import BaseModel, Field

# 表格/结构相关符号
TABLE_MARKERS = frozenset("|┌┐└┘├┤┬┴┼─═")
# 除字母、数字、中文、常见标点外的非常规字符
SPECIAL_CHAR_PATTERN = re.compile(
    r"[^\w\s\u4e00-\u9fff，。！？；：、""''（）【】《》\-—…·]"
)


class SourceSnapshot(BaseModel):
    """段落级原文快照，用于解析质量评估与引用校验。"""

    raw_char_length: int = Field(description="原始字符长度（含空白）")
    whitespace_count: int = Field(description="空白字符数量")
    whitespace_ratio: float = Field(description="空白字符占比 0~1")
    table_marker_count: int = Field(description="表格结构符号数量（| 等）")
    table_marker_density: float = Field(description="每百字符表格符号数")
    special_char_count: int = Field(description="非常规特殊字符数量")
    special_char_density: float = Field(description="每百字符特殊字符数")
    alphanumeric_count: int = Field(description="字母与数字字符数量")
    alphanumeric_ratio: float = Field(description="字母数字占比 0~1")
    cjk_count: int = Field(description="中日韩字符数量")
    line_count: int = Field(description="行数")


def build_source_snapshot(text: str) -> SourceSnapshot:
    """从段落原文计算快照指标。"""
    raw = text or ""
    length = len(raw)
    if length == 0:
        return SourceSnapshot(
            raw_char_length=0,
            whitespace_count=0,
            whitespace_ratio=0.0,
            table_marker_count=0,
            table_marker_density=0.0,
            special_char_count=0,
            special_char_density=0.0,
            alphanumeric_count=0,
            alphanumeric_ratio=0.0,
            cjk_count=0,
            line_count=0,
        )

    whitespace_count = sum(1 for ch in raw if ch.isspace())
    table_marker_count = sum(1 for ch in raw if ch in TABLE_MARKERS or ch == "\t")
    special_char_count = len(SPECIAL_CHAR_PATTERN.findall(raw))
    alphanumeric_count = sum(1 for ch in raw if ch.isascii() and ch.isalnum())
    cjk_count = sum(1 for ch in raw if "\u4e00" <= ch <= "\u9fff")
    line_count = max(1, raw.count("\n") + (0 if raw.endswith("\n") else 1))

    per_hundred = length / 100.0
    return SourceSnapshot(
        raw_char_length=length,
        whitespace_count=whitespace_count,
        whitespace_ratio=round(whitespace_count / length, 4),
        table_marker_count=table_marker_count,
        table_marker_density=round(table_marker_count / per_hundred, 2),
        special_char_count=special_char_count,
        special_char_density=round(special_char_count / per_hundred, 2),
        alphanumeric_count=alphanumeric_count,
        alphanumeric_ratio=round(alphanumeric_count / length, 4),
        cjk_count=cjk_count,
        line_count=line_count,
    )


def compute_section_parse_confidence(snapshot: SourceSnapshot) -> float:
    """
    基于快照启发式计算单段解析置信度（0~1）。

    低分常见原因：OCR 乱码、空白过多、特殊字符密度异常、有效文本过少。
    """
    if snapshot.raw_char_length == 0:
        return 0.0

    score = 1.0
    readable = snapshot.alphanumeric_count + snapshot.cjk_count
    readable_ratio = readable / snapshot.raw_char_length

    if readable_ratio < 0.25:
        score -= 0.45
    elif readable_ratio < 0.45:
        score -= 0.25

    if snapshot.whitespace_ratio > 0.55:
        score -= 0.15
    elif snapshot.whitespace_ratio > 0.4:
        score -= 0.08

    if snapshot.special_char_density > 20:
        score -= 0.2
    elif snapshot.special_char_density > 12:
        score -= 0.1

    if snapshot.table_marker_density > 8 and readable_ratio < 0.5:
        score -= 0.1

    if snapshot.raw_char_length < 20 and snapshot.special_char_density > 5:
        score -= 0.15

    return round(max(0.0, min(1.0, score)), 4)


def compute_document_parse_confidence(
    snapshots: list[SourceSnapshot],
    *,
    weights: Optional[list[int]] = None,
) -> float:
    """按字符长度加权汇总文档级解析置信度。"""
    if not snapshots:
        return 0.0

    total_weight = 0
    weighted_sum = 0.0
    for index, snapshot in enumerate(snapshots):
        weight = (
            weights[index]
            if weights and index < len(weights)
            else max(snapshot.raw_char_length, 1)
        )
        confidence = compute_section_parse_confidence(snapshot)
        weighted_sum += confidence * weight
        total_weight += weight

    if total_weight == 0:
        return 0.0
    return round(weighted_sum / total_weight, 4)


def normalize_for_match(text: str) -> str:
    """归一化文本以便引用片段匹配。"""
    collapsed = re.sub(r"\s+", "", text or "")
    return collapsed.lower()
