"""数据助手（F6）：找出段落里缺数据的地方，联网检索并给出可核实的补充。

三段式：
1. 模型识别「需要数据但没给数据」的缺口，并为每个缺口生成检索词；
2. 用 DeepSeek 搜索按检索词找资料；
3. 模型**只从检索结果里**抽取数据，每条必须附来源与原文引用。

铁律：检索结果里没有的，一律不写——宁可返回空，也不编造。
"""

import asyncio
import logging
from typing import Any

from app.services.llm import ChatMessage, LLMError, LLMProvider
from app.services.search.deepseek import web_search

logger = logging.getLogger(__name__)

MAX_GAPS = 2
# 来源太少模型看不到具体数字（实测 3 条时返回空），5 条是质量与耗时的平衡点
MAX_SOURCES_PER_GAP = 5

GAP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "gaps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "query": {"type": "string"},
                },
                "required": ["description", "query"],
            },
        }
    },
    "required": ["gaps"],
}

GAP_PROMPT = """你是学术写作助手。请找出给定段落中「需要具体数据支撑、但没有给出数据」的地方。

例如：
- "该方法效果显著" —— 缺具体准确率或提升幅度
- "用户数量增长迅速" —— 缺增长率与统计口径
- "成本大幅下降" —— 缺下降比例

要求：
1. 只找**确实需要数据**的地方，纯观点、纯方法描述不算缺口；
2. 每个缺口给出 description（说明缺什么）和 query（用于联网检索的关键词，要具体）；
3. 最多 2 个（优先选最影响说服力的）；没有缺口就返回空数组。

只输出 JSON：{"gaps": [{"description": "...", "query": "..."}]}"""

EXTRACT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "value": {"type": "string"},
                    "context": {"type": "string"},
                    "source_title": {"type": "string"},
                    "source_url": {"type": "string"},
                    "quote": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["value", "source_title", "source_url", "quote", "confidence"],
            },
        }
    },
    "required": ["suggestions"],
}

EXTRACT_PROMPT = """你是严谨的数据核查助手。下面给出原文缺口、以及联网检索到的若干网页摘要。

请**只从这些摘要里**抽取能填补缺口的具体数据。

每条建议必须包含：
- value：具体数值或事实（如「准确率 62.3%」「用户 1.2 亿」）；
- context：这条数据在原文里可以用在哪句话；
- source_title：来源网页标题（原样抄摘要里的）；
- source_url：来源链接（原样抄）；
- quote：摘要里支撑该数据的原句片段；
- confidence：0–1。

铁律：
1. **绝对不允许编造**。摘要里没有的数字，一个都不能写；
2. 摘要里没有可用的数据，就返回空数组；
3. 不要做推断、不要换算、不要合并多个来源的数字；
4. 数据必须与缺口相关，不相关的不写。

只输出 JSON：{"suggestions": [...]}"""


def _normalize_url(url: str) -> str:
    """去掉锚点与末尾斜杠，用于宽松比对模型回填的来源链接。"""
    return (url or "").strip().split("#")[0].rstrip("/").lower()


def _format_sources(results: list[dict]) -> str:
    blocks = []
    for index, item in enumerate(results[:MAX_SOURCES_PER_GAP], start=1):
        blocks.append(
            f"[来源 {index}] {item['title']}\n"
            f"URL: {item['url']}\n"
            f"站点: {item.get('site_name', '')}  日期: {item.get('date', '')}\n"
            f"摘要: {item.get('summary', '')[:500]}"
        )
    return "\n\n".join(blocks)


