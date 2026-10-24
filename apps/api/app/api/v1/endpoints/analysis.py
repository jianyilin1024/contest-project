"""单文档 AI 分析接口。

POST /analysis/single  上传一篇文档 → AI 判断文风异质性 + 归并建议 + 版式识别
POST /analysis/unify   按建议生成归并稿（逐段改写）
"""

import asyncio
import logging
import time
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas.analysis import (
    AnalysisStats,
    Assignment,
    AuthorshipGroup,
    LayoutConvention,
    LayoutResult,
    SegmentOut,
    SingleAnalysisResponse,
    StyleAdvice,
    StyleIssue,
    UnifyRequest,
    UnifyResponse,
)
from app.schemas.rewrite import (
    RewriteAssembleRequest,
    RewriteAssembleResponse,
    RewriteRequest,
    RewriteResponse,
    RewriteSegment,
)
from app.services.documents import ParseError, parse_document
from app.services.documents.ai_analysis import (
    advise_style,
    analyze_authorship,
    recognize_layout,
    unify_segments,
)
from app.services.documents.rewrite import assemble, rewrite_diff
from app.services.documents.segmentation import (
    MAX_UNITS,
    Segment,
    sample_segments,
    segment_document,
)
from app.services.llm import LLMError, get_llm_provider

router = APIRouter(prefix="/analysis", tags=["analysis"])
logger = logging.getLogger(__name__)

MAX_FILE_BYTES = 10 * 1024 * 1024


def _raise_llm_error(exc: LLMError) -> None:
    raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc


@router.post("/single", response_model=SingleAnalysisResponse, summary="单文档 AI 分析")
async def analyze_single(
    file: Annotated[UploadFile, File(description="待分析的文档，支持 docx / md / txt")],
    title: Annotated[str, Form()] = "",
    max_units: Annotated[int, Form()] = MAX_UNITS,
) -> SingleAnalysisResponse:
    started = time.perf_counter()
    filename = file.filename or "未命名文档"
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="文件内容为空")
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="文件超过 10MB 上限")

    try:
        doc = parse_document(filename, data)
    except ParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    segments = segment_document(doc)
    if not segments:
        raise HTTPException(status_code=422, detail="文档中没有足够长的段落可供分析")

    analyzed = sample_segments(segments, max(4, min(max_units, MAX_UNITS)))
    doc_title = title.strip() or filename.rsplit(".", 1)[0]
    provider = get_llm_provider()

    try:
        # 文风判定与版式识别互不依赖，并行发起；归并建议依赖文风判定结果
        authorship_raw, layout_raw = await asyncio.gather(
            analyze_authorship(analyzed, doc_title, provider),
            recognize_layout(doc, doc_title, provider),
        )
        style_raw = await advise_style(analyzed, authorship_raw, doc_title, provider)
    except LLMError as exc:
        _raise_llm_error(exc)

    # 把分组统计补全
    assignment_of = {item["unit_id"]: item for item in authorship_raw["assignments"]}
    groups: list[AuthorshipGroup] = []
    for group in authorship_raw["groups"]:
        members = [
            segment for segment in analyzed if assignment_of.get(segment.id, {}).get("group_id") == group["id"]
        ]
        avg_sentence = (
            round(sum(m.features["avg_sentence"] for m in members) / len(members), 1)
            if members
            else 0.0
        )
        groups.append(
            AuthorshipGroup(
                id=group["id"],
                label=group["label"],
                features=group["features"],
                units=len(members),
                characters=sum(m.chars for m in members),
                avg_sentence=avg_sentence,
                unit_ids=[m.id for m in members],
            )
        )

    assignments = [
        Assignment(
            unit_id=item["unit_id"],
            group_id=item["group_id"],
            confidence=item["confidence"],
            reason=item["reason"],
            section=next(
                (s.section for s in analyzed if s.id == item["unit_id"]), ""
            ),
            preview=next((s.text[:80] for s in analyzed if s.id == item["unit_id"]), ""),
        )
        for item in authorship_raw["assignments"]
    ]

    layout = LayoutResult(
        summary=str(layout_raw.get("summary") or ""),
        conventions=[
            LayoutConvention(
                aspect=str(item.get("aspect") or ""),
                observation=str(item.get("observation") or ""),
                consistent=bool(item.get("consistent", True)),
                suggestion=str(item.get("suggestion") or ""),
            )
            for item in (layout_raw.get("conventions") or [])
        ],
        facts=layout_raw.get("facts") or {},
    )

    style = StyleAdvice(
        canonical_style=str(style_raw.get("canonical_style") or ""),
        issues=[
            StyleIssue(
                type=str(item.get("type") or "other"),
                title=str(item.get("title") or ""),
                detail=str(item.get("detail") or ""),
                examples=[str(x) for x in (item.get("examples") or [])][:5],
                suggestion=str(item.get("suggestion") or ""),
            )
            for item in (style_raw.get("issues") or [])
        ],
        plan=[str(x) for x in (style_raw.get("plan") or [])][:8],
    )

    elapsed = int((time.perf_counter() - started) * 1000)
    logger.info(
        "单文档分析完成 file=%s units=%d groups=%d elapsed=%dms",
        filename,
        len(analyzed),
        len(groups),
        elapsed,
    )

    return SingleAnalysisResponse(
        title=doc_title,
        filename=filename,
        stats=AnalysisStats(
            sections=sum(1 for node in doc.nodes if node.level >= 1),
            paragraphs=len(segments),
            characters=sum(segment.chars for segment in segments),
            units_total=len(segments),
            units_analyzed=len(analyzed),
        ),
        authorship=authorship_raw and {
            "heterogeneity": authorship_raw["heterogeneity"],
            "conclusion": authorship_raw["conclusion"],
            "groups": groups,
            "assignments": assignments,
        },
        style=style,
        layout=layout,
        segments=[
            SegmentOut(
                id=segment.id,
                section=segment.section,
                text=segment.text,
                chars=segment.chars,
                features=segment.features,
            )
            for segment in segments
        ],
        model=provider.model,  # type: ignore[attr-defined]
        elapsed_ms=elapsed,
    )


