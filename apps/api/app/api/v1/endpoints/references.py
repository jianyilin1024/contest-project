"""参考文献助手（F7）接口。

POST /references/search  按概要/标题检索真实文献，返回 GB/T 7714 条目
POST /references/insert  把选中条目写入文稿的「参考文献」段
"""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.references import (
    ReferenceEntryOut,
    ReferenceInsertRequest,
    ReferenceInsertResponse,
    ReferenceSearchRequest,
    ReferenceSearchResponse,
)
from app.services.documents.references import find_reference_section
from app.services.references.gbt import format_entries
from app.services.references.sources import search_all

router = APIRouter(prefix="/references", tags=["references"])
logger = logging.getLogger(__name__)


@router.post("/search", response_model=ReferenceSearchResponse, summary="检索真实文献")
async def search_references(payload: ReferenceSearchRequest) -> ReferenceSearchResponse:
    wanted = {item.lower() for item in payload.sources}
    records = await search_all(
        [payload.query.strip()],
        limit=payload.limit,
        include_academic="academic" in wanted,
        include_books="book" in wanted,
        include_web="web" in wanted,
    )
    if not records:
        raise HTTPException(
            status_code=404,
            detail="没有检索到相关文献。可以换用更具体的关键词，或改用英文检索（学术库以英文文献为主）。",
        )
    entries = format_entries(records)
    logger.info("文献检索完成 query=%s hits=%d", payload.query, len(entries))
    return ReferenceSearchResponse(
        query=payload.query,
        total=len(entries),
        entries=[ReferenceEntryOut(**entry) for entry in entries],
    )


def append_references(markdown: str, entries: list[str]) -> str:
    """写入「参考文献」段：已有就替换，没有就追加。"""
    block = "\n".join(entries)
    section = find_reference_section(markdown)
    if section is None:
        return markdown.rstrip() + "\n\n## 参考文献\n\n" + block + "\n"

    lines = markdown.splitlines()
    head = lines[: section["heading_index"] + 1]
    tail = lines[section["end_index"] :]
    return "\n".join([*head, "", block, "", *tail]).replace("\n\n\n", "\n\n")


@router.post("/insert", response_model=ReferenceInsertResponse, summary="写入参考文献段")
async def insert_references(payload: ReferenceInsertRequest) -> ReferenceInsertResponse:
    return ReferenceInsertResponse(
        markdown=append_references(payload.markdown, payload.entries),
        inserted=len(payload.entries),
    )
