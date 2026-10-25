#!/usr/bin/env python3
"""MCP（Model Context Protocol）服务端。

把本项目的能力以标准 MCP 工具的形式暴露出去，任何支持 MCP 的客户端
（Claude Desktop、Cursor、自研 Agent 等）都能直接调用：

    merge_documents   合并多人文稿
    find_references   检索真实文献并按 GB/T 7714 格式化
    rewrite_style     逐段风格统一（返回原文/改后对照）
    deai_check        去 AI 味体检

实现方式是**零依赖的 JSON-RPC 2.0 over stdio**：MCP 的消息就是按行分隔的
JSON-RPC，握手 + tools/list + tools/call 三个方法即可跑通，因此不必引入
官方 SDK，镜像体积和启动速度都更可控。

注意：stdout 专供协议消息，所有日志必须走 stderr。
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import sys
from typing import Any

from app.services.documents import merge_documents, parse_document
from app.services.documents.deai import analyze as analyze_deai
from app.services.documents.rewrite import assemble, rewrite_diff
from app.services.llm import get_llm_provider
from app.services.references.gbt import format_entries
from app.services.references.sources import search_all

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "dafeiyu-workbench", "version": "1.0.0"}

# ---------------------------------------------------------------- 工具定义

TOOLS: list[dict[str, Any]] = [
    {
        "name": "merge_documents",
        "description": "把多份成员文稿合并成一篇：标题归一、重复段落检测、术语冲突提示。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "documents": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "章节标题，可留空"},
                            "author": {"type": "string", "description": "作者"},
                            "content": {"type": "string", "description": "Markdown 正文"},
                        },
                        "required": ["content"],
                    },
                },
                "title": {"type": "string", "description": "成稿标题"},
            },
            "required": ["documents"],
        },
    },
    {
        "name": "find_references",
        "description": "检索真实存在的文献（学术/图书/网页），按 GB/T 7714-2015 返回条目。绝不编造。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "检索词，英文召回更好"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "rewrite_style",
        "description": "逐段改写为统一学术书面语，返回原文/改后对照，可逐句接受。",
        "inputSchema": {
            "type": "object",
            "properties": {"markdown": {"type": "string"}},
            "required": ["markdown"],
        },
    },
    {
        "name": "deai_check",
        "description": "检测文本的「AI 味」：破折号、提示性冒号、模板化转折等，返回命中项与评分。",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
]


# ---------------------------------------------------------------- 工具实现


async def _tool_merge(args: dict) -> str:
    raw_docs = args.get("documents") or []
    if not raw_docs:
        raise ValueError("documents 不能为空")
    documents = []
    titles = []
    for index, item in enumerate(raw_docs):
        content = str(item.get("content") or "")
        filename = f"doc-{index + 1}.md"
        documents.append(parse_document(filename, content.encode("utf-8"), str(item.get("author") or "")))
        titles.append(str(item.get("title") or "").strip() or None)
    outcome = merge_documents(documents, titles, title=args.get("title") or "合并文稿")
    return json.dumps(
        {
            "markdown": outcome.markdown,
            "stats": outcome.stats,
            "duplicates": outcome.duplicates,
            "terms": outcome.terms,
            "warnings": outcome.warnings,
        },
        ensure_ascii=False,
    )


async def _tool_find_references(args: dict) -> str:
    query = str(args.get("query") or "").strip()
    if not query:
        raise ValueError("query 不能为空")
    limit = int(args.get("limit") or 5)
    records = await search_all([query], limit=max(1, min(limit, 20)))
    entries = format_entries(records)
    return json.dumps(
        {
            "count": len(entries),
            "entries": [item["text"] for item in entries],
            "note": "条目来自 OpenAlex / Crossref / Open Library / 网页检索的真实记录",
        },
        ensure_ascii=False,
    )


async def _tool_rewrite(args: dict) -> str:
    markdown = str(args.get("markdown") or "")
    if not markdown.strip():
        raise ValueError("markdown 不能为空")
    segments = await rewrite_diff(markdown, get_llm_provider())
    changed = [item["id"] for item in segments if item["changed"]]
    return json.dumps(
        {
            "segments": segments,
            "changed": changed,
            "applied_preview": assemble(markdown, segments, set(changed)),
        },
        ensure_ascii=False,
    )


async def _tool_deai(args: dict) -> str:
    text = str(args.get("text") or "")
    if not text.strip():
        raise ValueError("text 不能为空")
    report = analyze_deai(text)
    return json.dumps(report.to_dict(), ensure_ascii=False)


HANDLERS = {
    "merge_documents": _tool_merge,
    "find_references": _tool_find_references,
    "rewrite_style": _tool_rewrite,
    "deai_check": _tool_deai,
}


# ---------------------------------------------------------------- 协议处理


def _result(msg_id: Any, payload: dict) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "result": payload}


def _error(msg_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


async def handle(message: dict) -> dict | None:
    method = message.get("method")
    msg_id = message.get("id")

    if method == "initialize":
        return _result(
            msg_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
            },
        )

    if method in ("notifications/initialized", "initialized"):
        return None  # 通知无需响应

    if method == "tools/list":
        return _result(msg_id, {"tools": TOOLS})

    if method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        handler = HANDLERS.get(name or "")
        if handler is None:
            return _error(msg_id, -32602, f"未知工具：{name}")
        try:
            text = await handler(arguments)
            return _result(msg_id, {"content": [{"type": "text", "text": text}], "isError": False})
        except Exception as exc:  # noqa: BLE001 - 工具异常要回传给客户端而不是崩溃
            return _result(
                msg_id,
                {"content": [{"type": "text", "text": f"工具执行失败：{exc}"}], "isError": True},
            )

    if method == "ping":
        return _result(msg_id, {})

    return _error(msg_id, -32601, f"不支持的方法：{method}")


async def main() -> None:
    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            sys.stdout.write(json.dumps(_error(None, -32700, "JSON 解析失败")) + "\n")
            sys.stdout.flush()
            continue

        response = await handle(message)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
