from __future__ import annotations

from typing import Type

from deepeval.models import DeepEvalBaseLLM
from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel

from config.settings import settings


class GroqJudge(DeepEvalBaseLLM):
    """Use the project's Groq account as the opt-in DeepEval judge."""

    def load_model(self):
        return OpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )

    def generate(
        self, prompt: str, schema: Type[BaseModel] | None = None
    ) -> str | BaseModel:
        response = self.load_model().chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"} if schema else None,
            temperature=0.1,
        )
        content = response.choices[0].message.content or ""
        return schema.model_validate_json(content) if schema else content

    async def a_generate(
        self, prompt: str, schema: Type[BaseModel] | None = None
    ) -> str | BaseModel:
        client = AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"} if schema else None,
            temperature=0.1,
        )
        content = response.choices[0].message.content or ""
        return schema.model_validate_json(content) if schema else content

    def get_model_name(self) -> str:
        return f"groq/{settings.llm_model}"
