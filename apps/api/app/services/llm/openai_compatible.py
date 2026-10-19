"""OpenAI 兼容协议的供应商实现。

DeepSeek、通义千问、智谱 GLM、OpenAI 均提供 /chat/completions 接口，
因此共用同一份实现，仅 base_url / model / api_key 不同。
"""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import settings
from app.services.llm.base import ChatMessage, ChatResult, LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    name = "openai_compatible"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self.api_key = api_key or settings.llm_api_key
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.model = model or settings.llm_model
        self.timeout = timeout or settings.llm_timeout

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _payload(
        self, messages: list[ChatMessage], stream: bool, **kwargs: Any
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream,
        }
        for key in ("temperature", "max_tokens", "top_p", "response_format"):
            if kwargs.get(key) is not None:
                payload[key] = kwargs[key]
        return payload

    async def chat(self, messages: list[ChatMessage], **kwargs: Any) -> ChatResult:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=self._payload(messages, False, **kwargs),
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()

        choice = data["choices"][0]
        return ChatResult(
            content=choice["message"]["content"],
            model=data.get("model", self.model),
            usage=data.get("usage", {}),
            raw=data,
        )

    async def stream(  # type: ignore[override]
        self, messages: list[ChatMessage], **kwargs: Any
    ) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=self.timeout) as client, client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            json=self._payload(messages, True, **kwargs),
            headers=self._headers(),
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    break
                try:
                    delta = json.loads(chunk)["choices"][0]["delta"].get("content")
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
                if delta:
                    yield delta
