"""一键成稿：合并 → 过渡 → 参考文献 → 排版导出。

设计原则：
- 每一步都可独立降级——某一步失败不阻断整体，失败原因写进 steps；
- 所有 AI 环节都带"不编造"约束，参考文献只来自 OpenAlex/Crossref 的真实记录；
- 核心逻辑只写一遍：/oneclick 返回完整结果，/oneclick/stream 通过 SSE 边跑边推。
"""

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.api.v1.endpoints.references import append_references
from app.schemas.pipeline import OneClickResponse, StepOut
from app.services.documents import ParseError, merge_documents, parse_document
from app.services.documents.agent import make_plan, verify
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

# 事件通道：kind 可以是 step / agent / verify
StepSink = Callable[[str, dict], Awaitable[None]] | None


def _flag(value: str | None, default: bool = True) -> bool:
    """表单开关解析：缺省为 True，显式传 false/0/no 才关闭。"""
    if value is None or value == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _parse_meta(meta: str | None) -> list[dict]:
    if not meta:
        return []
    try:
        data = json.loads(meta)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"meta 不是合法 JSON：{exc}") from exc
    return [item if isinstance(item, dict) else {} for item in data]


def plan_steps(want_transitions: bool, want_references: bool) -> list[str]:
    """对外公布的计划步骤——前端先画出流程骨架，再逐格点亮。"""
    steps = ["合并文稿"]
    if want_transitions:
        steps.append("补写过渡段")
    if want_references:
        steps.append("检索参考文献")
    steps.append("排版导出")
    return steps


async def run_pipeline(
    files: list[UploadFile],
    meta: str | None,
    title: str,
    want_deai: bool,
    want_transitions: bool,
    want_references: bool,
    reference_limit: int,
    emit: StepSink = None,
) -> OneClickResponse:
    """执行完整流程。emit 每完成一步调用一次，用于流式推送。"""

    async def record(name: str, status: str, detail: str, mark: float) -> None:
        step = StepOut(
            name=name,
            status=status,
            detail=detail,
            elapsed_ms=int((time.perf_counter() - mark) * 1000),
        )
        steps.append(step)
        if emit is not None:
            await emit("step", step.model_dump())

    async def publish(kind: str, payload: dict) -> None:
        if emit is not None:
            await emit(kind, payload)

    started = time.perf_counter()
    steps: list[StepOut] = []

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
    await record(
        "合并文稿",
        "ok",
        f"{len(documents)} 份文稿，{outcome.stats['sections']} 个章节，{outcome.stats['characters']} 字",
        mark,
    )

    final_markdown = merged
    transition_info: dict = {"candidates": 0, "needed": 0, "applied": 0, "skipped": True}

    # ---------- 1.5 Agent 规划：决定这次到底该做什么 ----------
    provider = get_llm_provider()
    headings = [node.title for node in outcome.nodes if node.level >= 1]
    plan = await make_plan(
        headings, merged, want_transitions, want_references, reference_limit, provider
    )
    await publish("agent", plan)

    # ---------- 2. 过渡段落 ----------
    if plan["need_transitions"]:
        mark = time.perf_counter()
        try:
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
                await record(
                    "补写过渡段", "ok", f"识别 {len(boundaries)} 处断层，插入 {len(picks)} 段", mark
                )
            else:
                await record("补写过渡段", "skipped", "没有检测到章节断层", mark)
        except LLMError as exc:
            await record("补写过渡段", "failed", str(exc)[:120], mark)
            transition_info["skipped"] = True
    else:
        await record("补写过渡段", "skipped", "未启用", mark)

    # ---------- 3. 参考文献 ----------
    reference_info: dict = {"query": "", "entries": [], "inserted": 0, "skipped": True}
    if plan["need_references"]:
        mark = time.perf_counter()
        query = (title or "").strip()
        try:
            # 先把标题/章节转成具体关键词（含英文），再检索——单一中文标题召回很差
            excerpt = " ".join(
                block.text
                for node in outcome.nodes
                for block in node.blocks
                if block.kind == "paragraph"
            )[:600]
            queries = await suggest_queries(query, headings, excerpt, provider)
            limit = max(1, min(int(plan.get("reference_limit") or reference_limit), 20))
            records = await search_references(queries, limit=limit)
            repaired = False
            if not records:
                # 自检修复：关键词没搜到就退回最朴素的标题检索再试一次
                fallback = [query] if query else queries[:1]
                if fallback:
                    records = await search_references(fallback, limit=limit)
                    repaired = bool(records)
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
                    "repaired": repaired,
                }
                detail = f"用 {len(queries)} 组关键词检索到 {len(texts)} 条"
                if repaired:
                    detail += "（关键词未命中，已改用标题重试）"
                await record("检索参考文献", "ok", detail, mark)
            else:
                await record("检索参考文献", "skipped", "没有检索到匹配文献", mark)
        except Exception as exc:  # noqa: BLE001 - 检索失败不应中断成稿
            logger.warning("参考文献检索失败: %s", exc)
            await record("检索参考文献", "failed", str(exc)[:120], mark)
    else:
        await record("检索参考文献", "skipped", "未启用", mark)

    # ---------- 4. 自检（确定性规则，不再问模型） ----------
    checks = verify(merged, final_markdown, plan, transition_info, reference_info)
    await publish("verify", {"checks": checks})
    failed = [item["name"] for item in checks if not item["ok"]]
    if failed:
        logger.warning("成稿自检未通过 %d 项: %s", len(failed), failed)

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
        plan=plan,
        checks=checks,
        transitions=transition_info,
        references=reference_info,
        steps=steps,
        elapsed_ms=elapsed,
    )


