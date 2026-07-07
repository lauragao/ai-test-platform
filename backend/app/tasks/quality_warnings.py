"""从质检报告构建 nb_test_tasks.quality_warnings。"""

from datetime import datetime

from app.quality.parse_quality_service import ParseQualityReport
from app.quality.quality_check_service import QualityCheckResult
from app.tasks.models import QualityWarningItem, TaskQualityWarnings

_LEVEL_RANK = {"none": 0, "info": 1, "warning": 2, "critical": 3}


def build_quality_warnings(
    *,
    parse_report: ParseQualityReport | None = None,
    case_report: QualityCheckResult | None = None,
    requirement_quote_warnings: list[str] | None = None,
) -> TaskQualityWarnings:
    """合并解析质量、用例质量、需求引用等告警为任务级 quality_warnings。"""
    warnings = TaskQualityWarnings()

    if parse_report:
        for alert in parse_report.alerts:
            warnings.add_item(
                QualityWarningItem(
                    warning_type="parse_quality",
                    level=parse_report.alert_level if parse_report.alert_level != "none" else "warning",
                    message=alert,
                    metrics={
                        "document_parse_confidence": parse_report.document_parse_confidence,
                        "inferred_issue_ratio": parse_report.inferred_issue_ratio,
                        "broken_citation_ratio": parse_report.broken_citation_ratio,
                        "inferred_issue_count": parse_report.inferred_issue_count,
                        "broken_citation_count": parse_report.broken_citation_count,
                    },
                )
            )
        if parse_report.alert_level != "none":
            warnings._escalate(parse_report.alert_level)
            if parse_report.should_warn_user:
                warnings.should_warn_user = True

    if case_report and case_report.warnings:
        level = "warning" if not case_report.passed else "info"
        for message in case_report.warnings:
            warnings.add_item(
                QualityWarningItem(
                    warning_type="case_coverage",
                    level=level,
                    message=message,
                    metrics={
                        "coverage_rate": case_report.coverage_rate,
                        "orphan_case_count": len(case_report.orphan_cases),
                        "total_cases": case_report.total_cases,
                    },
                )
            )

    if requirement_quote_warnings:
        for message in requirement_quote_warnings:
            warnings.add_item(
                QualityWarningItem(
                    warning_type="requirement_quote",
                    level="warning",
                    message=message,
                    metrics={},
                )
            )

    warnings.updated_at = datetime.now()
    return warnings


def merge_quality_warnings(*parts: TaskQualityWarnings | None) -> TaskQualityWarnings:
    """合并多次检查产生的告警（取最高 alert_level）。"""
    merged = TaskQualityWarnings()
    for part in parts:
        if not part:
            continue
        for item in part.items:
            merged.add_item(item)
        if part.should_warn_user:
            merged.should_warn_user = True
        if _LEVEL_RANK.get(part.alert_level, 0) > _LEVEL_RANK.get(merged.alert_level, 0):
            merged.alert_level = part.alert_level

    merged.updated_at = datetime.now()
    return merged
