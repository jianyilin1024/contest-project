"""成稿 Agent 测试：规划与自检。"""

import pytest

from app.services.documents import agent
from app.services.llm import LLMError


class FakeProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self, result: dict | None = None, raises: bool = False) -> None:
        self._result = result or {}
        self._raises = raises

    async def structured(self, messages, schema, **kwargs):  # noqa: ANN001, ANN003
        if self._raises:
            raise LLMError("模拟失败")
        return self._result


@pytest.mark.asyncio
async def test_plan_from_model() -> None:
    provider = FakeProvider(
        {
            "need_transitions": True,
            "need_references": True,
            "reference_limit": 6,
            "transition_hint": "章节跳跃明显",
            "reasoning": "需要补过渡并检索文献",
        }
    )
    plan = await agent.make_plan(["绪论", "方法"], "正文", True, True, 8, provider)
    assert plan["need_transitions"] is True
    assert plan["need_references"] is True
    assert plan["reference_limit"] == 6
    assert plan["source"] == "model"


@pytest.mark.asyncio
async def test_plan_keeps_user_enabled_even_if_model_disagrees() -> None:
    """用户勾选的步骤不能因为模型判断而被取消。"""
    provider = FakeProvider(
        {"need_transitions": False, "need_references": False, "reasoning": "稿子太短，不必补"}
    )
    plan = await agent.make_plan(["绪论"], "正文", True, True, 8, provider)
    assert plan["need_transitions"] is True
    assert plan["need_references"] is True
    assert "已勾选" in plan["reasoning"]
    assert plan["model_suggests"] == {"transitions": False, "references": False}


@pytest.mark.asyncio
async def test_plan_respects_user_off() -> None:
    """用户关掉的步骤，模型说要也不能开。"""
    provider = FakeProvider(
        {"need_transitions": True, "need_references": True, "reasoning": "建议都做"}
    )
    plan = await agent.make_plan(["绪论"], "正文", False, True, 8, provider)
    assert plan["need_transitions"] is False
    assert plan["need_references"] is True


@pytest.mark.asyncio
async def test_plan_falls_back_on_error() -> None:
    provider = FakeProvider(raises=True)
    plan = await agent.make_plan(["绪论"], "正文", True, True, 8, provider)
    assert plan["source"] == "fallback"
    assert plan["need_transitions"] is True
    assert plan["need_references"] is True


@pytest.mark.asyncio
async def test_plan_skips_when_all_disabled() -> None:
    provider = FakeProvider({"need_transitions": True, "need_references": True, "reasoning": "x"})
    plan = await agent.make_plan(["绪论"], "正文", False, False, 8, provider)
    assert plan["source"] == "user"
    assert plan["need_transitions"] is False
    assert plan["need_references"] is False


MERGED = "# 合并稿\n\n## 1 绪论\n\n这是绪论内容。\n\n## 2 方法\n\n这是方法内容。\n"


def _plan(**kwargs) -> dict:
    base = {"need_transitions": False, "need_references": False, "reference_limit": 8, "reasoning": "t"}
    base.update(kwargs)
    return base


def test_verify_all_pass() -> None:
    final = MERGED
    checks = agent.verify(MERGED, final, _plan(), {}, {})
    assert all(item["ok"] for item in checks)
    assert {item["name"] for item in checks} >= {"正文未被截断", "章节结构完整", "无残留占位符"}


def test_verify_detects_truncation() -> None:
    final = MERGED[:20]
    checks = agent.verify(MERGED, final, _plan(), {}, {})
    truncated = next(item for item in checks if item["name"] == "正文未被截断")
    assert truncated["ok"] is False


def test_verify_detects_missing_references() -> None:
    checks = agent.verify(MERGED, MERGED, _plan(need_references=True), {}, {})
    refs = next(item for item in checks if item["name"] == "参考文献段完整")
    assert refs["ok"] is False
    assert "未生成" in refs["detail"]


def test_verify_accepts_references() -> None:
    final = MERGED + "\n## 参考文献\n\n[1] 某某. 书名[M]. 北京: 出版社, 2020.\n[2] 某某. 论文[J]. 期刊, 2021.\n"
    checks = agent.verify(MERGED, final, _plan(need_references=True), {}, {})
    refs = next(item for item in checks if item["name"] == "参考文献段完整")
    assert refs["ok"] is True
    assert "2 条" in refs["detail"]


def test_verify_detects_broken_numbering() -> None:
    final = MERGED + "\n## 参考文献\n\n[1] A.\n[3] C.\n"
    checks = agent.verify(MERGED, final, _plan(need_references=True), {}, {})
    refs = next(item for item in checks if item["name"] == "参考文献段完整")
    assert refs["ok"] is False
    assert "不连续" in refs["detail"]


def test_verify_detects_placeholder() -> None:
    final = MERGED + "\n正文里残留 {{待填写}}。\n"
    checks = agent.verify(MERGED, final, _plan(), {}, {})
    placeholder = next(item for item in checks if item["name"] == "无残留占位符")
    assert placeholder["ok"] is False


def test_verify_transition_expectation() -> None:
    checks = agent.verify(
        MERGED, MERGED, _plan(need_transitions=True), {"candidates": 2, "needed": 2, "applied": 0}, {}
    )
    transition = next(item for item in checks if item["name"] == "过渡段已插入")
    assert transition["ok"] is False
