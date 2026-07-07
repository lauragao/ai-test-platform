"""OpenAI 兼容 LLM 客户端封装（支持多网关 / 多模型）。"""

import time
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI

from app.ai.model_profiles import ModelProfile
from app.config import Settings


@dataclass
class LlmResponse:
    content: str
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    total_tokens: Optional[int]
    duration_ms: int
    model: str
    profile_key: str = ""
    model_category: str = ""


class LlmClient:
    """按 ModelProfile 调用，同一 (base_url, api_key) 复用 OpenAI 客户端。"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._clients: dict[tuple[str, str], OpenAI] = {}

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        profile: ModelProfile,
        temperature: Optional[float] = None,
    ) -> LlmResponse:
        client = self._get_client(profile)
        temp = (
            temperature
            if temperature is not None
            else profile.temperature
            if profile.temperature is not None
            else self.settings.ai_temperature
        )
        start = time.perf_counter()
        response = client.chat.completions.create(
            model=profile.model,
            temperature=temp,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        duration_ms = int((time.perf_counter() - start) * 1000)
        choice = response.choices[0].message
        usage = response.usage

        return LlmResponse(
            content=choice.content or "",
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
            total_tokens=usage.total_tokens if usage else None,
            duration_ms=duration_ms,
            model=response.model,
            profile_key=profile.profile_key,
            model_category=profile.category.value,
        )

    def _get_client(self, profile: ModelProfile) -> OpenAI:
        cache_key = (profile.base_url, profile.api_key)
        if cache_key not in self._clients:
            self._clients[cache_key] = OpenAI(
                api_key=profile.api_key,
                base_url=profile.base_url or None,
                timeout=self.settings.ai_timeout_seconds,
            )
        return self._clients[cache_key]
