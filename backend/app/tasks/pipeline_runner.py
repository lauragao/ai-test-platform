"""任务编排与 quality_warnings 持久化。"""

from pathlib import Path
from typing import Any, Optional

from app.ai.ai_service import AiService
from app.ai.models import CompletenessCheckResult, DocumentSectionInput
from app.ai.utils import collect_refill_section_ids, merge_requirements
from app.document.enrich import enrich_sections_with_snapshot
from app.quality.parse_quality_service import ParseQualityService
from app.quality.quality_check_service import QualityCheckService
from app.tasks.models import TaskRecord, TaskStatus
from app.tasks.quality_warnings import build_quality_warnings
from app.tasks.result_store import TaskResultStore
from app.tasks.step_runner import PipelineStepRunner
from app.tasks.step_service import TaskStepService
from app.tasks.task_service import TaskService


class PipelineTaskRunner:
    """串联 AI 流水线，写入步骤明细、质量告警，并执行 timeout / retry。"""

    def __init__(
        self,
        ai_service: AiService,
        task_service: TaskService,
        result_store: TaskResultStore | None = None,
        step_service: TaskStepService | None = None,
    ):
        self.ai_service = ai_service
        self.task_service = task_service
        self.result_store = result_store
        self.step_service = step_service or TaskStepService(
            task_service.storage_dir.parent / "task_steps"
        )
        self.step_runner = PipelineStepRunner(task_service, self.step_service)
        self.parse_quality_service = ParseQualityService()
        self.case_quality_service = QualityCheckService()

    def run_full(
        self,
        sections: list[DocumentSectionInput],
        *,
        task: TaskRecord | None = None,
        source_file: Optional[str] = None,
        document_title: Optional[str] = None,
        source_type: Optional[str] = None,
        document_id: Optional[int] = None,
        max_completeness_rounds: int = 2,
    ) -> dict[str, Any]:
        if task is None:
            task = self.task_service.create(
                document_id=document_id,
                task_type="full",
                source_file=source_file,
                config={
                    "document_title": document_title,
                    "source_type": source_type,
                },
            )
        else:
            task.config.update(
                {
                    "document_title": document_title,
                    "source_type": source_type,
                }
            )
            if source_file:
                task.source_file = source_file
            self.task_service.save(task)

        sections = enrich_sections_with_snapshot(sections)
        task_id = task.id

        try:
            extract_result = self.step_runner.run_step(
                task,
                "extract_requirements",
                lambda: self.ai_service.extract_requirements(sections, task_id=task_id),
                task_status=TaskStatus.ANALYZING,
                progress=15,
                step_message="抽取原子需求点",
            )
            requirements = list(extract_result.requirements)
            completeness_result: CompletenessCheckResult | None = None

            for round_index in range(max_completeness_rounds):
                completeness_result = self.step_runner.run_step(
                    task,
                    "check_requirement_completeness",
                    lambda: self.ai_service.check_requirement_completeness(
                        sections,
                        requirements,
                        document_title=document_title,
                        task_id=task_id,
                    ),
                    task_status=TaskStatus.ANALYZING,
                    progress=25 + round_index * 10,
                    step_message="需求点完备性自检",
                    input_snapshot={"round": round_index + 1, "requirement_count": len(requirements)},
                )
                refill_ids = collect_refill_section_ids(completeness_result)
                if not refill_ids:
                    break
                refill_sections = [s for s in sections if s.section_id in refill_ids]
                if not refill_sections:
                    break
                refill_result = self.step_runner.run_step(
                    task,
                    "extract_requirements",
                    lambda rs=refill_sections: self.ai_service.extract_requirements(
                        rs, task_id=task_id
                    ),
                    task_status=TaskStatus.ANALYZING,
                    progress=35,
                    step_message="定向补抽遗漏章节",
                    input_snapshot={"refill_section_ids": refill_ids},
                )
                requirements = merge_requirements(requirements, refill_result.requirements)

            analyze_result = self.step_runner.run_step(
                task,
                "analyze_requirements",
                lambda: self.ai_service.analyze_requirements(
                    sections, requirements, task_id=task_id
                ),
                task_status=TaskStatus.ANALYZING,
                progress=55,
                step_message="需求问题分析",
            )

            parse_quality = self.parse_quality_service.check_after_analysis(
                sections,
                analyze_result.issues,
                source_type=source_type,
            )

            cases_result = self.step_runner.run_step(
                task,
                "generate_cases",
                lambda: self.ai_service.generate_test_cases(
                    requirements,
                    analyze_result.issues,
                    task_id=task_id,
                ),
                task_status=TaskStatus.GENERATING_CASES,
                progress=75,
                step_message="生成测试用例",
            )

            case_report = self.step_runner.run_step(
                task,
                "validate",
                lambda: self.case_quality_service.check(
                    requirements,
                    cases_result.test_cases,
                ),
                task_status=TaskStatus.GENERATING_CASES,
                progress=90,
                step_message="用例质量校验",
            )

            quote_warnings = self.parse_quality_service.check_requirement_quotes(
                sections,
                requirements,
            )
            quality_warnings = build_quality_warnings(
                parse_report=parse_quality,
                case_report=case_report,
                requirement_quote_warnings=quote_warnings or None,
            )

            step_message = "任务完成"
            if quality_warnings.should_warn_user:
                step_message = "任务完成，存在质量告警，请查看 quality_warnings"

            task = self.task_service.apply_quality_warnings(
                task,
                quality_warnings,
                status=TaskStatus.CASE_COMPLETED,
                progress=100,
                current_step="validate",
                step_message=step_message,
                mark_finished=True,
            )

            pipeline_result = {
                "extract": extract_result,
                "completeness": completeness_result,
                "requirements": requirements,
                "analyze": analyze_result,
                "parse_quality": parse_quality,
                "cases": cases_result,
            }
            payload = self._build_result_payload(task, pipeline_result, case_report)
            if self.result_store:
                self.result_store.save(task.task_no, payload)

            return {
                "task": task,
                "pipeline": pipeline_result,
                "case_quality": case_report,
                "quality_warnings": quality_warnings,
            }
        except Exception as exc:
            if task.status != TaskStatus.FAILED.value:
                self.task_service.fail_task(
                    task,
                    error_code=getattr(exc, "error_code", None) or "pipeline_failed",
                    error_message=str(exc),
                )
            raise

    @staticmethod
    def _build_result_payload(task: TaskRecord, result: dict[str, Any], case_report) -> dict[str, Any]:
        pipeline = result
        return {
            "task_no": task.task_no,
            "task_status": task.status,
            "quality_warnings": task.quality_warnings.model_dump(mode="json")
            if task.quality_warnings
            else None,
            "extract": pipeline["extract"].model_dump(),
            "completeness": pipeline["completeness"].model_dump()
            if pipeline.get("completeness")
            else None,
            "requirements": [item.model_dump() for item in pipeline["requirements"]],
            "analyze": pipeline["analyze"].model_dump(),
            "parse_quality": pipeline["parse_quality"].model_dump(),
            "case_quality": case_report.model_dump(),
            "cases": pipeline["cases"].model_dump(),
        }


def default_task_service(backend_root: Path | None = None) -> TaskService:
    root = backend_root or Path(__file__).resolve().parents[2]
    return TaskService(root / "tmp" / "tasks")


def default_step_service(backend_root: Path | None = None) -> TaskStepService:
    root = backend_root or Path(__file__).resolve().parents[2]
    return TaskStepService(root / "tmp" / "task_steps")


def default_result_store(backend_root: Path | None = None) -> TaskResultStore:
    root = backend_root or Path(__file__).resolve().parents[2]
    return TaskResultStore(root / "tmp" / "results")
