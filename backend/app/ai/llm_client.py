"""OpenAI 兼容 LLM 客户端封装。"""

import time
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI

from app.config import Settings


@dataclass
class LlmResponse:
    content: str
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    total_tokens: Optional[int]
    duration_ms: int
    model: str


class LlmClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = OpenAI(
            api_key=settings.ai_api_key,
            base_url=settings.ai_base_url or None,
            timeout=settings.ai_timeout_seconds,
        )

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: Optional[float] = None,
    ) -> LlmResponse:
        start = time.perf_counter()
        response = self._client.chat.completions.create(
            model=self.settings.ai_model,
            temperature=temperature if temperature is not None else self.settings.ai_temperature,
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
        )
