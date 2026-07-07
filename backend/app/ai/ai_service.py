"""AiService：统一封装 AI 调用，不散落在业务代码中。"""

import json
import logging
from typing import Callable, Optional, TypeVar

import jsonschema
from openai import APITimeoutError
from pydantic import BaseModel, ValidationError

from app.config import Settings, get_settings
from app.ai.llm_client import LlmClient
from app.ai.model_profiles import ModelProfile
from app.ai.model_router import ModelRouter, estimate_sections_char_count
from app.ai.models import (
    AiRunRecord,
    AnalyzeRequirementsResult,
    CompletenessCheckResult,
    DocumentSectionInput,
    ExtractRequirementsResult,
    GenerateTestCasesResult,
    RequirementIssue,
    RequirementItem,
    RunType,
)
from app.ai.prompts import (
    case_generation,
    requirement_analysis,
    requirement_completeness_check,
    requirement_extract,
)
from app.ai.rules import get_case_generation_rules
from app.document.enrich import enrich_sections_with_snapshot
from app.ai.utils import (
    build_document_toc,
    build_retry_prompt,
    collect_refill_section_ids,
    items_to_json,
    merge_requirements,
    parse_json_content,
    requirements_to_summary_json,
    sections_to_json,
    validate_cases_schema,
    validate_completeness_schema,
    validate_issues_schema,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class AiServiceError(Exception):
    """AI 调用或结果校验失败。"""

    def __init__(self, message: str, *, error_code: str = "pipeline_failed"):
        super().__init__(message)
        self.error_code = error_code


class AiService:
    """
    统一 AI 编排服务。

    提供 4 个核心能力：
    1. extract_requirements           - 需求摘要 + 原子需求拆分
    2. check_requirement_completeness - 需求点完备性自检（反思）
    3. analyze_requirements           - 需求问题分析（不清晰/遗漏/矛盾/风险）
    4. generate_test_cases            - 测试用例生成
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        on_run_complete: Optional[Callable[[AiRunRecord], None]] = None,
    ):
        self.settings = settings or get_settings()
        self.client = LlmClient(self.settings)
        self.model_router = ModelRouter(self.settings)
        self.on_run_complete = on_run_complete

    def extract_requirements(
        self,
        sections: list[DocumentSectionInput],
        *,
        task_id: Optional[int] = None,
        task_step_id: Optional[int] = None,
    ) -> ExtractRequirementsResult:
        """从结构化章节中抽取原子需求点。"""
        system, user = requirement_extract.build_messages(
            sections_to_json(sections)
        )
        return self._run(
            run_type=RunType.EXTRACT_REQUIREMENTS,
            prompt_version=requirement_extract.VERSION,
            result_model=ExtractRequirementsResult,
            system_prompt=system,
            user_prompt=user,
            schema_validator=None,
            input_summary=f"sections={len(sections)}",
            input_char_count=estimate_sections_char_count(sections),
            task_id=task_id,
            task_step_id=task_step_id,
        )

    def check_requirement_completeness(
        self,
        sections: list[DocumentSectionInput],
        requirements: list[RequirementItem],
        *,
        document_title: Optional[str] = None,
        task_id: Optional[int] = None,
        task_step_id: Optional[int] = None,
    ) -> CompletenessCheckResult:
        """对照文档目录审视需求点覆盖是否完整（反思步骤）。"""
        system, user = requirement_completeness_check.build_messages(
            build_document_toc(sections, document_title),
            requirements_to_summary_json(requirements),
        )
        return self._run(
            run_type=RunType.CHECK_REQUIREMENT_COMPLETENESS,
            prompt_version=requirement_completeness_check.VERSION,
            result_model=CompletenessCheckResult,
            system_prompt=system,
            user_prompt=user,
            schema_validator=validate_completeness_schema,
            input_summary=(
                f"sections={len(sections)}, requirements={len(requirements)}"
            ),
            input_char_count=estimate_sections_char_count(sections),
            task_id=task_id,
            task_step_id=task_step_id,
        )

    def analyze_requirements(
        self,
        sections: list[DocumentSectionInput],
        requirements: list[RequirementItem],
        *,
        task_id: Optional[int] = None,
        task_step_id: Optional[int] = None,
    ) -> AnalyzeRequirementsResult:
        """对需求进行清晰度、完整性、一致性、风险检查。"""
        system, user = requirement_analysis.build_messages(
            sections_to_json(sections),
            items_to_json(requirements),
        )
        return self._run(
            run_type=RunType.ANALYZE_REQUIREMENTS,
            prompt_version=requirement_analysis.VERSION,
            result_model=AnalyzeRequirementsResult,
            system_prompt=system,
            user_prompt=user,
            schema_validator=validate_issues_schema,
            input_summary=f"sections={len(sections)}, requirements={len(requirements)}",
            input_char_count=estimate_sections_char_count(sections),
            task_id=task_id,
            task_step_id=task_step_id,
        )

    def generate_test_cases(
        self,
        requirements: list[RequirementItem],
        issues: Optional[list[RequirementIssue]] = None,
        *,
        task_id: Optional[int] = None,
        task_step_id: Optional[int] = None,
    ) -> GenerateTestCasesResult:
        """基于结构化需求点（及可选问题清单）生成测试用例。"""
        issues = issues or []
        system, user = case_generation.build_messages(
            items_to_json(requirements),
            items_to_json(issues),
            get_case_generation_rules(),
        )
        return self._run(
            run_type=RunType.GENERATE_CASES,
            prompt_version=case_generation.VERSION,
            result_model=GenerateTestCasesResult,
            system_prompt=system,
            user_prompt=user,
            schema_validator=validate_cases_schema,
            input_summary=f"requirements={len(requirements)}, issues={len(issues)}",
            input_char_count=len(items_to_json(requirements)) + len(items_to_json(issues)),
            task_id=task_id,
            task_step_id=task_step_id,
        )

    def run_full_pipeline(
        self,
        sections: list[DocumentSectionInput],
        *,
        document_title: Optional[str] = None,
        source_type: Optional[str] = None,
        task_id: Optional[int] = None,
        max_completeness_rounds: int = 2,
    ) -> dict:
        """串联执行：抽取需求 → 完备性自检（含定向补抽）→ 分析问题 → 解析质量告警 → 生成用例。"""
        sections = enrich_sections_with_snapshot(sections)
        extract_result = self.extract_requirements(sections, task_id=task_id)
        requirements = list(extract_result.requirements)
        completeness_result: Optional[CompletenessCheckResult] = None

        for _ in range(max_completeness_rounds):
            completeness_result = self.check_requirement_completeness(
                sections,
                requirements,
                document_title=document_title,
                task_id=task_id,
            )
            refill_ids = collect_refill_section_ids(completeness_result)
            if not refill_ids:
                break

            refill_sections = [
                section for section in sections if section.section_id in refill_ids
            ]
            if not refill_sections:
                break

            refill_result = self.extract_requirements(
                refill_sections,
                task_id=task_id,
            )
            requirements = merge_requirements(requirements, refill_result.requirements)

        analyze_result = self.analyze_requirements(
            sections,
            requirements,
            task_id=task_id,
        )
        from app.quality.parse_quality_service import ParseQualityService

        parse_quality = ParseQualityService().check_after_analysis(
            sections,
            analyze_result.issues,
            source_type=source_type,
        )
        cases_result = self.generate_test_cases(
            requirements,
            analyze_result.issues,
            task_id=task_id,
        )
        return {
            "extract": extract_result,
            "completeness": completeness_result,
            "requirements": requirements,
            "analyze": analyze_result,
            "parse_quality": parse_quality,
            "cases": cases_result,
        }

    def _run(
        self,
        *,
        run_type: RunType,
        prompt_version: str,
        result_model: type[T],
        system_prompt: str,
        user_prompt: str,
        schema_validator: Optional[Callable[[dict], None]],
        input_summary: str,
        task_id: Optional[int],
        task_step_id: Optional[int],
        input_char_count: int = 0,
    ) -> T:
        profile = self.model_router.resolve(run_type, input_char_count=input_char_count)
        enriched_summary = (
            f"{input_summary} | model_category={profile.category.value} | model={profile.model}"
        )
        last_error: Optional[str] = None
        last_raw: Optional[str] = None

        for attempt in range(1, self.settings.ai_max_retries + 1):
            llm_resp = None
            parsed: Optional[dict] = None
            validation_result: Optional[dict] = None
            error_message: Optional[str] = None

            try:
                llm_resp = self.client.chat_json(
                    system_prompt,
                    user_prompt,
                    profile=profile,
                )
                last_raw = llm_resp.content
                parsed = parse_json_content(llm_resp.content)

                if schema_validator:
                    schema_validator(parsed)

                result = result_model.model_validate(parsed)
                validation_result = {"valid": True, "attempt": attempt}

                self._emit_run_record(
                    task_id=task_id,
                    task_step_id=task_step_id,
                    run_type=run_type,
                    prompt_version=prompt_version,
                    input_summary=enriched_summary,
                    llm_resp=llm_resp,
                    profile=profile,
                    status="success",
                    output_raw=last_raw,
                    output_parsed=parsed,
                    validation_result=validation_result,
                )
                return result

            except (json.JSONDecodeError, ValidationError, jsonschema.ValidationError) as exc:
                error_message = str(exc)
                last_error = error_message
                validation_result = {"valid": False, "attempt": attempt, "error": error_message}
                logger.warning(
                    "AI 输出校验失败 [%s] attempt=%d/%d: %s",
                    run_type.value,
                    attempt,
                    self.settings.ai_max_retries,
                    error_message,
                )

                if attempt < self.settings.ai_max_retries:
                    user_prompt = build_retry_prompt(user_prompt, last_raw, error_message)
                else:
                    self._emit_run_record(
                        task_id=task_id,
                        task_step_id=task_step_id,
                        run_type=run_type,
                        prompt_version=prompt_version,
                        input_summary=enriched_summary,
                        llm_resp=llm_resp,
                        profile=profile,
                        status="failed",
                        output_raw=last_raw,
                        output_parsed=parsed,
                        validation_result=validation_result,
                        error_message=error_message,
                    )
                    raise AiServiceError(
                        f"AI 调用失败 [{run_type.value}]，已重试 {self.settings.ai_max_retries} 次: {error_message}",
                        error_code="validation_failed",
                    ) from exc

            except APITimeoutError as exc:
                error_message = str(exc)
                self._emit_run_record(
                    task_id=task_id,
                    task_step_id=task_step_id,
                    run_type=run_type,
                    prompt_version=prompt_version,
                    input_summary=enriched_summary,
                    llm_resp=llm_resp,
                    profile=profile,
                    status="failed",
                    output_raw=last_raw,
                    error_message=error_message,
                )
                raise AiServiceError(
                    f"AI 调用超时 [{run_type.value}]（>{self.settings.ai_timeout_seconds}s）: {error_message}",
                    error_code="ai_call_timeout",
                ) from exc

            except Exception as exc:
                self._emit_run_record(
                    task_id=task_id,
                    task_step_id=task_step_id,
                    run_type=run_type,
                    prompt_version=prompt_version,
                    input_summary=enriched_summary,
                    llm_resp=llm_resp,
                    profile=profile,
                    status="failed",
                    output_raw=last_raw,
                    error_message=str(exc),
                )
                raise AiServiceError(f"AI 调用异常 [{run_type.value}]: {exc}") from exc

        raise AiServiceError(last_error or "未知错误")

    def _emit_run_record(
        self,
        *,
        task_id: Optional[int],
        task_step_id: Optional[int],
        run_type: RunType,
        prompt_version: str,
        input_summary: str,
        llm_resp,
        profile: ModelProfile,
        status: str,
        output_raw: Optional[str] = None,
        output_parsed: Optional[dict] = None,
        validation_result: Optional[dict] = None,
        error_message: Optional[str] = None,
    ) -> None:
        if not self.on_run_complete:
            return

        record = AiRunRecord(
            task_id=task_id,
            task_step_id=task_step_id,
            run_type=run_type,
            model_name=llm_resp.model if llm_resp else profile.model,
            model_version=profile.category.value,
            prompt_version=prompt_version,
            input_tokens=llm_resp.input_tokens if llm_resp else None,
            output_tokens=llm_resp.output_tokens if llm_resp else None,
            total_tokens=llm_resp.total_tokens if llm_resp else None,
            duration_ms=llm_resp.duration_ms if llm_resp else 0,
            status=status,
            input_summary=input_summary,
            output_raw=output_raw,
            output_parsed=output_parsed,
            validation_result=validation_result,
            error_message=error_message,
        )
        self.on_run_complete(record)
