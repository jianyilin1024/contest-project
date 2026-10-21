"""过渡段落生成（F3）：识别需要衔接的断层，并给出多个备选。

两段式设计：
1. 本地先找出"章节衔接点"（上一节最后一个正文块 → 下一节标题+首段），成本为零；
2. 再把这些衔接点交给模型判断「这里是否真的需要过渡」，需要才生成 2–3 个风格不同的备选。

这样既不会漏检结构性断层，也不会对每一段都盲目调模型。
"""

import logging
import re
from dataclasses import dataclass
from typing import Any

from app.services.documents.deai import (
    DEAI_PROMPT,
    DEAI_SCHEMA,
    build_targets,
    conservation_check,
)
from app.services.documents.deai import (
    analyze as deai_analyze,
)
from app.services.llm import ChatMessage, LLMError, LLMProvider

logger = logging.getLogger(__name__)

MAX_BOUNDARIES = 10
CLIP_BEFORE = 160
CLIP_AFTER = 160

_MD_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_MD_LIST = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_MD_QUOTE = re.compile(r"^\s*>\s?")
_MD_TABLE = re.compile(r"^\s*\|.*\|\s*$")
_LEADING_NUMBER = re.compile(r"^\s*\d+(?:\.\d+)*[、.．]?\s+")


@dataclass
class DocBlock:
    id: int
    kind: str  # heading | paragraph | list | quote | table
    level: int
    text: str

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "level": self.level, "text": self.text}


def build_blocks(markdown: str) -> list[DocBlock]:
    """把 Markdown 拆成带稳定 id 的顺序块，供前端渲染与插入定位使用。"""
    blocks: list[DocBlock] = []
    next_id = 1
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        heading = _MD_HEADING.match(line)
        if heading:
            blocks.append(DocBlock(next_id, "heading", len(heading.group(1)), heading.group(2).strip()))
        elif _MD_TABLE.match(line):
            if line.strip().startswith("|---") or re.match(r"^\|[:\- |]+\|$", line.strip()):
                continue
            blocks.append(DocBlock(next_id, "table", 0, line.strip()))
        elif _MD_QUOTE.match(line):
            blocks.append(DocBlock(next_id, "quote", 0, _MD_QUOTE.sub("", line).strip()))
        elif _MD_LIST.match(line):
            blocks.append(DocBlock(next_id, "list", 0, _MD_LIST.sub("", line).strip()))
        else:
            blocks.append(DocBlock(next_id, "paragraph", 0, line.strip()))
        next_id += 1
    return blocks


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def find_boundaries(blocks: list[DocBlock]) -> list[dict]:
    """找出章节衔接点：每个标题之前的内容断层。"""
    boundaries: list[dict] = []
    section_title = "（前言）"
    last_content: DocBlock | None = None

    for index, block in enumerate(blocks):
        if block.kind == "heading":
            # 标题前若已有正文，说明这里是一个章节断层
            if last_content is not None and index > 0:
                following = blocks[index + 1] if index + 1 < len(blocks) else None
                boundaries.append(
                    {
                        "after_block_id": last_content.id,
                        "before_block_id": block.id,
                        "section_from": section_title,
                        "section_to": _LEADING_NUMBER.sub("", block.text).strip(),
                        "context_before": _clip(last_content.text, CLIP_BEFORE),
                        "context_after": _clip(
                            (following.text if following and following.kind != "heading" else ""),
                            CLIP_AFTER,
                        ),
                        "level": block.level,
                    }
                )
            section_title = _LEADING_NUMBER.sub("", block.text).strip()
            last_content = None
            continue
        last_content = block

    # 层级越浅（章）越重要，优先保留
    boundaries.sort(key=lambda item: (item["level"], item["after_block_id"]))
    selected = boundaries[:MAX_BOUNDARIES]
    selected.sort(key=lambda item: item["after_block_id"])
    for index, item in enumerate(selected, start=1):
        item["id"] = f"b{index}"
    return selected


