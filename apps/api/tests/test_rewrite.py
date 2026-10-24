"""逐段风格统一（F4）测试。"""

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import analysis as analysis_endpoint
from app.main import app
from app.services.documents import rewrite as service

client = TestClient(app)

MD = """# 标题

我们觉得吧，这个框架挺适合小样本场景的。

本文采用元学习框架，构建了基于任务采样的训练流程。
"""


class FakeProvider:
    name = "fake"
    model = "fake-model"

    async def structured(self, messages, schema, **kwargs):  # noqa: ANN001, ANN003
        return {
            "rewrites": [
                {"id": 1, "rewritten": "该框架较为适合小样本场景。", "changed": True, "reason": "去口语"},
                {
                    "id": 2,
                    "rewritten": "本文采用元学习框架，构建了基于任务采样的训练流程。",
                    "changed": False,
                    "reason": "",
                },
            ]
        }


def test_split_paragraphs_skips_headings() -> None:
    paragraphs = service.split_paragraphs(MD)
    assert len(paragraphs) == 2
    assert all("#" not in item["text"] for item in paragraphs)


@pytest.mark.asyncio
async def test_rewrite_diff_marks_changes() -> None:
    segments = await service.rewrite_diff(MD, FakeProvider())
    assert len(segments) == 2
    assert segments[0]["changed"] is True
    assert segments[0]["rewritten"] == "该框架较为适合小样本场景。"
    assert segments[1]["changed"] is False


@pytest.mark.asyncio
async def test_rewrite_diff_ignores_false_positive_changed() -> None:
    class SameProvider(FakeProvider):
        async def structured(self, messages, schema, **kwargs):  # noqa: ANN001, ANN003
            return {
                "rewrites": [
                    {"id": 1, "rewritten": "我们觉得吧，这个框架挺适合小样本场景的。", "changed": True}
                ]
            }

    segments = await service.rewrite_diff(MD, SameProvider())
    # 模型说改了但内容一致 -> 以实际比较为准
    assert segments[0]["changed"] is False


def test_assemble_applies_only_accepted() -> None:
    segments = [
        {"id": 1, "original": "我们觉得吧，这个框架挺适合小样本场景的。", "rewritten": "该框架较为适合小样本场景。", "changed": True},
        {"id": 2, "original": "本文采用元学习框架，构建了基于任务采样的训练流程。", "rewritten": "改后", "changed": True},
    ]
    out = service.assemble(MD, segments, {1})
    assert "该框架较为适合小样本场景。" in out
    assert "改后" not in out
    assert "# 标题" in out


def test_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_rewrite(markdown, provider):  # noqa: ANN001
        return [
            {
                "id": 1,
                "original": "原文",
                "rewritten": "改后",
                "changed": True,
                "reason": "去口语",
            }
        ]

    monkeypatch.setattr(analysis_endpoint, "rewrite_diff", fake_rewrite)
    response = client.post("/api/v1/analysis/rewrite", json={"markdown": MD})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["changed_count"] == 1
    assert body["segments"][0]["rewritten"] == "改后"

    assembled = client.post(
        "/api/v1/analysis/rewrite/assemble",
        json={"markdown": MD, "segments": body["segments"], "accepted": [1]},
    )
    assert assembled.status_code == 200
    assert assembled.json()["applied"] == 1


def test_openapi_exposes_rewrite_routes() -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/analysis/rewrite" in paths
    assert "/api/v1/analysis/rewrite/assemble" in paths
