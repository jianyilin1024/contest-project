"""过渡段落（F3）接口。

POST /transition/analyze  识别章节断层 + 生成备选过渡段
POST /transition/apply    按用户勾选把过渡段插入文档，返回 Markdown
"""

import logging
import time

from fastapi import APIRouter, HTTPException

from app.schemas.transition import (
    ApplyRequest,
    ApplyResponse,
    BlockOut,
    BoundaryOut,
    TransitionRequest,
    TransitionResponse,
)
from app.services.documents.transitions import (
    analyze_transitions,
    assemble_markdown,
    boundary_summary,
    build_blocks,
    find_boundaries,
)
from app.services.llm import LLMError, get_llm_provider

router = APIRouter(prefix="/transition", tags=["transition"])
logger = logging.getLogger(__name__)


@router.post("/analyze", response_model=TransitionResponse, summary="识别衔接点并生成备选")
async def analyze(payload: TransitionRequest) -> TransitionResponse:
    started = time.perf_counter()
    blocks = build_blocks(payload.markdown)
    if not blocks:
        raise HTTPException(status_code=422, detail="文档内容为空")

    boundaries = find_boundaries(blocks)
    title = payload.title.strip() or "未命名文档"

    if boundaries:
        provider = get_llm_provider()
        try:
            boundaries = await analyze_transitions(boundaries, provider, title)
        except LLMError as exc:
            raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc

    elapsed = int((time.perf_counter() - started) * 1000)
    logger.info("过渡分析完成 blocks=%d boundaries=%d", len(blocks), len(boundaries))
    return TransitionResponse(
        title=title,
        blocks=[BlockOut(**block.to_dict()) for block in blocks],
        boundaries=[BoundaryOut(**item) for item in boundaries],
        stats=boundary_summary(boundaries),
        elapsed_ms=elapsed,
    )


@router.post("/apply", response_model=ApplyResponse, summary="按勾选插入过渡段")
async def apply(payload: ApplyRequest) -> ApplyResponse:
    blocks = [block.model_dump() for block in payload.blocks]
    insertions = [item.model_dump() for item in payload.insertions]
    valid_ids = {block["id"] for block in blocks}
    usable = [item for item in insertions if item["after_block_id"] in valid_ids]
    return ApplyResponse(
        markdown=assemble_markdown(blocks, usable),
        inserted=len(usable),
    )