TRANSITION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "boundaries": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "needs": {"type": "boolean"},
                    "reason": {"type": "string"},
                    "confidence": {"type": "number"},
                    "options": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "text": {"type": "string"},
                            },
                            "required": ["label", "text"],
                        },
                    },
                },
                "required": ["id", "needs", "reason", "confidence", "options"],
            },
        }
    },
    "required": ["boundaries"],
}

TRANSITION_PROMPT = """你是学术写作编辑，负责在两节之间补写过渡段。

下面给出若干个"章节衔接点"，每个包含：上一节名称、上一节最后一段、下一节名称、下一节开头的段落。

对每个衔接点判断：

1. **needs**：这里是否真的需要一段过渡文字？
   - 如果上一段结尾已经有明确的承接句、或下一节与上节属于同一条论证线且衔接自然，返回 false；
   - 如果两节话题跳跃、缺少连接，返回 true。
2. **reason**：一句话说明判断依据（要具体，不要空泛）。
3. **confidence**：0–1。
4. **options**：needs 为 true 时给出 **2–3 个风格不同**的备选，每个不超过 120 字：
   - 「简洁承接」：一两句话，点明两节关系即可；
   - 「递进强调」：强调第二节是对第一节的深化或补充；
   - 「转折说明」：点出研究视角的转换或方法的差异。
   needs 为 false 时 options 返回空数组。

写作要求（非常重要）：
- 过渡段的任务是"架桥"，不是"预告"：承接上文提出的问题或结论，点明两节的关系即可；
- **严禁复述下一节的具体做法、数据或结论**。例如下一节开头写了"采用元学习框架"，
  过渡段就不能再写一次"采用元学习框架"——这是最常见的错误；
- 不要用"本节将……""下面我们……"这类空话开头；
- 中文 40–80 字，学术书面语，与原文风格一致。

铁律：
- 只能基于给定内容，**不得引入新的数据、结论或文献**；
- 若无法在不重复下一节的前提下写出有意义的过渡，就把 needs 判为 false。

只输出 JSON。"""


def longest_common_substring(a: str, b: str) -> int:
    """最长公共子串长度，用于检测过渡段是否复述了下一节内容。"""
    if not a or not b:
        return 0
    previous = [0] * (len(b) + 1)
    best = 0
    for i in range(1, len(a) + 1):
        current = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                current[j] = previous[j - 1] + 1
                if current[j] > best:
                    best = current[j]
        previous = current
    return best


def _flag_duplication(options: list[dict], context_after: str) -> list[dict]:
    """给与下一节高度重合的备选打标记。"""
    for option in options:
        overlap = longest_common_substring(option["text"], context_after or "")
        option["overlap"] = overlap
        option["duplicate"] = overlap >= 12
    return options


def _boundary_brief(boundary: dict) -> str:
    after = boundary["context_after"] or "（下一节没有正文段落）"
    return (
        f"[{boundary['id']}] 从「{boundary['section_from']}」→ 到「{boundary['section_to']}」\n"
        f"  上一节结尾：{boundary['context_before']}\n"
        f"  下一节开头：{after}"
    )


async def analyze_transitions(
    boundaries: list[dict], provider: LLMProvider, title: str
) -> list[dict]:
    """让模型判断每个衔接点并生成备选。"""
    if not boundaries:
        return []

    body = "\n\n".join(_boundary_brief(item) for item in boundaries)
    messages = [
        ChatMessage("system", TRANSITION_PROMPT),
        ChatMessage("user", f"文档标题：{title}\n共 {len(boundaries)} 个衔接点：\n\n{body}"),
    ]
    result = await provider.structured(messages, TRANSITION_SCHEMA, max_tokens=6000)

    judged: dict[str, dict] = {}
    for item in result.get("boundaries") or []:
        bid = str(item.get("id") or "").strip()
        if not bid:
            continue
        try:
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0.5))))
        except (TypeError, ValueError):
            confidence = 0.5
        options = []
        for index, option in enumerate(item.get("options") or [], start=1):
            text = str(option.get("text") or "").strip()
            if not text:
                continue
            options.append(
                {
                    "id": f"{bid}-o{index}",
                    "label": str(option.get("label") or f"备选 {index}")[:20],
                    "text": text[:400],
                }
            )
        judged[bid] = {
            "needs": bool(item.get("needs")),
            "reason": str(item.get("reason") or "")[:300],
            "confidence": round(confidence, 2),
            "options": options[:3],
        }

    merged: list[dict] = []
    for boundary in boundaries:
        verdict = judged.get(boundary["id"])
        options = _flag_duplication(
            list(verdict["options"]) if verdict else [], boundary.get("context_after", "")
        )
        merged.append(
            {
                **boundary,
                "needs": verdict["needs"] if verdict else False,
                "reason": verdict["reason"] if verdict else "模型未返回该衔接点的判断",
                "confidence": verdict["confidence"] if verdict else 0.0,
                "options": options,
            }
        )
    return merged


