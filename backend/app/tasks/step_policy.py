"""各流水线步骤的 timeout / max_retry 默认策略。"""

from dataclasses import dataclass
from typing import Any, Optional

from app.config import get_settings


@dataclass(frozen=True)
class StepPolicy:
    timeout_seconds: int
    max_retry: int


DEFAULT_STEP_POLICIES: dict[str, StepPolicy] = {
    "parse": StepPolicy(timeout_seconds=300, max_retry=2),
    "clean": StepPolicy(timeout_seconds=120, max_retry=2),
    "chunk": StepPolicy(timeout_seconds=120, max_retry=2),
    "extract_requirements": StepPolicy(timeout_seconds=120, max_retry=3),
    "check_requirement_completeness": StepPolicy(timeout_seconds=90, max_retry=2),
    "analyze_requirements": StepPolicy(timeout_seconds=180, max_retry=3),
    "generate_cases": StepPolicy(timeout_seconds=180, max_retry=3),
    "validate": StepPolicy(timeout_seconds=60, max_retry=2),
    "export": StepPolicy(timeout_seconds=60, max_retry=2),
}


def resolve_step_policy(
    step_name: str,
    task_config: Optional[dict[str, Any]] = None,
    *,
    task_timeout_seconds: Optional[int] = None,
) -> StepPolicy:
    """解析步骤策略，支持 task.config.step_policies 覆盖。"""
    settings = get_settings()
    base = DEFAULT_STEP_POLICIES.get(
        step_name,
        StepPolicy(timeout_seconds=task_timeout_seconds or settings.task_default_timeout_seconds, max_retry=3),
    )

    overrides = (task_config or {}).get("step_policies", {}).get(step_name, {})
    timeout = int(overrides.get("timeout_seconds", base.timeout_seconds))
    max_retry = int(overrides.get("max_retry", base.max_retry))

    if step_name in (
        "extract_requirements",
        "analyze_requirements",
        "generate_cases",
        "check_requirement_completeness",
    ):
        ai_budget = settings.ai_timeout_seconds * max(1, settings.ai_max_retries)
        timeout = max(timeout, ai_budget)

    return StepPolicy(timeout_seconds=timeout, max_retry=max_retry)


RETRIABLE_ERROR_CODES = frozenset(
    {
        "step_timeout",
        "ai_call_timeout",
        "pipeline_failed",
    }
)
