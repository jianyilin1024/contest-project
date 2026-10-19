"""LLM 供应商统一抽象。

业务代码只依赖 LLMProvider 接口，不关心底层是哪家模型，
因此切换 DeepSeek / 通义 / 智谱 / OpenAI 时无需改动业务逻辑。
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatMessage:
    role: str  # system | user | assistant
    content: str


@dataclass
class ChatResult:
    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """所有模型供应商需实现的接口。"""

    name: str = "base"

    @abstractmethod
    async def chat(self, messages: list[ChatMessage], **kwargs: Any) -> ChatResult:
        """一次性返回完整回复。"""

    @abstractmethod
    def stream(self, messages: list[ChatMessage], **kwargs: Any) -> AsyncIterator[str]:
        """流式返回增量文本。"""

    async def structured(
        self, messages: list[ChatMessage], schema: dict[str, Any], **kwargs: Any
    ) -> dict[str, Any]:
        """按 JSON Schema 返回结构化结果（P4 阶段实现）。"""
        raise NotImplementedError("structured() 将在 P4 阶段实现")
