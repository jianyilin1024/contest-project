"""AI 文档分析：文风异质性判定、归并建议、版式识别、归并稿生成。

所有判断都要求模型给出**依据**（confidence + reason），
并在提示词里明确"不要臆造"，避免把不确定的猜测说成结论。
"""

import asyncio
import logging
from typing import Any

from app.services.documents.ir import ParsedDocument
from app.services.documents.segmentation import (
    Segment,
    describe_layout_facts,
    extract_layout_facts,
)
from app.services.llm import ChatMessage, LLMError, LLMProvider

logger = logging.getLogger(__name__)

CLIP = 220
UNIFY_BATCH = 5
UNIFY_CONCURRENCY = 4
ANALYSIS_MAX_TOKENS = 6000
UNIFY_MAX_TOKENS = 6000


def _clip(text: str, limit: int = CLIP) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _segment_block(segment: Segment) -> str:
    f = segment.features
    return (
        f"[#{segment.id}] 章节：{segment.section}｜"
        f"字数 {f['chars']}，句数 {f['sentences']}，平均句长 {f['avg_sentence']}，"
        f"第一人称 {f['first_person']}，被动 {f['passive']}，连接词 {f['connectives']}，"
        f"英文词 {f['english_terms']}，数字 {f['numbers']}，口语词 {f['colloquial']}，"
        f"分号 {f['semicolon']}，破折号 {f['dash']}\n"
        f"正文：{_clip(segment.text)}"
    )


# ---------------- 1. 文风异质性判定 ----------------

AUTHORSHIP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "heterogeneity": {"type": "string", "enum": ["low", "medium", "high"]},
        "conclusion": {"type": "string"},
        "groups": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                    "features": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "label", "features"],
            },
        },
        "assignments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "unit_id": {"type": "integer"},
                    "group_id": {"type": "string"},
                    "confidence": {"type": "number"},
                    "reason": {"type": "string"},
                },
                "required": ["unit_id", "group_id", "confidence", "reason"],
            },
        },
    },
    "required": ["heterogeneity", "conclusion", "groups", "assignments"],
}

AUTHORSHIP_PROMPT = """你是文体分析专家。下面是一篇文档切分出的段落单元，每个单元带编号、所在章节和本地统计特征。

请判断这些段落在写作风格上可以聚成几类，每类对应一位**可能的**作者。

判断维度：
- 句长与句子结构（长句/短句、复句比例）
- 人称习惯（本文/我们/笔者/无主语）
- 连接词与过渡习惯
- 口语化程度与用词正式度
- 术语偏好（同一概念的不同叫法）
- 标点习惯（分号、破折号、顿号）
- 数字与英文的使用密度

要求：
1. 分组数 1–5。若风格高度一致，只输出 1 组，heterogeneity 填 low；
2. 每个单元都必须被分配到一个组；
3. confidence 表示"这个单元属于该组"的把握，取值 0–1；证据弱就给低分；
4. 每组的 features 要写**可核对的**具体特征（如"平均句长 45 字，明显长于其他组"）；
5. reason 要指出该单元的具体证据，不要空泛；
6. 这是**推测**，不要断言"一定是某人写的"。

只输出 JSON。"""


async def analyze_authorship(
    segments: list[Segment], title: str, provider: LLMProvider
) -> dict:
    """判断整篇文稿是否由多人写成，并给出可能的分组。

    可分析段落少于两段时直接返回"无法判断"——样本不足时模型给出的结论没有参考价值。
    """
    if len(segments) < 2:
        return {
            "heterogeneity": "low",
            "conclusion": "可分析段落过少，无法判断文风差异。",
            "groups": [],
            "assignments": [],
        }

    body = "\n\n".join(_segment_block(segment) for segment in segments)
    messages = [
        ChatMessage("system", AUTHORSHIP_PROMPT),
        ChatMessage(
            "user",
            f"文档标题：{title}\n共 {len(segments)} 个段落单元：\n\n{body}",
        ),
    ]
    result = await provider.structured(messages, AUTHORSHIP_SCHEMA, max_tokens=ANALYSIS_MAX_TOKENS)
    return _normalize_authorship(result, segments)


