"""OpenAI 兼容协议的供应商实现。

DeepSeek、通义千问、智谱 GLM、OpenAI 均提供 /chat/completions 接口，
因此共用同一份实现，仅 base_url / model / api_key 不同。
"""

import json
import logging
import re
from collections.abc import AsyncIterator, Iterable, Iterator
from typing import Any

import httpx

from app.core.config import settings
from app.services.llm.base import (
    ChatMessage,
    ChatResult,
    LLMError,
    LLMProvider,
    StreamDelta,
)

logger = logging.getLogger(__name__)

# 推理模型会先输出思考内容，默认额度需要留足余量
DEFAULT_MAX_TOKENS = 4096

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def extract_json_object(text: str) -> dict[str, Any] | None:
    """从模型输出里抽取第一个 JSON 对象，容忍 Markdown 代码块与前后废话。"""
    if not text or not text.strip():
        return None
    candidates: list[str] = [text.strip()]
    candidates.extend(match.group(1) for match in _JSON_FENCE.finditer(text))
    for candidate in candidates:
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end > start:
            try:
                data = json.loads(candidate[start : end + 1])
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                continue
    return None


def iter_sse_data(lines: Iterable[str]) -> Iterator[str]:
    """从 SSE 文本行中提取 data: 负载（按 SSE 规范去掉冒号后的空格）。"""
    for line in lines:
        if line.startswith("data:"):
            yield line[5:].strip()


def parse_sse_delta(chunk: str) -> StreamDelta | None:
    """解析一条 SSE 负载，返回增量；心跳、[DONE]、空内容均返回 None。"""
    chunk = chunk.strip()
    if not chunk or chunk == "[DONE]":
        return None
    try:
        payload = json.loads(chunk)
        delta = payload["choices"][0]["delta"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return None
    if delta.get("reasoning_content"):
        return StreamDelta("reasoning", delta["reasoning_content"])
    if delta.get("content"):
        return StreamDelta("content", delta["content"])
    return None


class OpenAICompatibleProvider(LLMProvider):
    name = "openai_compatible"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.llm_api_key
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.model = model or settings.llm_model
        self.timeout = timeout or settings.llm_timeout

    # ---------------- 内部工具 ----------------

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _payload(self, messages: list[ChatMessage], stream: bool, **kwargs: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": kwargs.get("model") or self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream,
            "max_tokens": kwargs.get("max_tokens") or DEFAULT_MAX_TOKENS,
        }
        for key in ("temperature", "top_p", "response_format"):
            if kwargs.get(key) is not None:
                payload[key] = kwargs[key]
        return payload

    @staticmethod
    def _wrap_http_error(exc: httpx.HTTPStatusError) -> LLMError:
        status = exc.response.status_code
        detail = exc.response.text[:300]
        hint = {
            401: "密钥无效或已过期",
            402: "账户余额不足",
            429: "请求过于频繁或超出额度",
        }.get(status, "")
        message = f"模型接口返回 {status}{('（' + hint + '）') if hint else ''}: {detail}"
        return LLMError(message, status_code=502)

    # ---------------- 接口实现 ----------------

    async def list_models(self) -> list[str]:
        self.ensure_ready()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/models", headers=self._headers())
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise self._wrap_http_error(exc) from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"无法连接模型服务: {exc}", status_code=502) from exc
        return [item["id"] for item in data.get("data", [])]

    async def chat(self, messages: list[ChatMessage], **kwargs: Any) -> ChatResult:
        self.ensure_ready()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=self._payload(messages, False, **kwargs),
                    headers=self._headers(),
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise self._wrap_http_error(exc) from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"无法连接模型服务: {exc}", status_code=502) from exc

        message = data["choices"][0]["message"]
        return ChatResult(
            content=message.get("content") or "",
            reasoning=message.get("reasoning_content") or "",
            model=data.get("model", self.model),
            usage=data.get("usage", {}),
            raw=data,
        )

    async def stream(  # type: ignore[override]
        self, messages: list[ChatMessage], **kwargs: Any
    ) -> AsyncIterator[StreamDelta]:
        self.ensure_ready()
        try:
            async with (
                httpx.AsyncClient(timeout=self.timeout) as client,
                client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    json=self._payload(messages, True, **kwargs),
                    headers=self._headers(),
                ) as response,
            ):
                response.raise_for_status()
                async for line in response.aiter_lines():
                    for payload in iter_sse_data([line]):
                        delta = parse_sse_delta(payload)
                        if delta is not None:
                            yield delta
        except httpx.HTTPStatusError as exc:
            raise self._wrap_http_error(exc) from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"无法连接模型服务: {exc}", status_code=502) from exc

    async def structured(
        self, messages: list[ChatMessage], schema: dict[str, Any], **kwargs: Any
    ) -> dict[str, Any]:
        instruction = (
            "你必须只输出一个 JSON 对象，不要包含任何解释或 Markdown 代码块，"
            "且严格符合以下 JSON Schema：\n" + json.dumps(schema, ensure_ascii=False)
        )
        prepared = [ChatMessage("system", instruction), *messages]
        budget = int(kwargs.get("max_tokens") or DEFAULT_MAX_TOKENS)

        # 第一次：启用 response_format，让服务端保证 JSON
        result = await self.chat(
            prepared, response_format={"type": "json_object"}, **kwargs
        )
        parsed = extract_json_object(result.content)
        if parsed is not None:
            return parsed

        # 降级重试：推理模型在额度被思考吃光时会返回空 content，
        # 这里去掉 response_format 并加倍额度，再从文本里抽取 JSON。
        logger.warning(
            "结构化输出失败（content %d 字符，推理 %d 字符），加倍额度重试",
            len(result.content),
            len(result.reasoning),
        )
        retry_kwargs = {**kwargs, "max_tokens": budget * 2}
        result = await self.chat(prepared, **retry_kwargs)
        parsed = extract_json_object(result.content)
        if parsed is not None:
            return parsed

        raise LLMError(
            f"模型未返回合法 JSON（content {len(result.content)} 字符，"
            f"推理 {len(result.reasoning)} 字符）: {result.content[:200]}"
        )
