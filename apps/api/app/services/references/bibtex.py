"""BibTeX 生成。

与 GB/T 7714 并行输出：写论文用前者，投稿或交 LaTeX 作业用后者。
不做转义美化——中文作者名与标题在有 biber/xelatex 的环境里能正确处理，
强行转成拼音反而会破坏原有信息。
"""

import re

from app.services.references.sources import ReferenceRecord

_ENTRY_TYPE = {
    "journal": "article",
    "book": "book",
    "conference": "inproceedings",
    "thesis": "phdthesis",
    "web": "misc",
    "other": "misc",
}

_CJK = re.compile(r"[\u4e00-\u9fff]")


def _ascii_key(text: str) -> str:
    """引用键只保留 ASCII 字母数字，避免 LaTeX 编译报错。"""
    cleaned = re.sub(r"[^A-Za-z0-9]", "", text)
    return cleaned or "ref"


def citation_key(record: ReferenceRecord) -> str:
    """生成引用键：第一作者姓 + 年份 + 标题首个英文词，冲突由调用方加后缀。

    中文作者的姓名无法直接做 LaTeX 键（会报错），统一用 zh 占位；
    标题里的中文同理跳过，取第一个英文词。
    """
    name = (record.authors[0] if record.authors else "anon").strip()
    if _CJK.search(name):
        author = "zh"
    else:
        parts = name.split()
        author = parts[-1] if parts else "anon"

    year = str(record.year or "nd")

    word = ""
    for token in (record.title or "").split():
        if _CJK.search(token):
            continue
        cleaned = re.sub(r"[^A-Za-z]", "", token)
        if cleaned:
            word = cleaned
            break

    return _ascii_key(f"{author}{year}{word}") or f"ref{year}"


def _field(name: str, value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    return f"  {name} = {{{value}}},\n"


def format_bibtex(record: ReferenceRecord, key: str | None = None) -> str:
    """把一条记录渲染成 BibTeX。空字段自动省略，不留空的 volume 之类残迹。"""
    entry_type = _ENTRY_TYPE.get(record.kind, "misc")
    fields = "".join(
        [
            _field("title", record.title.rstrip(".")),
            _field("author", " and ".join(record.authors)) if record.authors else "",
            _field("year", str(record.year)) if record.year else "",
            _field("journal", record.venue) if record.kind == "journal" else "",
            _field("booktitle", record.venue) if record.kind == "conference" else "",
            _field("publisher", record.venue) if record.kind in ("book", "thesis") else "",
            _field("volume", record.volume),
            _field("number", record.issue),
            _field("pages", record.pages.replace("-", "--")),
            _field("doi", record.doi),
            _field("url", record.url) if record.kind in ("web", "other") else "",
        ]
    )
    return f"@{entry_type}{{{key or citation_key(record)},\n{fields}}}\n"


def format_bibtex_entries(records: list[ReferenceRecord]) -> list[dict]:
    """批量生成，处理键冲突：重复键追加 a/b/c 后缀。"""
    used: dict[str, int] = {}
    results = []
    for record in records:
        base = citation_key(record)
        if base in used:
            used[base] += 1
            key = f"{base}{chr(ord('a') + used[base])}"
        else:
            used[base] = 0
            key = base
        results.append({"key": key, "text": format_bibtex(record, key)})
    return results
