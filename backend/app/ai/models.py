"""AI 输入输出 Pydantic 模型，对齐设计文档与 DB 表字段。"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.document.section_snapshot import SourceSnapshot


class RunType(str, Enum):
    EXTRACT_REQUIREMENTS = "extract_requirements"
    CHECK_REQUIREMENT_COMPLETENESS = "check_requirement_completeness"
    ANALYZE_REQUIREMENTS = "analyze_requirements"
    GENERATE_CASES = "generate_cases"


class DocumentSectionInput(BaseModel):
    """对应 nb_test_document_sections 的 AI 输入切片。"""

    section_id: str = Field(..., description="章节标识，如 sec_001")
    title: Optional[str] = None
    level: int = 1
    content: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    source_snapshot: Optional[SourceSnapshot] = Field(
        default=None,
        description="原文快照：字符长度、空白比、表格/特殊字符密度等",
    )
    parse_confidence: Optional[float] = Field(
        default=None,
        description="本段解析置信度 0~1，由 source_snapshot 启发式计算",
    )


class RequirementItem(BaseModel):
    """对应 nb_test_requirements。"""

    req_key: str
    section_id: Optional[str] = None
    module: Optional[str] = None
    title: str
    description: str
    req_type: Optional[str] = Field(default="functional")
    priority: Optional[str] = Field(default="P1")
    acceptance_criteria: Optional[str] = None
    source_quote: Optional[str] = None
    page_no: Optional[int] = None


class SourceRef(BaseModel):
    """对应 nb_test_issue_source_refs。"""

    section_id: str
    quote: str
    page_no: Optional[int] = None


class RequirementIssue(BaseModel):
    """对应 nb_test_requirement_issues。"""

    issue_key: str
    requirement_id: Optional[str] = None
    issue_type: str
    severity: str
    title: str
    description: str
    suggestion: Optional[str] = None
    evidence_type: str = Field(default="explicit")
    source_refs: list[SourceRef] = Field(default_factory=list)


class TestCaseItem(BaseModel):
    """对应 nb_test_test_cases。"""

    case_key: str
    module: Optional[str] = None
    title: str
    priority: str
    case_type: str = Field(default="functional")
    precondition: Optional[str] = None
    steps: list[str]
    expected_result: str
    source_requirement_ids: list[str] = Field(default_factory=list)
    design_methods: list[str] = Field(default_factory=list)
    regression_type: Optional[str] = None
    tag: Optional[str] = None
    remark: Optional[str] = None
    risk_notes: list[str] = Field(default_factory=list)


class ExtractRequirementsResult(BaseModel):
    summary: str
    requirements: list[RequirementItem]


class SectionCoverageItem(BaseModel):
    """单个章节的覆盖映射。"""

    section_id: str
    section_title: Optional[str] = None
    coverage_status: str = Field(description="covered | partial | missing")
    requirement_count: int = 0
    linked_req_keys: list[str] = Field(default_factory=list)
    gap_reason: Optional[str] = None


class RefillSection(BaseModel):
    """需定向补抽的章节。"""

    section_id: str
    reason: str


class CompletenessCheckResult(BaseModel):
    """需求点完备性自检结果。"""

    summary: str
    coverage_map: list[SectionCoverageItem]
    sections_to_refill: list[RefillSection] = Field(default_factory=list)
    overall_coverage_rate: Optional[float] = None


class AnalyzeRequirementsResult(BaseModel):
    summary: str
    issues: list[RequirementIssue]


class GenerateTestCasesResult(BaseModel):
    summary: str
    test_cases: list[TestCaseItem]
    coverage_notes: Optional[str] = None


class AiRunRecord(BaseModel):
    """对应 nb_test_ai_runs 写入结构。"""

    model_config = {"protected_namespaces": ()}

    task_id: Optional[int] = None
    task_step_id: Optional[int] = None
    run_type: RunType
    model_name: str
    model_version: Optional[str] = None
    prompt_version: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    duration_ms: int
    status: str
    input_summary: str
    output_raw: Optional[str] = None
    output_parsed: Optional[dict[str, Any]] = None
    validation_result: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