@router.post("/oneclick", response_model=OneClickResponse, summary="一键成稿")
async def oneclick(
    files: Annotated[list[UploadFile], File(description="成员文稿，支持 docx / md / txt")],
    meta: Annotated[str | None, Form()] = None,
    title: Annotated[str, Form()] = "合并文稿",
    deai: Annotated[str | None, Form()] = None,
    add_transitions: Annotated[str | None, Form()] = None,
    find_references: Annotated[str | None, Form()] = None,
    reference_limit: Annotated[int, Form()] = 8,
) -> OneClickResponse:
    # 用字符串接收再解析：FastAPI 对 bool 表单的缺省值处理不符合预期
    # （不传参时会变成 False），用 str + 显式默认最可靠。
    return await run_pipeline(
        files=files,
        meta=meta,
        title=title,
        want_deai=_flag(deai),
        want_transitions=_flag(add_transitions),
        want_references=_flag(find_references),
        reference_limit=reference_limit,
    )


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/oneclick/stream", summary="一键成稿（SSE 流式进度）")
async def oneclick_stream(
    files: Annotated[list[UploadFile], File(description="成员文稿，支持 docx / md / txt")],
    meta: Annotated[str | None, Form()] = None,
    title: Annotated[str, Form()] = "合并文稿",
    deai: Annotated[str | None, Form()] = None,
    add_transitions: Annotated[str | None, Form()] = None,
    find_references: Annotated[str | None, Form()] = None,
    reference_limit: Annotated[int, Form()] = 8,
) -> StreamingResponse:
    """与 /oneclick 等价，但把每一步的完成情况实时推给前端。

    事件类型：
      plan   → {"steps": [...]}   计划步骤，前端先画出骨架
      step   → StepOut           某一步完成（含状态与耗时）
      result → OneClickResponse  最终完整结果
      error  → {"detail": "..."} 失败原因
    """
    want_deai = _flag(deai)
    want_transitions = _flag(add_transitions)
    want_references = _flag(find_references)
    queue: asyncio.Queue[tuple[str, dict]] = asyncio.Queue()

    async def emit(kind: str, payload: dict) -> None:
        await queue.put((kind, payload))

    async def worker() -> None:
        try:
            result = await run_pipeline(
                files=files,
                meta=meta,
                title=title,
                want_deai=want_deai,
                want_transitions=want_transitions,
                want_references=want_references,
                reference_limit=reference_limit,
                emit=emit,
            )
            await queue.put(("result", result.model_dump()))
        except HTTPException as exc:
            await queue.put(("error", {"detail": str(exc.detail)}))
        except Exception as exc:  # noqa: BLE001 - 任何异常都要让前端收到
            logger.exception("一键成稿流式执行失败")
            await queue.put(("error", {"detail": f"执行失败：{exc}"[:200]}))

    async def event_stream():
        task = asyncio.create_task(worker())
        try:
            yield _sse("plan", {"steps": plan_steps(want_transitions, want_references)})
            while True:
                kind, payload = await queue.get()
                yield _sse(kind, payload)
                if kind in ("result", "error"):
                    break
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # 关键：告诉 nginx 不要缓冲，否则前端会一次性收到全部事件
            "X-Accel-Buffering": "no",
        },
    )
