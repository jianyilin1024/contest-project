"""数据助手（F6）测试。"""

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import data_assistant as data_endpoint
from app.main import app
from app.services.documents import data_assistant as service

client = TestClient(app)

TEXT = "本文方法在图像分类上效果显著，相比基线明显提升，且推理更快、参数更小。"


class FakeProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self, suggestions=None):
        self._suggestions = suggestions or []

    async def structured(self, messages, schema, **kwargs):  # noqa: ANN001, ANN003
        required = schema.get("required", [])
        if "gaps" in required:
            return {
                "gaps": [
                    {"description": "缺少准确率数值", "query": "图像分类 准确率"},
                ]
            }
        if "suggestions" in required:
            return {"suggestions": self._suggestions}
        return {}


@pytest.mark.asyncio
async def test_detect_gaps() -> None:
    gaps = await service.detect_gaps(TEXT, FakeProvider())
    assert len(gaps) == 1
    assert gaps[0]["query"] == "图像分类 准确率"


@pytest.mark.asyncio
async def test_extract_keeps_only_sourced_suggestions() -> None:
    results = [{"title": "来源A", "url": "https://example.com/a", "site_name": "站A", "date": "", "summary": "准确率 62.3%"}]
    provider = FakeProvider(
        suggestions=[
            {
                "value": "准确率 62.3%",
                "context": "可用于结果段",
                "source_title": "来源A",
                "source_url": "https://example.com/a#frag",
                "quote": "准确率 62.3%",
                "confidence": 0.9,
            },
            {
                "value": "编造的 99%",
                "source_title": "不存在的来源",
                "source_url": "https://fake.example.com/x",
                "quote": "无",
                "confidence": 0.9,
            },
        ]
    )
    gap = {"description": "缺少准确率", "query": "q"}
    out = await service.extract_suggestions(TEXT, gap, results, provider)
    # 只保留来源可追溯的那条
    assert len(out) == 1
    assert out[0]["value"] == "准确率 62.3%"
    assert out[0]["source_url"].startswith("https://example.com/a")


@pytest.mark.asyncio
async def test_assist_without_gaps() -> None:
    class NoGapProvider(FakeProvider):
        async def structured(self, messages, schema, **kwargs):  # noqa: ANN001, ANN003
            return {"gaps": []}

    out = await service.assist(TEXT, NoGapProvider())
    assert out["gaps"] == []
    assert out["suggestions"] == []


def test_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_assist(text, provider):  # noqa: ANN001
        return {
            "gaps": [{"description": "缺少准确率", "query": "q"}],
            "suggestions": [
                {
                    "value": "准确率 62.3%",
                    "context": "",
                    "source_title": "来源A",
                    "source_url": "https://example.com/a",
                    "quote": "准确率 62.3%",
                    "confidence": 0.9,
                    "gap": "缺少准确率",
                }
            ],
            "searched": 5,
        }

    monkeypatch.setattr(data_endpoint, "assist", fake_assist)
    response = client.post("/api/v1/data/assist", json={"text": TEXT})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["suggestions"][0]["source_url"] == "https://example.com/a"
    assert body["searched"] == 5


def test_endpoint_rejects_short_text() -> None:
    response = client.post("/api/v1/data/assist", json={"text": "太短"})
    assert response.status_code == 422


def test_openapi_exposes_data_route() -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/data/assist" in paths
