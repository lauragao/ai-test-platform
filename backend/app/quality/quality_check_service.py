"""测试用例质量检查服务。"""

from pydantic import BaseModel, Field

from app.ai.models import RequirementItem, TestCaseItem


class QualityCheckResult(BaseModel):
    total_requirements: int
    covered_requirements: int
    uncovered_requirements: list[str]
    coverage_rate: float
    total_cases: int
    coverage_depth: float
    orphan_cases: list[str]
    priority_distribution: dict[str, int]
    design_method_distribution: dict[str, int]
    warnings: list[str] = Field(default_factory=list)
    passed: bool


class QualityCheckService:
    """对 AI 生成用例做确定性校验，避免完全依赖 Prompt 自检。"""

    MIN_COVERAGE_RATE = 95.0
    PRIORITY_TARGETS = {
        "P0": (5, 25),
        "P1": (20, 50),
        "P2": (20, 60),
        "P3": (0, 30),
    }

    def check(
        self,
        requirements: list[RequirementItem],
        cases: list[TestCaseItem],
    ) -> QualityCheckResult:
        requirement_ids = {item.req_key for item in requirements}
        covered_ids: set[str] = set()
        orphan_cases: list[str] = []
        priority_distribution = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
        design_method_distribution = {"EP": 0, "BVA": 0, "ST": 0, "EG": 0, "EP+BVA": 0}
        warnings: list[str] = []

        for case in cases:
            priority = case.priority.upper()
            if priority in priority_distribution:
                priority_distribution[priority] += 1

            for method in case.design_methods:
                if method in design_method_distribution:
                    design_method_distribution[method] += 1

            valid_refs = [req_id for req_id in case.source_requirement_ids if req_id in requirement_ids]
            if valid_refs:
                covered_ids.update(valid_refs)
            else:
                orphan_cases.append(case.case_key)

        uncovered_requirements = sorted(requirement_ids - covered_ids)
        total_requirements = len(requirement_ids)
        total_cases = len(cases)
        coverage_rate = (len(covered_ids) / total_requirements * 100) if total_requirements else 100.0
        coverage_depth = (total_cases / total_requirements) if total_requirements else 0.0

        if coverage_rate < self.MIN_COVERAGE_RATE:
            warnings.append(f"需求覆盖率 {coverage_rate:.1f}% 低于目标 {self.MIN_COVERAGE_RATE:.1f}%")

        if orphan_cases:
            warnings.append(f"存在 {len(orphan_cases)} 条未关联有效需求的孤儿用例")

        warnings.extend(self._check_priority_distribution(priority_distribution, total_cases))

        if not any(design_method_distribution.values()):
            warnings.append("所有用例均缺少设计方法标记")

        return QualityCheckResult(
            total_requirements=total_requirements,
            covered_requirements=len(covered_ids),
            uncovered_requirements=uncovered_requirements,
            coverage_rate=round(coverage_rate, 2),
            total_cases=total_cases,
            coverage_depth=round(coverage_depth, 2),
            orphan_cases=orphan_cases,
            priority_distribution=priority_distribution,
            design_method_distribution=design_method_distribution,
            warnings=warnings,
            passed=not warnings,
        )

    def _check_priority_distribution(
        self,
        distribution: dict[str, int],
        total_cases: int,
    ) -> list[str]:
        if total_cases == 0:
            return ["未生成任何测试用例"]

        warnings: list[str] = []
        for priority, count in distribution.items():
            percent = count / total_cases * 100
            min_percent, max_percent = self.PRIORITY_TARGETS[priority]
            if percent < min_percent or percent > max_percent:
                warnings.append(
                    f"{priority} 占比 {percent:.1f}% 超出建议范围 {min_percent}-{max_percent}%"
                )
        return warnings
