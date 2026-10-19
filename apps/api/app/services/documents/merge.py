"""多部分整合：标题归一、重复段落检测、术语不一致检测、合并稿生成。

设计取舍：
- 合并采用"一份文稿 = 一个章节"的模型，符合小组作业最常见的分工方式；
- 每份文稿的标题层级整体下移一级，挂在它自己的章节之下；
- 文稿开头没有归属章节的正文，收进该章节的引言部分；
- 检测结果是**启发式**的，只做提示，不自动删改内容。
"""

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

from app.services.documents.ir import Node, ParsedDocument

MAX_DUPLICATE_GROUPS = 20
MAX_TERM_CONFLICTS = 12
MIN_PARAGRAPH_LEN = 25
# 中文技术术语通常 4 字以上；门槛设成 3 会把"数据集""经网络"这类碎片放进来
MIN_TERM_LEN = 4
# 首尾是虚词的候选基本是从句子里切出来的碎片，不是术语
_FUNCTION_CHARS = set(
    "的在是了和与为有上下中对以及或并就都也很更最可能会把被从到向由于而则若但因所使让给还只才又再已将该其之此等者地得着过们个种些每各本多少"
)

# 只承认"已知修饰词"造成的形式差异。
# 这样宁可漏报，也不把"神经网络在图"这种切词碎片报成术语冲突。
_QUALIFIER_PREFIXES = set(
    "类新旧多少大小高低深浅长短单双全总主次同异正负超亚准半反前后内外中泛广强弱无有非重轻微宏粗精实虚特通专公跨"
)
_QUALIFIER_SUFFIXES = {
    "模型", "方法", "技术", "系统", "算法", "网络", "数据", "学习", "分析",
    "框架", "策略", "理论", "机制", "结构", "体系", "平台", "工具", "函数",
    "矩阵", "序列", "空间", "集合", "性能", "能力", "应用",
}


@dataclass
class MergeOutcome:
    nodes: list[Node]
    markdown: str
    stats: dict
    duplicates: list[dict] = field(default_factory=list)
    terms: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------- 文本归一化 ----------------


def normalize_text(text: str) -> str:
    """去掉空白与标点，用于相似度比较。"""
    return re.sub(r"[\s\W_]+", "", text.lower())


def _signature(normalized: str) -> str:
    return normalized[:16]


# ---------------- 章节构建 ----------------


def _resolve_chapter_title(doc: ParsedDocument, provided: str | None) -> tuple[str, bool]:
    """返回（章节标题, 是否消耗掉文稿的第一个标题）。"""
    headings = [n for n in doc.nodes if n.level >= 1]
    title = (provided or "").strip()
    if not title:
        title = headings[0].title if headings else Path(doc.filename).stem
    consume_first = bool(headings) and headings[0].title == title
    return title, consume_first


def _build_nodes(
    documents: list[ParsedDocument],
    chapter_titles: list[str] | None,
    warnings: list[str],
) -> list[Node]:
    nodes: list[Node] = []

    for index, doc in enumerate(documents):
        provided = chapter_titles[index] if chapter_titles and index < len(chapter_titles) else None
        title, consume_first = _resolve_chapter_title(doc, provided)
        label = doc.author or Path(doc.filename).stem

        if doc.heading_count == 0:
            warnings.append(f"《{doc.filename}》没有识别到标题，已整篇作为章节「{title}」的正文")

        chapter = Node(level=1, title=title, source=doc.filename)
        nodes.append(chapter)

        # 文稿开头无归属的正文 → 章节引言
        if doc.nodes and doc.nodes[0].level == 0:
            chapter.blocks.extend(doc.nodes[0].blocks)

        headings = [n for n in doc.nodes if n.level >= 1]
        if not headings:
            continue

        base = min(n.level for n in headings)
        # 首标题被当作章节名时，它的下一级应落在第 2 层；
        # 首标题未被消耗时，首标题本身落在第 2 层。两者偏移量不同。
        offset = 1 if consume_first else 2
        for position, node in enumerate(headings):
            if position == 0 and consume_first:
                chapter.blocks.extend(node.blocks)
                continue
            new_level = min(node.level - base + offset, 5)
            nodes.append(
                Node(
                    level=new_level,
                    title=node.title,
                    blocks=list(node.blocks),
                    source=f"{label} · {doc.filename}",
                )
            )

    return nodes


def _assign_numbers(nodes: list[Node]) -> None:
    """按层级生成 1 / 1.1 / 1.1.1 形式的编号。

    同时把"跨级"的节点拉平一级，避免出现 1.0.1 这种读起来很怪的编号。
    """
    counters = [0] * 6
    previous = 0
    for node in nodes:
        level = max(1, min(node.level, 5))
        if previous and level > previous + 1:
            level = previous + 1
        node.level = level
        counters[level - 1] += 1
        for deeper in range(level, 6):
            counters[deeper] = 0
        node.number = ".".join(str(c) for c in counters[:level])
        previous = level