def _normalize_authorship(raw: dict, segments: list[Segment]) -> dict:
    """把模型输出对齐回真实存在的单元编号，过滤幻觉。"""
    valid_ids = {segment.id for segment in segments}
    groups = []
    group_ids: set[str] = set()
    for group in raw.get("groups") or []:
        gid = str(group.get("id") or "").strip()
        if not gid or gid in group_ids:
            continue
        group_ids.add(gid)
        groups.append(
            {
                "id": gid,
                "label": str(group.get("label") or f"风格 {gid}"),
                "features": [str(item) for item in (group.get("features") or [])][:6],
            }
        )

    assignments = []
    seen: set[int] = set()
    for item in raw.get("assignments") or []:
        try:
            unit_id = int(item.get("unit_id"))
        except (TypeError, ValueError):
            continue
        if unit_id not in valid_ids or unit_id in seen:
            continue
        gid = str(item.get("group_id") or "").strip()
        if gid not in group_ids:
            continue
        seen.add(unit_id)
        try:
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0.5))))
        except (TypeError, ValueError):
            confidence = 0.5
        assignments.append(
            {
                "unit_id": unit_id,
                "group_id": gid,
                "confidence": round(confidence, 2),
                "reason": str(item.get("reason") or "")[:300],
            }
        )

    # 模型漏掉的单元归到第一个组，并标注低置信度
    if groups:
        for segment in segments:
            if segment.id not in seen:
                assignments.append(
                    {
                        "unit_id": segment.id,
                        "group_id": groups[0]["id"],
                        "confidence": 0.3,
                        "reason": "模型未给出判定，暂归入第一组",
                    }
                )

    heterogeneity = str(raw.get("heterogeneity") or "low")
    if heterogeneity not in ("low", "medium", "high"):
        heterogeneity = "low"

    return {
        "heterogeneity": heterogeneity,
        "conclusion": str(raw.get("conclusion") or "")[:600],
        "groups": groups,
        "assignments": assignments,
    }


# ---------------- 2. 文风归并建议 ----------------

STYLE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "canonical_style": {"type": "string"},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                    "examples": {"type": "array", "items": {"type": "string"}},
                    "suggestion": {"type": "string"},
                },
                "required": ["type", "title", "detail", "suggestion"],
            },
        },
        "plan": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["canonical_style", "issues", "plan"],
}

STYLE_PROMPT = """你是学术写作编辑。下面是同一篇文档中不同文风分组的统计特征与代表性段落。

请给出**统一文风的建议**：

1. canonical_style：描述建议统一到的目标文风（句长区间、人称、语气、术语密度等），要具体可执行；
2. issues：列出需要处理的具体问题，type 用 terminology / sentence_length / person / tone / punctuation / connective / structure 之一；
   - detail 要说清"哪里不一致、差多少"，用数据说话；
   - examples 给 2–4 个原文片段（短句即可）；
   - suggestion 给出可操作的改法；
3. plan：3–6 条按顺序执行的归并步骤。

不要臆造原文没有的内容；只针对给出的材料下判断。只输出 JSON。"""


async def advise_style(
    segments: list[Segment], authorship: dict, title: str, provider: LLMProvider
) -> dict:
    """按文风分组给出统一建议。

    先按 authorship 的分组把段落聚起来，再让模型针对「组与组之间的差异」提建议。
    逐段点评只会得到一堆「这段有点口语」，无法指导整体改写。
    """
    by_group: dict[str, list[Segment]] = {}
    group_of = {item["unit_id"]: item["group_id"] for item in authorship.get("assignments", [])}
    for segment in segments:
        gid = group_of.get(segment.id)
        if gid:
            by_group.setdefault(gid, []).append(segment)

    blocks: list[str] = []
    for group in authorship.get("groups", []):
        members = by_group.get(group["id"], [])
        if not members:
            continue
        avg_len = round(sum(m.features["avg_sentence"] for m in members) / len(members), 1)
        first_person = sum(m.features["first_person"] for m in members)
        colloquial = sum(m.features["colloquial"] for m in members)
        connectives = sum(m.features["connectives"] for m in members)
        blocks.append(
            f"【分组 {group['id']}｜{group['label']}】共 {len(members)} 段\n"
            f"平均句长 {avg_len} 字，第一人称 {first_person} 次，口语词 {colloquial} 次，连接词 {connectives} 次\n"
            f"特征：{'；'.join(group['features'])}\n"
            f"代表段落：\n"
            + "\n".join(f"  - {_clip(m.text, 150)}" for m in members[:3])
        )

    messages = [
        ChatMessage("system", STYLE_PROMPT),
        ChatMessage(
            "user",
            f"文档标题：{title}\n整体判断：{authorship.get('conclusion', '')}\n\n"
            + "\n\n".join(blocks),
        ),
    ]
    return await provider.structured(messages, STYLE_SCHEMA, max_tokens=ANALYSIS_MAX_TOKENS)


# ---------------- 3. 版式识别 ----------------

LAYOUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "conventions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "aspect": {"type": "string"},
                    "observation": {"type": "string"},
                    "consistent": {"type": "boolean"},
                    "suggestion": {"type": "string"},
                },
                "required": ["aspect", "observation", "consistent", "suggestion"],
            },
        },
    },
    "required": ["summary", "conventions"],
}

LAYOUT_PROMPT = """你是文档排版审校专家。下面是从文档里**客观提取**出来的版式事实，以及开头部分原文。

请判断这份文档的版式规范，并指出不一致之处：

- aspect 用：标题层级 / 编号样式 / 段落长度 / 图表与列表 / 导语与前言 / 其他 之一；
- observation 要基于给定事实，写清"现状是什么"，必要时引用样例标题；
- consistent 表示该项是否前后一致；
- suggestion 给出具体可执行的修改建议（例如"第 2 级标题混用了「1.1」与「（一）」两种编号，建议统一为 1.1 式"）。

不要臆造事实中没有的信息。只输出 JSON。"""


async def recognize_layout(doc: ParsedDocument, title: str, provider: LLMProvider) -> dict:
    """识别文稿原有的版式约定（标题层级写法、编号风格、图表标注等）。

    先抽取结构事实再交给模型，避免模型凭空描述版式。
    """
    facts = extract_layout_facts(doc)
    opening = "\n".join(
        block.text for node in doc.nodes[:6] for block in node.blocks[:2]
    )[:900]
    messages = [
        ChatMessage("system", LAYOUT_PROMPT),
        ChatMessage(
            "user",
            f"文档标题：{title}\n\n【版式事实】\n{describe_layout_facts(facts)}\n\n"
            f"【开头原文片段】\n{opening}",
        ),
    ]
    result = await provider.structured(messages, LAYOUT_SCHEMA, max_tokens=ANALYSIS_MAX_TOKENS)
    result["facts"] = facts
    return result


# ---------------- 4. 归并稿生成 ----------------

UNIFY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "rewrites": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "unit_id": {"type": "integer"},
                    "text": {"type": "string"},
                    "note": {"type": "string"},
                },
                "required": ["unit_id", "text"],
            },
        }
    },
    "required": ["rewrites"],
}

UNIFY_PROMPT = """你是学术写作编辑。请把给定的段落改写为统一的**目标文风**。

铁律：
1. **不得改变原意，不得增删事实、数据、结论**；
2. 只调整表达：句长、人称、连接词、术语叫法、语气正式度、标点；
3. 术语以目标文风为准（例如统一用"神经网络"而不是"类神经网络"）；
4. 保留原文的信息密度，不要把一句话拆成三句凑长度；
5. 原文有 Markdown 记号（如 **加粗**）时保留。

只输出 JSON，rewrites 数组里每个元素对应一个输入段落，unit_id 必须原样返回。"""


async def unify_segments(
    segments: list[Segment],
    style_brief: str,
    provider: LLMProvider,
) -> dict:
    """分批改写段落，返回改写结果与统计。"""
    if not segments:
        return {"rewrites": [], "notes": []}

    semaphore = asyncio.Semaphore(UNIFY_CONCURRENCY)
    batches = [
        segments[index : index + UNIFY_BATCH]
        for index in range(0, len(segments), UNIFY_BATCH)
    ]

    async def run_batch(batch: list[Segment]) -> tuple[list[dict], str | None]:
        body = "\n\n".join(
            f"[#{segment.id}]\n{segment.text}" for segment in batch
        )
        messages = [
            ChatMessage("system", UNIFY_PROMPT),
            ChatMessage("user", f"目标文风：{style_brief}\n\n待改写段落：\n\n{body}"),
        ]
        async with semaphore:
            try:
                result = await provider.structured(
                    messages, UNIFY_SCHEMA, max_tokens=UNIFY_MAX_TOKENS
                )
            except LLMError as exc:
                logger.warning("改写批次失败: %s", exc)
                return [], str(exc)
        valid = {segment.id for segment in batch}
        rewrites = []
        for item in result.get("rewrites") or []:
            try:
                unit_id = int(item.get("unit_id"))
            except (TypeError, ValueError):
                continue
            text = str(item.get("text") or "").strip()
            if unit_id in valid and text:
                rewrites.append(
                    {"unit_id": unit_id, "text": text, "note": str(item.get("note") or "")[:200]}
                )
        return rewrites, None

    outcomes = await asyncio.gather(*(run_batch(batch) for batch in batches))
    rewrites: list[dict] = []
    notes: list[str] = []
    for items, error in outcomes:
        rewrites.extend(items)
        if error:
            notes.append(error)
    return {"rewrites": rewrites, "notes": notes}