@router.post("/unify", response_model=UnifyResponse, summary="生成归并稿")
async def unify(payload: UnifyRequest) -> UnifyResponse:
    provider = get_llm_provider()
    targets = [
        segment
        for segment in payload.segments
        if payload.target_group is None or segment.group_id != payload.target_group
    ]
    if not targets:
        targets = list(payload.segments)

    segments = [
        Segment(
            id=item.id,
            section=item.section,
            text=item.text,
            features={},
        )
        for item in targets
    ]

    try:
        outcome = await unify_segments(segments, payload.style_brief or "统一、规范的学术书面语", provider)
    except LLMError as exc:
        _raise_llm_error(exc)

    rewritten_map = {item["unit_id"]: item["text"] for item in outcome["rewrites"]}

    # 按原文顺序重组，章节变化时插入二级标题
    lines = [f"# {payload.title}", ""]
    current_section = None
    for item in payload.segments:
        if item.section and item.section != current_section:
            lines.extend([f"## {item.section}", ""])
            current_section = item.section
        lines.extend([rewritten_map.get(item.id, item.text), ""])

    markdown = "\n".join(lines).rstrip() + "\n"
    return UnifyResponse(
        markdown=markdown,
        rewritten=len(rewritten_map),
        failed=len(targets) - len(rewritten_map),
        notes=outcome["notes"],
    )

# ---------------- F4：逐段风格统一（可逐句接受/拒绝） ----------------


@router.post("/rewrite", response_model=RewriteResponse, summary="逐段风格统一")
async def rewrite_style(payload: RewriteRequest) -> RewriteResponse:
    """返回「原文 / 改后」成对结果，前端逐段勾选后调用 /rewrite/assemble。"""
    try:
        segments = await rewrite_diff(payload.markdown, get_llm_provider())
    except LLMError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc

    changed = sum(1 for item in segments if item["changed"])
    logger.info("风格统一完成 segments=%d changed=%d", len(segments), changed)
    return RewriteResponse(
        segments=[RewriteSegment(**item) for item in segments],
        changed_count=changed,
    )


@router.post("/rewrite/assemble", response_model=RewriteAssembleResponse, summary="应用选中的改写")
async def rewrite_assemble(payload: RewriteAssembleRequest) -> RewriteAssembleResponse:
    accepted = set(payload.accepted)
    markdown = assemble(
        payload.markdown,
        [item.model_dump() for item in payload.segments],
        accepted,
    )
    return RewriteAssembleResponse(markdown=markdown, applied=len(accepted))
