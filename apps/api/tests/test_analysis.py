"""单文档 AI 分析测试：本地特征、JSON 抽取、接口编排（LLM 全部打桩）。"""


import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import analysis as analysis_endpoint
from app.main import app
from app.services.documents import parse_document
from app.services.documents.segmentation import (
    describe_layout_facts,
    extract_layout_facts,
    extract_style_features,
    sample_segments,
    segment_document,
)
from app.services.llm.openai_compatible import extract_json_object

client = TestClient(app)

DOC = """# 一、研究背景

随着深度学习的发展，卷积神经网络已经成为图像分类任务中的主流方法，并在多个公开数据集上取得了显著进展。

我们其实试了几种办法，感觉都差不多，数据集挺小的，跑起来特别快。

# 二、实验设置

本文采用标准的划分方式，将数据分为训练集与测试集两部分，以保证评估结果的可靠性。

所以最后就选了最简单的那个方案，效果还行。
"""


# ---------------- 本地特征 ----------------


def test_style_features_capture_tone() -> None:
    formal = extract_style_features(
        "本文采用卷积神经网络作为基础模型，并在多个公开数据集上验证了其有效性。"
    )
    casual = extract_style_features("我们试了几种办法吧，感觉还行，挺快的。")
    assert formal["avg_sentence"] > casual["avg_sentence"]
    assert casual["colloquial"] > formal["colloquial"]
    assert formal["first_person"] >= 1


def test_segmentation_skips_short_blocks() -> None:
    doc = parse_document("a.md", DOC.encode("utf-8"))
    segments = segment_document(doc)
    assert len(segments) == 4
    assert all(segment.chars >= 20 for segment in segments)
    assert segments[0].section == "研究背景"


def test_sampling_is_even_and_bounded() -> None:
    doc = parse_document("a.md", DOC.encode("utf-8"))
    segments = segment_document(doc)
    assert sample_segments(segments, 2) == [segments[0], segments[2]]
    assert len(sample_segments(segments, 100)) == len(segments)


def test_layout_facts_detect_numbering() -> None:
    doc = parse_document("a.md", DOC.encode("utf-8"))
    facts = extract_layout_facts(doc)
    assert facts["headings"] == 2
    assert facts["max_level"] == 1
    assert facts["paragraphs"] == 4
    assert facts["levels"][0]["styles"]["chinese_enum"] == 2
    assert "第 1 级标题" in describe_layout_facts(facts)


# ---------------- JSON 抽取 ----------------


def test_extract_json_plain() -> None:
    assert extract_json_object('{"a": 1}') == {"a": 1}


def test_extract_json_from_fence() -> None:
    assert extract_json_object('好的，结果如下：\n```json\n{"a": 1}\n```\n') == {"a": 1}


def test_extract_json_from_prose() -> None:
    assert extract_json_object('前面有废话 {"a": [1, 2]} 后面有废话') == {"a": [1, 2]}


def test_extract_json_returns_none_on_garbage() -> None:
    assert extract_json_object("") is None
    assert extract_json_object("完全没有 JSON") is None


# ---------------- 接口（LLM 打桩） ----------------


class FakeProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    async def structured(self, messages, schema, **kwargs):  # noqa: ANN001, ANN003
        self.calls += 1
        if self.fail:
            from app.services.llm import LLMError

            raise LLMError("打桩失败")
        required = schema.get("required", [])
        if "assignments" in required:
            return {
                "heterogeneity": "high",
                "conclusion": "两段文风差异明显。",
                "groups": [
                    {"id": "G1", "label": "学术书面", "features": ["句长较长"]},
                    {"id": "G2", "label": "口语随性", "features": ["句长短"]},
                ],
                "assignments": [
                    {"unit_id": 1, "group_id": "G1", "confidence": 0.9, "reason": "长句"},
                    {"unit_id": 3, "group_id": "G1", "confidence": 0.8, "reason": "长句"},
                    {"unit_id": 2, "group_id": "G2", "confidence": 0.85, "reason": "口语"},
                    {"unit_id": 4, "group_id": "G2", "confidence": 0.7, "reason": "口语"},
                ],
            }
        if "conventions" in required:
            return {
                "summary": "版式基本一致。",
                "conventions": [
                    {
                        "aspect": "标题层级",
                        "observation": "只有一级标题",
                        "consistent": True,
                        "suggestion": "建议补充二级标题",
                    }
                ],
            }
        if "canonical_style" in required:
            return {
                "canonical_style": "统一为学术书面语。",
                "issues": [
                    {
                        "type": "tone",
                        "title": "口语化",
                        "detail": "存在口语表达",
                        "examples": ["感觉还行"],
                        "suggestion": "改为客观陈述",
                    }
                ],
                "plan": ["统一人称", "调整句长"],
            }
        return {
            "rewrites": [
                {"unit_id": 2, "text": "实验采用了较为简洁的实现方案。", "note": "去口语化"},
                {"unit_id": 4, "text": "最终选用结构最简单的方案。", "note": "去口语化"},
            ]
        }


@pytest.fixture
def fake_provider(monkeypatch: pytest.MonkeyPatch) -> FakeProvider:
    provider = FakeProvider()
    monkeypatch.setattr(analysis_endpoint, "get_llm_provider", lambda: provider)
    return provider


def test_analysis_single_endpoint(fake_provider: FakeProvider) -> None:
    response = client.post(
        "/api/v1/analysis/single",
        files={"file": ("a.md", DOC.encode("utf-8"), "text/markdown")},
        data={"title": "测试文档"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["stats"]["units_total"] == 4
    assert body["authorship"]["heterogeneity"] == "high"
    assert len(body["authorship"]["groups"]) == 2
    assert body["authorship"]["groups"][0]["units"] == 2
    assert body["style"]["issues"][0]["type"] == "tone"
    assert body["layout"]["facts"]["headings"] == 2
    assert len(body["segments"]) == 4
    assert fake_provider.calls == 3


def test_analysis_single_rejects_unsupported(monkeypatch: pytest.MonkeyPatch) -> None:
    response = client.post(
        "/api/v1/analysis/single",
        files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 422


def test_analysis_single_surfaces_llm_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(analysis_endpoint, "get_llm_provider", lambda: FakeProvider(fail=True))
    response = client.post(
        "/api/v1/analysis/single",
        files={"file": ("a.md", DOC.encode("utf-8"), "text/markdown")},
    )
    assert response.status_code == 502
    assert "打桩失败" in response.text


def test_unify_endpoint(fake_provider: FakeProvider) -> None:
    payload = {
        "title": "归并稿",
        "style_brief": "统一为学术书面语",
        "segments": [
            {"id": 1, "section": "研究背景", "text": "这是第一段。", "group_id": "G1"},
            {"id": 2, "section": "研究背景", "text": "我们试了几种办法吧。", "group_id": "G2"},
        ],
    }
    response = client.post("/api/v1/analysis/unify", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["rewritten"] >= 1
    assert body["markdown"].startswith("# 归并稿")
    assert "## 研究背景" in body["markdown"]


def test_openapi_exposes_analysis_routes() -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/analysis/single" in paths
    assert "/api/v1/analysis/unify" in paths
