"""逐段风格统一（F4）：产出「原文 / 改后」成对结果，供用户逐句接受或拒绝。

设计要点：
- 按段处理而不是整篇重写——整篇重写会让用户无法判断哪里被改了；
- 每段都带 changed 标记与理由，前端只默认勾选真正改动的段；
- 提示词严禁增删事实：只改语体，不改内容。
"""

import asyncio
import logging
from typing import Any

from app.services.llm import ChatMessage, LLMError, LLMProvider

logger = logging.getLogger(__name__)

BATCH = 6
CONCURRENCY = 4
MAX_TOKENS = 4000
FENCE = chr(96) * 3  # 代码围栏，避免源码里出现三反引号

REWRITE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "rewrites": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "rewritten": {"type": "string"},
                    "changed": {"type": "boolean"},
                    "reason": {"type": "string"},
                },
                "required": ["id", "rewritten", "changed"],
            },
        }
    },
    "required": ["rewrites"],
}

REWRITE_PROMPT = """你是学术写作编辑。请把下面各段改写为**统一的学术书面语**。

要求：
1. 只改语体，不改事实：不增加原文没有的信息，不删除原文的观点与数据；
2. 去掉口语化表达、网络用语、第一人称主观表述（如「我觉得」「我们认为可以」改为客观陈述）；
3. 统一术语与标点（中文用全角标点，破折号用「——」）；
4. 保持每段长度接近原文，不要扩写成大段议论；
5. 如果某段本来就符合学术书面语，**原样返回并把 changed 设为 false**；
6. reason 用一句话说明改了什么（没改则留空）。

只输出 JSON：{"rewrites": [{"id": 段号, "rewritten": "改写后全文", "changed": true, "reason": "..."}]}"""


def split_paragraphs(markdown: str) -> list[dict]:
    """按行切段，跳过标题行、代码块、列表与表格。"""
    paragraphs: list[dict] = []
    in_code = False
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if line.startswith(FENCE):
            in_code = not in_code
            continue
        if in_code or not line.strip():
            continue
        if line.lstrip().startswith("#"):
            continue
        if line.strip().startswith(("- ", "* ", "|", ">")):
            continue
        if len(line.strip()) < 12:
            continue
        paragraphs.append({"id": len(paragraphs) + 1, "text": line.strip()})
    return paragraphs


async def _rewrite_batch(batch: list[dict], provider: LLMProvider) -> dict[int, dict]:
    body = "\n\n".join(f"[{item['id']}] {item['text']}" for item in batch)
    messages = [ChatMessage("system", REWRITE_PROMPT), ChatMessage("user", body)]
    try:
        result = await provider.structured(messages, REWRITE_SCHEMA, max_tokens=MAX_TOKENS)
    except LLMError as exc:
        logger.warning("风格统一批次失败: %s", exc)
        return {}

    mapping: dict[int, dict] = {}
    for item in result.get("rewrites") or []:
        try:
            key = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        mapping[key] = item
    return mapping


async def rewrite_diff(markdown: str, provider: LLMProvider) -> list[dict]:
    """逐段改写并返回「原文 / 改后」对照。

    分批 + 信号量并发：段落一多，单次调用会超时且 JSON 容易被截断，
    分批把耗时和失败面都压到可控范围。
    """
    paragraphs = split_paragraphs(markdown)
    if not paragraphs:
        return []

    batches = [paragraphs[i : i + BATCH] for i in range(0, len(paragraphs), BATCH)]
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async def run(batch: list[dict]) -> dict[int, dict]:
        async with semaphore:
            return await _rewrite_batch(batch, provider)

    results = await asyncio.gather(*(run(batch) for batch in batches), return_exceptions=True)

    merged: dict[int, dict] = {}
    for batch in results:
        if isinstance(batch, BaseException):
            continue
        merged.update(batch)

    segments = []
    for paragraph in paragraphs:
        item = merged.get(paragraph["id"]) or {}
        rewritten = item.get("rewritten") or paragraph["text"]
        changed = bool(item.get("changed"))
        # 模型声称改了但内容一致时，以实际比较为准
        if rewritten.strip() == paragraph["text"].strip():
            changed = False
        segments.append(
            {
                "id": paragraph["id"],
                "original": paragraph["text"],
                "rewritten": rewritten.strip(),
                "changed": changed,
                "reason": str(item.get("reason") or ""),
            }
        )
    return segments


def assemble(original_markdown: str, segments: list[dict], accepted: set[int]) -> str:
    """把用户选中的改写结果替换回原文，保持段落顺序。"""
    by_text = {
        item["original"]: item["rewritten"] for item in segments if item["id"] in accepted
    }
    lines = []
    for raw in original_markdown.splitlines():
        lines.append(by_text.get(raw.strip(), raw))
    return "\n".join(lines)
