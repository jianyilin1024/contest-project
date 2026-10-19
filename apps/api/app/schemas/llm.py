"""大模型相关请求 / 响应模型。"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessageIn(BaseModel):
    role: Literal["system", "user", "assistant"] = "user"
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    messages: list[ChatMessageIn] = Field(min_length=1)
    system: str | None = None
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=32768)


class ChatResponse(BaseModel):
    content: str
    reasoning: str = ""
    model: str
    usage: dict[str, Any] = Field(default_factory=dict)


class LLMHealth(BaseModel):
    status: str
    provider: str
    base_url: str
    default_model: str
    models: list[str] = Field(default_factory=list)
    detail: str | None = None
