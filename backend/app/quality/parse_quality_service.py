"""文档解析质量与 AI 引用质量告警服务。"""

from pydantic import BaseModel, Field

from app.ai.models import DocumentSectionInput, RequirementIssue, RequirementItem
from app.document.section_snapshot import (
    compute_document_parse_confidence,
    normalize_for_match,
)


class CitationCheckItem(BaseModel):
    issue_key: str
    section_id: str
    quote: str
    matched: bool
    reason: str


class ParseQualityReport(BaseModel):
    """解析质量 + AI 引用质量综合报告。"""

    document_parse_confidence: float
    inferred_issue_count: int
    total_issue_count: int
    inferred_issue_ratio: float
    broken_citation_count: int
    citation_check_total: int
    broken_citation_ratio: float
    citation_checks: list[CitationCheckItem] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)
    alert_level: str = Field(default="none", description="none | info | warning | critical")
    should_warn_user: bool = False
    passed: bool = True


class ParseQualityService:
    """
    基于原文快照与 AI 分析结果，主动识别「解析质量不足」风险。

    触发告警的典型场景：
    1. 文档级解析置信度低于阈值
    2. 大量问题标记为 inferred（未找到原文依据）
    3. source_refs 引用片段无法在对应章节中匹配（引用错乱）
    """

    MIN_DOCUMENT_CONFIDENCE = 0.65
    MAX_INFERRED_ISSUE_RATIO = 0.45
    MAX_BROKEN_CITATION_RATIO = 0.35

    ALERT_PARSE_LOW = (
        "文档解析置信度低于阈值，可能影响分析质量，建议检查 PDF 是否为扫描件或版式是否复杂。"
    )
    ALERT_INFERRED_HIGH = (
        "AI 分析结果中存在较多「未找到原文依据」的问题，可能与文档解析不完整有关。"
    )
    ALERT_CITATION_BROKEN = (
        "AI 引用的原文片段与结构化章节内容匹配失败，可能存在引用错乱或解析丢字。"
    )

    def evaluate_document_confidence(
        self,
        sections: list[DocumentSectionInput],
    ) -> float:
        snapshots = [
            section.source_snapshot
            for section in sections
            if section.source_snapshot is not None
        ]
        if snapshots:
            return compute_document_parse_confidence(snapshots)

        confidences = [
            section.parse_confidence
            for section in sections
            if section.parse_confidence is not None
        ]
        if confidences:
            return round(sum(confidences) / len(confidences), 4)
        return 1.0

    def check_citations(
        self,
        sections: list[DocumentSectionInput],
        issues: list[RequirementIssue],
    ) -> list[CitationCheckItem]:
        section_map = {section.section_id: section for section in sections}
        results: list[CitationCheckItem] = []

        for issue in issues:
            if not issue.source_refs:
                continue
            for ref in issue.source_refs:
                section = section_map.get(ref.section_id)
                if section is None:
                    results.append(
                        CitationCheckItem(
                            issue_key=issue.issue_key,
                            section_id=ref.section_id,
                            quote=ref.quote,
                            matched=False,
                            reason="章节不存在",
                        )
                    )
                    continue

                normalized_quote = normalize_for_match(ref.quote)
                normalized_content = normalize_for_match(section.content)
                if not normalized_quote:
                    results.append(
                        CitationCheckItem(
                            issue_key=issue.issue_key,
                            section_id=ref.section_id,
                            quote=ref.quote,
                            matched=False,
                            reason="引用片段为空",
                        )
                    )
                elif normalized_quote in normalized_content:
                    results.append(
                        CitationCheckItem(
                            issue_key=issue.issue_key,
                            section_id=ref.section_id,
                            quote=ref.quote,
                            matched=True,
                            reason="匹配成功",
                        )
                    )
                else:
                    results.append(
                        CitationCheckItem(
                            issue_key=issue.issue_key,
                            section_id=ref.section_id,
                            quote=ref.quote,
                            matched=False,
                            reason="引用片段未在章节正文中找到",
                        )
                    )
        return results

    def check_after_analysis(
        self,
        sections: list[DocumentSectionInput],
        issues: list[RequirementIssue],
        *,
        source_type: str | None = None,
    ) -> ParseQualityReport:
        """在需求问题分析完成后执行解析质量与引用质量检查。"""
        document_confidence = self.evaluate_document_confidence(sections)
        total_issues = len(issues)
        inferred_count = sum(
            1
            for issue in issues
            if issue.evidence_type == "inferred"
            or not issue.source_refs
        )
        inferred_ratio = (inferred_count / total_issues) if total_issues else 0.0

        citation_checks = self.check_citations(sections, issues)
        citation_total = len(citation_checks)
        broken_count = sum(1 for item in citation_checks if not item.matched)
        broken_ratio = (broken_count / citation_total) if citation_total else 0.0

        alerts: list[str] = []
        alert_level = "none"
        should_warn = False

        def escalate(level: str) -> None:
            nonlocal alert_level, should_warn
            level_rank = {"none": 0, "info": 1, "warning": 2, "critical": 3}
            if level_rank[level] > level_rank[alert_level]:
                alert_level = level
            if level in ("warning", "critical"):
                should_warn = True

        if document_confidence < self.MIN_DOCUMENT_CONFIDENCE:
            msg = self.ALERT_PARSE_LOW
            if source_type:
                msg = f"{msg}（当前文档类型：{source_type}）"
            alerts.append(msg)
            escalate("warning")

        if total_issues > 0 and inferred_ratio >= self.MAX_INFERRED_ISSUE_RATIO:
            alerts.append(
                f"{self.ALERT_INFERRED_HIGH}（inferred/无引用占比 {inferred_ratio:.0%}）"
            )
            escalate("warning")

        if citation_total > 0 and broken_ratio >= self.MAX_BROKEN_CITATION_RATIO:
            alerts.append(
                f"{self.ALERT_CITATION_BROKEN}（匹配失败占比 {broken_ratio:.0%}）"
            )
            escalate("critical")

        if (
            document_confidence < self.MIN_DOCUMENT_CONFIDENCE
            and (inferred_ratio >= self.MAX_INFERRED_ISSUE_RATIO or broken_ratio >= 0.2)
        ):
            alerts.append(
                "综合判断：解析质量与 AI 引用质量同时异常，强烈建议重新上传更清晰的可编辑文档后再分析。"
            )
            escalate("critical")

        passed = alert_level in ("none", "info")
        return ParseQualityReport(
            document_parse_confidence=document_confidence,
            inferred_issue_count=inferred_count,
            total_issue_count=total_issues,
            inferred_issue_ratio=round(inferred_ratio, 4),
            broken_citation_count=broken_count,
            citation_check_total=citation_total,
            broken_citation_ratio=round(broken_ratio, 4),
            citation_checks=citation_checks,
            alerts=alerts,
            alert_level=alert_level,
            should_warn_user=should_warn,
            passed=passed,
        )

    def check_requirement_quotes(
        self,
        sections: list[DocumentSectionInput],
        requirements: list[RequirementItem],
    ) -> list[str]:
        """检查需求抽取阶段的原文引用是否可匹配。"""
        section_map = {section.section_id: section for section in sections}
        warnings: list[str] = []

        for req in requirements:
            if not req.source_quote or not req.section_id:
                continue
            section = section_map.get(req.section_id)
            if section is None:
                warnings.append(f"{req.req_key} 引用了不存在的章节 {req.section_id}")
                continue
            normalized_quote = normalize_for_match(req.source_quote)
            if normalized_quote and normalized_quote not in normalize_for_match(section.content):
                warnings.append(f"{req.req_key} 的 source_quote 无法在章节正文中匹配")

        return warnings
