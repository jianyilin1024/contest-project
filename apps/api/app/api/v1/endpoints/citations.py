"""引用建议接口。

POST /citations/suggest  上传一篇论文，返回「哪些句子该补引用」以及每处的候选文献
"""

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.citations import CitationSuggestResponse
from app.services.documents import ParseError, parse_document
from app.services.documents.citation_suggest import suggest as suggest_citations
from app.services.llm import LLMError, get_llm_provider

router = APIRouter(prefix="/citations", tags=["citations"])
logger = logging.getLogger(__name__)

MAX_BYTES = 10 * 1024 * 1024


@router.post("/suggest", response_model=CitationSuggestResponse, summary="通读论文，指出该补引用的地方")
async def suggest(file: UploadFile = File(description="论文文件，支持 docx / md / txt")) -> CitationSuggestResponse:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="文件为空")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="文件超过 10MB")

    filename = file.filename or "document.md"
    try:
        document = parse_document(filename, data, "")
    except ParseError as exc:
        raise HTTPException(status_code=422, detail=f"解析失败：{exc}") from exc

    paragraphs = [
        block.text.strip()
        for node in document.nodes
        for block in node.blocks
        if block.kind == "paragraph" and len(block.text.strip()) >= 15
    ]
    if not paragraphs:
        raise HTTPException(status_code=422, detail="没有找到可分析的正文段落")

    try:
        outcome = await suggest_citations("\n\n".join(paragraphs), get_llm_provider())
    except LLMError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc

    return CitationSuggestResponse(**outcome)
