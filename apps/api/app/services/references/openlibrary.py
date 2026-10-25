"""Open Library 图书检索。

为什么需要它：OpenAlex 只覆盖学术出版物，而参考文献里经常出现
科普读物、文学作品、教材等图书，这些只能用图书库检索。
Open Library 免费、无需 Key，覆盖英文图书较好，中文图书次之。
"""

import logging

import httpx

from app.services.references.sources import ReferenceRecord

logger = logging.getLogger(__name__)

OPENLIBRARY = "https://openlibrary.org/search.json"
# 实测国内访问 Open Library 常在 20 秒以上且经常空结果，
# 超时压到 6 秒：拿得到就拿，拿不到不拖慢整体。
TIMEOUT = 6


async def search_books(query: str, limit: int = 4) -> list[ReferenceRecord]:
    """在 Open Library 检索图书。

    专门用来补齐「科普读物、教材、文学作品」这类非学术引用——学术文献走 OpenAlex，
    只靠学术库会漏掉所有没有 DOI 的书。
    """
    params = {
        "q": query,
        "limit": max(1, min(limit, 10)),
        "fields": "title,author_name,first_publish_year,publisher,isbn,key,subject",
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(OPENLIBRARY, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        logger.info("Open Library 检索失败: %s", exc)
        return []

    records: list[ReferenceRecord] = []
    for item in data.get("docs") or []:
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        publishers = item.get("publisher") or []
        isbn_list = item.get("isbn") or []
        records.append(
            ReferenceRecord(
                title=title,
                authors=[str(name) for name in (item.get("author_name") or [])][:5],
                year=item.get("first_publish_year"),
                venue=str(publishers[0]) if publishers else "",
                doi="",
                url=f"https://openlibrary.org{item.get('key', '')}",
                kind="book",
                source="openlibrary",
                abstract=("ISBN " + isbn_list[0]) if isbn_list else "",
            )
        )
    return records
