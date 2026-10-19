"""LLM 供应商工厂。"""

from app.core.config import settings
from app.services.llm.base import (
    ChatMessage,
    ChatResult,
    LLMError,
    LLMProvider,
    StreamDelta,
)
from app.services.llm.openai_compatible import (
    OpenAICompatibleProvider,
    iter_sse_data,
    parse_sse_delta,
)

_PROVIDERS: dict[str, type[LLMProvider]] = {
    "openai_compatible": OpenAICompatibleProvider,
}


def get_llm_provider(name: str | None = None) -> LLMProvider:
    """按名称获取供应商实例；未注册的名称会明确报错而不是静默降级。"""
    key = name or settings.llm_provider
    if key not in _PROVIDERS:
        raise ValueError(f"未注册的 LLM 供应商: {key}，可选: {sorted(_PROVIDERS)}")
    return _PROVIDERS[key]()


__all__ = [
    "ChatMessage",
    "ChatResult",
    "LLMError",
    "LLMProvider",
    "StreamDelta",
    "get_llm_provider",
    "iter_sse_data",
    "parse_sse_delta",
]
