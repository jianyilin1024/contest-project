"""一键成稿：合并 → 过渡 → 参考文献 → 排版导出。

设计原则：
- 每一步都可独立降级——某一步失败不阻断整体，失败原因写进 steps；
- 所有 AI 环节都带"不编造"约束，参考文献只来自 OpenAlex/Crossref 的真实记录。
"""

import json
import logging
import time
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.api.v1.endpoints.references import append_references
from app.schemas.pipeline import OneClickResponse, StepOut
from app.services.documents import ParseError, merge_documents, parse_document
from app.services.documents.transitions import (
    analyze_transitions,
    apply_deai,
    assemble_markdown,
    build_blocks,
    find_boundaries,
)
from app.services.llm import LLMError, get_llm_provider
from app.services.references.gbt import format_entries
from app.services.references.queries import suggest_queries
from app.services.references.sources import search_all as search_references

router = APIRouter(prefix="/pipeline", tags=["pipeline"])
logger = logging.getLogger(__name__)

MAX_FILES = 20
MAX_FILE_BYTES = 10 * 1024 * 1024


def _parse_meta(meta: str | None) -> list[dict]:
    if not meta:
        return []
    try:
        data = json.loads(meta)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"meta 不是合法 JSON：{exc}") from exc
    return [item if isinstance(item, dict) else {} for item in data]


@router.post("/oneclick", response_model=OneClickResponse, summary="一键成稿")
async def oneclick(
    files: Annotated[list[UploadFile], File(description="成员文稿，支持 docx / md / txt")],
    meta: Annotated[str | None, Form()] = None,
    title: Annotated[str, Form()] = "合并文稿",
    deai: Annotated[bool | None, Form()] = None,
    add_transitions: Annotated[bool | None, Form()] = None,
    find_references: Annotated[bool | None, Form()] = None,
    reference_limit: Annotated[int, Form()] = 8,
) -> OneClickResponse:
    # 不传参时默认全开；显式传 false 才关闭（Form 的布尔默认值在缺省时不可靠）
    want_deai = True if deai is None else deai
    want_transitions = True if add_transitions is None else add_transitions
    want_references = True if find_references is None else find_references
    started = time.perf_counter()
    steps: list[StepOut] = []

    def record(name: str, status: str, detail: str, mark: float) -> None:
        steps.append(
            StepOut(
                name=name,
                status=status,
                detail=detail,
                elapsed_ms=int((time.perf_counter() - mark) * 1000),
            )
        )

    if not files:
        raise HTTPException(status_code=422, detail="请至少上传一份文稿")

    # ---------- 1. 解析与合并 ----------
    mark = time.perf_counter()
    entries = _parse_meta(meta)
    documents = []
    errors: list[str] = []
    for index, upload in enumerate(files):
        filename = upload.filename or f"未命名-{index + 1}"
        data = await upload.read()
        if len(data) > MAX_FILE_BYTES:
            errors.append(f"《{filename}》超过 10MB，已跳过")
            continue
        entry = entries[index] if index < len(entries) else {}
        try:
            documents.append(parse_document(filename, data, str(entry.get("author") or "")))
        except ParseError as exc:
            errors.append(f"《{filename}》解析失败：{exc}")

    if not documents:
        raise HTTPException(status_code=422, detail="；".join(errors) or "没有可用的文稿")

    chapter_titles = [
        str((entries[i] if i < len(entries) else {}).get("title") or "").strip() or None
        for i in range(len(documents))
    ]
    outcome = merge_documents(documents, chapter_titles, title=title or "合并文稿")
    merged = outcome.markdown
    record(
        "合并文稿",
        "ok",
        f"{len(documents)} 份文稿，{outcome.stats['sections']} 个章节，{outcome.stats['characters']} 字",
        mark,
    )

    final_markdown = merged
    transition_info: dict = {"candidates": 0, "needed": 0, "applied": 0, "skipped": True}

    # ---------- 2. 过渡段落 ----------
    if want_transitions:
        mark = time.perf_counter()
        try:
            provider = get_llm_provider()
            blocks = build_blocks(final_markdown)
            boundaries = find_boundaries(blocks)
            if boundaries:
                boundaries = await analyze_transitions(boundaries, provider, title or "合并文稿")
                if want_deai:
                    await apply_deai(boundaries, provider)
                picks = []
                for boundary in boundaries:
                    if not boundary["needs"] or not boundary["options"]:
                        continue
                    option = next(
                        (item for item in boundary["options"] if not item.get("duplicate")),
                        boundary["options"][0],
                    )
                    picks.append(
                        {"after_block_id": boundary["after_block_id"], "text": option["text"]}
                    )
                if picks:
                    final_markdown = assemble_markdown(
                        [block.to_dict() for block in blocks], picks
                    )
                transition_info = {
                    "candidates": len(boundaries),
                    "needed": sum(1 for item in boundaries if item["needs"]),
                    "applied": len(picks),
                    "skipped": False,
                }
                record("补写过渡段", "ok", f"识别 {len(boundaries)} 处断层，插入 {len(picks)} 段", mark)
            else:
                record("补写过渡段", "skipped", "没有检测到章节断层", mark)
        except LLMError as exc:
            record("补写过渡段", "failed", str(exc)[:120], mark)
            transition_info["skipped"] = True
    else:
        record("补写过渡段", "skipped", "未启用", mark)

    # ---------- 3. 参考文献 ----------
    reference_info: dict = {"query": "", "entries": [], "inserted": 0, "skipped": True}
    if want_references:
        mark = time.perf_counter()
        query = (title or "").strip()
        headings = [node.title for node in outcome.nodes if node.level >= 1]
        try:
            # 先把标题/章节转成具体关键词（含英文），再检索——单一中文标题召回很差
            excerpt = " ".join(
                block.text
                for node in outcome.nodes
                for block in node.blocks
                if block.kind == "paragraph"
            )[:600]
            queries = await suggest_queries(query, headings, excerpt, get_llm_provider())
            records = await search_references(
                queries, limit=max(1, min(reference_limit, 20))
            )
            if records:
                formatted = format_entries(records)
                texts = [item["text"] for item in formatted]
                final_markdown = append_references(final_markdown, texts)
                reference_info = {
                    "query": query,
                    "queries": queries,
                    "entries": formatted,
                    "inserted": len(texts),
                    "skipped": False,
                }
                record(
                    "检索参考文献",
                    "ok",
                    f"用 {len(queries)} 组关键词检索到 {len(texts)} 条",
                    mark,
                )
            else:
                record("检索参考文献", "skipped", "没有检索到匹配文献", mark)
        except Exception as exc:  # noqa: BLE001 - 检索失败不应中断成稿
            logger.warning("参考文献检索失败: %s", exc)
            record("检索参考文献", "failed", str(exc)[:120], mark)
    else:
        record("检索参考文献", "skipped", "未启用", mark)

    elapsed = int((time.perf_counter() - started) * 1000)
    logger.info(
        "一键成稿完成 files=%d sections=%d refs=%d elapsed=%dms",
        len(documents),
        outcome.stats["sections"],
        reference_info.get("inserted", 0),
        elapsed,
    )

    return OneClickResponse(
        title=title or "合并文稿",
        merged_markdown=merged,
        final_markdown=final_markdown,
        stats=outcome.stats,
        duplicates=outcome.duplicates,
        terms=outcome.terms,
        warnings=list(outcome.warnings) + errors,
        transitions=transition_info,
        references=reference_info,
        steps=steps,
        elapsed_ms=elapsed,
    )
