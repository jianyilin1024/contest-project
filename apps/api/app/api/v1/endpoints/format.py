"""论文排版（F5）接口。

GET  /format/templates   可用排版模板
POST /format/docx        按模板把 Markdown 渲染成 docx
POST /format/references  AI 规范化参考文献（GB/T 7714-2015）
"""

import logging
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Response

from app.schemas.format import (
    FormatRequest,
    ReferenceEntry,
    ReferenceRequest,
    ReferenceResponse,
    TemplateInfo,
)
from app.services.documents.references import (
    find_reference_section,
    normalize_entries,
    rewrite_section,
)
from app.services.documents.typesetting import DEFAULT_TEMPLATE, TEMPLATES, build_docx
from app.services.llm import LLMError, get_llm_provider

router = APIRouter(prefix="/format", tags=["format"])
logger = logging.getLogger(__name__)


@router.get("/templates", response_model=list[TemplateInfo], summary="排版模板列表")
async def list_templates() -> list[TemplateInfo]:
    return [
        TemplateInfo(
            key=item.key,
            name=item.name,
            description=item.description,
            toc=item.toc,
            numbering=item.numbering,
            page_numbers=item.page_numbers,
        )
        for item in TEMPLATES.values()
    ]


@router.post("/docx", summary="渲染 docx")
async def render_docx(payload: FormatRequest) -> Response:
    key = payload.template or DEFAULT_TEMPLATE
    if key not in TEMPLATES:
        raise HTTPException(
            status_code=422, detail=f"未知模板 {key}，可选：{', '.join(TEMPLATES)}"
        )

    try:
        content = build_docx(
            payload.markdown,
            key,
            payload.title or None,
            toc=payload.toc,
            numbering=payload.numbering,
            page_numbers=payload.page_numbers,
        )
    except Exception as exc:  # noqa: BLE001 - 排版失败要给出可读原因
        logger.exception("排版失败")
        raise HTTPException(status_code=500, detail=f"排版失败：{type(exc).__name__}") from exc

    filename = f"{payload.title.strip() or '排版稿'}.docx"
    disposition = f"attachment; filename*=UTF-8''{quote(filename)}"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": disposition},
    )


@router.post("/references", response_model=ReferenceResponse, summary="AI 规范化参考文献")
async def format_references(payload: ReferenceRequest) -> ReferenceResponse:
    section = find_reference_section(payload.markdown)
    if section is None:
        return ReferenceResponse(
            found=False,
            notes=["未找到「参考文献」标题。请把标题写成一行 参考文献 或 ## 参考文献。"],
        )

    if not section["entries"]:
        return ReferenceResponse(
            found=True, heading=section["heading_line"], notes=["参考文献段里没有解析到条目。"]
        )

    provider = get_llm_provider()
    try:
        normalized = await normalize_entries(section["entries"], provider)
    except LLMError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc

    notes = [f"「{item['original'][:24]}…」{item['note']}" for item in normalized if item["note"]]
    return ReferenceResponse(
        found=True,
        heading=section["heading_line"],
        entries=[ReferenceEntry(**item) for item in normalized],
        markdown=rewrite_section(payload.markdown, section, normalized),
        notes=notes,
    )
