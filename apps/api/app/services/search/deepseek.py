"""DeepSeek 搜索 API 客户端。

接口：POST {base}/search，base 默认 https://api.deepseek.com/v1/tools
请求：{"query": "...", "count": 1-50, "ori_question": "可选"}
返回：{"results": [{title, url, summary, site_name, date, authority, rerank_score}]}
"""

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_BASE = "https://api.deepseek.com/v1/tools"
TIMEOUT = 40


async def web_search(query: str, count: int = 8, ori_question: str | None = None) -> list[dict]:
    """返回网页搜索结果；未配置 Key 或调用失败时返回空列表（调用方自行降级）。"""
    if not settings.search_api_key:
        logger.info("未配置 SEARCH_API_KEY，跳过网页检索")
        return []

    base = (settings.search_base_url or DEFAULT_BASE).rstrip("/")
    payload: dict[str, Any] = {"query": query, "count": max(1, min(count, 50))}
    if ori_question:
        payload["ori_question"] = ori_question[:128]

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{base}/search",
                json=payload,
                headers={"Authorization": f"Bearer {settings.search_api_key}"},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        logger.warning("网页检索失败: %s", exc)
        return []

    results = []
    for item in data.get("results") or []:
        url = str(item.get("url") or "").strip()
        title = str(item.get("title") or "").strip()
        if not url or not title:
            continue
        results.append(
            {
                "title": title,
                "url": url,
                "summary": str(item.get("summary") or "")[:800],
                "site_name": str(item.get("site_name") or ""),
                "date": str(item.get("date") or ""),
                "authority": item.get("authority") or 0,
                "score": float(item.get("rerank_score") or 0.0),
            }
        )
    return results