async def detect_gaps(text: str, provider: LLMProvider) -> list[dict]:
    """找出段落里「需要数据支撑、却没有给数据」的地方。

    返回 [{description, query}]。query 是给联网检索用的关键词而不是给人看的描述——
    两者分开是为了提高检索召回。模型失败时返回空列表，由上层决定是否继续。
    """
    messages = [
        ChatMessage("system", GAP_PROMPT),
        ChatMessage("user", f"段落：\n{text[:1500]}"),
    ]
    # 同引用建议：模型不可用要让用户看见，不能伪装成"没有缺口"
    result = await provider.structured(messages, GAP_SCHEMA, max_tokens=1200)

    gaps = []
    for item in result.get("gaps") or []:
        description = str(item.get("description") or "").strip()
        query = str(item.get("query") or "").strip()
        if description and query:
            gaps.append({"description": description, "query": query})
    return gaps[:MAX_GAPS]


async def extract_suggestions(
    text: str, gap: dict, results: list[dict], provider: LLMProvider
) -> list[dict]:
    """从检索结果中抽取能填补缺口的数据。

    每条建议都要求给出 source_url 与 quote，且 URL 必须落在本次检索结果里。
    这是防编造的关键：模型编一句话容易，编一个能对上原文的引用很难。
    """
    if not results:
        return []
    messages = [
        ChatMessage("system", EXTRACT_PROMPT),
        ChatMessage(
            "user",
            f"原文段落：\n{text[:1200]}\n\n"
            f"缺口：{gap['description']}\n\n"
            f"检索结果：\n{_format_sources(results)}",
        ),
    ]
    try:
        result = await provider.structured(messages, EXTRACT_SCHEMA, max_tokens=2000)
    except LLMError as exc:
        logger.warning("数据抽取失败: %s", exc)
        return []

    allowed_urls = {_normalize_url(item["url"]) for item in results}
    allowed_hosts = {
        _normalize_url(item["url"]).split("/")[2] for item in results if "://" in item["url"]
    }
    suggestions = []
    for item in result.get("suggestions") or []:
        url = str(item.get("source_url") or "").strip()
        value = str(item.get("value") or "").strip()
        # 只接受来自本次检索结果的链接，防止模型编造来源。
        # 模型常改写 #片段、末尾斜杠或路径细节，因此「完全匹配」或「同域」都放行。
        normalized = _normalize_url(url)
        same_host = "://" in url and normalized.split("/")[2] in allowed_hosts
        if not value or (normalized not in allowed_urls and not same_host):
            logger.debug("丢弃来源不匹配的建议: %s -> %s", value[:30], url[:80])
            continue
        try:
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0.5))))
        except (TypeError, ValueError):
            confidence = 0.5
        suggestions.append(
            {
                "value": value[:300],
                "context": str(item.get("context") or "")[:300],
                "source_title": str(item.get("source_title") or "")[:200],
                "source_url": url,
                "quote": str(item.get("quote") or "")[:400],
                "confidence": round(confidence, 2),
                "gap": gap["description"],
            }
        )
    return suggestions


async def assist(text: str, provider: LLMProvider) -> dict:
    """数据助手主流程：识别缺口 → 并发检索 → 抽取建议。

    某个缺口检索失败只是少一条建议，不影响其他缺口——单点失败不升级为整体失败。
    """
    gaps = await detect_gaps(text, provider)
    if not gaps:
        return {"gaps": [], "suggestions": [], "searched": 0}

    # 各缺口的检索并发执行
    searches = await asyncio.gather(
        *(web_search(gap["query"], count=MAX_SOURCES_PER_GAP, ori_question=text[:128]) for gap in gaps),
        return_exceptions=True,
    )

    results_by_gap: list[list[dict]] = []
    for batch in searches:
        results_by_gap.append([] if isinstance(batch, BaseException) else batch)

    extractions = await asyncio.gather(
        *(
            extract_suggestions(text, gap, results, provider)
            for gap, results in zip(gaps, results_by_gap, strict=False)
        ),
        return_exceptions=True,
    )
    suggestions: list[dict] = []
    for batch in extractions:
        if isinstance(batch, BaseException):
            continue
        suggestions.extend(batch)

    suggestions.sort(key=lambda item: -item["confidence"])
    return {
        "gaps": gaps,
        "suggestions": suggestions,
        "searched": sum(len(items) for items in results_by_gap),
    }