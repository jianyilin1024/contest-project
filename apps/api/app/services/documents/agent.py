"""成稿 Agent：规划 → 执行 → 自检 → 修复。

为什么需要它：固定流水线只能"照做"，无法判断"这次该不该做、做完对不对"。
这一层补三件事：
1. 规划——读一眼合并后的文档，决定是否值得补过渡、需要多少文献；
2. 自检——用确定性规则检查产出（不是再问一次模型，避免模型自评自夸）；
3. 修复——自检不通过时定点重试，而不是整体重来。

设计取舍：自检全部用规则实现，成本为零且可解释；模型只负责"规划"这一步，
因为它需要理解内容，而规则判断不了。
"""

import logging
import re
from typing import Any

from app.services.llm import ChatMessage, LLMError, LLMProvider

logger = logging.getLogger(__name__)

PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "need_transitions": {"type": "boolean"},
        "transition_hint": {"type": "string"},
        "need_references": {"type": "boolean"},
        "reference_limit": {"type": "integer"},
        "reasoning": {"type": "string"},
    },
    "required": ["need_transitions", "need_references", "reasoning"],
}

PLAN_PROMPT = """你是成稿流程的规划者。根据下面这份合并后的文稿概况，决定接下来该做什么。

判断依据：
- 如果各章节主题跳跃明显、缺少承接句，就需要补过渡段；
- 如果正文出现了具体结论、方法或数据，但没有任何引用，就需要检索参考文献；
- 参考文献数量：综述型文稿可多（8–10 条），单一实验报告可少（4–6 条）。

只输出 JSON：
{"need_transitions": true/false, "transition_hint": "一句话说明理由",
 "need_references": true/false, "reference_limit": 8, "reasoning": "整体判断"}"""


def summarize(headings: list[str], text: str) -> str:
    """把文档压成一段概况，供规划使用。"""
    outline = " / ".join(item for item in headings[:10] if item) or "（无章节标题）"
    excerpt = re.sub(r"\s+", " ", text)[:700]
    return f"章节：{outline}\n\n正文摘录：{excerpt}"


async def make_plan(
    headings: list[str],
    text: str,
    want_transitions: bool,
    want_references: bool,
    reference_limit: int,
    provider: LLMProvider,
) -> dict:
    """模型规划；失败或用户已明确关闭时退回用户的原始选择。"""
    if not (want_transitions or want_references):
        return {
            "need_transitions": False,
            "need_references": False,
            "reference_limit": reference_limit,
            "transition_hint": "",
            "reasoning": "用户已关闭全部 AI 步骤",
            "source": "user",
        }

    messages = [
        ChatMessage("system", PLAN_PROMPT),
        ChatMessage("user", summarize(headings, text)),
    ]
    try:
        result = await provider.structured(messages, PLAN_SCHEMA, max_tokens=800)
    except LLMError as exc:
        logger.warning("规划失败，沿用用户选择: %s", exc)
        return {
            "need_transitions": want_transitions,
            "need_references": want_references,
            "reference_limit": reference_limit,
            "transition_hint": "",
            "reasoning": "规划失败，沿用用户选择",
            "source": "fallback",
        }

    # 分工：用户决定"做不做"，模型决定"怎么做"。
    # 用户勾选的步骤不会因为模型判断而被取消——否则勾选框就成了摆设。
    model_wants_transitions = bool(result.get("need_transitions"))
    model_wants_references = bool(result.get("need_references"))
    need_transitions = want_transitions
    need_references = want_references

    try:
        limit = int(result.get("reference_limit") or reference_limit)
    except (TypeError, ValueError):
        limit = reference_limit

    reasoning = str(result.get("reasoning") or "")[:200]
    advisories = []
    if want_transitions and not model_wants_transitions:
        advisories.append("Agent 判断本稿不必补过渡，但你已勾选，仍会执行")
    if want_references and not model_wants_references:
        advisories.append("Agent 判断本稿暂不需要文献，但你已勾选，仍会执行")
    if advisories:
        reasoning = "；".join(advisories) + ("。" + reasoning if reasoning else "")

    return {
        "need_transitions": need_transitions,
        "need_references": need_references,
        "reference_limit": max(3, min(limit, 20)),
        "transition_hint": str(result.get("transition_hint") or "")[:120],
        "reasoning": reasoning[:260],
        "model_suggests": {
            "transitions": model_wants_transitions,
            "references": model_wants_references,
        },
        "source": "model",
    }


def _count_sections(markdown: str) -> int:
    return len(re.findall(r"^#{1,3}\s+", markdown, flags=re.MULTILINE))


def _reference_numbers(markdown: str) -> list[int]:
    return [int(m) for m in re.findall(r"^\[(\d+)\]\s", markdown, flags=re.MULTILINE)]


def verify(
    merged: str,
    final: str,
    plan: dict,
    transition_info: dict,
    reference_info: dict,
) -> list[dict]:
    """确定性自检。返回 [{name, ok, detail}]。"""
    checks: list[dict] = []

    # 1. 字数不应缩水（改写类步骤有可能误删内容）
    merged_chars = max(1, len(merged))
    ratio = len(final) / merged_chars
    checks.append(
        {
            "name": "正文未被截断",
            "ok": ratio >= 0.9,
            "detail": f"成稿 {len(final)} 字 / 合并稿 {merged_chars} 字（{ratio:.0%}）",
        }
    )

    # 2. 章节数不应减少
    merged_sections = _count_sections(merged)
    final_sections = _count_sections(final)
    checks.append(
        {
            "name": "章节结构完整",
            "ok": final_sections >= merged_sections,
            "detail": f"合并稿 {merged_sections} 节 → 成稿 {final_sections} 节",
        }
    )

    # 3. 计划要补过渡，且确实识别到断层时，应当有插入
    if plan.get("need_transitions"):
        candidates = int(transition_info.get("candidates") or 0)
        needs = int(transition_info.get("needed") or 0)
        applied = int(transition_info.get("applied") or 0)
        if needs > 0:
            checks.append(
                {
                    "name": "过渡段已插入",
                    "ok": applied > 0,
                    "detail": f"识别 {candidates} 处，需补 {needs} 处，实际插入 {applied} 段",
                }
            )
        else:
            checks.append(
                {"name": "过渡段已检查", "ok": True, "detail": f"识别 {candidates} 处，均无需补写"}
            )

    # 4. 计划要文献时，参考文献段必须存在且编号连续
    if plan.get("need_references"):
        numbers = _reference_numbers(final)
        continuous = numbers == list(range(1, len(numbers) + 1))
        checks.append(
            {
                "name": "参考文献段完整",
                "ok": bool(numbers) and continuous,
                "detail": (
                    f"共 {len(numbers)} 条，编号连续" if numbers and continuous
                    else "未生成参考文献" if not numbers
                    else "编号不连续"
                ),
            }
        )

    # 5. 不应出现占位符或未替换的变量
    placeholder = re.search(r"\{\{[^}]+\}\}|\$\{[^}]+\}", final)
    checks.append(
        {
            "name": "无残留占位符",
            "ok": placeholder is None,
            "detail": "未发现" if placeholder is None else f"发现 {placeholder.group(0)[:20]}",
        }
    )

    del reference_info  # 目前未参与判定，保留参数便于后续扩展
    return checks
