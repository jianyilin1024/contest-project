"""GB/T 7714-2015 参考文献格式化。

在本地完成，不调用模型——格式是确定性的，交给模型反而容易改错。
条目编号由调用方统一添加，这里只产出「作者. 题名[类型]. 出处.」主体。
"""

import re
from datetime import date

from app.services.references.sources import ReferenceRecord

_CJK = re.compile(r"[\u4e00-\u9fff]")

TYPE_MARK = {
    "journal": "J",
    "book": "M",
    "conference": "C",
    "thesis": "D",
    "web": "EB/OL",
    "other": "Z",
}


def format_author(name: str) -> str:
    """西文作者转「姓 名首字母」，中文作者原样保留。"""
    name = (name or "").strip()
    if not name:
        return ""
    if _CJK.search(name):
        # OpenAlex 对中文作者有时给「名 姓」，按 GB/T 7714 应为「姓名」且不加空格
        parts = name.split()
        if len(parts) == 2:
            return f"{parts[1]}{parts[0]}"
        return name.replace(" ", "")
    if "," in name:
        family, given = (part.strip() for part in name.split(",", 1))
    else:
        parts = name.split()
        if len(parts) == 1:
            return name
        family, given = parts[-1], " ".join(parts[:-1])
    initials = "".join(chunk[0].upper() for chunk in re.split(r"[\s\-]+", given) if chunk)
    return f"{family} {initials}".strip()


def format_authors(authors: list[str], limit: int = 3) -> str:
    """按 GB/T 7714 拼接作者。

    超过 limit 位时截断：中文用「等」、西文用「et al」——
    国标对中英文的省略写法要求不同，混用会被判为格式错误。
    """
    names = [format_author(name) for name in (authors or []) if name]
    if not names:
        return ""
    shown = names[:limit]
    text = ", ".join(shown)
    if len(names) > limit:
        text += ", 等" if any(_CJK.search(name) for name in names) else ", et al"
    return text


def _ensure_dot(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    return text if text.endswith((".", "．")) else text + "."


def format_gbt(record: ReferenceRecord) -> str:
    """生成一条 GB/T 7714-2015 条目（不含序号）。"""
    mark = TYPE_MARK.get(record.kind, "Z")
    segments: list[str] = []

    authors = format_authors(record.authors)
    if authors:
        segments.append(_ensure_dot(authors))

    title = (record.title or "").strip().rstrip(".")
    if title:
        segments.append(f"{title}[{mark}].")

    venue = (record.venue or "").strip().rstrip(".")
    year = record.year
    volume = (record.volume or "").strip()
    issue = (record.issue or "").strip()
    pages = (record.pages or "").strip().replace("–", "-")

    if record.kind == "journal":
        detail = venue
        if year:
            detail = f"{detail}, {year}" if detail else str(year)
        if volume:
            detail += f", {volume}"
        if issue:
            detail += f"({issue})"
        if pages:
            detail += f": {pages}"
        if detail:
            segments.append(_ensure_dot(detail))
    elif record.kind in ("book", "conference", "thesis"):
        place = ""
        detail = venue
        if year:
            detail = f"{detail}, {year}" if detail else str(year)
        if pages:
            detail += f": {pages}"
        if place:
            detail = f"{place}: {detail}" if detail else place
        if detail:
            segments.append(_ensure_dot(detail))
    else:
        detail = venue
        if year:
            detail = f"{detail}, {year}" if detail else str(year)
        if detail:
            segments.append(_ensure_dot(detail))

    if record.doi:
        segments.append(f"DOI: {record.doi}.")
    elif record.url and record.kind in ("web", "other"):
        # 国标对电子资源要求给出引用日期，缺了这条格式不完整
        segments.append(f"[引用日期 {date.today().isoformat()}].")
        segments.append(_ensure_dot(record.url))

    return " ".join(segment for segment in segments if segment)


def format_entries(records: list[ReferenceRecord], start: int = 1) -> list[dict]:
    """批量格式化，带 [序号]。"""
    entries = []
    for offset, record in enumerate(records):
        number = start + offset
        entries.append(
            {
                "index": number,
                "text": f"[{number}] {format_gbt(record)}",
                "record": record.to_dict(),
            }
        )
    return entries
