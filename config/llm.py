from __future__ import annotations

import json
import logging
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Small provider boundary so agents are not coupled to one LLM vendor."""

    def __init__(self) -> None:
        self.provider = settings.llm_provider.lower()
        self.model = settings.llm_model

    @property
    def enabled(self) -> bool:
        return (
            self.provider == "openai"
            and bool(settings.openai_api_key)
        ) or (
            self.provider == "groq"
            and bool(settings.groq_api_key)
        )

    def _client_options(self) -> dict[str, str]:
        if self.provider == "groq":
            return {
                "api_key": settings.groq_api_key or "",
                "base_url": "https://api.groq.com/openai/v1",
            }
        return {"api_key": settings.openai_api_key or ""}

    async def complete_json(
        self,
        system_prompt: str,
        user_payload: dict[str, Any],
        fallback: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.enabled:
            return fallback

        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            **self._client_options(),
            timeout=settings.request_timeout_seconds,
            max_retries=2,
        )
        try:
            response = await client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_payload)},
                ],
                temperature=0.1,
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("LLM returned an empty response")
            result = json.loads(content)
            return result if isinstance(result, dict) else fallback
        except Exception as exc:
            from config.metrics import LLM_FALLBACKS

            logger.warning("LLM call failed; using deterministic fallback: %s", exc)
            LLM_FALLBACKS.labels(provider=self.provider).inc()
            return fallback


llm = LLMClient()
