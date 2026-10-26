"""引用建议：读一篇论文，指出哪些地方该补引用，并为每处给出候选文献。

与"按关键词检索文献"的区别：那个是用户先想到关键词再找文献，
这个是让 AI 通读全文，判断哪一句是"别人的观点 / 数据 / 方法"却没有任何标注。

四步：
1. 切段（复用统一的分段逻辑）；
2. 模型逐条判断哪些句子需要引用，并给出检索词；
3. 用检索词并发查 OpenAlex；
4. 每条建议带上 GB/T 7714 与 BibTeX 两种格式，供直接插入。
"""

import asyncio
import logging
from typing import Any

from app.services.llm import ChatMessage, LLMProvider
from app.services.references.bibtex import format_bibtex_entries
from app.services.references.gbt import format_entries
from app.services.references.sources import search_openalex

logger = logging.getLogger(__name__)

MAX_PARAGRAPHS = 60
MAX_SPOTS = 8
CANDIDATES_PER_SPOT = 3
CONCURRENCY = 4

SPOT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "spots": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "sentence": {"type": "string"},
                    "reason": {"type": "string"},
                    "query": {"type": "string"},
                },
                "required": ["id", "sentence", "reason", "query"],
            },
        }
    },
    "required": ["spots"],
}

SPOT_PROMPT = """你是论文的引用审稿人。下面是一篇论文的段落，请找出**需要标注引用但正文没有引用标注**的地方。

判断标准（满足其一即可）：
1. 陈述了某个事实、数据或统计结果（如「准确率提升 12%」「市场规模达 3000 亿」）；
2. 引用了别人的方法、模型、结论（如「元学习被广泛用于小样本场景」）；
3. 给出了领域内的共识或定义（如「注意力机制最早由…提出」）；
4. 提到了具体研究、系统、标准。

**不要**把以下情况列为需要引用：
- 作者自己的实验设计与结论（如「本文采用 ResNet-18」「我们在 ImageNet 上测试」）；
- 纯过渡句、章节总结、未来展望；
- 已经带 [1]、(张三, 2020) 这类标注的句子。

每条输出：
- sentence：原文句子（**原样摘录，不要改写**，最多 80 字）；
- reason：一句话说明为什么这里需要引用；
- query：用于检索文献的关键词（英文优先，2–6 个词，要具体到领域与方法）。

最多 8 条，按重要性排序。只输出 JSON：{"spots": [{"id": 1, "sentence": "...", "reason": "...", "query": "..."}]}"""


def split_paragraphs(markdown: str, limit: int = MAX_PARAGRAPHS) -> list[str]:
    """按行切段，跳过标题、代码块、列表与表格，只保留正文段落。"""
    fence = chr(96) * 3
    paragraphs: list[str] = []
    in_code = False
    for raw in markdown.splitlines():
        line = raw.strip()
        if line.startswith(fence):
            in_code = not in_code
            continue
        if in_code or not line:
            continue
        if line.startswith("#") or line.startswith(("- ", "* ", "|", ">")):
            continue
        if len(line) < 15:
            continue
        paragraphs.append(line)
        if len(paragraphs) >= limit:
            break
    return paragraphs


async def find_spots(paragraphs: list[str], provider: LLMProvider) -> list[dict]:
    """让模型判断哪些句子需要引用。"""
    if not paragraphs:
        return []
    body = "\n".join(f"[{i}] {text}" for i, text in enumerate(paragraphs, start=1))
    messages = [
        ChatMessage("system", SPOT_PROMPT),
        ChatMessage("user", f"全文共 {len(paragraphs)} 段：\n\n{body}"),
    ]
    # 这里不吞掉异常：模型不可用时必须让用户看到原因，
    # 否则界面会显示"没有需要引用的地方"，与事实相反。
    result = await provider.structured(messages, SPOT_SCHEMA, max_tokens=2500)

    spots = []
    for item in result.get("spots") or []:
        sentence = str(item.get("sentence") or "").strip()
        query = str(item.get("query") or "").strip()
        if not sentence or not query:
            continue
        spots.append(
            {
                "sentence": sentence[:200],
                "reason": str(item.get("reason") or "")[:160],
                "query": query[:120],
            }
        )
    return spots[:MAX_SPOTS]


async def _search_one(spot: dict, semaphore: asyncio.Semaphore) -> dict:
    async with semaphore:
        records = await search_openalex(spot["query"], CANDIDATES_PER_SPOT)

    entries = format_entries(records)
    bibtex = format_bibtex_entries(records)
    candidates = []
    for entry, bib in zip(entries, bibtex, strict=False):
        record = entry["record"]
        candidates.append(
            {
                "index": entry["index"],
                "text": entry["text"],
                "bibtex": bib["text"],
                "title": record["title"],
                "year": record["year"],
                "venue": record["venue"],
                "doi": record["doi"],
            }
        )
    return {**spot, "candidates": candidates}


async def suggest(markdown: str, provider: LLMProvider) -> dict:
    paragraphs = split_paragraphs(markdown)
    spots = await find_spots(paragraphs, provider)
    if not spots:
        return {"spots": [], "total": 0, "scanned_paragraphs": len(paragraphs)}

    semaphore = asyncio.Semaphore(CONCURRENCY)
    enriched = await asyncio.gather(
        *(_search_one(spot, semaphore) for spot in spots), return_exceptions=True
    )

    results = []
    for item in enriched:
        if isinstance(item, BaseException):
            continue
        results.append(item)

    logger.info("引用建议完成 paragraphs=%d spots=%d", len(paragraphs), len(results))
    return {"spots": results, "total": len(results), "scanned_paragraphs": len(paragraphs)}
