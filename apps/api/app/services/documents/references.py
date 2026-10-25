"""参考文献识别与 AI 规范化（GB/T 7714-2015）。

流程：定位「参考文献」标题 → 切出条目 → 交给模型逐条规范化 → 回写整篇 Markdown。
模型不允许编造缺失信息，缺什么就在 note 里说明。
"""

import re
from typing import Any

from app.services.llm import ChatMessage, LLMProvider

_HEADING = re.compile(
    r"^\s*#{0,6}\s*(参考文献|参考资料|引用文献|references?)\s*$", re.IGNORECASE
)
_ENTRY_PREFIX = re.compile(r"^\s*(?:\[\d+\]|\d+[.、])\s*")
_HEADING_MARK = re.compile(r"^\s*(#{1,6})\s+(.*)$")

REFERENCE_TYPES = ["journal", "book", "conference", "thesis", "web", "other"]

REFERENCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "entries": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "type": {"type": "string", "enum": REFERENCE_TYPES},
                    "formatted": {"type": "string"},
                    "note": {"type": "string"},
                },
                "required": ["index", "type", "formatted"],
            },
        }
    },
    "required": ["entries"],
}

REFERENCE_PROMPT = """你是参考文献编辑。请把给定条目逐条规范成 GB/T 7714-2015 格式。

格式要点：
- 期刊：作者. 题名[J]. 刊名, 年, 卷(期): 起止页码.
- 专著：作者. 书名[M]. 版本. 出版地: 出版者, 年.
- 会议论文：作者. 题名[C]//论文集名. 出版地: 出版者, 年: 页码.
- 学位论文：作者. 题名[D]. 保存地: 保存者, 年.
- 电子资源：作者. 题名[EB/OL]. (发布日期)[引用日期]. URL.
- 作者超过 3 个只列前 3 个，其后加 ", 等."（英文用 ", et al."）。
- 英文作者姓前名后，名用缩写；中文作者姓名全写。

铁律：
1. 不要编造任何缺失信息（卷期、页码、出版地等缺就缺，保持条目结构完整但留空）；
2. 若某条信息明显缺失，在 note 里用一句话说明缺什么；
3. index 必须原样返回，用来对应输入条目；
4. formatted 里不要带序号 [1]，序号由系统统一加。

只输出 JSON。"""


def find_reference_section(markdown: str) -> dict | None:
    """定位参考文献段，返回起止行与条目。"""
    lines = markdown.splitlines()
    heading_index = -1
    heading_level = 0
    for index, line in enumerate(lines):
        if _HEADING.match(line):
            heading_index = index
            match = _HEADING_MARK.match(line)
            heading_level = len(match.group(1)) if match else 0
            break
    if heading_index < 0:
        return None

    end_index = len(lines)
    if heading_level:
        for index in range(heading_index + 1, len(lines)):
            match = _HEADING_MARK.match(lines[index])
            if match and len(match.group(1)) <= heading_level:
                end_index = index
                break

    entries: list[str] = []
    for line in lines[heading_index + 1 : end_index]:
        text = _ENTRY_PREFIX.sub("", line.strip())
        if text:
            entries.append(text)

    return {
        "heading_index": heading_index,
        "heading_line": lines[heading_index],
        "end_index": end_index,
        "entries": entries,
    }


async def normalize_entries(entries: list[str], provider: LLMProvider) -> list[dict]:
    """把用户粘贴的零散参考文献规范成 GB/T 7714 格式。

    只做格式归一，不增删条目：模型回填数量少于输入时，缺的条目原样保留，
    宁可格式没改好，也不能把作者提供的文献弄丢。
    """
    if not entries:
        return []
    body = "\n".join(f"[{index}] {text}" for index, text in enumerate(entries, start=1))
    messages = [
        ChatMessage("system", REFERENCE_PROMPT),
        ChatMessage("user", f"共 {len(entries)} 条：\n\n{body}"),
    ]
    result = await provider.structured(messages, REFERENCE_SCHEMA, max_tokens=6000)

    by_index: dict[int, dict] = {}
    for item in result.get("entries") or []:
        try:
            index = int(item.get("index"))
        except (TypeError, ValueError):
            continue
        if not 1 <= index <= len(entries) or index in by_index:
            continue
        formatted = str(item.get("formatted") or "").strip()
        if not formatted:
            continue
        by_index[index] = {
            "index": index,
            "original": entries[index - 1],
            "formatted": formatted,
            "type": str(item.get("type") or "other"),
            "note": str(item.get("note") or "")[:200],
        }

    # 模型漏掉的条目原样保留，避免丢文献
    for index, text in enumerate(entries, start=1):
        if index not in by_index:
            by_index[index] = {
                "index": index,
                "original": text,
                "formatted": text,
                "type": "other",
                "note": "模型未返回该条，已保留原文",
            }
    return [by_index[index] for index in sorted(by_index)]


def rewrite_section(markdown: str, section: dict, normalized: list[dict]) -> str:
    """把规范化后的条目写回 Markdown。"""
    lines = markdown.splitlines()
    head = lines[: section["heading_index"] + 1]
    tail = lines[section["end_index"] :]
    entries = [f"[{item['index']}] {item['formatted']}" for item in normalized]
    merged = [*head, "", *entries, "", *tail]
    return "\n".join(merged).replace("\n\n\n", "\n\n")