# ---------------- 重复段落 ----------------


def find_duplicates(documents: list[ParsedDocument], threshold: float = 0.86) -> list[dict]:
    """跨文稿的重复 / 高度相似段落。"""
    buckets: dict[str, list[dict]] = {}

    for doc in documents:
        for node in doc.nodes:
            section = node.title or "（前言）"
            for block in node.blocks:
                if block.kind != "paragraph":
                    continue
                normalized = normalize_text(block.text)
                if len(normalized) < MIN_PARAGRAPH_LEN:
                    continue
                buckets.setdefault(_signature(normalized), []).append(
                    {
                        "text": block.text,
                        "normalized": normalized,
                        "source": doc.filename,
                        "author": doc.author,
                        "section": section,
                    }
                )

    groups: list[dict] = []
    for items in buckets.values():
        used: set[int] = set()
        for i in range(len(items)):
            if i in used:
                continue
            cluster = [i]
            for j in range(i + 1, len(items)):
                if j in used:
                    continue
                ratio = SequenceMatcher(None, items[i]["normalized"], items[j]["normalized"]).ratio()
                if ratio >= threshold:
                    cluster.append(j)
                    used.add(j)
            if len(cluster) < 2:
                continue
            used.add(i)
            sources = {items[k]["source"] for k in cluster}
            if len(sources) < 2:
                # 同一份文稿内部的重复也提示，但排在后面
                pass
            representative = max((items[k] for k in cluster), key=lambda x: len(x["text"]))
            groups.append(
                {
                    "text": representative["text"],
                    "length": len(representative["text"]),
                    "occurrences": [
                        {
                            "source": items[k]["source"],
                            "author": items[k]["author"],
                            "section": items[k]["section"],
                        }
                        for k in cluster
                    ],
                    "cross_document": len(sources) > 1,
                }
            )

    groups.sort(key=lambda g: (not g["cross_document"], -g["length"]))
    return groups[:MAX_DUPLICATE_GROUPS]


# ---------------- 术语不一致 ----------------

_CJK_RUN = re.compile(r"[\u4e00-\u9fa5]+")
MAX_TERM_LEN = 8


def _collect_term_stats(documents: list[ParsedDocument]) -> dict[str, dict]:
    """收集候选 n-gram 的统计信息。

    除了出现次数，还记录每个 n-gram 的**左邻字**与**右邻字**集合——
    真正成词的术语上下文丰富，从长词里切出来的碎片上下文单一，
    这是区分二者的关键信号。
    """
    stats: dict[str, dict] = {}
    for doc in documents:
        for node in doc.nodes:
            for block in node.blocks:
                for match in _CJK_RUN.finditer(block.text):
                    run = match.group()
                    length = len(run)
                    for size in range(MIN_TERM_LEN, min(length, MAX_TERM_LEN) + 1):
                        for start in range(0, length - size + 1):
                            term = run[start : start + size]
                            entry = stats.setdefault(
                                term, {"docs": {}, "left": set(), "right": set()}
                            )
                            entry["docs"][doc.filename] = entry["docs"].get(doc.filename, 0) + 1
                            entry["left"].add(run[start - 1] if start > 0 else "")
                            entry["right"].add(run[start + size] if start + size < length else "")
    return stats


