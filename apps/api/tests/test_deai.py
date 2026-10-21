"""去 AI 味（检测 + 定点改写）测试。"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.documents.deai import (
    analyze,
    conservation_check,
    entity_counter,
)
from app.services.documents.transitions import apply_deai

client = TestClient(app)

AI_ISH = (
    "值得注意的是，这种方法不是简单的阈值判断，而是基于概率的推断"
    "——它在小样本上更稳。核心是：鲁棒性。"
)
CLEAN = "上述样本稀缺导致的过拟合风险，说明常规监督训练难以直接适用。"


# ---------------- 检测 ----------------


def test_detects_contrast_structure() -> None:
    report = analyze("这不是简单的阈值判断，而是基于概率的推断。")
    codes = [item.code for item in report.issues]
    assert "contrast" in codes


def test_detects_contrast_variant() -> None:
    """DeepSeek 常用的「…而非…」也应被识别。"""
    report = analyze("本文以规则驱动为主，而非依赖大规模统计。")
    codes = [item.code for item in report.issues]
    assert "contrast_alt" in codes


def test_detects_dash_colon_and_zero_anaphora() -> None:
    report = analyze(AI_ISH)
    codes = {item.code for item in report.issues}
    assert {"contrast", "dash", "colon", "zero_anaphora"} <= codes
    assert report.score < 60


def test_clean_text_scores_full() -> None:
    report = analyze(CLEAN)
    assert report.issues == []
    assert report.score == 100


def test_anaphor_suppresses_zero_anaphora() -> None:
    # 有回指成分，属于正常衔接，不该报
    report = analyze("这些问题说明常规监督训练难以直接适用。")
    assert all(item.code != "zero_anaphora" for item in report.issues)


def test_empty_text() -> None:
    report = analyze("")
    assert report.score == 100 and report.issues == []


# ---------------- 信息守恒 ----------------


def test_conservation_rejects_lost_numbers() -> None:
    ok, problems = conservation_check("准确率 62.3%，提升 4.1 个百分点", "准确率显著提升")
    assert not ok
    assert any("62.3" in item for item in problems)


def test_conservation_rejects_strength_inflation() -> None:
    ok, problems = conservation_check("可能有提升", "一定提升")
    assert not ok
    assert any("判断强度" in item for item in problems)


def test_conservation_rejects_length_blowup() -> None:
    ok, problems = conservation_check("短句。", "这是一个被大幅扩写的很长的句子，长度远远超过原文。")
    assert not ok


def test_conservation_accepts_faithful_rewrite() -> None:
    ok, problems = conservation_check(
        "准确率 62.3%，提升 4.1 个百分点",
        "准确率为 62.3%，较基线提升 4.1 个百分点",
    )
    assert ok, problems


def test_entity_counter() -> None:
    assert entity_counter("62.3% 与 4.1 和 2026") == {"62.3": 1, "4.1": 1, "2026": 1}


# ---------------- 集成：批量去味 ----------------


class DeAIFakeProvider:
    """把命中的痕迹按规则改掉，模拟真实模型的行为。"""

    name = "fake"
    model = "fake-model"

    def __init__(self, keep_numbers: bool = True) -> None:
        self.keep_numbers = keep_numbers
        self.calls = 0

    async def structured(self, messages, schema, **kwargs):  # noqa: ANN001, ANN003
        self.calls += 1
        text = messages[-1].content
        rewrites = []
        for block in text.split("[id=")[1:]:
            option_id, _, rest = block.partition("]")
            original = rest.split("原文：", 1)[-1].strip()
            fixed = (
                original.replace("值得注意的是，", "上述分析表明，")
                .replace("——", "。")
                .replace("核心是：", "")
                .replace("不是简单的阈值判断，而是基于概率的推断", "基于概率的推断")
            )
            if not self.keep_numbers:
                fixed = "改写后没有任何数字"
            rewrites.append({"id": option_id.strip(), "text": fixed})
        return {"rewrites": rewrites}


def _boundary(text: str) -> dict:
    return {
        "id": "b1",
        "options": [{"id": "b1-o1", "label": "简洁承接", "text": text}],
    }


@pytest.mark.asyncio
async def test_apply_deai_rewrites_and_records() -> None:
    boundaries = [_boundary(AI_ISH)]
    await apply_deai(boundaries, DeAIFakeProvider())
    option = boundaries[0]["options"][0]
    info = option["deai"]
    assert info["applied"] is True
    assert info["after_score"] > info["before_score"]
    assert info["original"] == AI_ISH
    assert "值得注意的是" not in option["text"]


@pytest.mark.asyncio
async def test_apply_deai_rejects_on_conservation_failure() -> None:
    boundaries = [_boundary("准确率 62.3%，不是简单的阈值判断，而是概率推断。")]
    await apply_deai(boundaries, DeAIFakeProvider(keep_numbers=False))
    option = boundaries[0]["options"][0]
    info = option["deai"]
    assert info["applied"] is False
    assert info["rejected"]
    assert "62.3%" in option["text"]


@pytest.mark.asyncio
async def test_apply_deai_skips_clean_text() -> None:
    boundaries = [_boundary(CLEAN)]
    provider = DeAIFakeProvider()
    await apply_deai(boundaries, provider)
    option = boundaries[0]["options"][0]
    assert option["deai"]["issues"] == []
    assert provider.calls == 0


def test_option_schema_exposes_deai() -> None:
    spec = client.get("/openapi.json").json()["components"]["schemas"]["TransitionOption"]
    assert "deai" in spec["properties"]
