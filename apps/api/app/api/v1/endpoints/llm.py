"""大模型网关端点。

/llm/health        连通性自检（列出可用模型，不消耗 token）
/llm/chat          一次性对话
/llm/chat/stream   流式对话（SSE，区分推理过程与正式回答）
"""

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.llm import ChatRequest, ChatResponse, LLMHealth
from app.services.llm import ChatMessage, LLMError, get_llm_provider

router = APIRouter(prefix="/llm", tags=["llm"])
logger = logging.getLogger(__name__)


def _to_messages(payload: ChatRequest) -> list[ChatMessage]:
    messages: list[ChatMessage] = []
    if payload.system:
        messages.append(ChatMessage("system", payload.system))
    messages.extend(ChatMessage(m.role, m.content) for m in payload.messages)
    return messages


def _options(payload: ChatRequest) -> dict:
    return {
        "model": payload.model,
        "temperature": payload.temperature,
        "max_tokens": payload.max_tokens,
    }


@router.get("/health", response_model=LLMHealth, summary="大模型连通性自检")
async def llm_health() -> LLMHealth:
    provider = get_llm_provider()
    try:
        models = await provider.list_models()
    except LLMError as exc:
        return LLMHealth(
            status="error",
            provider=provider.name,
            base_url=provider.base_url,  # type: ignore[attr-defined]
            default_model=provider.model,  # type: ignore[attr-defined]
            detail=str(exc),
        )
    return LLMHealth(
        status="ok",
        provider=provider.name,
        base_url=provider.base_url,  # type: ignore[attr-defined]
        default_model=provider.model,  # type: ignore[attr-defined]
        models=models,
    )


@router.post("/chat", response_model=ChatResponse, summary="一次性对话")
async def llm_chat(payload: ChatRequest) -> ChatResponse:
    provider = get_llm_provider()
    try:
        result = await provider.chat(_to_messages(payload), **_options(payload))
    except LLMError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc
    return ChatResponse(
        content=result.content,
        reasoning=result.reasoning,
        model=result.model,
        usage=result.usage,
    )


@router.post("/chat/stream", summary="流式对话（SSE）")
async def llm_chat_stream(payload: ChatRequest) -> StreamingResponse:
    provider = get_llm_provider()
    messages = _to_messages(payload)
    options = _options(payload)

    async def event_stream():
        try:
            async for delta in provider.stream(messages, **options):
                chunk = json.dumps({"type": delta.kind, "text": delta.text}, ensure_ascii=False)
                yield f"data: {chunk}\n\n"
            yield 'data: {"type": "done"}\n\n'
        except LLMError as exc:
            logger.warning("流式对话失败: %s", exc)
            error = json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False)
            yield f"data: {error}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