def find_term_conflicts(documents: list[ParsedDocument]) -> list[dict]:
    """找出"短形式 / 长形式"并存的疑似术语不一致。

    判定条件（缺一不可）：
    1. 短形式是长形式的子串，且长度差不超过 3 个字（差异是修饰词）；
    2. **短形式出现过"不被长形式包含"的独立用法**（出现次数多于长形式）——
       否则像"标注成"这种，每次出现都只是"标注成本"的一部分，是切词伪影而非术语；
    3. 短形式与长形式在不同文稿中分布**不同**——
       若用到长形式的文稿也都用了短形式，那只是正常的长短并用，不算不一致。
    """
    if not documents:
        return []
    stats = _collect_term_stats(documents)

    def docs_of(counts: dict[str, int]) -> set[str]:
        return {name for name, count in counts.items() if count > 0}

    # 建立"短形式 → [(长形式, 关系)]"索引。
    # 只承认"已知修饰词"（类/新/多… 前缀，模型/方法/系统… 后缀）造成的差异，
    # 复杂度 O(词表 × 2)，不随文档增长而爆炸。
    index: dict[str, list[tuple[str, str]]] = {}
    for long in stats:
        length = len(long)
        for extra in (1, 2):
            if length - extra < MIN_TERM_LEN:
                continue
            prefix_modifier = long[:extra]
            suffix_modifier = long[length - extra :]
            prefix_form = long[extra:]  # 长形式 = 修饰词 + 短形式
            suffix_form = long[: length - extra]  # 长形式 = 短形式 + 修饰词
            if prefix_modifier in _QUALIFIER_PREFIXES and prefix_form in stats:
                index.setdefault(prefix_form, []).append((long, "prefix"))
            if suffix_modifier in _QUALIFIER_SUFFIXES and suffix_form in stats:
                index.setdefault(suffix_form, []).append((long, "suffix"))

    scored: list[dict] = []
    for short, long_candidates in index.items():
        if short[0] in _FUNCTION_CHARS or short[-1] in _FUNCTION_CHARS:
            continue  # 首尾是虚词，多半是从句子里切出来的碎片
        short_entry = stats[short]
        short_total = sum(short_entry["docs"].values())
        if short_total < 2:
            continue  # 短形式本身要是个像样的词，至少出现两次
        docs_short = docs_of(short_entry["docs"])

        best: dict | None = None
        for long, relation in long_candidates:
            long_entry = stats[long]
            long_total = sum(long_entry["docs"].values())
            if short_total <= long_total:
                continue  # 短形式没有独立用法，属于切词伪影
            docs_long = docs_of(long_entry["docs"])
            if docs_short == docs_long:
                continue  # 分布一致，属于正常长短并用
            # 上下文单一 = 碎片；只有上下文足够丰富才可能是真术语
            contexts = short_entry["left"] if relation == "prefix" else short_entry["right"]
            if len(contexts) < 2:
                continue
            item = {
                "short": short,
                "long": long,
                "short_docs": sorted(docs_short),
                "long_docs": sorted(docs_long),
                "total": short_total + long_total,
                "spread": len(docs_short ^ docs_long),
            }
            if best is None or (item["spread"], item["total"]) > (best["spread"], best["total"]):
                best = item
        if best is not None:
            scored.append(best)

    # 差异越大越可疑；其次看出现频次
    scored.sort(key=lambda c: (-c["spread"], -c["total"], c["short"]))
    result: list[dict] = []
    used_short: set[str] = set()
    for item in scored:
        if item["short"] in used_short:
            continue
        used_short.add(item["short"])
        result.append(item)
        if len(result) >= MAX_TERM_CONFLICTS:
            break
    return result


# ---------------- Markdown 生成 ----------------


def to_markdown(nodes: list[Node], title: str, document_count: int) -> str:
    lines: list[str] = [f"# {title}", ""]
    lines.append(f"> 由 {document_count} 份文稿合并生成，标题层级与编号已统一。")
    lines.append("")

    for node in nodes:
        hashes = "#" * min(node.level + 1, 6)
        heading = f"{node.number} {node.title}".strip()
        lines.append(f"{hashes} {heading}")
        lines.append("")
        for block in node.blocks:
            if block.kind == "list":
                lines.append(f"- {block.text}")
            elif block.kind == "quote":
                lines.append(f"> {block.text}")
            elif block.kind == "table":
                lines.append(block.text)
            else:
                lines.append(block.text)
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ---------------- 主流程 ----------------


def merge_documents(
    documents: list[ParsedDocument],
    chapter_titles: list[str] | None = None,
    *,
    title: str = "合并文稿",
) -> MergeOutcome:
    if not documents:
        raise ValueError("至少需要一份文稿")

    warnings: list[str] = []
    nodes = _build_nodes(documents, chapter_titles, warnings)
    _assign_numbers(nodes)

    duplicates = find_duplicates(documents)
    terms = find_term_conflicts(documents)

    cross_duplicates = sum(1 for d in duplicates if d["cross_document"])
    if cross_duplicates:
        warnings.append(f"发现 {cross_duplicates} 处跨文稿重复内容，建议核对后合并或删除")

    markdown = to_markdown(nodes, title, len(documents))

    stats = {
        "documents": len(documents),
        "sections": sum(1 for n in nodes if n.level >= 1),
        "sub_sections": sum(1 for n in nodes if n.level >= 2),
        "characters": sum(n.char_count for n in nodes),
        "duplicates": len(duplicates),
        "cross_duplicates": cross_duplicates,
        "term_conflicts": len(terms),
        "per_document": [
            {
                "filename": doc.filename,
                "author": doc.author,
                "headings": doc.heading_count,
                "characters": doc.char_count,
            }
            for doc in documents
        ],
    }

    return MergeOutcome(
        nodes=nodes,
        markdown=markdown,
        stats=stats,
        duplicates=duplicates,
        terms=terms,
        warnings=warnings,
    )
