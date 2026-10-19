"""LLM 供应商统一抽象。

业务代码只依赖 LLMProvider 接口，不关心底层是哪家模型，
因此切换 DeepSeek / 通义 / 智谱 / OpenAI 时无需改动业务逻辑。

注意：当前主力模型是**推理模型**——会先输出思考过程（reasoning_content），
再输出正式回答（content）。因此 ChatResult 与 StreamDelta 都区分这两者，
且 max_tokens 必须留足余量，否则思考会吃光额度导致 content 为空。
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal

DeltaKind = Literal["reasoning", "content"]


class LLMError(RuntimeError):
    """调用大模型失败（网络异常、鉴权失败、额度不足等）。"""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class ChatMessage:
    role: str  # system | user | assistant
    content: str


@dataclass
class StreamDelta:
    """一条流式增量。"""

    kind: DeltaKind
    text: str


@dataclass
class ChatResult:
    content: str
    model: str
    reasoning: str = ""
    usage: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def reasoning_tokens(self) -> int:
        details = self.usage.get("completion_tokens_details") or {}
        return int(details.get("reasoning_tokens", 0) or 0)


class LLMProvider(ABC):
    """所有模型供应商需实现的接口。"""

    name: str = "base"
    requires_api_key: bool = True

    @abstractmethod
    async def chat(self, messages: list[ChatMessage], **kwargs: Any) -> ChatResult:
        """一次性返回完整回复。"""

    @abstractmethod
    def stream(self, messages: list[ChatMessage], **kwargs: Any) -> AsyncIterator[StreamDelta]:
        """流式返回增量（含推理过程）。"""

    @abstractmethod
    async def list_models(self) -> list[str]:
        """列出该账号可用的模型，用于连通性自检。"""

    @abstractmethod
    async def structured(
        self, messages: list[ChatMessage], schema: dict[str, Any], **kwargs: Any
    ) -> dict[str, Any]:
        """按 JSON Schema 返回结构化结果。"""

    def ensure_ready(self) -> None:
        """调用前的自检：缺密钥时给出明确错误，而不是等到 HTTP 401。"""
        if self.requires_api_key and not self.api_key:
            raise LLMError("未配置 LLM_API_KEY，请在 .env 中填写模型密钥", status_code=503)
