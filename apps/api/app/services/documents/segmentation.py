"""文档分段、本地文体特征与版式事实提取。

设计思路：AI 负责"判断"，本地统计负责"提供可量化依据"。
把特征算好再交给模型，比直接丢全文更稳、更省 token，结论也更容易解释和复核。
"""

import re
from dataclasses import dataclass, field

from app.services.documents.ir import ParsedDocument

MIN_UNIT_CHARS = 20
MAX_UNITS = 40

_SENTENCE_SPLIT = re.compile(r"[。！？；!?;]")
_ENGLISH_WORD = re.compile(r"[A-Za-z]{2,}")
_DIGITS = re.compile(r"[0-9]+")

_FIRST_PERSON = ("我们", "本文", "笔者", "本人", "咱们")
_PASSIVE = ("被", "由", "受到", "得以")
_CONNECTIVES = (
    "因此", "所以", "然而", "但是", "并且", "此外", "首先", "其次",
    "最后", "综上", "总之", "同时", "另外", "进而", "从而",
)
_COLLOQUIAL = ("挺", "特别", "其实", "的话", "吧", "呢", "嘛", "搞", "弄")


@dataclass
class Segment:
    """一个可独立分析的段落单元。"""

    id: int
    section: str
    text: str
    features: dict = field(default_factory=dict)

    @property
    def chars(self) -> int:
        return len(self.text)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "section": self.section,
            "text": self.text,
            "chars": self.chars,
            "features": self.features,
        }


def extract_style_features(text: str) -> dict:
    """提取可量化的文体特征。"""
    sentences = [s for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    sentence_count = max(1, len(sentences))
    chars = len(text)
    return {
        "chars": chars,
        "sentences": len(sentences),
        "avg_sentence": round(chars / sentence_count, 1),
        "first_person": sum(text.count(word) for word in _FIRST_PERSON),
        "passive": sum(text.count(word) for word in _PASSIVE),
        "connectives": sum(text.count(word) for word in _CONNECTIVES),
        "english_terms": len(_ENGLISH_WORD.findall(text)),
        "numbers": len(_DIGITS.findall(text)),
        "colloquial": sum(text.count(word) for word in _COLLOQUIAL),
        "semicolon": text.count("；") + text.count(";"),
        "dash": text.count("——") + text.count("—"),
        "exclaim": text.count("！") + text.count("!"),
    }


def segment_document(doc: ParsedDocument, min_chars: int = MIN_UNIT_CHARS) -> list[Segment]:
    """把文档切成段落级分析单元（过短的段落跳过）。"""
    segments: list[Segment] = []
    next_id = 1
    for node in doc.nodes:
        section = node.title or "（前言）"
        for block in node.blocks:
            text = block.text.strip()
            if len(text) < min_chars:
                continue
            segments.append(
                Segment(
                    id=next_id,
                    section=section,
                    text=text,
                    features=extract_style_features(text),
                )
            )
            next_id += 1
    return segments


def sample_segments(segments: list[Segment], limit: int = MAX_UNITS) -> list[Segment]:
    """等距抽样，保证覆盖全文而不是只看开头。"""
    if len(segments) <= limit:
        return list(segments)
    step = len(segments) / limit
    return [segments[min(int(index * step), len(segments) - 1)] for index in range(limit)]


# ---------------- 版式事实 ----------------

_NUMBER_STYLES: list[tuple[str, re.Pattern[str] | None]] = [
    ("chinese_chapter", re.compile(r"^第[一二三四五六七八九十百零]+[章篇节]")),
    ("chinese_enum", re.compile(r"^[一二三四五六七八九十]+[、.．]")),
    ("chinese_paren", re.compile(r"^（[一二三四五六七八九十]+）")),
    ("arabic_multi", re.compile(r"^\d+\.\d+")),
    ("arabic_single", re.compile(r"^\d+[、.．]")),
]

NUMBER_STYLE_LABEL = {
    "chinese_chapter": "「第X章」式",
    "chinese_enum": "「一、」式",
    "chinese_paren": "「（一）」式",
    "arabic_multi": "「1.1」式",
    "arabic_single": "「1.」式",
    "none": "无编号",
}


def detect_number_style(raw_title: str) -> str:
    """判断标题用的是哪种编号风格（「一、」/「1.」/「1.1」…），无编号时返回 "none"。"""
    for name, pattern in _NUMBER_STYLES:
        if pattern and pattern.match(raw_title.strip()):
            return name
    return "none"


def extract_layout_facts(doc: ParsedDocument) -> dict:
    """提取版式相关的事实（不做判断，判断交给 AI）。"""
    headings = [n for n in doc.nodes if n.level >= 1]
    levels: dict[int, dict] = {}
    for node in headings:
        info = levels.setdefault(node.level, {"count": 0, "styles": {}, "samples": []})
        info["count"] += 1
        style = detect_number_style(node.raw_title or node.title)
        info["styles"][style] = info["styles"].get(style, 0) + 1
        if len(info["samples"]) < 3:
            info["samples"].append(node.raw_title or node.title)

    paragraphs = [b.text for n in doc.nodes for b in n.blocks if b.kind == "paragraph"]
    lengths = [len(p) for p in paragraphs] or [0]

    # 标题层级是否跳跃（如一级标题下直接出现三级标题）
    sequence = [n.level for n in headings]
    skips = [
        {"from": sequence[i], "to": sequence[i + 1]}
        for i in range(len(sequence) - 1)
        if sequence[i + 1] > sequence[i] + 1
    ]

    return {
        "headings": len(headings),
        "max_level": max((n.level for n in headings), default=0),
        "levels": [
            {
                "level": level,
                "count": info["count"],
                "styles": info["styles"],
                "samples": info["samples"],
            }
            for level, info in sorted(levels.items())
        ],
        "level_skips": skips,
        "paragraphs": len(paragraphs),
        "avg_paragraph": round(sum(lengths) / len(lengths), 1),
        "min_paragraph": min(lengths),
        "max_paragraph": max(lengths),
        "lists": sum(1 for n in doc.nodes for b in n.blocks if b.kind == "list"),
        "tables": sum(1 for n in doc.nodes for b in n.blocks if b.kind == "table"),
        "quotes": sum(1 for n in doc.nodes for b in n.blocks if b.kind == "quote"),
        "has_leading_text": bool(doc.nodes and doc.nodes[0].level == 0 and doc.nodes[0].blocks),
    }


def describe_layout_facts(facts: dict) -> str:
    """把版式事实转成给模型看的紧凑文本。"""
    lines = [
        f"标题总数：{facts['headings']}，最大层级：{facts['max_level']}",
        f"段落数：{facts['paragraphs']}，平均段长：{facts['avg_paragraph']} 字"
        f"（最短 {facts['min_paragraph']}，最长 {facts['max_paragraph']}）",
        f"列表项：{facts['lists']}，表格：{facts['tables']}，引用块：{facts['quotes']}",
        f"正文前有无标题的导语：{'有' if facts['has_leading_text'] else '无'}",
    ]
    for level in facts["levels"]:
        styles = "、".join(
            f"{NUMBER_STYLE_LABEL.get(key, key)}×{value}"
            for key, value in level["styles"].items()
        )
        samples = " / ".join(level["samples"])
        lines.append(
            f"第 {level['level']} 级标题：{level['count']} 个，编号样式 {styles}，"
            f"样例：{samples}"
        )
    if facts["level_skips"]:
        jumps = "、".join(f"{item['from']}→{item['to']}" for item in facts["level_skips"])
        lines.append(f"存在标题层级跳跃：{jumps}")
    return "\n".join(lines)
