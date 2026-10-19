"""多部分整合（F1）接口。

POST /merge/analyze  上传多份文稿 → 合并结果 + 冲突报告
POST /merge/export   把合并稿导出为 md / docx 文件
"""

import json
import logging
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.schemas.merge import (
    DuplicateGroup,
    ExportRequest,
    MergeResponse,
    MergeStats,
    OutlineNode,
)
from app.services.documents import ParseError, merge_documents, parse_document
from app.services.documents.export import markdown_to_docx, to_markdown

router = APIRouter(prefix="/merge", tags=["merge"])
logger = logging.getLogger(__name__)

MAX_FILES = 20
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 40 * 1024 * 1024


def _parse_meta(meta: str | None) -> list[dict[str, Any]]:
    """meta 是 JSON 数组：[{"author": "张三", "title": "第一章 绪论"}, ...]"""
    if not meta:
        return []
    try:
        data = json.loads(meta)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"meta 不是合法 JSON：{exc}") from exc
    if not isinstance(data, list):
        raise HTTPException(status_code=422, detail="meta 必须是数组")
    return [item if isinstance(item, dict) else {} for item in data]


@router.post("/analyze", response_model=MergeResponse, summary="整合多份文稿")
async def analyze(
    files: Annotated[list[UploadFile], File(description="成员文稿，支持 docx / md / txt")],
    meta: Annotated[str | None, Form()] = None,
    title: Annotated[str, Form()] = "合并文稿",
) -> MergeResponse:
    if not files:
        raise HTTPException(status_code=422, detail="请至少上传一份文稿")
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=422, detail=f"一次最多上传 {MAX_FILES} 份文稿")

    entries = _parse_meta(meta)
    documents = []
    errors: list[str] = []
    total_bytes = 0

    for index, upload in enumerate(files):
        filename = upload.filename or f"未命名-{index + 1}"
        data = await upload.read()
        total_bytes += len(data)

        if len(data) > MAX_FILE_BYTES:
            errors.append(f"《{filename}》超过 10MB 上限，已跳过")
            continue
        if total_bytes > MAX_TOTAL_BYTES:
            raise HTTPException(status_code=413, detail="上传总量超过 40MB 上限")

        entry = entries[index] if index < len(entries) else {}
        author = str(entry.get("author") or "").strip()
        try:
            documents.append(parse_document(filename, data, author))
        except ParseError as exc:
            errors.append(f"《{filename}》解析失败：{exc}")
        except Exception as exc:  # noqa: BLE001 - 单份失败不应中断整体
            logger.exception("解析文稿失败: %s", filename)
            errors.append(f"《{filename}》解析异常：{type(exc).__name__}")

    if not documents:
        raise HTTPException(status_code=422, detail="；".join(errors) or "没有可用的文稿")

    chapter_titles = [
        str((entries[i] if i < len(entries) else {}).get("title") or "").strip() or None
        for i in range(len(documents))
    ]

    outcome = merge_documents(documents, chapter_titles, title=title or "合并文稿")

    outline = []
    for node in outcome.nodes:
        preview = ""
        for block in node.blocks:
            if block.kind in ("paragraph", "list"):
                preview = block.text[:80]
                break
        outline.append(
            OutlineNode(
                level=node.level,
                number=node.number,
                title=node.title,
                source=node.source,
                characters=node.char_count,
                preview=preview,
            )
        )

    warnings = list(outcome.warnings) + errors
    logger.info(
        "整合完成 documents=%d sections=%d duplicates=%d",
        outcome.stats["documents"],
        outcome.stats["sections"],
        outcome.stats["duplicates"],
    )

    return MergeResponse(
        title=title or "合并文稿",
        stats=MergeStats(**outcome.stats),
        outline=outline,
        duplicates=[DuplicateGroup(**item) for item in outcome.duplicates],
        terms=outcome.terms,
        warnings=warnings,
        markdown=outcome.markdown,
    )


@router.post("/export", summary="导出合并稿（md / docx）")
async def export(payload: ExportRequest) -> Response:
    safe_title = payload.title.strip() or "合并文稿"
    if payload.format == "docx":
        try:
            content = markdown_to_docx(payload.markdown, safe_title)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        suffix = "docx"
    else:
        content = to_markdown(payload.markdown)
        media_type = "text/markdown; charset=utf-8"
        suffix = "md"

    filename = f"{safe_title}.{suffix}"
    disposition = f"attachment; filename*=UTF-8''{quote(filename)}"
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": disposition})
