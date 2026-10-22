"""用模型把文档标题/章节标题转成检索关键词。

为什么需要这一步：OpenAlex 对中文长标题的召回很差，「小样本学习研究」
会命中大量讲「学习」的无关文献。抽成多个具体关键词（并给出英文对应词）
能显著提升相关性。
"""

import logging

from app.services.llm import ChatMessage, LLMError, LLMProvider

logger = logging.getLogger(__name__)

QUERY_SCHEMA = {
    "type": "object",
    "properties": {
        "queries": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["queries"],
}

QUERY_PROMPT = """你是学术检索助手。请根据文档标题与章节标题，生成 3–5 个用于检索文献的关键词组合。

要求：
1. 关键词要具体（领域 + 方法 + 任务），不要用「研究」「分析」这类泛词；
2. 中文文档也要给出对应的英文关键词——OpenAlex 的英文文献覆盖远好于中文；
3. 每个查询 2–6 个词，不要写成整句；
4. 覆盖不同角度（例如：任务本身、所用方法、应用场景）。

只输出 JSON：{"queries": ["few-shot image classification", "meta-learning", ...]}"""


async def suggest_queries(
    title: str, headings: list[str], excerpt: str, provider: LLMProvider
) -> list[str]:
    """返回 3–5 个检索关键词；失败时退化为标题本身。

    excerpt 是正文摘录——标题常常很泛（如「小组作业合并稿」），
    只看标题会抽出与内容无关的关键词，必须结合正文。
    """
    outline = "\n".join(f"- {item}" for item in headings[:12] if item)
    body = (excerpt or "").strip()[:600]
    messages = [
        ChatMessage("system", QUERY_PROMPT),
        ChatMessage(
            "user",
            f"文档标题：{title}\n章节：\n{outline or '（无章节）'}\n\n正文摘录：\n{body or '（无正文）'}",
        ),
    ]
    try:
        result = await provider.structured(messages, QUERY_SCHEMA, max_tokens=800)
    except LLMError as exc:
        logger.warning("关键词抽取失败，退化为标题检索: %s", exc)
        return [title] if title.strip() else []

    queries = [
        str(item).strip() for item in (result.get("queries") or []) if str(item).strip()
    ]
    if title.strip() and title.strip() not in queries:
        queries.append(title.strip())
    return queries[:6]