async def apply_deai(boundaries: list[dict], provider: LLMProvider) -> None:
    """对生成的备选做去 AI 味处理（原地修改 options）。

    流程：体检 → 一次性批量改写命中的备选 → 信息守恒校验 → 重新体检；
    任何一步不通过就保留原文，绝不为了"去味"牺牲事实。
    """
    targets: list[dict] = []
    for boundary in boundaries:
        for option in boundary["options"]:
            report = deai_analyze(option["text"])
            option["deai"] = {
                "before_score": report.score,
                "after_score": report.score,
                "issues": [issue.label for issue in report.issues],
                "applied": False,
                "original": None,
            }
            if report.issues:
                targets.append(
                    {
                        "id": option["id"],
                        "text": option["text"],
                        "issues": [issue.to_dict() for issue in report.issues],
                    }
                )

    if not targets:
        return

    messages = [
        ChatMessage("system", DEAI_PROMPT),
        ChatMessage("user", f"共 {len(targets)} 段需要处理：\n\n{build_targets(targets)}"),
    ]
    try:
        result = await provider.structured(messages, DEAI_SCHEMA, max_tokens=4000)
    except LLMError as exc:
        logger.warning("去味改写失败，保留原文: %s", exc)
        return

    rewritten = {
        str(item.get("id")): str(item.get("text") or "").strip()
        for item in (result.get("rewrites") or [])
    }

    for boundary in boundaries:
        for option in boundary["options"]:
            info = option.get("deai")
            if not info or not info["issues"]:
                continue
            candidate = rewritten.get(option["id"], "")
            if not candidate:
                continue
            ok, problems = conservation_check(option["text"], candidate)
            if not ok:
                info["rejected"] = problems
                continue
            after = deai_analyze(candidate)
            if after.score <= info["before_score"]:
                info["rejected"] = ["改写后仍存在同类痕迹，已保留原文"]
                continue
            info["original"] = option["text"]
            info["after_score"] = after.score
            info["applied"] = True
            info["remaining"] = [issue.label for issue in after.issues]
            option["text"] = candidate


def assemble_markdown(blocks: list[dict], insertions: list[dict]) -> str:
    """把选用后的块重新拼成 Markdown。

    insertions: [{"after_block_id": 12, "text": "过渡段"}]
    """
    by_after: dict[int, list[str]] = {}
    for item in insertions:
        try:
            after_id = int(item.get("after_block_id"))
        except (TypeError, ValueError):
            continue
        text = str(item.get("text") or "").strip()
        if text:
            by_after.setdefault(after_id, []).append(text)

    lines: list[str] = []
    for block in blocks:
        kind = block.get("kind")
        text = str(block.get("text") or "")
        if kind == "heading":
            lines.append("#" * max(1, min(int(block.get("level") or 1), 6)) + " " + text)
        elif kind == "list":
            lines.append(f"- {text}")
        elif kind == "quote":
            lines.append(f"> {text}")
        else:
            lines.append(text)

        for inserted in by_after.get(int(block.get("id")), []):
            lines.append(inserted)
    return "\n\n".join(lines).strip() + "\n"


def boundary_summary(boundaries: list[dict]) -> dict:
    needed = [item for item in boundaries if item["needs"] and item["options"]]
    return {
        "candidates": len(boundaries),
        "needed": len(needed),
        "skipped": len(boundaries) - len(needed),
    }
