"""参考文献检索：OpenAlex + Crossref。

设计取舍（参考 pyalex / habanero / bibverify 的做法）：
- 只用**真实存在的学术元数据源**，不靠模型生成文献，从根上杜绝编造；
- OpenAlex 负责检索（覆盖面广、免费、无需 Key），Crossref 负责按 DOI 补全卷期页码；
- 格式化在本地完成（GB/T 7714-2015），不消耗 token，也不会被模型改错。
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

OPENALEX = "https://api.openalex.org"
CROSSREF = "https://api.crossref.org"
MAILTO = "dafeiyu-workbench@example.com"  # OpenAlex 建议带上联系方式，进入"礼貌池"
TIMEOUT = 20

_KIND_MAP = {
    "article": "journal",
    "review": "journal",
    "book": "book",
    "book-chapter": "conference",
    "dissertation": "thesis",
    # 预印本按电子资源著录（[EB/OL]），比 [Z] 更贴近国标实践
    "preprint": "web",
    "report": "other",
    "dataset": "other",
}


@dataclass
class ReferenceRecord:
    title: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    doi: str = ""
    url: str = ""
    kind: str = "other"
    source: str = ""
    cited_by: int = 0
    relevance: float = 0.0
    abstract: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "venue": self.venue,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
            "doi": self.doi,
            "url": self.url,
            "kind": self.kind,
            "source": self.source,
            "cited_by": self.cited_by,
            "relevance": round(self.relevance, 3),
            "abstract": self.abstract,
        }


def _clean_doi(value: str) -> str:
    value = (value or "").strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if value.lower().startswith(prefix):
            value = value[len(prefix) :]
    return value.strip()


def _abstract_from_inverted(index: dict[str, list[int]] | None) -> str:
    """OpenAlex 的摘要是倒排索引，还原成文本。"""
    if not index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, places in index.items():
        for place in places:
            positions.append((place, word))
    positions.sort()
    return " ".join(word for _, word in positions)[:600]


async def search_openalex(query: str, limit: int = 8) -> list[ReferenceRecord]:
    params = {
        "search": query,
        "per_page": max(1, min(limit, 25)),
        "mailto": MAILTO,
        "filter": "type:article|book|book-chapter|dissertation|preprint",
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{OPENALEX}/works", params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        logger.warning("OpenAlex 检索失败: %s", exc)
        return []

    records: list[ReferenceRecord] = []
    for item in data.get("results") or []:
        biblio = item.get("biblio") or {}
        first_page = biblio.get("first_page") or ""
        last_page = biblio.get("last_page") or ""
        pages = f"{first_page}-{last_page}" if first_page and last_page else first_page
        location = (item.get("primary_location") or {}).get("source") or {}
        authors = [
            (authorship.get("author") or {}).get("display_name", "")
            for authorship in (item.get("authorships") or [])
        ]
        records.append(
            ReferenceRecord(
                title=(item.get("display_name") or item.get("title") or "").strip(),
                authors=[name for name in authors if name],
                year=item.get("publication_year"),
                venue=(location.get("display_name") or "").strip(),
                volume=str(biblio.get("volume") or ""),
                issue=str(biblio.get("issue") or ""),
                pages=pages,
                doi=_clean_doi(item.get("doi") or ""),
                url=item.get("doi") or item.get("id") or "",
                kind=_KIND_MAP.get(item.get("type") or "", "other"),
                source="openalex",
                cited_by=int(item.get("cited_by_count") or 0),
                relevance=float(item.get("relevance_score") or 0.0),
                abstract=_abstract_from_inverted(item.get("abstract_inverted_index")),
            )
        )
    return [record for record in records if record.title]


async def lookup_crossref(doi: str) -> ReferenceRecord | None:
    """按 DOI 补全卷期页码（Crossref 的字段更规整）。"""
    doi = _clean_doi(doi)
    if not doi:
        return None
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{CROSSREF}/works/{doi}", params={"mailto": MAILTO})
            response.raise_for_status()
            message = response.json().get("message") or {}
    except httpx.HTTPError as exc:
        logger.info("Crossref 查询失败 %s: %s", doi, exc)
        return None

    authors = []
    for author in message.get("author") or []:
        family = author.get("family") or ""
        given = author.get("given") or ""
        authors.append(f"{family} {given}".strip() if family else (author.get("name") or ""))
    issued = (message.get("issued") or {}).get("date-parts") or [[None]]
    year = issued[0][0] if issued and issued[0] else None
    container = (message.get("container-title") or [""])
    return ReferenceRecord(
        title=(message.get("title") or [""])[0],
        authors=[name for name in authors if name],
        year=year,
        venue=container[0] if container else "",
        volume=str(message.get("volume") or ""),
        issue=str(message.get("issue") or ""),
        pages=str(message.get("page") or ""),
        doi=doi,
        url=f"https://doi.org/{doi}",
        kind="journal" if message.get("container-title") else "book",
        source="crossref",
    )


def merge_enrichment(primary: ReferenceRecord, extra: ReferenceRecord) -> ReferenceRecord:
    """用 Crossref 的数据补齐 OpenAlex 缺的字段，不覆盖已有值。"""
    for attr in ("venue", "volume", "issue", "pages", "year"):
        if not getattr(primary, attr) and getattr(extra, attr):
            setattr(primary, attr, getattr(extra, attr))
    if not primary.authors and extra.authors:
        primary.authors = extra.authors
    return primary


def _dedupe_key(record: ReferenceRecord) -> str:
    if record.doi:
        return record.doi.lower()
    return "".join(ch for ch in record.title.lower() if ch.isalnum())[:60]


async def search_multi(
    queries: list[str], limit: int = 8, per_query: int = 6
) -> list[ReferenceRecord]:
    """多关键词检索后合并去重，按相关度排序。

    单一中文标题在 OpenAlex 上召回很差（容易命中「学习」这类泛词），
    因此先用模型抽出多个中英文关键词，再分别检索。
    """
    results = await asyncio.gather(
        *(search_openalex(query, per_query) for query in queries if query.strip()),
        return_exceptions=True,
    )

    merged: dict[str, ReferenceRecord] = {}
    for batch in results:
        if isinstance(batch, BaseException):
            continue
        for record in batch:
            key = _dedupe_key(record)
            existing = merged.get(key)
            if existing is None:
                merged[key] = record
            else:
                existing.relevance = max(existing.relevance, record.relevance)

    ranked = sorted(
        merged.values(), key=lambda item: (item.relevance, item.cited_by), reverse=True
    )
    return ranked[:limit]


# 网页结果里常见的噪声：PDF 片段、导航文字、抓取残留
_WEB_NOISE = re.compile(
    r"^(\[\d+\]|跳到|跳至|登录|注册|首页|目录|第\s*\d+\s*页)|跳到主要内容|跳至主要内容|Ask Learn"
)


def _web_result_usable(item: dict) -> bool:
    """过滤掉标题是正文片段、导航文字或缺少站点信息的网页结果。"""
    title = (item.get("title") or "").strip()
    if not (6 <= len(title) <= 90):
        return False
    if _WEB_NOISE.search(title):
        return False
    if not item.get("site_name"):
        return False
    # 权威度太低（0/1）的多为论坛、转载页，宁缺毋滥
    return int(item.get("authority") or 0) >= 2


def _year_from_date(value: str) -> int | None:
    match = re.search(r"(19|20)\d{2}", value or "")
    return int(match.group(0)) if match else None


async def search_all(
    queries: list[str],
    limit: int = 8,
    include_academic: bool = True,
    include_books: bool = True,
    include_web: bool = True,
) -> list[ReferenceRecord]:
    """聚合三类来源：学术论文、图书、网页资料。

    参考文献不只有学术论著——科普读物、文学作品、政策文件同样会被引用，
    因此这里把「学术库 / 图书库 / 网页检索」并列，各自带 kind 标识。
    """
    from app.services.references.openlibrary import search_books  # 延迟导入避免循环依赖
    from app.services.search.deepseek import web_search

    records: list[ReferenceRecord] = []
    if include_academic:
        records.extend(await search_multi(queries, limit=limit))

    if include_books:
        for query in queries[:2]:
            records.extend(await search_books(query, limit=3))

    if include_web:
        for query in queries[:2]:
            items = await web_search(query, count=6, ori_question=queries[0] if queries else None)
            for item in [entry for entry in items if _web_result_usable(entry)][:3]:
                records.append(
                    ReferenceRecord(
                        title=item["title"],
                        authors=[],
                        year=_year_from_date(item["date"]),
                        venue=item["site_name"],
                        url=item["url"],
                        kind="web",
                        source="deepseek-web",
                        relevance=item["score"],
                        abstract=item["summary"],
                    )
                )

    # 跨来源去重（同标题或同 URL）
    seen: set[str] = set()
    deduped: list[ReferenceRecord] = []
    for record in records:
        key = _dedupe_key(record) or record.url
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)

    return deduped[:limit]


async def search(query: str, limit: int = 8, enrich: bool = True) -> list[ReferenceRecord]:
    records = await search_openalex(query, limit)
    if not enrich or not records:
        return records

    # 只对前若干条做 DOI 补全，控制外部请求数量
    for record in records[:5]:
        if not record.doi:
            continue
        extra = await lookup_crossref(record.doi)
        if extra:
            merge_enrichment(record, extra)
    return records
